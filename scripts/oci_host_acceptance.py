#!/usr/bin/env python3
"""Explicit real rootless-manager acceptance; never run generated code on host.

Use a dedicated unprivileged Ubuntu account in a delegated systemd user scope.
Starts a disposable authenticated manager with NEW private state, fixed reviewed
fixtures only, and the explicit immutable local image. Startup probes must pass.
Never enables the owner's application or changes host security/resource policy.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
from pathlib import Path
import platform
import re
import secrets
import signal
import socket
import sys
import time

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sandbox_manager.oci_runtime import Runtime
from sandbox_manager.oci import command
from foxory.sandbox_protocol import OCIProject
from scripts.verify_oci_runtime import SITE

ACTIVE_LIMITS = r'''import fs from 'node:fs';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
const counters=name=>Object.fromEntries(fs.readFileSync('/sys/fs/cgroup/'+name,'utf8').trim().split('\n').map(x=>x.split(/\s+/)).map(([k,v])=>[k,Number(v)]));
const evidence={};
const before=counters('cpu.stat'),start=performance.now();
await Promise.all([1,2,3].map(()=>new Promise((resolve,reject)=>{
 const child=spawn(process.execPath,['-e','const end=Date.now()+1500;while(Date.now()<end){}'],{stdio:'ignore'});
 child.once('error',reject);child.once('close',code=>code===0?resolve():reject(Error('CPU child failed')));
})));
const after=counters('cpu.stat'),elapsed=performance.now()-start;
evidence.cpu={before,after,elapsed_ms:elapsed};
assert.ok(after.nr_throttled>before.nr_throttled,'CPU quota did not throttle competing workers');
assert.ok(after.usage_usec-before.usage_usec<elapsed*1400+300000,'Unexpected aggregate CPU use');
const pidsBefore=counters('pids.events'),children=[];
try {
 for(let i=0;i<150;i++) {
  const child=spawn('/bin/sleep',['10'],{stdio:'ignore'});children.push(child);
  const ok=await new Promise(resolve=>{child.once('spawn',()=>resolve(true));child.once('error',()=>resolve(false));});
  if(!ok)break;
 }
 const pidsAfter=counters('pids.events');
 evidence.pids={before:pidsBefore,after:pidsAfter,current:Number(fs.readFileSync('/sys/fs/cgroup/pids.current','utf8'))};
 assert.ok(pidsAfter.max>pidsBefore.max,'PID quota did not reject process creation');
 assert.ok(evidence.pids.current<=128,'PID quota exceeded');
} finally {
 await Promise.all(children.filter(c=>c.pid).map(c=>new Promise(resolve=>{c.once('close',resolve);c.kill('SIGKILL');})));
}
const memoryBefore=counters('memory.events');
const memoryChild=spawn(process.execPath,['--max-old-space-size=64','-e',"const blocks=[];setInterval(()=>blocks.push(Buffer.alloc(32*1024*1024,1)),15)"],{stdio:'ignore'});
const memoryExit=await new Promise((resolve,reject)=>{memoryChild.once('error',reject);memoryChild.once('close',(code,signal)=>resolve({code,signal}));});
const memoryAfter=counters('memory.events');
evidence.memory={before:memoryBefore,after:memoryAfter,exit:memoryExit};
assert.ok(memoryAfter.oom_kill>memoryBefore.oom_kill,'Missing actual cgroup OOM kill counter');
assert.equal(memoryExit.signal,'SIGKILL');
fs.writeFileSync('/out/result.json',JSON.stringify(evidence));
console.log('FOXORY_ACTIVE_LIMITS_OK');'''

DENIALS = r'''import fs from 'node:fs';
import net from 'node:net';
import assert from 'node:assert/strict';
for(const path of ['/work/escape','/etc/escape','/root/escape'])assert.throws(()=>fs.writeFileSync(path,'no'));
for(const path of ['/run/docker.sock','/var/run/docker.sock','/run/podman/podman.sock'])assert.equal(fs.existsSync(path),false);
assert.equal(process.env.FOXORY_SANDBOX_KEY,undefined);
for(const host of ['169.254.169.254','1.1.1.1','10.0.0.1'])await new Promise((resolve,reject)=>{
 const s=net.connect({host,port:80});s.once('connect',()=>{s.destroy();reject(Error('Unauthorized destination reached'));});
 s.once('error',resolve);s.setTimeout(500,()=>{s.destroy();reject(Error('No explicit network denial'));});
});
console.log('FOXORY_DENIALS_OK');'''

RUNNING = "console.log('FOXORY_RUNNING');setInterval(()=>{},1000);"


async def acceptance(image: str, evidence: Path, transport: str = 'tcp') -> None:
    if os.getuid() == 0 or platform.system() != 'Linux':
        raise ValueError('Dedicated non-root Linux account required')
    if not re.fullmatch(r'sha256:[a-f0-9]{64}', image):
        raise ValueError('Immutable local image ID required')
    if transport not in {'tcp','unix'}:raise ValueError('Invalid manager transport')
    evidence.mkdir(mode=0o700, parents=True, exist_ok=False)
    state = evidence / 'manager-state'
    state.mkdir(mode=0o700)
    runtime = Runtime(state)
    key = secrets.token_urlsafe(40)
    with socket.socket() as reservation:
        reservation.bind(('127.0.0.1', 0))
        port = reservation.getsockname()[1]
    env = {**os.environ, 'FOXORY_SANDBOX_DATA': str(state),
           'FOXORY_SANDBOX_KEY': key, 'FOXORY_SANDBOX_ENABLED': '1',
           'FOXORY_SANDBOX_OCI_ENABLED': '1', 'FOXORY_SANDBOX_OCI_IMAGE': image}
    process = None
    foreign_id = None
    listener = None
    socket_path = evidence / 'manager.sock'
    if transport == 'unix':
        listener = socket.socket(socket.AF_UNIX)
        listener.bind(str(socket_path));listener.listen(128);socket_path.chmod(0o660)
    log = (evidence / 'manager.log').open('xb')
    summary = {'status': 'failed', 'image': image, 'os': platform.platform(), 'transport':transport,
               'checks': [], 'application_execution_enabled': False}
    client = httpx.AsyncClient(base_url=f'http://127.0.0.1:{port}', trust_env=False,
                               timeout=10, headers={'Authorization': 'Bearer ' + key,
                                                    'X-Foxory-Workspace': 'host-fixture'},
                               transport=httpx.AsyncHTTPTransport(uds=str(socket_path),trust_env=False) if listener else None)

    async def request(method, path, **kwargs):
        result = await client.request(method, path, **kwargs)
        result.raise_for_status()
        return result.json()

    async def start():
        nonlocal process
        process = await asyncio.create_subprocess_exec(
            sys.executable, '-m', 'uvicorn', 'sandbox_manager.service:app',
            *(['--fd',str(listener.fileno())] if listener else ['--host','127.0.0.1','--port',str(port)]),
            '--workers', '1', '--no-access-log', cwd=ROOT, env=env, stdout=log, stderr=log,
            pass_fds=(listener.fileno(),) if listener else ())
        deadline = time.monotonic() + 190
        while time.monotonic() < deadline:
            if process.returncode is not None:
                raise RuntimeError('Disposable manager startup failed; inspect private manager.log')
            try:
                response = await client.get('/v1/health', timeout=1)
                if response.status_code == 200:
                    caps = response.json()
                    if not all(caps['profiles'][p]['enabled'] for p in ['javascript', 'typescript', 'browser']):
                        raise RuntimeError('Actual startup isolation probes failed: ' + json.dumps(caps['profiles']))
                    return
            except httpx.HTTPError:
                pass
            await asyncio.sleep(.2)
        raise TimeoutError('Disposable manager startup deadline')

    async def stop(crash=False):
        nonlocal process
        if process and process.returncode is None:
            process.send_signal(signal.SIGKILL if crash else signal.SIGTERM)
            try:
                await asyncio.wait_for(process.wait(), 20)
            except TimeoutError:
                process.kill()
                await process.wait()

    async def submit(code=RUNNING, *, profile='javascript', **extra):
        suffix = 'ts' if profile == 'typescript' else 'js'
        body = {'profile': profile, 'files': {'app.' + suffix: code},
                'entrypoint': 'app.' + suffix, 'idempotency_key': secrets.token_hex(16), **extra}
        return body, await request('POST', '/v1/jobs', json=body)

    async def wait(id, *, marker=None):
        deadline = time.monotonic() + 70
        while time.monotonic() < deadline:
            job = await request('GET', '/v1/jobs/' + id)
            if marker and marker in job.get('stdout', ''):
                return job
            if job['status'] not in {'queued', 'running', 'cancelling'}:
                if marker:
                    raise AssertionError('Job ended before expected live marker: ' + json.dumps(job))
                return job
            await asyncio.sleep(.1)
        raise TimeoutError('Real manager task deadline')

    async def absent(id):
        rc, _, _ = await runtime.cli('container', 'exists', 'foxory-task-' + id)
        assert rc == 1, 'Whole-container cleanup not established'
        assert not list(state.glob('foxory-oci-*')), 'Source/request staging survived terminal state'

    def record(name, **details):
        summary['checks'].append({'name': name, 'passed': True, **details})
        print('FOXORY_HOST_CHECK_PASSED ' + name, flush=True)

    try:
        await start()
        record('actual-startup-js-ts-chromium-probes')
        if listener:
            # Exercise the actual application adapter too, not just the harness
            # HTTP client. Temporary control-process env is never sent to workers.
            from foxory import sandbox_client
            from foxory.scope import workspace_id
            overrides={'FOXORY_ENABLE_SANDBOX':'1','FOXORY_SANDBOX_KEY':key,
                       'FOXORY_SANDBOX_URL':'','FOXORY_SANDBOX_SOCKET':str(socket_path)}
            saved={name:os.environ.get(name) for name in overrides}
            token=workspace_id.set('host-fixture')
            try:
                os.environ.update(overrides)
                caps=await sandbox_client.capabilities()
                assert caps['profiles']['javascript']['enabled']
                result=await sandbox_client.run_profile({'files':{'app.js':"console.log('REAL_UNIX_ADAPTER_OK')"},
                    'entrypoint':'app.js'},secrets.token_hex(16),'javascript')
                assert result['status']=='completed' and 'REAL_UNIX_ADAPTER_OK' in result['stdout'],result
                await absent(result['id'])
                record('actual-application-adapter-unix-authenticated-execution')
            finally:
                workspace_id.reset(token)
                for name,value in saved.items():
                    if value is None:os.environ.pop(name,None)
                    else:os.environ[name]=value
        assert (await client.get('/v1/health', headers={'Authorization': 'Bearer wrong'})).status_code == 401
        for profile in ['javascript', 'typescript']:
            body, job = await submit(DENIALS, profile=profile)
            result = await wait(job['id'])
            assert result['status'] == 'completed' and 'FOXORY_DENIALS_OK' in result['stdout'], result
            assert (await request('POST', '/v1/jobs', json=body))['id'] == job['id']
            assert (await client.get('/v1/jobs/' + job['id'], headers={'X-Foxory-Workspace': 'foreign'})).status_code == 404
            assert (await client.post('/v1/jobs/' + job['id'] + '/cancel', headers={'X-Foxory-Workspace': 'foreign'})).status_code == 404
            body['files'][body['entrypoint']] = '0'
            assert (await client.post('/v1/jobs', json=body)).status_code == 409
            await absent(job['id'])
        record('authentication-idempotency-tenancy-fs-network-js-ts')

        _, job = await submit(ACTIVE_LIMITS)
        result = await wait(job['id'])
        assert result['status'] == 'completed' and 'FOXORY_ACTIVE_LIMITS_OK' in result['stdout'], result
        counters = json.loads(base64.b64decode(result['artifacts']['result.json']['base64'], validate=True))
        await absent(job['id'])
        record('actual-cpu-throttling-pid-denial-memory-oom', counters=counters)

        browser = {'profile': 'browser', 'files': {'index.html': SITE, 'report.txt': 'Controlled fixture download'},
                   'actions': [{'action': 'type', 'target': '#name', 'text': 'FOXORY_HOST_BROWSER'},
                               {'action': 'click', 'target': '#show'}, {'action': 'inspect'},
                               {'action': 'screenshot'}, {'action': 'download', 'target': 'a'}],
                   'entrypoint': '', 'idempotency_key': secrets.token_hex(16)}
        job = await request('POST', '/v1/jobs', json=browser)
        result = await wait(job['id'])
        assert result['status'] == 'completed' and 'FOXORY_HOST_BROWSER' in result['stdout'], result
        assert base64.b64decode(result['artifacts']['result.txt']['base64']) == b'Controlled fixture download'
        (evidence / 'controlled-site.png').write_bytes(base64.b64decode(result['artifacts']['screenshot-1.png']['base64']))
        await absent(job['id'])
        record('authenticated-browser-interaction-screenshot-download')
        browser['actions'] = [{'action': 'navigate', 'target': 'http://169.254.169.254/'}]
        browser['idempotency_key'] = secrets.token_hex(16)
        assert (await client.post('/v1/jobs', json=browser)).status_code == 422
        record('browser-external-navigation-rejected')

        _, running = await submit()
        await wait(running['id'], marker='FOXORY_RUNNING')
        _, queued = await submit()
        assert queued['status'] == 'queued'
        await request('POST', '/v1/jobs/' + queued['id'] + '/cancel')
        assert (await wait(queued['id']))['status'] == 'cancelled'
        await request('POST', '/v1/jobs/' + queued['id'] + '/cancel')
        await request('POST', '/v1/jobs/' + running['id'] + '/cancel')
        assert (await wait(running['id']))['status'] == 'cancelled'
        await absent(running['id'])
        await absent(queued['id'])
        record('running-queued-repeat-cancellation-and-cleanup')

        started = time.monotonic()
        _, job = await submit()
        result = await wait(job['id'])
        elapsed = time.monotonic() - started
        assert result['status'] == 'failed' and elapsed < 60, result
        await absent(job['id'])
        record('infinite-worker-bounded-timeout-and-cleanup', elapsed_seconds=elapsed)

        _, job = await submit()
        await wait(job['id'], marker='FOXORY_RUNNING')
        await stop(crash=True)
        # Fixed, stopped fixture containers: prove label ownership explicitly,
        # including when a crash occurs before a worker was ever started.
        fixture = evidence / 'orphan-fixture'
        fixture.mkdir(mode=0o700)
        source = fixture / 'source'
        source.mkdir(mode=0o700)
        (source / 'app.js').write_text('console.log(42)')
        wire = fixture / 'request.json'
        wire.write_text(OCIProject(profile='javascript', files={'app.js': 'console.log(42)'}, entrypoint='app.js').model_dump_json())
        own_id = secrets.token_hex(32)
        for owner, id in [(runtime.owner, own_id), ('f' * 32, secrets.token_hex(32))]:
            args = command(image=image, task_id=id, source=source, request=wire, profile='javascript', owner=owner)[2:]
            args[0] = 'create'
            rc, _, err = await runtime.cli(*args, timeout=15)
            assert rc == 0, err
            if owner != runtime.owner:
                foreign_id = id  # Only this successfully created fixture may be removed below.
        await start()
        interrupted = await request('GET', '/v1/jobs/' + job['id'])
        assert interrupted['status'] == 'interrupted', interrupted
        await absent(job['id'])
        await absent(own_id)
        assert (await runtime.cli('container', 'exists', 'foxory-task-' + foreign_id))[0] == 0
        record('actual-manager-kill-restart-no-replay-owned-orphan-cleanup')
        record('foreign-owner-container-preserved')
        summary['status'] = 'passed'
    finally:
        await stop()
        await client.aclose()
        try:
            await runtime.recover()
            if foreign_id:
                await runtime.cli('rm', '--force', '--time=0', 'foxory-task-' + foreign_id)
                assert (await runtime.cli('container', 'exists', 'foxory-task-' + foreign_id))[0] == 1
            assert not list(state.glob('foxory-oci-*')), 'Orphan staging remains'
            summary['owned_container_cleanup'] = True
        except Exception as error:
            summary['owned_container_cleanup'] = False
            summary['status'] = 'failed'
            summary['cleanup_error'] = type(error).__name__
        log.close()
        if listener:
            listener.close();socket_path.unlink(missing_ok=True)
        (evidence / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    if summary['status'] != 'passed':
        raise RuntimeError('Host acceptance failed; inspect retained evidence')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', required=True)
    parser.add_argument('--evidence', required=True, type=Path, help='NEW private evidence directory')
    parser.add_argument('--transport',choices=['tcp','unix'],default='tcp')
    args = parser.parse_args()
    os.umask(0o077)
    asyncio.run(acceptance(args.image, args.evidence.resolve(),args.transport))


if __name__ == '__main__':
    main()
