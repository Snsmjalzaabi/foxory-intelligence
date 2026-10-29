"""Authenticated manager protocol only. No local code or shell execution here."""
import asyncio
import os
import hashlib
import json
from pathlib import Path
import stat
from urllib.parse import urlsplit
import httpx
from .scope import workspace_id
from .sandbox_protocol import validate_artifacts

def settings():
    url=os.getenv('FOXORY_SANDBOX_URL','').rstrip('/')
    key=os.getenv('FOXORY_SANDBOX_KEY','')
    socket=os.getenv('FOXORY_SANDBOX_SOCKET','')
    if socket:
        path=Path(socket)
        if os.getenv('FOXORY_ENABLE_SANDBOX','0')!='1' or len(key)<32 or url:
            raise PermissionError('Explicit sandbox opt-in/key and a single manager transport are required')
        try:
            mode=path.lstat().st_mode;parent=path.parent.lstat().st_mode
            if (not path.is_absolute() or len(socket.encode())>100 or not stat.S_ISSOCK(mode)
                    or mode&0o002 or not stat.S_ISDIR(parent) or parent&0o022):
                raise PermissionError('Manager socket and private parent permissions are not safe')
        except (OSError,ValueError):
            raise PermissionError('Trusted private manager socket is unavailable') from None
        return 'http://sandbox-manager',key
    try:
        parsed=urlsplit(url)
        if parsed.port is not None and not 1<=parsed.port<=65535:raise ValueError('Invalid port')
    except ValueError:
        raise PermissionError('Sandbox trusted local manager endpoint is invalid') from None
    if (os.getenv('FOXORY_ENABLE_SANDBOX','0')!='1' or len(key)<32
        or parsed.scheme not in {'http','https'} or parsed.hostname not in {'localhost','127.0.0.1','::1','sandbox-manager','host.docker.internal'}
        or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment):
        raise PermissionError('Sandbox is disabled or its trusted local manager endpoint is not configured')
    return url,key

def transport():
    url,key=settings()
    socket=os.getenv('FOXORY_SANDBOX_SOCKET','')
    return httpx.AsyncClient(base_url=url,headers={'Authorization':'Bearer '+key,'X-Foxory-Workspace':workspace_id.get()},
                             timeout=3,trust_env=False,follow_redirects=False,
                             transport=httpx.AsyncHTTPTransport(uds=socket,trust_env=False) if socket else None)

async def capabilities():
    try:
        async with transport() as client:
            response=await client.get('/v1/health');response.raise_for_status();return response.json()
    except (PermissionError,httpx.HTTPError):
        return {'enabled':False,'blockers':['Configure and verify the separate local sandbox manager to enable Python execution.'],
                'browser_enabled':False,'javascript_enabled':False}

async def run_python(args:dict,key:str):
    return await run_profile(args,key,'python')

async def run_profile(args:dict,key:str,profile:str):
    if profile not in {'python','javascript','typescript','browser'}:raise ValueError('Invalid sandbox profile')
    id=None;terminal=False
    async with transport() as client:
        try:
            payload={'files':args['files'],'entrypoint':args.get('entrypoint',''),'idempotency_key':key}
            if profile!='python':payload.update(profile=profile,actions=args.get('actions',[]))
            response=await client.post('/v1/jobs',json=payload)
            response.raise_for_status();result=response.json();id=result['id']
            expected=hashlib.sha256((workspace_id.get()+':'+key).encode()).hexdigest()
            if id!=expected or result.get('workspace')!=workspace_id.get():raise PermissionError('Manager task ownership mismatch')
            async with asyncio.timeout(23 if profile=='python' else 100):
                while result['status'] in {'queued','running','cancelling'}:
                    await asyncio.sleep(.2)
                    response=await client.get('/v1/jobs/'+id);response.raise_for_status();result=response.json()
            if result.get('id')!=expected or result.get('workspace')!=workspace_id.get():raise PermissionError('Manager task ownership mismatch')
            expected_profile='python-single-process-v1' if profile=='python' else profile
            if result.get('profile')!=expected_profile:raise PermissionError('Manager profile mismatch')
            if result.get('status') not in {'completed','failed','cancelled','interrupted'}:raise ValueError('Invalid manager terminal state')
            result['artifacts']=validate_artifacts(result.get('artifacts',{}),allow_png=profile=='browser')
            terminal=True
            return {k:v for k,v in result.items() if k in {'id','profile','status','exit_code','artifacts','error'}}|{
                'stdout':result.get('stdout','')[-8000:],'stderr':result.get('stderr','')[-8000:],
                'logs_truncated':len(result.get('stdout',''))>8000 or len(result.get('stderr',''))>8000,
                'workspace':workspace_id.get(),
                'source_sha256':hashlib.sha256(json.dumps(args['files'],sort_keys=True).encode()).hexdigest(),
                'warning':'Untrusted program output. Exit code alone does not prove test adequacy or correctness.'}
        finally:
            if id and not terminal:
                async def cancel():
                    try:await client.post('/v1/jobs/'+id+'/cancel')
                    except httpx.HTTPError:pass
                task=asyncio.create_task(cancel())
                try:await asyncio.shield(task)
                except asyncio.CancelledError:
                    await task
                    raise
