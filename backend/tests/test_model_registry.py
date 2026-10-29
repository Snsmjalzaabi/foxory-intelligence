"""Real metadata protocol adapter with deterministic HTTP boundary fixtures."""
import asyncio
import json

import httpx
import pytest

from foxory import inference, model_registry as registry, knowledge


def endpoint(monkeypatch, handler):
    original=httpx.AsyncClient
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kwargs:original(transport=httpx.MockTransport(handler),**kwargs))


async def test_explicit_capabilities_distinguish_embedding_completion_and_unknown(monkeypatch):
    requests=[]
    def handler(request):
        name=json.loads(request.content)['model'];requests.append(name)
        return httpx.Response(200,json={'capabilities':{'embed':['embedding'],'chat':['completion'],'old':[]}[name]})
    endpoint(monkeypatch,handler)
    models=await registry.catalog([{'name':n,'size':100,'details':{'quantization_level':'test'}} for n in ['embed','chat','old']],endpoint='http://local')
    assert models[0]['completion_supported'] is False and models[0]['embedding_supported'] is True
    assert models[1]['completion_supported'] is True and models[1]['embedding_supported'] is False
    assert models[2]['completion_supported'] is None and models[2]['capability_status']=='unknown'
    assert models[1]['details']['quantization_level']=='test'
    await registry.inspect('chat',endpoint='http://local')
    assert requests.count('chat')==1
    await registry.inspect('chat',endpoint='http://local',refresh=True)
    assert requests.count('chat')==2


async def test_tag_digest_changes_invalidate_metadata_and_cache_is_bounded(monkeypatch):
    calls=0
    def handler(request):
        nonlocal calls;calls+=1
        return httpx.Response(200,json={'capabilities':['embedding'] if calls>1 else ['completion']})
    endpoint(monkeypatch,handler)
    first=await registry.inspect('changed',endpoint='http://local',digest='old')
    changed=await registry.inspect('changed',endpoint='http://local',digest='new')
    assert first['completion_supported'] and not changed['completion_supported']
    for n in range(130):await registry.inspect(str(n),endpoint='http://local')
    assert len(registry._cache)==128


async def test_catalog_deadline_cancels_metadata_workers_without_claiming_support(monkeypatch):
    active=0;peak=0
    async def handler(request):
        nonlocal active,peak
        active+=1;peak=max(peak,active)
        try:await asyncio.Event().wait()
        finally:active-=1
    endpoint(monkeypatch,handler)
    monkeypatch.setattr(registry,'CATALOG_SECONDS',.03)
    models=await registry.catalog([{'name':str(n)} for n in range(100)],endpoint='http://local')
    assert active==0 and peak<=4 and len(models)==100
    assert all(m['completion_supported'] is None for m in models)


@pytest.mark.parametrize('data',[{}, {'capabilities':[123]}, {'capabilities':[]}, {'capabilities':'completion'}])
async def test_malformed_or_absent_capabilities_remain_unknown(monkeypatch,data):
    endpoint(monkeypatch,lambda _:httpx.Response(200,json=data))
    assert (await registry.inspect('unknown',endpoint='http://local'))['capability_status']=='unknown'


async def test_oversized_metadata_is_declined(monkeypatch):
    endpoint(monkeypatch,lambda _:httpx.Response(200,content=b'x'*2_000_001))
    assert (await registry.inspect('large',endpoint='http://local'))['capability_status']=='unknown'


async def test_known_unsupported_models_never_reach_generation_or_embedding(monkeypatch):
    paths=[]
    def handler(request):
        paths.append(request.url.path)
        model=json.loads(request.content)['model']
        return httpx.Response(200,json={'capabilities':['embedding'] if model=='embed' else ['completion']})
    endpoint(monkeypatch,handler)
    with pytest.raises(registry.CapabilityError,match='completion'):
        _=[event async for event in inference.stream('embed',[{'role':'user','content':'Hello'}])]
    with pytest.raises(registry.CapabilityError,match='embedding'):
        await knowledge.embed('chat',['text'])
    assert '/api/chat' not in paths and '/api/embed' not in paths


async def test_http_chat_reports_incompatible_model_without_private_server_errors(client,monkeypatch):
    async def require(*args,**kwargs):raise registry.CapabilityError('Choose a compatible local model in Settings.')
    monkeypatch.setattr(registry,'require',require)
    row=(await client.post('/api/records/conversation',json={'title':'Wrong model'})).json()
    response=await client.post(f'/api/conversations/{row["id"]}/chat',json={'content':'Hello','model':'embed'})
    assert 'event: error' in response.text and 'Choose a compatible local model' in response.text
