"""Separate, authenticated, fail-closed single-process Python sandbox manager.

Run under a dedicated unprivileged OS account, never in the application container.
No Docker socket or user-selected mounts, commands, interpreters or URLs.
"""
import asyncio
import base64
import contextlib
import csv
import io
import math
import hashlib
import hmac
import fcntl
import json
import logging
import os
from pathlib import Path
import re
import secrets
import shutil
import signal
import tempfile
from datetime import datetime, timezone
from typing import Literal
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .oci_runtime import Runtime
from foxory.sandbox_protocol import BrowserAction, OCIProject, valid_path

log=logging.getLogger('foxory.sandbox')
ROOT=Path(os.getenv('FOXORY_SANDBOX_DATA','./sandbox-data')).resolve()
KEY=os.getenv('FOXORY_SANDBOX_KEY','')
ENABLED=os.getenv('FOXORY_SANDBOX_ENABLED','0')=='1'
PYTHON=Path('/usr/bin/python3').resolve()
BOOTSTRAP=Path(__file__).with_name('bootstrap.py').resolve()
LIMIT_SECONDS=15
MAX_LOG=128000
processes:dict[str,asyncio.subprocess.Process]={}
tasks:dict[str,asyncio.Task]={}
slots=asyncio.Semaphore(1)
SEAL_VERIFIED=False
oci_runtime=Runtime(ROOT)

def stamp():return datetime.now(timezone.utc).isoformat()
def audit(event:str,job:str,workspace:str,**extra):
    log.info(json.dumps({'event':event,'job_id':job,'workspace':workspace,'at':stamp(),**extra}))
class Run(BaseModel):
    model_config=ConfigDict(extra='forbid')
    files:dict[str,str]=Field(min_length=1,max_length=50)
    profile:Literal['python','javascript','typescript','browser']='python'
    entrypoint:str=Field(default='',max_length=180)
    actions:list[BrowserAction]=Field(default_factory=list,max_length=12)
    idempotency_key:str=Field(min_length=8,max_length=120)
    @model_validator(mode='after')
    def validate_project(self):
        if any(not valid_path(k) or '\x00' in v for k,v in self.files.items()):raise ValueError('Invalid source path/content')
        if sum(len(v.encode()) for v in self.files.values())>20000:raise ValueError('Source byte budget')
        if self.profile=='python':
            if self.entrypoint not in self.files or not self.entrypoint.endswith('.py') or self.actions:raise ValueError('Entrypoint must be a supplied Python file without browser actions')
        else:OCIProject.model_validate(self.model_dump(exclude={'idempotency_key'}))
        return self

def runtime_check(check_seal:bool=True)->dict:
    blockers=[]
    if check_seal and not SEAL_VERIFIED:blockers.append('Runtime isolation preflight has not passed')
    if not ENABLED:blockers.append('Explicit manager opt-in is required')
    if len(KEY)<32:blockers.append('Manager key must contain at least 32 characters')
    if os.getuid()==0:blockers.append('Manager must run as a dedicated non-root user')
    for executable in ('bwrap','prlimit'):
        if not shutil.which(executable):blockers.append(executable+' is required')
    if not PYTHON.is_file() or not Path('/usr/lib/python'+str(PYTHON.name.removeprefix('python'))).is_dir():blockers.append('Supported system Python runtime missing')
    if not Path('/usr/lib/x86_64-linux-gnu/libseccomp.so.2').exists():blockers.append('Linux x86_64 libseccomp runtime required')
    return {'enabled':not blockers,'profile':'python-single-process-v1','blockers':blockers,
            'limits':{'wall_seconds':LIMIT_SECONDS,'cpu_seconds':8,'memory_bytes':512*1024*1024,'processes':1,'network':'none','artifact_bytes':20000,'source_bytes':20000},
            'browser_enabled':oci_runtime.capabilities()['browser']['enabled'],
            'javascript_enabled':oci_runtime.capabilities()['javascript']['enabled'],
            'typescript_enabled':oci_runtime.capabilities()['typescript']['enabled'],
            'profiles':{'python':{'enabled':not blockers,'blockers':blockers},**oci_runtime.capabilities()}}

def auth(request:Request)->str:
    header=request.headers.get('authorization','')
    supplied=header.removeprefix('Bearer ')
    if not header.startswith('Bearer ') or len(KEY)<32 or not hmac.compare_digest(supplied.encode(),KEY.encode()):raise HTTPException(401,'Invalid manager authentication')
    workspace=request.headers.get('x-foxory-workspace','')
    if not re.fullmatch('[A-Za-z0-9_-]{1,64}',workspace):raise HTTPException(400,'Invalid workspace scope')
    return workspace

def job_path(id:str):
    if not re.fullmatch('[a-f0-9]{64}',id):raise HTTPException(404,'Sandbox job not found')
    return ROOT/(id+'.json')
def save(data:dict):
    ROOT.mkdir(mode=0o700,parents=True,exist_ok=True)
    path=job_path(data['id']);temporary=path.with_suffix('.'+secrets.token_hex(8)+'.tmp')
    descriptor=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(descriptor,'w') as output:
        json.dump(data,output);output.flush();os.fsync(output.fileno())
    os.replace(temporary,path)
    descriptor=os.open(ROOT,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(descriptor)
    finally:os.close(descriptor)
def load(id:str,workspace:str):
    path=job_path(id)
    if not path.is_file():raise HTTPException(404,'Sandbox job not found')
    data=json.loads(path.read_text())
    if data['workspace']!=workspace:raise HTTPException(404,'Sandbox job not found')
    return data

def command(work:Path):
    # Bind only trusted system runtime libraries, this task's read-only source and
    # the fixed bootstrap. The manager state, host /etc, /home, /workspace, /proc,
    # sockets, environment and other tasks are absent from the mount namespace.
    return ['prlimit','--as=536870912','--cpu=8','--fsize=1048576','--nofile=32','--core=0','--',
        'bwrap','--unshare-all','--die-with-parent','--new-session','--cap-drop','ALL',
        '--hostname','foxory-sandbox','--ro-bind',str(PYTHON),'/usr/bin/python3',
        '--ro-bind','/usr/lib/python'+PYTHON.name.removeprefix('python'),'/usr/lib/python'+PYTHON.name.removeprefix('python'),
        '--ro-bind','/usr/lib/x86_64-linux-gnu','/usr/lib/x86_64-linux-gnu',
        '--symlink','usr/lib','/lib','--symlink','usr/lib/x86_64-linux-gnu','/lib64',
        '--ro-bind',str(work),'/work','--ro-bind',str(BOOTSTRAP),'/runner.py',
        '--dev','/dev','--dir','/tmp','--ro-bind',str(work.parent/'output'),'/out',
        *[arg for name in ('result.txt','result.json','result.csv','result.md') for arg in ('--bind',str(work.parent/'output'/name),'/out/'+name)],
        '--remount-ro','/','--clearenv','--setenv','LANG','C.UTF-8','--setenv','HOME','/tmp',
        '/usr/bin/python3','-I','-B','/runner.py']

def kill(process):
    if process.returncode is None:
        with contextlib.suppress(ProcessLookupError):os.killpg(process.pid,signal.SIGKILL)

async def execute(id:str,workspace:str,body:Run):
    process=None
    try:
        async with slots:
            data=load(id,workspace)
            if data['status']=='cancelled':return
            with tempfile.TemporaryDirectory(prefix='foxory-sandbox-') as temporary:
                work=Path(temporary)/'source';work.mkdir()
                output=Path(temporary)/'output';output.mkdir()
                for name in ('result.txt','result.json','result.csv','result.md'):(output/name).touch()
                for name,text in body.files.items():
                    path=work/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
                data.update(status='running',started_at=stamp());save(data);audit('started',id,workspace)
                spawning=asyncio.create_task(asyncio.create_subprocess_exec(*command(work),'/work/'+body.entrypoint,
                    stdin=asyncio.subprocess.DEVNULL,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,
                    env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'},start_new_session=True))
                try:process=await asyncio.shield(spawning)
                except asyncio.CancelledError:
                    process=await spawning
                    raise
                processes[id]=process
                async def read(pipe,label):
                    content=bytearray()
                    while part:=await pipe.read(4096):
                        content.extend(part)
                        if len(content)>MAX_LOG:raise ValueError('Execution output budget exceeded')
                        # Bounded incremental persisted output, visible without browser sessions.
                        current=load(id,workspace)
                        if current['status']=='cancelled':raise asyncio.CancelledError()
                        current[label]=content.decode('utf-8','replace');save(current)
                    return content.decode('utf-8','replace')
                async with asyncio.timeout(LIMIT_SECONDS):
                    async with asyncio.TaskGroup() as group:
                        out=group.create_task(read(process.stdout,'stdout'))
                        err=group.create_task(read(process.stderr,'stderr'))
                        await process.wait()
                data=load(id,workspace)
                artifacts={};text=out.result()
                # Read only the four files created by the manager. The source
                # mount and output directory were read-only; code could write
                # these inodes but could not replace them with links or devices.
                total=0
                for name in ('result.txt','result.json','result.csv','result.md'):
                    path=output/name
                    if path.is_symlink() or not path.is_file():raise ValueError('Artifact type changed')
                    with path.open('rb') as stream:decoded=stream.read(20001)
                    if not decoded:continue  # Unwritten output slots are not generated artifacts.
                    total+=len(decoded)
                    if total>20000:raise ValueError('Artifact byte budget')
                    decoded_text=decoded.decode('utf-8')
                    if '\x00' in decoded_text:raise ValueError('Binary artifact rejected')
                    if name.endswith('.json') and decoded_text.strip():json.loads(decoded_text)
                    if name.endswith('.csv'):
                        for cells in csv.reader(io.StringIO(decoded_text)):
                            for cell in cells:
                                value=cell.lstrip()
                                if value.startswith(('=','+','-','@')):
                                    try:numeric=float(value)
                                    except ValueError:raise ValueError('Active spreadsheet formula rejected')
                                    if not math.isfinite(numeric):raise ValueError('Unsafe spreadsheet numeric value')
                    artifacts[name]={'base64':base64.b64encode(decoded).decode(),'sha256':hashlib.sha256(decoded).hexdigest(),'size':len(decoded)}
                data.update(status='completed' if process.returncode==0 else 'failed',exit_code=process.returncode,stdout=text,stderr=err.result(),artifacts=artifacts,finished_at=stamp())
                save(data);audit(data['status'],id,workspace,exit_code=process.returncode)
    except asyncio.CancelledError:
        data=load(id,workspace);data.update(status='cancelled',finished_at=stamp());save(data);audit('cancelled',id,workspace)
    except Exception as error:
        data=load(id,workspace);data.update(status='failed',error=type(error).__name__+': '+str(error)[:500],finished_at=stamp());save(data);audit('failed',id,workspace,error_type=type(error).__name__)
    finally:
        async def cleanup_python():
            try:
                if process:
                    kill(process)
                    with contextlib.suppress(Exception):await asyncio.wait_for(process.wait(),3)
            finally:processes.pop(id,None);tasks.pop(id,None)
        cleanup=asyncio.create_task(cleanup_python())
        try:await asyncio.shield(cleanup)
        except asyncio.CancelledError:await cleanup;raise


async def execute_oci(id:str,workspace:str,body:Run):
    try:
        async with slots:
            data=load(id,workspace)
            if data['status'] not in {'queued','running'}:return
            data.update(status='running',started_at=stamp());save(data);audit('oci.started',id,workspace,profile=body.profile)
            async def progress(message):
                current=load(id,workspace)
                if current['status']=='cancelling':raise asyncio.CancelledError()
                text=current.get('stdout','')+message
                if len(text)>32000:raise ValueError('Persisted execution log budget')
                current['stdout']=text;save(current)
            result=await oci_runtime.run(id,OCIProject.model_validate(body.model_dump(exclude={'idempotency_key'})),progress)
            data=load(id,workspace);data.update(result,finished_at=stamp());save(data)
            audit('oci.'+data['status'],id,workspace,exit_code=data.get('exit_code'))
    except asyncio.CancelledError:
        data=load(id,workspace);data.update(status='cancelled',finished_at=stamp());save(data);audit('oci.cancelled',id,workspace)
    except Exception as error:
        data=load(id,workspace);data.update(status='failed',error=type(error).__name__+': '+str(error)[:500],finished_at=stamp());save(data)
        audit('oci.failed',id,workspace,error_type=type(error).__name__)
    finally:tasks.pop(id,None)


PREFLIGHT = """import os, socket, resource
assert os.getuid()!=0
assert resource.getrlimit(resource.RLIMIT_AS)==(536870912,536870912)
assert resource.getrlimit(resource.RLIMIT_CPU)==(8,8)
for operation in (lambda:socket.socket(), lambda:os.fork(), lambda:open('/etc/passwd'), lambda:open('/tmp/escape','w'), lambda:open('/work/escape','w'), lambda:open('/out/new-file','w')):
    try:operation()
    except OSError:pass
    else:raise RuntimeError('Isolation check failed')
try:resource.setrlimit(resource.RLIMIT_AS,(1073741824,1073741824))
except (ValueError,OSError):pass
else:raise RuntimeError('Memory hard limit bypass')
print('FOXORY_ISOLATION_OK')
"""

@contextlib.asynccontextmanager
async def lifespan(app):
    global SEAL_VERIFIED,oci_runtime
    if not log.handlers:
        handler=logging.StreamHandler();handler.setFormatter(logging.Formatter('%(message)s'));log.addHandler(handler)
    log.setLevel(logging.INFO);log.propagate=False
    SEAL_VERIFIED=False
    oci_runtime=Runtime(ROOT)
    ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)
    if ROOT.stat().st_mode & 0o077 or ROOT.stat().st_uid!=os.getuid():raise RuntimeError('Manager data directory must be private (0700)')
    lock=(ROOT/'.lock').open('a')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close();raise RuntimeError('Only one manager process may use this data directory')
    await oci_runtime.startup(authorized=ENABLED and len(KEY)>=32 and os.getuid()!=0)
    # A restart never replays code silently. Explicit fresh request is required.
    for path in ROOT.glob('*.json'):
        data=json.loads(path.read_text())
        if data['status'] in {'queued','running','cancelling'}:
            data.update(status='interrupted',error='Manager restarted; submit a new reviewed run',finished_at=stamp());save(data);audit('recovered.interruption',data['id'],data['workspace'])
    if runtime_check(check_seal=False)['enabled']:
        probe=Run(files={'probe.py':PREFLIGHT},entrypoint='probe.py',idempotency_key='internal-preflight')
        probe_id=secrets.token_hex(32)
        save({'id':probe_id,'workspace':'internal','status':'queued'})
        await execute(probe_id,'internal',probe)
        result=load(probe_id,'internal')
        SEAL_VERIFIED=result['status']=='completed' and 'FOXORY_ISOLATION_OK' in result['stdout']
        job_path(probe_id).unlink()
        if not SEAL_VERIFIED:audit('preflight.failed',probe_id,'internal',execution_enabled=False)
    async def reconcile_orphans():
        while True:
            await asyncio.sleep(3)
            try:
                for orphan in await oci_runtime.recover(frozenset(tasks)):
                    audit('oci.orphan.recovered',orphan,'internal')
            except Exception:
                oci_runtime.disable('OCI orphan reconciliation failed; execution quarantined')
                audit('oci.orphan.failed','none','internal')
                return
    reconciler=asyncio.create_task(reconcile_orphans()) if shutil.which('podman') else None
    try:yield
    finally:
        if reconciler:
            reconciler.cancel()
            await asyncio.gather(reconciler,return_exceptions=True)
        SEAL_VERIFIED=False
        pending=list(tasks.values())
        for task in pending:
            if not task.cancelling():task.cancel()
        await asyncio.gather(*pending,return_exceptions=True)
        lock.close()
app=FastAPI(title='FOXORY authenticated sandbox manager',lifespan=lifespan)
@app.middleware('http')
async def body_limit(request:Request,call_next):
    if request.method=='POST':
        size=0;chunks=[]
        async for chunk in request.stream():
            size+=len(chunk)
            if size>70000:return Response('Manager request byte budget',413)
            chunks.append(chunk)
        request._body=b''.join(chunks)
    return await call_next(request)

@app.get('/v1/health')
def health(workspace:str=Depends(auth)):return runtime_check()
@app.post('/v1/jobs',status_code=201)
async def create(body:Run,workspace:str=Depends(auth)):
    caps=runtime_check()
    if not caps['profiles'][body.profile]['enabled']:raise HTTPException(503,caps['profiles'][body.profile])
    # Preserve legacy Python idempotency digests across the protocol extension.
    request=body.model_dump(exclude={'profile','actions'}) if body.profile=='python' else body.model_dump()
    digest=hashlib.sha256(json.dumps(request,sort_keys=True).encode()).hexdigest()
    id=hashlib.sha256((workspace+':'+body.idempotency_key).encode()).hexdigest()
    if job_path(id).exists():
        data=load(id,workspace)
        if data['request_hash']!=digest:raise HTTPException(409,'Idempotency key reused with different inputs')
        return data
    if len(tasks)>=8:raise HTTPException(429,'Manager queue limit')
    if sum(json.loads(job_path(task_id).read_text())['workspace']==workspace for task_id in tasks)>=4:raise HTTPException(429,'Workspace queue limit')
    if len(list(ROOT.glob('*.json')))>=500:raise HTTPException(507,'Manager history quota reached; administrator retention cleanup required')
    data={'id':id,'workspace':workspace,'request_hash':digest,'status':'queued','created_at':stamp(),'profile':'python-single-process-v1' if body.profile=='python' else body.profile,'stdout':'','stderr':'','artifacts':{}}
    save(data);audit('submitted',id,workspace);tasks[id]=asyncio.create_task(execute(id,workspace,body) if body.profile=='python' else execute_oci(id,workspace,body))
    tasks[id].add_done_callback(lambda _:tasks.pop(id,None))
    return data
@app.get('/v1/jobs/{id}')
def inspect(id:str,workspace:str=Depends(auth)):return load(id,workspace)
@app.post('/v1/jobs/{id}/cancel')
async def cancel(id:str,workspace:str=Depends(auth)):
    data=load(id,workspace)
    if data['status'] in {'queued','running','cancelling'}:
        data.update(status='cancelling' if data.get('profile')!='python-single-process-v1' else 'cancelled',finished_at=stamp());save(data)
        if id in tasks:
            if not data.get('started_at'):data.update(status='cancelled');save(data)
            if not tasks[id].cancelling():tasks[id].cancel()
        if id in processes:kill(processes[id])
        audit('cancel.request',id,workspace)
    return data
