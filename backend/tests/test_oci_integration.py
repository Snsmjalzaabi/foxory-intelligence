"""Real manager/application flows, mocked OCI boundary; never host execution."""
import asyncio
import base64
import hashlib
import json
from pathlib import Path
import sys
import pytest
import httpx
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sandbox_manager import service as manager
from sandbox_manager.oci_runtime import Runtime
from foxory.sandbox_protocol import validate_artifacts, validate_png, OCIProject
from scripts.oci_fixture import Engine,SITE,artifact,png

async def test_control_children_only_receive_identity_environment(tmp_path,monkeypatch):
    values={'HOME':'/home/dedicated','XDG_RUNTIME_DIR':'/run/user/1002',
            'DBUS_SESSION_BUS_ADDRESS':'unix:path=/run/user/1002/bus',
            'FOXORY_SANDBOX_KEY':'private-manager-key','GITHUB_TOKEN':'private-token',
            'LISTEN_FDS':'1','LISTEN_PID':'42','NOTIFY_SOCKET':'/run/notify',
            'CONTAINER_HOST':'ssh://other-host','CONTAINERS_STORAGE_CONF':'/other/config'}
    for name,value in values.items():monkeypatch.setenv(name,value)
    async def child(*args,**kwargs):
        assert args==('podman','--remote=false','info')
        assert {name:kwargs['env'][name] for name in ('HOME','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS')}=={
            name:values[name] for name in ('HOME','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS')}
        assert set(kwargs['env']).isdisjoint(set(values)-{'HOME','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS'})
        return 'controlled child'
    monkeypatch.setattr(asyncio,'create_subprocess_exec',child)
    assert await Runtime(tmp_path).spawn('podman','--remote=false','info')=='controlled child'

@pytest.fixture
async def oci(tmp_path,monkeypatch):
    engine=Engine();engine.install(monkeypatch)
    monkeypatch.setattr(manager,'ROOT',tmp_path/'manager')
    monkeypatch.setattr(manager,'KEY','oci-test-secret-'+'x'*40)
    monkeypatch.setattr(manager,'ENABLED',False)  # No native Python/runtime probes.
    manager.slots=asyncio.Semaphore(1)
    async with manager.app.router.lifespan_context(manager.app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=manager.app),base_url='http://manager',headers={
            'Authorization':'Bearer '+manager.KEY,'X-Foxory-Workspace':'local'}) as client:
            yield client,engine
    assert not engine.containers and not manager.oci_runtime.processes

async def submit(client,profile='javascript',key='oci-reviewed-task'):
    source={'files':{'app.js':'console.log(42)'},'entrypoint':'app.js'}
    if profile=='typescript':source={'files':{'app.ts':'const n:number=42;'},'entrypoint':'app.ts'}
    if profile=='browser':source={'files':{'index.html':SITE,'report.txt':'Controlled download'},'actions':[
        {'action':'navigate','target':'/'},{'action':'type','target':'#name','text':'FOXORY'},
        {'action':'click','target':'#show'},{'action':'inspect'},{'action':'screenshot'},{'action':'download','target':'a'}]}
    response=await client.post('/v1/jobs',json={'profile':profile,**source,'idempotency_key':key})
    assert response.status_code==201,response.text
    return response.json()
async def complete(client,id):
    for _ in range(200):
        value=(await client.get('/v1/jobs/'+id)).json()
        if value['status'] not in {'queued','running','cancelling'}:return value
        await asyncio.sleep(.01)
    raise AssertionError('Mocked OCI task did not finish')

@pytest.mark.parametrize('profile',['javascript','typescript','browser'])
async def test_authenticated_profile_dispatch_and_artifacts(oci,profile):
    client,engine=oci
    assert (await client.get('/v1/health',headers={'Authorization':'Bearer wrong'})).status_code==401
    created=await submit(client,profile)
    result=await complete(client,created['id'])
    assert result['status']=='completed',result
    assert 'Mock worker' in ''.join(result['events'])
    created_args = [args for args in engine.calls if args[0] == 'create']
    assert len(created_args) == 1
    assert [arg for arg in created_args[0] if arg.startswith('--cap-add=')] == (
        ['--cap-add=SYS_CHROOT'] if profile == 'browser' else [])
    assert '--cap-drop=ALL' in created_args[0]
    assert '--security-opt=no-new-privileges' in created_args[0]
    assert '--network=none' in created_args[0]
    assert not engine.containers
    if profile=='browser':
        assert 'FOXORY' in result['stdout']
        assert base64.b64decode(result['artifacts']['screenshot-1.png']['base64'])==png()
    assert (await submit(client,profile))['id']==created['id']
    assert engine.runs==1
    assert (await client.get('/v1/jobs/'+created['id'],headers={'X-Foxory-Workspace':'other'})).status_code==404
    assert (await client.post('/v1/jobs/'+created['id']+'/cancel',headers={'X-Foxory-Workspace':'other'})).status_code==404
    conflict=await client.post('/v1/jobs',json={'profile':'javascript','files':{'a.js':'0'},'entrypoint':'a.js','idempotency_key':'oci-reviewed-task'})
    assert conflict.status_code==409

async def test_cancellation_and_timeout_remove_whole_container(oci,monkeypatch):
    client,engine=oci;engine.hang=True
    job=await submit(client)
    for _ in range(100):
        if engine.runs:break
        await asyncio.sleep(.01)
    await client.post('/v1/jobs/'+job['id']+'/cancel')
    assert (await complete(client,job['id']))['status']=='cancelled'
    assert not engine.containers
    monkeypatch.setattr('sandbox_manager.oci_runtime.WALL_SECONDS',.03)
    job=await submit(client,key='timeout-reviewed-task')
    result=await complete(client,job['id'])
    assert result['status']=='failed' and 'TimeoutError' in result['error']
    assert not engine.containers and not manager.oci_runtime.processes

async def test_malicious_output_and_quarantine(oci):
    client,engine=oci;engine.corrupt=True
    result=await complete(client,(await submit(client))['id'])
    assert result['status']=='failed' and 'integrity' in result['error']
    assert not result['artifacts']
    engine.corrupt=False;engine.cleanup_failure=True
    result=await complete(client,(await submit(client,key='cleanup-failure-job'))['id'])
    assert result['status']=='failed'
    assert not manager.oci_runtime.capabilities()['browser']['enabled']
    assert manager.oci_runtime.quarantine.exists()
    engine.cleanup_failure=False
    await manager.oci_runtime.recover()
    assert not engine.containers

async def test_restart_orphan_cleanup_and_ownership(tmp_path,monkeypatch):
    engine=Engine();engine.install(monkeypatch)
    root=tmp_path/'manager';root.mkdir()
    runtime=Runtime(root);id='a'*64
    engine.containers['foxory-task-'+id]={'labels':{'io.foxory.manager':runtime.owner,'io.foxory.task':id}}
    engine.containers['foxory-task-'+'b'*64]={'labels':{'io.foxory.manager':'other','io.foxory.task':'b'*64}}
    assert await runtime.recover()==[id]
    assert len(engine.containers)==1
    with pytest.raises(PermissionError):await runtime.remove('b'*64)

@pytest.mark.parametrize('name,data',[('result.json',b'invalid'),('result.json',b'NaN'),('result.csv',b'=HYPERLINK("bad")'),('result.txt',b'\x00'),('screenshot-1.png',b'not png'),('../result.txt',b'escape')])
def test_strict_artifact_content_and_names(name,data):
    with pytest.raises(ValueError):validate_artifacts({name:artifact(data)},allow_png=True)

def test_png_checksum_decompression_and_trailing_data():
    validate_png(png())
    for data in [png()+b'extra',png()[:-1],png()[:40]+b'changed'+png()[47:]]:
        with pytest.raises(ValueError):validate_png(data)
    with pytest.raises(ValueError):validate_artifacts({'result.txt':artifact(b'x'*20001)})

async def test_default_off_does_not_probe_or_spawn(tmp_path,monkeypatch):
    monkeypatch.delenv('FOXORY_SANDBOX_OCI_ENABLED',raising=False)
    monkeypatch.setattr('sandbox_manager.oci_runtime.shutil.which',lambda _:None)
    runtime=Runtime(tmp_path)
    await runtime.startup(authorized=True)
    assert not runtime.capabilities()['javascript']['enabled']
    with pytest.raises(PermissionError):await runtime.run('a'*64,OCIProject(profile='javascript',files={'a.js':'0'},entrypoint='a.js'),lambda _:None)

@pytest.mark.parametrize('profile',['javascript','typescript','browser'])
async def test_computer_approval_dispatch_download_ownership_and_isolation(client,oci,monkeypatch,profile):
    from foxory import sandbox_client,inference
    from foxory.scope import workspace_id
    from foxory.db import Session,get_record
    from test_agents import agent,finish,prose
    from test_accounts import setup
    remote,engine=oci
    monkeypatch.setattr(inference,'complete',prose)
    def transport():
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=manager.app),base_url='http://manager',headers={
            'Authorization':'Bearer '+manager.KEY,'X-Foxory-Workspace':workspace_id.get()})
    monkeypatch.setattr(sandbox_client,'transport',transport)
    await setup(client)
    tools=['sandbox.'+profile]+([] if profile=='browser' else ['source.package'])
    coder=await agent(client,'OCI specialist',tools)
    source={'title':'Controlled fixture','files':{'app.js':'console.log(42)'},'entrypoint':'app.js'}
    if profile=='typescript':source={'title':'Controlled TS','files':{'app.ts':'const n:number=42;'},'entrypoint':'app.ts'}
    if profile=='browser':source={'title':'Controlled browser','files':{'index.html':SITE,'report.txt':'Controlled download'},'actions':[{'action':'navigate','target':'/'},{'action':'screenshot'},{'action':'download','target':'a'}]}
    body={'agent_id':coder['id'],'objective':'Test-only mocked OCI workflow','profile':profile,'source':source,'idempotency_key':'scoped-computer-oci'}
    response=await client.post('/api/computer/tasks',json=body);assert response.status_code==201,response.text
    id=response.json()['id'];first=await finish(id)
    assert first['status']=='awaiting_approval' and engine.runs==0
    pending=first['approval_id']
    assert (await client.post('/api/approvals/'+pending+'/approve')).status_code==200
    result=await finish(id)
    if profile!='browser':
        assert result['status']=='awaiting_approval',result
        assert (await client.post('/api/approvals/'+result['approval_id']+'/approve')).status_code==200
        result=await finish(id)
    assert result['status']=='completed',result
    assert engine.runs==1
    path='/api/computer/jobs/'+id+'/artifacts/0/'+('screenshot-1.png' if profile=='browser' else 'result.json')
    download=await client.get(path);assert download.status_code==200,download.text
    assert download.headers['cache-control']=='no-store' and download.headers['x-content-type-options']=='nosniff'
    assert (await client.post('/api/approvals/'+pending+'/approve')).status_code==409
    # Mutated stored ownership cannot become a downloadable artifact.
    with Session() as session:
        row=get_record(session,id,'job');value=json.loads(row.payload)
        value['outputs'][0]['result']['workspace']='foreign';row.payload=json.dumps(value);session.commit()
    assert (await client.get(path)).status_code==409
    other=(await client.post('/api/auth/workspaces',json={'name':'Isolated tenant'})).json()['id']
    client.headers['X-Workspace-ID']=other
    assert (await client.get(path)).status_code==404
    assert (await client.get('/api/computer/jobs/'+id+'/execution')).status_code==404
    assert (await client.post('/api/computer/tasks',json=body)).status_code==404

async def test_restart_marks_interrupted_oci_without_replaying(tmp_path,monkeypatch):
    engine=Engine();engine.install(monkeypatch)
    monkeypatch.setattr(manager,'ROOT',tmp_path/'manager')
    monkeypatch.setattr(manager,'KEY','x'*40);monkeypatch.setattr(manager,'ENABLED',False)
    manager.ROOT.mkdir(mode=0o700)
    id='c'*64;runtime=Runtime(manager.ROOT)
    manager.save({'id':id,'workspace':'tenant-a','status':'running','profile':'javascript'})
    engine.containers['foxory-task-'+id]={'labels':{'io.foxory.manager':runtime.owner,'io.foxory.task':id}}
    async with manager.app.router.lifespan_context(manager.app):
        assert manager.load(id,'tenant-a')['status']=='interrupted'
        assert engine.runs==0 and not engine.containers

async def test_manager_rejects_unsafe_browser_and_runtime_fields(oci):
    client,engine=oci
    for patch in [
        {'actions':[{'action':'navigate','target':'https://outside.invalid'}]},
        {'files':{'../escape.html':'bad'}}, {'image':'arbitrary:latest'},
        {'actions':[{'action':'shell','target':'id'}]}, {'mounts':['/var/run/docker.sock']},
        {'files':{'.ENV':'secret'}},
    ]:
        body={'profile':'browser','files':{'index.html':SITE},'actions':[{'action':'inspect'}],'idempotency_key':'unsafe-browser-input',**patch}
        assert (await client.post('/v1/jobs',json=body)).status_code==422
    assert engine.runs==0

async def test_startup_never_authorizes_invalid_configuration(tmp_path,monkeypatch):
    monkeypatch.setenv('FOXORY_SANDBOX_OCI_ENABLED','1')
    monkeypatch.setenv('FOXORY_SANDBOX_OCI_IMAGE','latest')
    monkeypatch.setattr('sandbox_manager.oci_runtime.shutil.which',lambda _:None)
    runtime=Runtime(tmp_path)
    async def forbidden(*args,**kwargs):raise AssertionError('Unsafe startup must not execute')
    monkeypatch.setattr(runtime,'spawn',forbidden)
    await runtime.startup(authorized=True)
    assert not runtime.verified
    runtime.image='sha256:'+'a'*64
    await runtime.startup(authorized=False)
    assert not runtime.verified

async def test_preflight_failure_keeps_profiles_disabled(tmp_path,monkeypatch):
    monkeypatch.setenv('FOXORY_SANDBOX_OCI_ENABLED','1')
    monkeypatch.setenv('FOXORY_SANDBOX_OCI_IMAGE','sha256:'+'a'*64)
    monkeypatch.setattr('sandbox_manager.oci_runtime.shutil.which',lambda _:None)
    runtime=Runtime(tmp_path)
    from scripts.oci_fixture import Process
    async def spawn(*args,**kwargs):return Process([{'status':'blocked'}],code=2)
    async def recover(*args):return []
    monkeypatch.setattr(runtime,'spawn',spawn);monkeypatch.setattr(runtime,'recover',recover)
    await runtime.startup(authorized=True)
    assert not runtime.verified and not runtime.capabilities()['browser']['enabled']

def test_worker_supply_chain_integrity_check(tmp_path,monkeypatch):
    from scripts import verify_worker_supply_chain as verifier
    import shutil
    assert verifier.verify()['registry_bytes_verified'] is False
    staged=tmp_path/'runtime';shutil.copytree(verifier.ROOT,staged)
    monkeypatch.setattr(verifier,'ROOT',staged)
    (staged/'worker.mjs').write_text('tampered')
    with pytest.raises(ValueError,match='Worker inputs changed'):verifier.verify()

async def test_combined_research_data_browser_coding_report_workflow(client,oci,monkeypatch):
    """Real state machine, arithmetic/PDF/ZIP; web/model and OCI are fixtures."""
    from foxory import sandbox_client,inference,web
    from foxory.scope import workspace_id
    from test_agents import agent,finish,prose
    remote,engine=oci
    def transport():return httpx.AsyncClient(transport=httpx.ASGITransport(app=manager.app),base_url='http://manager',headers={
        'Authorization':'Bearer '+manager.KEY,'X-Foxory-Workspace':workspace_id.get()})
    monkeypatch.setattr(sandbox_client,'transport',transport);monkeypatch.setattr(inference,'complete',prose)
    url='https://example.org/controlled-evidence'
    async def retrieved(value):
        assert value==url
        return {'url':url,'title':'Controlled source fixture','text':'Controlled evidence fixture, not a live web result. Source: '+url}
    monkeypatch.setattr(web,'retrieve_page',retrieved)
    browser=await agent(client,'Browser specialist',['sandbox.browser'])
    root=await agent(client,'Coordinator',['web.retrieve','math.calculate','sandbox.javascript','document.generate','source.package'],delegates=[browser['id']])
    files={'test_app.js':'if(6*7!==42)throw Error("failed");'}
    plan={'steps':[
        {'title':'Retrieve evidence','tool':'web.retrieve','args':{'url':url}},
        {'title':'Calculate','tool':'math.calculate','args':{'expression':'6*7'}},
        {'title':'Test code','tool':'sandbox.javascript','args':{'title':'Fixture project','files':files,'entrypoint':'test_app.js'},'depends_on':[1]},
        {'title':'Inspect fixture','agent_id':'specialist_1','tool':'sandbox.browser','args':{'title':'Fixture website','files':{'index.html':SITE},'actions':[{'action':'inspect'},{'action':'screenshot'}]},'depends_on':[0]},
        {'title':'Save report','tool':'document.generate','args':{'title':'Combined report','content':{'$step':0,'path':['text']}},'depends_on':[0,1,2,3]},
        {'title':'Package tested source','tool':'source.package','args':{'title':'Fixture project','files':files},'depends_on':[2,4]},
    ]}
    async def planned(*args):return json.dumps(plan)
    monkeypatch.setattr(inference,'structured',planned)
    response=await client.post('/api/computer/tasks',json={'agent_id':root['id'],'profile':'javascript','objective':'Combine evidence, calculation, coding, browser, report and source export','idempotency_key':'combined-computer-flow'})
    assert response.status_code==201,response.text
    id=response.json()['id'];approvals=[]
    for _ in range(6):
        state=await finish(id,limit=30)
        if state['status']=='completed':break
        assert state['status']=='awaiting_approval',state
        approvals.append(state['approval_id'])
        assert (await client.post('/api/approvals/'+state['approval_id']+'/approve')).status_code==200
    assert state['status']=='completed' and engine.runs==2 and len(approvals)==4,state
    assert state['outputs'][1]['result']['value']==42
    report=next(o['result']['record_id'] for o in state['outputs'] if o['tool']=='document.generate')
    response=await client.get('/api/artifacts/'+report+'/export?format=pdf');assert response.status_code==200
    from pypdf import PdfReader
    import io,zipfile
    assert url in ''.join(p.extract_text() for p in PdfReader(io.BytesIO(response.content)).pages)
    archive=next(o['result']['record_id'] for o in state['outputs'] if o['tool']=='source.package')
    response=await client.get('/api/artifacts/'+archive+'/export?format=zip');assert response.status_code==200
    with zipfile.ZipFile(io.BytesIO(response.content)) as zipped:
        assert zipped.testzip() is None and zipped.read('test_app.js').decode()==files['test_app.js']

async def test_repeated_cancel_waits_for_cleanup_before_terminal_state(oci,monkeypatch):
    client,engine=oci;engine.hang=True
    entered=asyncio.Event();release=asyncio.Event();original=engine.cli
    async def delayed(runtime,*args,**kwargs):
        if args[0]=='rm':entered.set();await release.wait()
        return await original(runtime,*args,**kwargs)
    monkeypatch.setattr(engine,'cli',delayed)
    created=await submit(client)
    for _ in range(100):
        if engine.runs:break
        await asyncio.sleep(.01)
    await client.post('/v1/jobs/'+created['id']+'/cancel')
    await asyncio.wait_for(entered.wait(),1)
    assert (await client.get('/v1/jobs/'+created['id'])).json()['status']=='cancelling'
    await client.post('/v1/jobs/'+created['id']+'/cancel')
    release.set()
    assert (await complete(client,created['id']))['status']=='cancelled'
    assert not manager.oci_runtime.processes and not engine.containers

async def test_orphan_recovery_skips_active_and_removes_staging(tmp_path,monkeypatch):
    root=tmp_path/'manager';root.mkdir(mode=0o700)
    engine=Engine();runtime=Runtime(root);active='d'*64
    engine.containers['foxory-task-'+active]={'labels':{'io.foxory.manager':runtime.owner,'io.foxory.task':active}}
    async def cli(*args,**kwargs):return await engine.cli(runtime,*args,**kwargs)
    monkeypatch.setattr(runtime,'cli',cli)
    assert await runtime.recover({active})==[] and len(engine.containers)==1
    stage=root/'foxory-oci-stale';stage.mkdir();(stage/'request.json').write_text('private fixture')
    monkeypatch.setattr('sandbox_manager.oci_runtime.shutil.which',lambda _:'/usr/bin/podman')
    runtime.opt_in=False
    await runtime.startup(authorized=False)
    assert not stage.exists() and not engine.containers and not runtime.verified

def test_png_decompression_bomb_and_invalid_compression_rejected():
    import struct,zlib
    def chunk(tag,body):return struct.pack('>I',len(body))+tag+body+struct.pack('>I',zlib.crc32(tag+body)&0xffffffff)
    header=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,2,0,0,0))
    for compressed in (b'invalid compressed data',zlib.compress(b'\0'*1000000)):
        with pytest.raises(ValueError):validate_png(header+chunk(b'IDAT',compressed)+chunk(b'IEND',b''))

async def test_legacy_python_artifacts_remain_bound_to_consumed_approval(client):
    from test_agents import agent,finish
    from foxory.db import Session,get_record
    from foxory.scope import workspace_id
    coder=await agent(client,'Legacy coder',['sandbox.python','source.package'])
    response=await client.post('/api/computer/tasks',json={'agent_id':coder['id'],'objective':'Legacy Python artifact','idempotency_key':'legacy-python-artifact','source':{'title':'Legacy','files':{'a.py':'print(42)'},'entrypoint':'a.py'}})
    id=response.json()['id'];state=await finish(id);approval_id=state['approval_id']
    with Session() as session:
        row=get_record(session,id,'job');data=json.loads(row.payload)
        approved=get_record(session,approval_id,'approval');approval=json.loads(approved.payload)
        approval['status']='consumed';approved.payload=json.dumps(approval)
        data['sandbox_authorizations']={'0':{'approval_id':approval_id,'context_hash':approval['context_hash']}}
        data['outputs']=[{'index':0,'tool':'sandbox.python','result':{
            'id':hashlib.sha256((workspace_id.get()+':agent:'+approval_id).encode()).hexdigest(),
            'status':'completed','artifacts':{'result.txt':artifact(b'legacy output')}}}]
        data['status']='completed';row.payload=json.dumps(data);session.commit()
    path='/api/computer/jobs/'+id+'/artifacts/0/result.txt'
    assert (await client.get(path)).content==b'legacy output'
    with Session() as session:
        approved=get_record(session,approval_id,'approval');approval=json.loads(approved.payload)
        approval['status']='rejected';approved.payload=json.dumps(approval);session.commit()
    assert (await client.get(path)).status_code==409
