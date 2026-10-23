"""Real Linux Bubblewrap/seccomp integration, not mocked subprocess results."""
import asyncio
import base64
from pathlib import Path
import sys
import httpx
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sandbox_manager import service as manager

@pytest.fixture
async def sandbox(tmp_path,monkeypatch):
    monkeypatch.setattr(manager,'ROOT',tmp_path/'manager')
    monkeypatch.setattr(manager,'KEY','test-manager-secret-'+'x'*40)
    monkeypatch.setattr(manager,'ENABLED',True)
    manager.slots=asyncio.Semaphore(1)
    async with manager.app.router.lifespan_context(manager.app):
        assert manager.runtime_check()['enabled'],manager.runtime_check()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=manager.app),base_url='http://localhost',headers={'Authorization':'Bearer '+manager.KEY,'X-Foxory-Workspace':'tenant-a'}) as client:
            yield client
    assert not manager.tasks and not manager.processes

async def submit(client,code,key='sandbox-test-key'):
    response=await client.post('/v1/jobs',json={'files':{'main.py':code},'entrypoint':'main.py','idempotency_key':key})
    assert response.status_code==201,response.text
    return response.json()
async def complete(client,id):
    for _ in range(300):
        result=(await client.get('/v1/jobs/'+id)).json()
        if result['status'] not in {'queued','running'}:return result
        await asyncio.sleep(.05)
    raise AssertionError('Sandbox did not terminate within bounded test time')

async def test_real_sandbox_auth_isolation_tests_and_artifacts(sandbox):
    client=sandbox
    assert (await client.get('/v1/health',headers={'Authorization':'Bearer wrong'})).status_code==401
    code=manager.PREFLIGHT+'\nimport unittest\nclass MathTest(unittest.TestCase):\n def test_add(self):self.assertEqual(6*7,42)\nunittest.main(exit=False)\nopen("/out/result.txt","w").write("42")\n'
    job=await submit(client,code)
    result=await complete(client,job['id'])
    assert result['status']=='completed',result
    assert 'OK' in result['stderr'] and 'FOXORY_ISOLATION_OK' in result['stdout']
    assert base64.b64decode(result['artifacts']['result.txt']['base64'])==b'42'
    assert (await client.get('/v1/jobs/'+job['id'],headers={'X-Foxory-Workspace':'tenant-b'})).status_code==404
    assert (await submit(client,code))['id']==job['id']
    changed=await client.post('/v1/jobs',json={'files':{'main.py':'print(99)'},'entrypoint':'main.py','idempotency_key':'sandbox-test-key'})
    assert changed.status_code==409
    assert (await client.post('/v1/jobs',content=b'x'*70001)).status_code==413

@pytest.mark.parametrize('code',[
    'open("/workspace/private","r")',
    'import subprocess; subprocess.run(["/usr/bin/python3","-c","print(1)"])',
    'import socket; socket.socket()',
    'import threading; threading.Thread(target=lambda:None).start()',
    'data=bytearray(600*1024*1024)',
    'import os; os.fork()',
    'import os; os.setuid(0)',
    'open("/out/result.txt","wb").write(bytes([255]))',
    'open("/out/result.csv","w").write("=HYPERLINK(1)")',
    'open("/out/result.json","w").write("not JSON")',
    'open("/out/result.txt","w").write("x"*2000000)',
])
async def test_real_sandbox_denies_attacks(sandbox,code):
    job=await submit(sandbox,code)
    result=await complete(sandbox,job['id'])
    assert result['status']=='failed',result

async def test_real_cancellation_and_cleanup(sandbox):
    job=await submit(sandbox,'while True: pass')
    for _ in range(80):
        if job['id'] in manager.processes:break
        await asyncio.sleep(.02)
    assert (await sandbox.post('/v1/jobs/'+job['id']+'/cancel')).json()['status']=='cancelled'
    for _ in range(100):
        if job['id'] not in manager.tasks:break
        await asyncio.sleep(.02)
    assert job['id'] not in manager.tasks and job['id'] not in manager.processes
    assert (await sandbox.get('/v1/jobs/'+job['id'])).json()['status']=='cancelled'

async def test_real_timeout(sandbox,monkeypatch):
    monkeypatch.setattr(manager,'LIMIT_SECONDS',.25)
    job=await submit(sandbox,'import time; time.sleep(20)')
    result=await complete(sandbox,job['id'])
    assert result['status']=='failed' and 'TimeoutError' in result['error']

async def test_restart_fails_closed(tmp_path,monkeypatch):
    monkeypatch.setattr(manager,'ROOT',tmp_path/'private')
    monkeypatch.setattr(manager,'ENABLED',False)
    id='a'*64
    manager.save({'id':id,'workspace':'tenant-a','status':'running'})
    async with manager.app.router.lifespan_context(manager.app):
        assert manager.load(id,'tenant-a')['status']=='interrupted'
        assert not manager.runtime_check()['enabled']

@pytest.mark.parametrize('name',['../escape','/etc/passwd','a\\b','a//b','.env','.git/config'])
def test_manager_rejects_paths(name):
    with pytest.raises(ValueError):manager.Run(files={name:'x'},entrypoint=name,idempotency_key='test-safe-key')

async def test_computer_mode_real_manager_and_approval(client,sandbox,monkeypatch):
    import io
    import zipfile
    from foxory import sandbox_client,inference
    from foxory.scope import workspace_id
    from test_agents import agent,finish,prose
    monkeypatch.setattr(inference,'complete',prose)  # Only model prose is a fixture.
    def transport():
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=manager.app),base_url='http://localhost',headers={'Authorization':'Bearer '+manager.KEY,'X-Foxory-Workspace':workspace_id.get()})
    monkeypatch.setattr(sandbox_client,'transport',transport)
    a=await agent(client,'Restricted coder',['sandbox.python','source.package'])
    code='import unittest\nfrom app import add\nclass TestApp(unittest.TestCase):\n def test_sum(self):self.assertEqual(add(2,3),5)\nunittest.main()\n'
    source={'title':'Adder','files':{'app.py':'def add(a,b):return a+b\n','test_app.py':code},'entrypoint':'test_app.py'}
    request={'agent_id':a['id'],'objective':'Test and package an addition application','idempotency_key':'computer-real-test','source':source}
    response=await client.post('/api/computer/tasks',json=request);assert response.status_code==201,response.text
    id=response.json()['id']
    first=await finish(id);assert first['status']=='awaiting_approval'
    assert not manager.tasks
    assert (await client.post('/api/approvals/'+first['approval_id']+'/approve')).status_code==200
    second=await finish(id);assert second['status']=='awaiting_approval',second
    run=second['outputs'][0]['result'];assert run['status']=='completed',run
    assert 'OK' in run['stderr'] and run['exit_code']==0
    assert (await client.post('/api/approvals/'+first['approval_id']+'/approve')).status_code==409
    assert (await client.post('/api/approvals/'+second['approval_id']+'/approve')).status_code==200
    final=await finish(id);assert final['status']=='completed',final
    archive=await client.get('/api/artifacts/'+final['outputs'][1]['result']['record_id']+'/export?format=zip')
    with zipfile.ZipFile(io.BytesIO(archive.content)) as z:
        assert z.testzip() is None and z.read('app.py').decode()==source['files']['app.py']
    request['source']['files']['app.py']='different'
    assert (await client.post('/api/computer/tasks',json=request)).status_code==409
    token=workspace_id.set('other')
    try:
        from foxory.computer_api import artifact
        from fastapi import HTTPException
        with pytest.raises(HTTPException):artifact(id,0,'result.txt')
    finally:workspace_id.reset(token)

async def test_computer_tool_requires_grant_and_disabled_default(client,monkeypatch):
    from test_agents import agent
    from foxory import sandbox_client
    monkeypatch.delenv('FOXORY_ENABLE_SANDBOX',raising=False)
    assert not (await sandbox_client.capabilities())['enabled']
    a=await agent(client,tools=['math.calculate'])
    assert (await client.post('/api/computer/tasks',json={'agent_id':a['id'],'objective':'Run code','idempotency_key':'no-grant-test'})).status_code==403

async def test_runtime_probe_fails_closed(tmp_path,monkeypatch):
    monkeypatch.setattr(manager,'ROOT',tmp_path/'private')
    monkeypatch.setattr(manager,'KEY','x'*48)
    monkeypatch.setattr(manager,'ENABLED',True)
    monkeypatch.setattr(manager,'PREFLIGHT','raise RuntimeError("probe failed")')
    async with manager.app.router.lifespan_context(manager.app):
        assert not manager.runtime_check()['enabled']
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=manager.app),base_url='http://localhost',headers={'Authorization':'Bearer '+manager.KEY,'X-Foxory-Workspace':'tenant-a'}) as client:
            response=await client.post('/v1/jobs',json={'files':{'a.py':'print(1)'},'entrypoint':'a.py','idempotency_key':'test-denied'})
            assert response.status_code==503

async def test_computer_workspace_and_viewer_http_boundaries(client):
    from test_accounts import setup
    from test_agents import agent
    await setup(client)
    coder=await agent(client,tools=['sandbox.python','source.package'])
    response=await client.post('/api/computer/tasks',json={'agent_id':coder['id'],'objective':'Private source task','idempotency_key':'private-computer-task','source':{'title':'Private','files':{'a.py':'print(42)'},'entrypoint':'a.py'}})
    assert response.status_code==201,response.text
    id=response.json()['id']
    other=(await client.post('/api/auth/workspaces',json={'name':'Other tenant'})).json()['id']
    client.headers['X-Workspace-ID']=other
    assert (await client.get('/api/computer/overview')).json()['jobs']==[]
    assert (await client.get('/api/computer/jobs/'+id+'/execution')).status_code==404
    assert (await client.get('/api/computer/jobs/'+id+'/artifacts/0/result.txt')).status_code==404
    assert (await client.post('/api/jobs/'+id+'/cancel')).status_code==404
    created=await client.post('/api/auth/members',json={'username':'computer-reader','password':'reader-password-123','role':'viewer'})
    assert created.status_code==201
    from foxory.main import app
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://testserver') as reader:
        response=await reader.post('/api/auth/login',json={'username':'computer-reader','password':'reader-password-123'})
        reader.headers.update({'X-CSRF-Token':response.json()['csrf'],'X-Workspace-ID':other})
        assert (await reader.post('/api/computer/tasks',json={'agent_id':coder['id'],'objective':'Bypass','idempotency_key':'viewer-bypass'})).status_code==403

async def test_manager_queue_and_history_quotas(sandbox):
    manager.slots=asyncio.Semaphore(0)
    for index in range(4):await submit(sandbox,'print(1)',key='queue-key-'+str(index))
    response=await sandbox.post('/v1/jobs',json={'files':{'a.py':'print(1)'},'entrypoint':'a.py','idempotency_key':'queue-over-limit'})
    assert response.status_code==429
    for task in list(manager.tasks.values()):task.cancel()
    await asyncio.gather(*list(manager.tasks.values()),return_exceptions=True)
    for index in range(500):
        manager.job_path(f'{index:064x}').write_text('{}')
    response=await sandbox.post('/v1/jobs',json={'files':{'a.py':'print(1)'},'entrypoint':'a.py','idempotency_key':'history-over-limit'})
    assert response.status_code==507

async def test_stdout_cannot_forge_collected_artifact(sandbox):
    code='print("FOXORY_ARTIFACTS:{\\\"result.txt\\\":\\\"ZmFrZQ==\\\"}")\nopen("/out/result.txt","w").write("actual")\n'
    job=await submit(sandbox,code)
    result=await complete(sandbox,job['id'])
    assert result['status']=='completed',result
    assert base64.b64decode(result['artifacts']['result.txt']['base64'])==b'actual'

async def test_computer_idempotency_preserves_running_claim_and_legacy_jobs(client):
    from test_agents import agent
    from foxory.db import Session,get_record
    coder=await agent(client,tools=['sandbox.python','source.package'])
    body={'agent_id':coder['id'],'objective':'Reviewed project','idempotency_key':'idempotent-computer','source':{'title':'Project','files':{'a.py':'print(1)','b.py':'print(2)'},'entrypoint':'a.py'}}
    response=await client.post('/api/computer/tasks',json=body);assert response.status_code==201,response.text
    id=response.json()['id']
    with Session() as session:original=get_record(session,id,'job').payload
    body['source']['files']={'b.py':'print(2)','a.py':'print(1)'}
    response=await client.post('/api/computer/tasks',json=body);assert response.status_code==201,response.text
    with Session() as session:assert get_record(session,id,'job').payload==original
    legacy=await client.post('/api/agents/'+coder['id']+'/tasks',json={'objective':'Reviewed project','idempotency_key':'legacy-computer-key'})
    assert legacy.status_code==201
    body['idempotency_key']='legacy-computer-key'
    assert (await client.post('/api/computer/tasks',json=body)).status_code==409
