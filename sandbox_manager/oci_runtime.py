"""Rootless OCI lifecycle boundary. No generated program runs on the manager host."""
from __future__ import annotations
import asyncio
import contextlib
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from . import oci
from foxory.sandbox_protocol import OCIProject, validate_artifacts

WALL_SECONDS=45
MAX_OUTPUT=100000
log=logging.getLogger('foxory.sandbox.oci')

def diagnostic(event:str,detail:str):
    key=os.getenv('FOXORY_SANDBOX_KEY','')
    if key:detail=detail.replace(key,'[redacted]')
    log.warning(json.dumps({'event':event,'detail':detail[-1500:]}))

class Runtime:
    def __init__(self, root:Path):
        self.root=root
        self.owner=hashlib.sha256((str(root.resolve())+':'+str(os.getuid())).encode()).hexdigest()[:32]
        self.image=os.getenv('FOXORY_SANDBOX_OCI_IMAGE','')
        self.opt_in=os.getenv('FOXORY_SANDBOX_OCI_ENABLED','0')=='1'
        self.verified=False
        self.blockers=['OCI profiles require explicit opt-in and startup isolation verification']
        self.processes:dict[str,asyncio.subprocess.Process]={}
        self.quarantine=root/'.oci-quarantined'

    def capabilities(self):
        enabled=self.verified and self.opt_in and not self.quarantine.exists()
        return {p:{'enabled':enabled,'blockers':[] if enabled else self.blockers,
                   'limits':{'wall_seconds':WALL_SECONDS,'memory_bytes':1073741824,'pids':128,'cpus':1,
                             'network':'offline fixture only' if p=='browser' else 'none','artifact_bytes':20000},
                   'image':self.image if enabled else None} for p in ('javascript','typescript','browser')}

    async def spawn(self,*args,**kwargs):
        return await asyncio.create_subprocess_exec(*args,**kwargs)

    async def cli(self,*args:str,timeout:float=10,limit:int=64000)->tuple[int,str,str]:
        process=await self.spawn('podman','--remote=false',*args,
            stdin=asyncio.subprocess.DEVNULL,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
        async def read(pipe):
            result=bytearray()
            while chunk:=await pipe.read(4096):
                result.extend(chunk)
                if len(result)>limit:raise ValueError('Runtime control output budget')
            return result.decode('utf8','replace')
        try:
            async with asyncio.timeout(timeout):
                async with asyncio.TaskGroup() as group:
                    out=group.create_task(read(process.stdout));err=group.create_task(read(process.stderr))
                    await process.wait()
            return process.returncode,out.result(),err.result()
        finally:
            if process.returncode is None:process.kill()
            await process.wait()

    async def remove(self,task_id:str):
        if not re.fullmatch('[a-f0-9]{64}',task_id):raise ValueError('Invalid container task ID')
        name='foxory-task-'+task_id
        # Check labels first; never remove a same-name container owned by others.
        rc,out,_=await self.cli('container','inspect',name,'--format','{{json .Config.Labels}}')
        if rc:
            exists,_,_=await self.cli('container','exists',name)
            if exists==1:return
            raise RuntimeError('Cannot establish container ownership/absence')
        labels=json.loads(out)
        if labels.get('io.foxory.manager')!=self.owner or labels.get('io.foxory.task')!=task_id:
            raise PermissionError('Container ownership mismatch')
        await self.cli('rm','--force','--time=0',name)
        exists,_,_=await self.cli('container','exists',name)
        if exists!=1:raise RuntimeError('Container cleanup was not established')

    async def recover(self,active_ids=frozenset()):
        rc,out,err=await self.cli('ps','--all','--filter','label=io.foxory.manager='+self.owner,'--format','json')
        if rc:
            diagnostic('oci.enumeration.failed',err)
            raise RuntimeError('Cannot enumerate manager-owned containers')
        rows=json.loads(out)
        if not isinstance(rows,list) or len(rows)>500:raise RuntimeError('Orphan container enumeration budget')
        recovered=[]
        for row in rows:
            names=row.get('Names',[])
            if isinstance(names,str):names=[names]
            for name in names:
                match=re.fullmatch('foxory-task-([a-f0-9]{64})',name)
                if not match:raise RuntimeError('Unexpected manager-owned container name')
                if match[1] not in active_ids:
                    await self.remove(match[1]);recovered.append(match[1])
        return recovered

    def disable(self,reason:str):
        self.verified=False;self.blockers=[reason]
        self.root.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.quarantine.write_text(reason);self.quarantine.chmod(0o600)

    async def startup(self,*,authorized:bool):
        self.verified=False
        # Recovery applies even after opt-out; never silently leave owned workers.
        if shutil.which('podman'):
            try:
                await self.recover()
                for stage in self.root.glob('foxory-oci-*'):
                    if stage.is_symlink() or not stage.is_dir() or stage.stat().st_uid!=os.getuid():raise RuntimeError('Unsafe orphan staging ownership')
                    shutil.rmtree(stage)
            except Exception as error:
                diagnostic('oci.recovery.failed',type(error).__name__+': '+str(error))
                self.disable('OCI orphan cleanup failed; operator intervention required');return
        if not self.opt_in:return
        if not authorized or not re.fullmatch('sha256:[a-f0-9]{64}',self.image):
            self.blockers=['OCI requires manager opt-in, non-root authentication and an immutable image ID'];return
        # The reviewed fixed probes check controls for the exact configured image.
        script=Path(__file__).resolve().parents[1]/'scripts/verify_oci_runtime.py'
        process=await self.spawn(sys.executable,str(script),'--image',self.image,'--owner',self.owner,
            stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.DEVNULL)
        try:
            async with asyncio.timeout(160):
                output=await process.stdout.read(64001)
                if len(output)>64000:raise ValueError('Preflight output budget')
                await process.wait()
            report=json.loads(output)
            if process.returncode or report.get('status')!='fixed_probes_passed':raise RuntimeError('Isolation probes did not pass')
            if {x['profile'] for x in report['evidence'] if x.get('fixture_passed')}!={'javascript','typescript','browser'}:
                raise RuntimeError('Incomplete profile verification')
            self.quarantine.unlink(missing_ok=True);self.verified=True;self.blockers=[]
        except Exception:
            self.blockers=['OCI active isolation preflight failed; consult Ubuntu validation checklist']
        finally:
            if process.returncode is None:process.kill()
            await process.wait()
            # Also catch any owned worker left by interrupted preflight/previous runs.
            try:await self.recover()
            except Exception:self.disable('OCI cleanup after preflight failed')

    async def run(self,task_id:str,project:OCIProject,progress)->dict:
        if not self.capabilities()[project.profile]['enabled']:raise PermissionError('OCI profile disabled')
        process=None;result=None;stderr='';events=[]
        # Staging stays until the whole container has been removed, including children.
        with tempfile.TemporaryDirectory(prefix='foxory-oci-',dir=self.root) as directory:
            root=Path(directory);source=root/'source';source.mkdir()
            for name,text in project.files.items():
                target=source/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text)
            request=root/'request.json';request.write_text(project.model_dump_json());request.chmod(0o600)
            try:
                # Finish container creation before observing cancellation, so cleanup
                # cannot race an engine that has not registered the name yet.
                args=oci.command(image=self.image,task_id=task_id,source=source,request=request,
                                 profile=project.profile,owner=self.owner)
                args=args[2:];args[0]='create'
                creating=asyncio.create_task(self.cli(*args,timeout=15))
                try:created=await asyncio.shield(creating)
                except asyncio.CancelledError:await creating;raise
                if created[0]:raise RuntimeError('OCI container creation failed: '+created[2][-1000:])
                spawning=asyncio.create_task(self.spawn('podman','--remote=false','start','--attach',
                    'foxory-task-'+task_id,stdin=asyncio.subprocess.DEVNULL,
                    stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE))
                try:process=await asyncio.shield(spawning)
                except asyncio.CancelledError:process=await spawning;raise
                self.processes[task_id]=process
                async def output():
                    nonlocal result
                    total=0
                    while line:=await process.stdout.readline():
                        total+=len(line)
                        if total>MAX_OUTPUT or len(line)>64000:raise ValueError('Worker output budget')
                        frame=json.loads(line)
                        if not isinstance(frame,dict):raise ValueError('Invalid worker frame')
                        if frame.get('event')=='progress':
                            if result is not None:raise ValueError('Progress after terminal result')
                            message=frame.get('message')
                            if not isinstance(message,str) or len(message)>32000 or len(events)>=80:raise ValueError('Progress budget')
                            events.append(message);await progress(message)
                        else:
                            if result is not None:raise ValueError('Duplicate worker result')
                            result=frame
                async def errors():
                    nonlocal stderr
                    content=bytearray()
                    while part:=await process.stderr.read(4096):
                        content.extend(part)
                        if len(content)>32000:raise ValueError('Worker error-output budget')
                    stderr=content.decode('utf8','replace')
                async with asyncio.timeout(WALL_SECONDS):
                    async with asyncio.TaskGroup() as group:
                        group.create_task(output());group.create_task(errors());await process.wait()
                if result is None:
                    return {'status':'failed','exit_code':process.returncode,'error':'Worker exited without a validated result','stderr':stderr[-8000:],'artifacts':{}}
                if set(result)-{'event','exit_code','stdout','artifacts'}:raise ValueError('Invalid worker envelope')
                if type(result.get('exit_code')) is not int or not isinstance(result.get('stdout'),str) or len(result['stdout'])>32000:
                    raise ValueError('Invalid worker result/logs')
                artifacts=validate_artifacts(result.get('artifacts',{}),allow_png=project.profile=='browser')
                return {'status':'completed' if process.returncode==result['exit_code']==0 else 'failed',
                    'exit_code':process.returncode or result['exit_code'],'stdout':result['stdout'][-8000:],
                    'stderr':stderr[-8000:],'artifacts':artifacts,'events':events[-20:]}
            finally:
                # Do not kill the launcher before it has stopped creating containers.
                # Otherwise a cancelled podman client may leave a late-starting orphan.
                async def cleanup():
                    if process and process.returncode is None:
                        process.terminate()
                        try:await asyncio.wait_for(process.wait(),3)
                        except TimeoutError:process.kill();await process.wait()
                    try:await self.remove(task_id)
                    except Exception:
                        self.disable('OCI cleanup failed; execution quarantined')
                        raise
                    finally:self.processes.pop(task_id,None)
                task=asyncio.create_task(cleanup())
                try:await asyncio.shield(task)
                except asyncio.CancelledError:await task;raise
