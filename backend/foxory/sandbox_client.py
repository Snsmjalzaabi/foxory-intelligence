"""Authenticated manager protocol only. No local code or shell execution here."""
import asyncio
import os
import hashlib
import json
from urllib.parse import urlsplit
import httpx
from .scope import workspace_id

def settings():
    url=os.getenv('FOXORY_SANDBOX_URL','').rstrip('/')
    key=os.getenv('FOXORY_SANDBOX_KEY','')
    parsed=urlsplit(url)
    if (os.getenv('FOXORY_ENABLE_SANDBOX','0')!='1' or len(key)<32
        or parsed.scheme not in {'http','https'} or parsed.hostname not in {'localhost','127.0.0.1','::1','sandbox-manager','host.docker.internal'}
        or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment):
        raise PermissionError('Sandbox is disabled or its trusted local manager endpoint is not configured')
    return url,key

def transport():
    url,key=settings()
    return httpx.AsyncClient(base_url=url,headers={'Authorization':'Bearer '+key,'X-Foxory-Workspace':workspace_id.get()},
                             timeout=3,trust_env=False,follow_redirects=False)

async def capabilities():
    try:
        async with transport() as client:
            response=await client.get('/v1/health');response.raise_for_status();return response.json()
    except (PermissionError,httpx.HTTPError):
        return {'enabled':False,'blockers':['Configure and verify the separate local sandbox manager to enable Python execution.'],
                'browser_enabled':False,'javascript_enabled':False}

async def run_python(args:dict,key:str):
    id=None;terminal=False
    async with transport() as client:
        try:
            response=await client.post('/v1/jobs',json={'files':args['files'],'entrypoint':args['entrypoint'],'idempotency_key':key})
            response.raise_for_status();result=response.json();id=result['id']
            async with asyncio.timeout(23):
                while result['status'] in {'queued','running'}:
                    await asyncio.sleep(.2)
                    response=await client.get('/v1/jobs/'+id);response.raise_for_status();result=response.json()
            terminal=True
            return {k:v for k,v in result.items() if k in {'id','profile','status','exit_code','artifacts','error'}}|{
                'stdout':result.get('stdout','')[-8000:],'stderr':result.get('stderr','')[-8000:],
                'logs_truncated':len(result.get('stdout',''))>8000 or len(result.get('stderr',''))>8000,
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
