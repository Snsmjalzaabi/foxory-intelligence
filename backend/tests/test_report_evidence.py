import json
from foxory.db import Session,Record
from foxory.intelligence import council_step
from foxory.evidence_policy import MODEL_ONLY_NOTICE

async def test_repository_address_is_not_accepted_as_council_evidence(client):
    for prompt in ['git@github.com:Snsmjalzaabi/foxory-intelligence.git','Audit https://github.com/example/project']:
        response=await client.post('/api/jobs',json={'type':'council','prompt':prompt,'models':['a','b'],'idempotency_key':'source-gate-123'})
        assert response.status_code==422
        assert 'does not fetch or clone' in response.text
    response=await client.post('/api/jobs',json={'type':'council','prompt':'Compare general project planning approaches','models':['a','b'],'idempotency_key':'general-ideas-123'})
    assert response.status_code==201

async def test_queued_legacy_repository_review_stops_without_model_calls(monkeypatch):
    async def forbidden(*args,**kwargs):raise AssertionError('Should not call a model without source text')
    monkeypatch.setattr('foxory.intelligence.ask',forbidden)
    result=await council_step({'type':'council','prompt':'git@github.com:owner/project.git','models':['a','b'],'step':0})
    assert result['status']=='failed' and result['stage']=='needs_sources'
    assert 'source text is required' in result['error']

async def test_model_only_council_has_explicit_notice(monkeypatch):
    async def answer(*args,**kwargs):return 'General planning suggestions.'
    monkeypatch.setattr('foxory.intelligence.ask',answer)
    result=await council_step({'type':'council','prompt':'Brainstorm ways to plan my week','models':['a','b'],'step':3})
    assert result['status']=='completed' and result['result'].startswith(MODEL_ONLY_NOTICE)
    assert result['source_status']=='no_sources'

async def test_legacy_unverified_repository_exports_blocked_and_general_exports_labeled(client):
    with Session() as s:
        repo=Record(kind='job',title='Repository',payload=json.dumps({'type':'council','prompt':'git@github.com:owner/project.git','result':'Invented repository audit','sources':[]}))
        general=Record(kind='job',title='Ideas',payload=json.dumps({'type':'council','prompt':'General ideas','result':'A thought','sources':[]}))
        s.add_all([repo,general]);s.commit();repo_id=repo.id;general_id=general.id
    for fmt in ['md','pdf','docx','xlsx']:assert (await client.get('/api/jobs/'+repo_id+'/export?format='+fmt)).status_code==409
    assert MODEL_ONLY_NOTICE in (await client.get('/api/jobs/'+general_id+'/export')).text

def test_pdf_export_renders_heading_and_bold_markup():
    from foxory.reports import report
    from pypdf import PdfReader
    import io
    raw,mime=report('Export formatting check','### Findings\n\n**Evidence** is required.\n- One source',[], 'pdf')
    text='\n'.join(page.extract_text() for page in PdfReader(io.BytesIO(raw)).pages)
    assert '###' not in text and '**' not in text and 'Findings' in text

async def test_source_council_without_references_returns_saved_evidence(monkeypatch):
    import hashlib
    text='This source records a Python backend and React frontend.'
    async def unsupported(*args,**kwargs):return 'There are 900 contributors and every test passed.'
    monkeypatch.setattr('foxory.intelligence.ask',unsupported)
    source={'id':1,'title':'Actual source','text':text,'content_hash':hashlib.sha256(text.encode()).hexdigest(),'evidence_type':'document_excerpt','url':'/api/documents/test/download'}
    result=await council_step({'type':'council','prompt':'Review the supplied source','models':['a','b'],'step':3,'sources':[source]})
    assert result['evidence_mode']=='extractive_fallback'
    assert '900 contributors' not in result['result']
    assert text in result['result'] and result['citation_verification']['valid']
