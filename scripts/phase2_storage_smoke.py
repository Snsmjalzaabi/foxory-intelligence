"""Recovery and logical restore checks for the explicit disposable Phase 2 project."""
import json
import subprocess
import tempfile
import time
from pathlib import Path
from uuid import uuid4
import httpx
root=Path(__file__).resolve().parents[1]
project=['docker','compose','-p','foxory-phase2-verify','-f','compose.yaml','-f','/tmp/foxory-phase2-compose.yaml']
def compose(*args,**kwargs):return subprocess.run(project+list(args),cwd=root,check=True,**kwargs)
def sql(database,statement):return compose('exec','-T','db','psql','-U','foxory','-d',database,'-At','-v','ON_ERROR_STOP=1','-c',statement,capture_output=True,text=True).stdout.strip()
if __name__=='__main__':
    evidence=json.loads(Path('/tmp/foxory-phase2-acceptance-evidence.json').read_text())
    credentials=json.loads(Path('/tmp/foxory-phase2-disposable-credentials.json').read_text())
    c=httpx.Client(base_url='http://127.0.0.1:8003/api',trust_env=False,timeout=60)
    for _ in range(60):
        try:
            if c.get('/health',timeout=3).status_code==200:break
        except httpx.HTTPError:pass
        time.sleep(1)
    else:raise AssertionError('Verification API did not start')
    login=c.post('/auth/login',json=credentials);login.raise_for_status();c.headers['X-CSRF-Token']=login.json()['csrf'];c.headers['X-Workspace-ID']=evidence['workspace_id']
    uploaded=c.post('/documents',files={'file':('parent-io-verification.txt',b'Bounded parent parser I/O validation after container replacement.')});uploaded.raise_for_status()
    docs=c.get('/records/document').json();assert docs
    original=c.get('/documents/'+docs[0]['id']+'/download').content
    job=c.post('/jobs',json={'type':'research','prompt':'Review the uploaded evidence','models':['qwen2.5:0.5b'],'document_only':True,'document_ids':[docs[0]['id']],'idempotency_key':uuid4().hex});job.raise_for_status();id=job.json()['id']
    c.post('/jobs/'+id+'/pause').raise_for_status()
    compose('restart','app')
    for _ in range(60):
        try:
            if c.get('/health',timeout=3).status_code==200:break
        except httpx.HTTPError:pass
        time.sleep(1)
    else:raise AssertionError('API did not recover')
    me=c.get('/auth/me');assert me.status_code==200
    restored=next(x for x in c.get('/records/job').json() if x['id']==id)
    assert restored['data']['status']=='paused'
    c.post('/jobs/'+id+'/resume').raise_for_status();c.post('/jobs/'+id+'/cancel').raise_for_status()
    assert next(x for x in c.get('/records/job').json() if x['id']==id)['data']['status']=='cancelled'
    assert c.get('/documents/'+docs[0]['id']+'/download').content==original
    print('PASS: sessions, original document bytes and paused job survive app restart; resume/cancel enforced',flush=True)
    database='phase2_restore_'+uuid4().hex[:12]
    compose('exec','-T','db','createdb','-U','foxory',database)
    try:
        with tempfile.TemporaryDirectory(prefix='foxory-phase2-restore-') as folder:
            dump=Path(folder)/'database.dump'
            with dump.open('wb') as f:compose('exec','-T','db','pg_dump','-U','foxory','-d','foxory','-Fc',stdout=f)
            dump.chmod(0o600)
            with dump.open('rb') as f:compose('exec','-T','db','pg_restore','-U','foxory','-d',database,stdin=f)
            assert sql(database,'SELECT version_num FROM alembic_version')=='0003'
            assert int(sql(database,'SELECT count(*) FROM users'))>=1
            assert int(sql(database,'SELECT count(*) FROM memberships'))>=2
            assert int(sql(database,"SELECT count(*) FROM records WHERE kind='document'"))>=2
            assert int(sql(database,"SELECT count(*) FROM records WHERE kind='job'"))>=3
        print('PASS: PostgreSQL revision 0003/users/memberships/documents/jobs restored in disposable database',flush=True)
    finally:compose('exec','-T','db','dropdb','-U','foxory',database)
    c.post('/auth/logout').raise_for_status()
