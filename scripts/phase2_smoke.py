"""Real Phase 2 acceptance smoke against an isolated LOCAL test Compose project.

Never point this at an owner's configured workspace. Creates a disposable admin,
workspace, documents and jobs in the explicit verification installation.
"""
import hashlib
import json
import os
import secrets
import time
from pathlib import Path
import httpx

base=os.getenv('FOXORY_PHASE2_TEST_URL','http://127.0.0.1:8003')
if base not in {'http://127.0.0.1:8003','http://localhost:8003'}:raise SystemExit('This smoke is restricted to the disposable loopback verification port 8003')
root=Path(__file__).resolve().parents[1]
config=dict(line.split('=',1) for line in (root/'.env').read_text().splitlines() if line and not line.startswith('#') and '=' in line)
c=httpx.Client(base_url=base+'/api',trust_env=False,timeout=120)

def call(method,path,**kwargs):
    response=c.request(method,path,**kwargs)
    if response.status_code>=400:raise RuntimeError(f'{method} {path}: HTTP {response.status_code}: {response.text[:200]}')
    return response.json() if response.headers.get('content-type','').startswith('application/json') and response.content else response

def finish(job):
    deadline=time.monotonic()+600
    while time.monotonic()<deadline:
        rows=call('GET','/records/job');data=next(r['data'] for r in rows if r['id']==job['id'])
        if data['status']=='failed':raise AssertionError(data.get('error'))
        if data['status']=='completed':return data
        time.sleep(1)
    raise AssertionError('Acceptance job timed out')

def job(type,prompt,models,**extra):return call('POST','/jobs',json={'type':type,'prompt':prompt,'models':models,'idempotency_key':secrets.token_hex(16),**extra})

if __name__=='__main__':
    for _ in range(60):
        try:
            if c.get('/health',timeout=3).status_code==200:break
        except httpx.HTTPError:pass
        time.sleep(1)
    else:raise SystemExit('Verification API did not become healthy')
    password=secrets.token_urlsafe(32)
    status=call('GET','/auth/status')
    credential_file=Path('/tmp/foxory-phase2-disposable-credentials.json')
    if status['setup_required']:
        setup=call('POST','/auth/setup',json={'username':'phase2-verification-admin','password':password,'bootstrap_token':config['FOXORY_TOKEN']})
        fd=os.open(credential_file,os.O_WRONLY|os.O_CREAT|os.O_TRUNC|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'w') as f:json.dump({'username':'phase2-verification-admin','password':password},f)
    else:
        if not credential_file.exists():raise SystemExit('Refusing an existing configured installation without this test run credentials')
        credentials=json.loads(credential_file.read_text())
        setup=call('POST','/auth/login',json=credentials)
    c.headers['X-CSRF-Token']=setup['csrf']
    initial=call('GET','/auth/me');assert initial['role']=='admin'
    first=call('POST','/records/memory',json={'title':'Disposable private fact','data':{'body':'Only in local workspace'}})
    other=call('POST','/auth/workspaces',json={'name':'Isolated acceptance workspace'})
    c.headers['X-Workspace-ID']=other['id']
    assert call('GET','/records/memory')==[]
    assert c.delete('/records/'+first['id']).status_code==404
    print('PASS: real account/session/CSRF and cross-workspace isolation',flush=True)
    one=call('POST','/documents',files={'file':('revenue.txt',b'Business revenue was 100 units in June. Income increased from 80 units in May.','text/plain')})
    two=call('POST','/documents',files={'file':('operations.txt',b'Customer support resolved 45 tickets in June. All safety inspections passed.','text/plain')})
    for doc in [one,two]:call('POST','/documents/'+doc['id']+'/index',json={'model':'nomic-embed-text:latest'})
    matches=call('GET','/documents/retrieve',params={'q':'What was business income?','model':'nomic-embed-text:latest'})
    assert matches and matches[0]['document_id']==one['id']
    print('PASS: isolated document parsing and real local semantic indexing/retrieval',flush=True)
    docjob=job('research','What was the business income in June? Cite the uploaded evidence.',['qwen2.5:0.5b'],document_ids=[one['id'],two['id']],document_only=True,embedding_model='nomic-embed-text:latest')
    docdata=finish(docjob);assert docdata['citation_verification']['valid']
    print('PASS: real document-grounded research with saved references; mode='+docdata.get('evidence_mode','model_synthesis'),flush=True)
    webjob=job('research','retrieval augmented generation',['qwen2.5:0.5b'],budget={'max_searches':2,'max_pages':2,'max_seconds':600,'max_input_chars':12000})
    call('POST','/jobs/'+webjob['id']+'/pause')
    paused=next(r['data'] for r in call('GET','/records/job') if r['id']==webjob['id']);assert paused['status']=='paused'
    call('POST','/jobs/'+webjob['id']+'/resume')
    print('PASS: real deep-research pause/resume with durable saved state',flush=True)
    data=finish(webjob);assert data['sources'] and data['citation_verification']['valid']
    assert all(s['content_hash']==hashlib.sha256(s['text'].encode()).hexdigest() for s in data['sources'])
    for format,magic in [('pdf',b'%PDF'),('docx',b'PK'),('xlsx',b'PK')]:
        report=call('GET','/jobs/'+webjob['id']+'/export',params={'format':format});assert report.content.startswith(magic)
    print('PASS: real internet research, reference integrity and PDF/DOCX/XLSX reports; mode='+data.get('evidence_mode','model_synthesis'),flush=True)
    council=job('council','In one sentence, explain why local data ownership matters. State uncertainty.',['qwen2.5:0.5b','smollm2:135m'])
    councildata=finish(council)
    assert len(councildata['analyses'])==2 and councildata.get('comparison_output') and councildata.get('result')
    assert [a['model'] for a in councildata['analyses']]==['qwen2.5:0.5b','smollm2:135m']
    print('PASS: two distinct real local models, independent analysis, comparison and synthesis',flush=True)
    raw=c.cookies.get('foxory_session');call('POST','/auth/logout')
    assert c.get('/overview').status_code==401
    print('PASS: server-side logout revocation. No GPU or model-quality claim.',flush=True)
    evidence={'workspace_id':other['id'],'web_job':webjob['id'],'document_job':docjob['id'],'council_job':council['id'],'web_sources':[{'url':s['url'],'content_hash':s['content_hash']} for s in data['sources']],'web_mode':data.get('evidence_mode','model_synthesis'),'document_mode':docdata.get('evidence_mode','model_synthesis')}
    Path('/tmp/foxory-phase2-acceptance-evidence.json').write_text(json.dumps(evidence,indent=2))
