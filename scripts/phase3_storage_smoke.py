"""Disposable Phase 3 Docker recovery and PostgreSQL logical restore check.
Requires phase3_smoke.py and the cloud-local verification Compose override.
"""
import json
import subprocess
import tempfile
import time
from datetime import datetime,timedelta,timezone
from pathlib import Path
from uuid import uuid4
import httpx
ROOT=Path(__file__).resolve().parents[1]
def compose(*args,**kwargs):return subprocess.run(['docker','compose','-p','foxory-phase3-verify','-f','compose.yaml','-f','/tmp/foxory-phase3-compose.yaml',*args],cwd=ROOT,check=True,**kwargs)
def database(*args,**kwargs):return subprocess.run(['docker','compose','exec','-T','db',*args],cwd=ROOT,check=True,**kwargs)
def sql(db,query):return database('psql','-U','foxory','-d',db,'-Atc',query,stdout=subprocess.PIPE).stdout.decode().strip()
def main():
    saved=json.loads(Path('/tmp/foxory-phase3-test-session.json').read_text())
    c=httpx.Client(base_url='http://127.0.0.1:8003/api',timeout=30,trust_env=False)
    login=c.post('/auth/login',json=saved['credentials']);login.raise_for_status();c.headers.update({'X-CSRF-Token':login.json()['csrf'],'X-Workspace-ID':saved['workspace_id']})
    row=c.post('/agents/'+saved['agent_id']+'/tasks',json={'objective':'Restart-safe read-only task','plan':[{'title':'Draft','instruction':'Summarize the authorized task'}],'idempotency_key':uuid4().hex});row.raise_for_status();id=row.json()['id']
    c.post('/jobs/'+id+'/pause').raise_for_status()
    scheduled=c.post('/agent-schedules',json={'agent_id':saved['agent_id'],'objective':'Recover scheduled task','start_at':(datetime.now(timezone.utc)+timedelta(seconds=8)).isoformat(),'max_runs':1});scheduled.raise_for_status();schedule_id=scheduled.json()['id']
    compose('restart','app')
    for _ in range(60):
        try:
            if c.get('/health').status_code==200:break
        except httpx.HTTPError:pass
        time.sleep(1)
    else:raise RuntimeError('Container failed to recover')
    assert c.get('/auth/me').status_code==200
    data=next(r['data'] for r in c.get('/records/job').json() if r['id']==id);assert data['status']=='paused'
    c.post('/jobs/'+id+'/resume').raise_for_status();c.post('/jobs/'+id+'/cancel').raise_for_status()
    for _ in range(30):
        schedule=next(r for r in c.get('/records/schedule').json() if r['id']==schedule_id)
        if schedule['data']['runs']==1:break
        time.sleep(1)
    assert schedule['data']['runs']==1
    dispatched=schedule['data']['last_job_id'];c.post('/jobs/'+dispatched+'/cancel').raise_for_status()
    # Another restart/tick cannot dispatch the consumed due instant again.
    compose('restart','app')
    for _ in range(60):
        try:
            if c.get('/health').status_code==200:break
        except httpx.HTTPError:pass
        time.sleep(1)
    rows=c.get('/records/job');rows.raise_for_status()
    assert sum(r['data'].get('schedule_id')==schedule_id for r in rows.json())==1
    print('PASS: session, paused task and scheduler survive container restarts; resume/cancel and once-only recovery enforced',flush=True)
    destination='phase3_restore_'+uuid4().hex[:10]
    database('createdb','-U','foxory',destination)
    try:
        with tempfile.TemporaryDirectory(prefix='foxory-phase3-backup-') as directory:
            path=Path(directory)/'database.dump'
            with path.open('wb') as stream:database('pg_dump','-U','foxory','-d','phase3_verify','-Fc',stdout=stream)
            path.chmod(0o600)
            with path.open('rb') as stream:database('pg_restore','-U','foxory','-d',destination,stdin=stream)
        assert sql(destination,'SELECT version_num FROM alembic_version')=='0003'
        for kind in ['agent','job','schedule','approval','agent_memory']:
            query="SELECT count(*) FROM records WHERE kind='"+kind+"'"
            assert int(sql(destination,query))>0 and sql(destination,query)==sql('phase3_verify',query)
        assert sql(destination,'SELECT count(*) FROM memberships')==sql('phase3_verify','SELECT count(*) FROM memberships')
        print('PASS: PostgreSQL restore preserves revision0003, accounts, agents, task checkpoints, schedules, approvals and memory',flush=True)
    finally:database('dropdb','-U','foxory',destination)
    c.post('/auth/logout').raise_for_status()
if __name__=='__main__':main()
