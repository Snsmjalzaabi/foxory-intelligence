"""Real CPU local-model acceptance against an explicitly disposable loopback installation.
Never runs against the owner's port 8000 or prints credentials/model output.
"""
import json
import os
import secrets
import time
from pathlib import Path
from uuid import uuid4
from datetime import datetime,timedelta,timezone
import httpx

def main():
    root=Path(__file__).resolve().parents[1]
    c=httpx.Client(base_url='http://127.0.0.1:8003/api',timeout=30,trust_env=False)
    for _ in range(60):
        try:
            if c.get('/health').status_code==200:break
        except httpx.HTTPError:pass
        time.sleep(1)
    else:raise RuntimeError('Disposable installation unavailable')
    config=dict(line.split('=',1) for line in (root/'.env').read_text().splitlines() if '=' in line and not line.startswith('#'))
    private=Path('/tmp/foxory-phase3-test-session.json')
    if private.exists():
        saved=json.loads(private.read_text());credentials=saved['credentials']
        setup=c.post('/auth/login',json=credentials);setup.raise_for_status()
    else:
        credentials={'username':'phase3-'+uuid4().hex[:8],'password':secrets.token_urlsafe(24)}
        setup=c.post('/auth/setup',json={**credentials,'bootstrap_token':config['FOXORY_TOKEN']});setup.raise_for_status()
    c.headers['X-CSRF-Token']=setup.json()['csrf']
    workspace=c.get('/auth/me').json()['workspace_id'];c.headers['X-Workspace-ID']=workspace
    # Every rerun uses a fresh disposable workspace while preserving failed-run evidence.
    if not os.getenv('FOXORY_PHASE3_RESUME'):
        ws=c.post('/auth/workspaces',json={'name':'Real agent acceptance '+uuid4().hex[:6]});ws.raise_for_status()
        workspace=ws.json()['id']
    else:workspace=saved['workspace_id']
    c.headers['X-Workspace-ID']=workspace
    private.write_text(json.dumps({'credentials':credentials,'csrf':setup.json()['csrf'],'workspace_id':workspace}));private.chmod(0o600)
    def make(name,tools,delegates=None):
        scopes={'math.calculate':'calculate','data.analyze':'calculate','project.create':'projects.write'}
        r=c.post('/agents',json={'name':name,'config':{'role':name,'model':'qwen2.5:0.5b','tools':tools,'permissions':list({scopes[t] for t in tools}),'delegate_ids':delegates or [],'max_steps':4,'max_model_calls':10,'step_timeout':240,'max_seconds':1200}});r.raise_for_status();return r.json()
    def wait(id,wanted=None):
        deadline=time.monotonic()+1250
        while time.monotonic()<deadline:
            try:rows=c.get('/records/job',timeout=60)
            except httpx.TransportError:
                print('Retry: transient status connection; persisted job is not resubmitted',flush=True);time.sleep(1);continue
            rows.raise_for_status();d=next(r['data'] for r in rows.json() if r['id']==id)
            if wanted and d['status']==wanted:return d
            if d['status'] in {'completed','failed','cancelled','awaiting_approval'}:
                assert d['status']==(wanted or 'completed'),{'status':d['status'],'error':d.get('error'),'detail':d.get('error_detail'),'stage':d.get('stage')}
                return d
            time.sleep(2)
        raise TimeoutError('Real task deadline')
    if os.getenv('FOXORY_PHASE3_RESUME'):
        rows=c.get('/records/job',timeout=120);rows.raise_for_status()
        job=next(r for r in rows.json() if r['data']['prompt'].startswith('Estimate a contingency budget'))
        coordinator={'id':job['data']['agent_id']};analyst={'id':job['data']['agent_snapshot']['delegate_ids'][0]}
        d=wait(job['id'])
    else:
        analyst=make('Real cost analyst',['math.calculate','data.analyze'])
        writer=make('Real writing specialist',[])
        coordinator=make('Real general coordinator',[],[analyst['id'],writer['id']])
        objective="Estimate a contingency budget of 15 percent for a project cost of 2400 units. Delegate the calculation to specialist_1 using math.calculate with expression 2400*0.15. Use exactly one tool step. The coordinator will review and consolidate the actual result afterward."
        r=c.post('/agents/'+coordinator['id']+'/tasks',json={'objective':objective,'idempotency_key':uuid4().hex});r.raise_for_status();job=r.json();d=wait(job['id'])
    assert len(d['outputs'])==1 and d['outputs'][0]['result']['value']==360
    assert d['outputs'][0]['agent_id']==analyst['id'] and coordinator['id']!=analyst['id']
    assert d['quality_review'] and d['result'] and d['model_trace']
    print('PASS: actual Qwen structured autonomous plan, delegated contingency calculation, coordinator quality review and consolidation',flush=True)
    assert c.get('/agents/'+coordinator['id']+'/memory').json()
    for format in ['md','pdf','docx','xlsx']:
        out=c.get('/jobs/'+job['id']+'/export',params={'format':format});out.raise_for_status();assert out.content
    print('PASS: unverified task summary memory and four report exports',flush=True)
    workflow=make('Real approval workflow',['project.create'])
    plan=[{'title':'Create internal project','tool':'project.create','args':{'title':'Real approved internal plan','content':'Use local calculations and human review.'}}]
    r=c.post('/agents/'+workflow['id']+'/tasks',json={'objective':'Prepare an internal project after approval','plan':plan,'idempotency_key':uuid4().hex});r.raise_for_status();approved_job=r.json();a=wait(approved_job['id'],'awaiting_approval')
    assert not c.get('/records/project').json()
    c.post('/approvals/'+a['approval_id']+'/approve').raise_for_status()
    wait(approved_job['id']);assert len(c.get('/records/project').json())==1
    assert c.post('/approvals/'+a['approval_id']+'/approve').status_code==409
    print('PASS: real approved internal write, atomic consumption and stale reuse rejection',flush=True)
    schedule=c.post('/agent-schedules',json={'agent_id':analyst['id'],'objective':'Calculate 6*7 using math.calculate','start_at':(datetime.now(timezone.utc)-timedelta(seconds=2)).isoformat(),'max_runs':1});schedule.raise_for_status()
    for _ in range(20):
        s=next(r for r in c.get('/records/schedule').json() if r['id']==schedule.json()['id'])
        if s['data'].get('last_job_id'):break
        time.sleep(1)
    assert s['data']['runs']==1
    wait(s['data']['last_job_id'])
    print('PASS: scheduled safe task executes without browser, persists history and runs once',flush=True)
    private_data=json.loads(private.read_text());private_data.update(job_id=job['id'],agent_id=coordinator['id'],schedule_id=schedule.json()['id']);private.write_text(json.dumps(private_data))
    Path('/tmp/foxory-phase3-evidence.json').write_text(json.dumps({'model':'qwen2.5:0.5b','plan_steps':len(d['plan']),'tool_result':360,'stages':[t['event'] for t in d['timeline']],'model_calls':d['agent_model_calls'],'job_id':job['id']},indent=2))
    c.post('/auth/logout').raise_for_status()
    print('PASS: logout revoked; CPU connectivity/workflow evidence only, no GPU or reasoning-quality claim',flush=True)
if __name__=='__main__':main()
