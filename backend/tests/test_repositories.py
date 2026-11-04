import base64,hashlib,json
import httpx
import pytest
from pathlib import Path
from foxory import repositories
from foxory.db import Session,Record
from foxory.config import DATA
from foxory.scope import system_scope

COMMIT='a'*40
FILES={'README.md':b'# Example\nA local app with documented architecture.','src/main.py':b'print("local source only")\n','.env':b'SECRET=not-imported','assets/image.png':b'fake'}
def sha(raw):return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()

@pytest.fixture
def github_mock(monkeypatch):
    calls=[]
    def handle(request):
        calls.append(str(request.url));path=request.url.path
        if path=='/repos/owner/example':return httpx.Response(200,json={'default_branch':'main','description':'Example repo','license':{'spdx_id':'Apache-2.0'}})
        if '/commits/' in path:return httpx.Response(200,json={'sha':COMMIT})
        if '/git/trees/' in path:return httpx.Response(200,json={'truncated':False,'tree':[{'path':p,'type':'blob','size':len(raw),'sha':sha(raw)} for p,raw in FILES.items()]})
        for p,raw in FILES.items():
            if path.endswith('/git/blobs/'+sha(raw)):return httpx.Response(200,json={'encoding':'base64','content':base64.b64encode(raw).decode()})
        return httpx.Response(404)
    real=httpx.AsyncClient
    monkeypatch.setattr(repositories.httpx,'AsyncClient',lambda **kw:real(transport=httpx.MockTransport(handle),timeout=10))
    return calls

async def test_snapshot_import_pins_bytes_reuses_documents_and_excludes_secrets(client,github_mock):
    url='git@github.com:owner/example.git'
    preview=await client.post('/api/repositories/preview',json={'url':url});assert preview.status_code==200,preview.text
    assert {x['path'] for x in preview.json()['eligible_files']}=={'README.md','src/main.py'}
    body={'url':url,'commit':COMMIT,'paths':['README.md','src/main.py']}
    result=await client.post('/api/repositories/import',json=body);assert result.status_code==201,result.text
    row=result.json();assert row['data']['commit']==COMMIT
    ids=row['data']['document_ids'];assert len(ids)==2
    again=await client.post('/api/repositories/import',json=body)
    assert again.json()['id']==row['id'] and again.json()['data']['document_ids']==ids
    file=await client.get('/api/repositories/'+row['id']+'/files/'+ids[0]);assert '# Example' in file.json()['data']['text']
    assert (DATA/'uploads'/ids[0]).read_bytes()==FILES['README.md']
    sources=await client.get('/api/documents/search',params={'q':'architecture'});assert sources.status_code==200
    assert all(url.startswith('https://api.github.com/repos/owner/example') for url in github_mock)
    assert (await client.post('/api/repositories/import',json={**body,'paths':['.env']})).status_code==422
    assert (await client.post('/api/repositories/import',json={**body,'paths':['README.md','README.md']})).status_code==422

async def test_repository_addresses_and_source_paths_are_constrained(client,github_mock):
    for url in ['http://127.0.0.1/x','https://evil.example/owner/repo','git@evil.example:owner/repo','https://github.com/owner/repo?token=secret','https://github.com/../repo']:
        assert (await client.post('/api/repositories/preview',json={'url':url})).status_code==422
    assert not repositories.eligible('../outside.py',10)
    assert not repositories.eligible('id_rsa',10)
    assert not repositories.eligible('node_modules/code.js',10)
    assert not repositories.eligible('large.py',100001)

async def test_repository_snapshots_are_workspace_scoped(client,github_mock):
    row=(await client.post('/api/repositories/import',json={'url':'https://github.com/owner/example','commit':COMMIT,'paths':['README.md']})).json()
    with system_scope(),Session() as s:
        record=s.get(Record,row['id']);record.workspace='another';s.commit()
    assert (await client.get('/api/repositories')).json()==[]
    assert (await client.get('/api/repositories/'+row['id'])).status_code==404
    assert (await client.get('/api/repositories/'+row['id']+'/files/'+row['data']['document_ids'][0])).status_code==404

async def test_selected_sources_reach_council_even_without_query_keyword_overlap(client,github_mock):
    row=(await client.post('/api/repositories/import',json={'url':'https://github.com/owner/example','commit':COMMIT,'paths':['README.md','src/main.py']})).json()
    from foxory.knowledge import document_evidence
    found=await document_evidence('git@github.com:owner/example.git',row['data']['document_ids'])
    assert {x['document_id'] for x in found}==set(row['data']['document_ids'])
    assert all(x['text'] and x['content_hash'] for x in found)

def test_council_budget_preserves_valid_json_and_every_model(monkeypatch):
    from foxory.intelligence import council_prompt
    from foxory import inference
    monkeypatch.setattr(inference,'background_limits',lambda:(4096,1024))
    data={'prompt':'Review the supplied source excerpts','sources':[{'id':i+1,'title':'source'+str(i),'text':'source content '*1000} for i in range(6)]}
    analyses=[{'model':'model-'+str(i),'content':'analysis '*2000} for i in range(4)]
    prompt=council_prompt(data,'Compare evidence',analyses,'comparison '*2000)
    assert len(prompt)<=6144
    payload=json.loads(prompt[prompt.index('{'):])
    assert len(payload['sources'])==6
    assert {x['model'] for x in payload['independent_analyses']}=={'model-0','model-1','model-2','model-3'}
    assert all(x['text'] for x in payload['sources'])
    assert data['warnings'] and len(data['model_source_coverage'])==6

async def test_import_rejects_blob_bytes_that_do_not_match_git_hash(client,github_mock,monkeypatch):
    previous=repositories.github
    async def corrupt(client,path):
        value=await previous(client,path)
        if '/git/blobs/' in path:value['content']=base64.b64encode(b'wrong bytes').decode()
        return value
    monkeypatch.setattr(repositories,'github',corrupt)
    response=await client.post('/api/repositories/import',json={'url':'https://github.com/owner/example','commit':COMMIT,'paths':['README.md']})
    assert response.status_code==422
    assert (await client.get('/api/repositories')).json()==[]

def test_grouped_citations_are_normalized_and_invalid_ids_removed():
    from foxory.research import validate_citations
    assert validate_citations('Stack [1, 2, 99]',[{'id':1},{'id':2}])=='Stack [1] [2] [unverified reference removed]'
