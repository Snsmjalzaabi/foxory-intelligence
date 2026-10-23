"""Core chat grounding uses real HTTP/state with deterministic model/web fixtures."""
import hashlib

import pytest

from foxory import main
from foxory.research import grounded_answer


def source():
    text = 'Retrieval augments generation with relevant saved evidence. Source review is still necessary.'
    return {'id':1, 'text':text, 'content_hash':hashlib.sha256(text.encode()).hexdigest(),
            'url':'https://example.org/retrieval', 'title':'Retrieved evidence', 'evidence_type':'retrieved_page'}


@pytest.mark.parametrize('answer', ['Uncited unsupported claim.', 'Unsupported claim [999].',
                                  '[N] Unsupported claim https://invented.example/fake'])
def test_uncited_prose_is_replaced_with_actual_saved_evidence(answer):
    result, verification, mode = grounded_answer(answer, [source()], 'What is retrieval?')
    assert mode == 'extractive_fallback' and verification['valid']
    assert 'Extractive evidence report' in result and 'Retrieval augments generation' in result
    assert '[1]' in result and 'Unsupported claim' not in result and 'invented.example' not in result


def test_valid_citations_preserved_without_claiming_factual_verification():
    result, verification, mode = grounded_answer('Saved evidence is useful [1].', [source()], 'Evidence?')
    assert result == 'Saved evidence is useful [1].' and mode == 'model_synthesis'
    assert verification['valid'] and 'claim correctness requires review' in verification['citations'][0]['meaning']


def test_missing_or_tampered_evidence_cannot_create_grounded_fallback():
    for sources in [[], [{**source(), 'content_hash':'forged'}], [{**source(), 'evidence_type':'search_snippet'}]]:
        result, verification, mode = grounded_answer('Unsupported claim', sources, 'Question')
        assert mode == 'no_evidence' and not verification['valid']
        assert 'No usable retrieved evidence' in result and 'Unsupported claim' not in result


async def test_search_chat_releases_only_checked_answer_and_persists_sources(client, monkeypatch):
    async def gather(*args, **kwargs): return [source()], []
    async def stream(*args, **kwargs):
        yield {'message':{'content':'[N] Unsupported definition from a small model.'}, 'done':True}
    monkeypatch.setattr(main, 'gather', gather)
    monkeypatch.setattr(main.inference, 'stream', stream)
    row = (await client.post('/api/records/conversation',json={'title':'Grounding regression'})).json()
    response = await client.post(f'/api/conversations/{row["id"]}/chat',json={
        'content':'What is retrieval?', 'model':'fixture', 'mode':'research'})
    assert response.status_code == 200 and 'event: done' in response.text
    assert 'Unsupported definition' not in response.text
    assert 'Extractive evidence report' in response.text
    saved = (await client.get(f'/api/conversations/{row["id"]}/messages')).json()[-1]
    assert saved['metadata']['evidence_mode'] == 'extractive_fallback'
    assert saved['metadata']['citation_verification']['valid']
    assert saved['metadata']['sources'][0]['content_hash'] == source()['content_hash']


async def test_document_chat_without_evidence_never_calls_model(client, monkeypatch):
    async def empty(*args, **kwargs): return []
    async def forbidden(*args, **kwargs):
        raise AssertionError('No evidence should not invoke inference')
        yield
    monkeypatch.setattr(main, 'document_evidence', empty)
    monkeypatch.setattr(main.inference, 'stream', forbidden)
    row = (await client.post('/api/records/conversation',json={'title':'No documents'})).json()
    response = await client.post(f'/api/conversations/{row["id"]}/chat',json={
        'content':'Summarize the uploaded evidence.', 'model':'fixture', 'mode':'documents'})
    assert 'event: error' not in response.text
    assert 'No usable retrieved evidence' in response.text
    saved = (await client.get(f'/api/conversations/{row["id"]}/messages')).json()[-1]
    assert saved['metadata']['evidence_mode'] == 'no_evidence'
    assert not saved['metadata']['citation_verification']['valid']


async def test_explicit_chat_output_budget_is_bounded_and_reaches_local_inference(client, monkeypatch):
    async def stream(*args, **kwargs):
        assert kwargs['max_output'] == 128
        yield {'message':{'content':'Local response'}, 'done':True}
    monkeypatch.setattr(main.inference, 'stream', stream)
    row = (await client.post('/api/records/conversation',json={'title':'Bounded output'})).json()
    path = f'/api/conversations/{row["id"]}/chat'
    body = {'content':'Reply briefly.', 'model':'fixture', 'max_output':128}
    response = await client.post(path,json=body)
    assert 'event: error' not in response.text and 'Local response' in response.text
    for limit in [0, 31, 2049]:
        assert (await client.post(path,json={**body,'max_output':limit})).status_code == 422
