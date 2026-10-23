import asyncio
import httpx
import pytest
from foxory import inference, research

async def test_ollama_ndjson_protocol_and_serialization(monkeypatch):
    active=0;maximum=0
    async def handler(request):
        nonlocal active,maximum
        active+=1;maximum=max(maximum,active)
        await asyncio.sleep(.02)
        active-=1
        return httpx.Response(200,content=b'{"message":{"content":"Local"}}\n{"done":true,"eval_count":1}\n')
    original=httpx.AsyncClient
    monkeypatch.setattr(inference.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handler),**kw))
    async def run():
        events=[e async for e in inference.stream('fixture',[{'role':'user','content':'hello'}])]
        assert events[0]['message']['content']=='Local' and events[-1]['eval_count']==1
    await asyncio.gather(run(),run(),run())
    assert maximum==1

async def test_searx_adapter_metadata_dedup_and_unsafe_urls(monkeypatch):
    def handler(request):
        assert request.url.params['format']=='json'
        return httpx.Response(200,json={'results':[
            {'url':'javascript:alert(1)','title':'Unsafe'},
            {'url':'https://example.test/a','title':'Actual returned title','content':'Search snippet','publishedDate':'2026-01-01'},
            {'url':'https://example.test/a','title':'Duplicate'},
            {'url':'https://user:password@example.test/b','title':'Credential URL'},
            {'url':'https://example.test/c','title':'Second source'},
        ]})
    original=httpx.AsyncClient
    monkeypatch.setattr(research.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handler),**kw))
    monkeypatch.setattr(research,'SEARXNG_URL','http://private-search.test')
    result=await research.search('question')
    assert len(result)==2 and [s['id'] for s in result]==[1,2]
    assert result[0]['title']=='Actual returned title' and result[0]['published']=='2026-01-01'
    assert result[0]['evidence_type']=='search_snippet'
