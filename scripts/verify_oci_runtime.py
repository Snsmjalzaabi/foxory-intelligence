#!/usr/bin/env python3
"""Opt-in rootless OCI integration probes; never enables application profiles.

Run as the manager account: python3 scripts/verify_oci_runtime.py --image sha256:...
Requires Pydantic (use the project venv). Runs only fixed reviewed fixtures.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sandbox_manager.capabilities import inspect_host
from sandbox_manager.oci import OCIProject, command

PROBE = '''import fs from 'node:fs';
import assert from 'node:assert/strict';
import os from 'node:os';
assert.equal(process.getuid(),1000);
const status=fs.readFileSync('/proc/self/status','utf8');
for(const field of ['CapInh','CapPrm','CapEff','CapBnd','CapAmb']) {
  const value=status.match(new RegExp('^'+field+':\\\\s+([0-9a-f]+)$','m'));
  assert.ok(value,'Missing '+field);
  assert.equal(BigInt('0x'+value[1]),0n,field+' must be empty for JS/TS');
}
assert.match(status,/^NoNewPrivs:\\s+1$/m);
assert.match(status,/^Seccomp:\\s+2$/m);
assert.equal(fs.readFileSync('/sys/fs/cgroup/memory.max','utf8').trim(),'1073741824');
assert.equal(fs.readFileSync('/sys/fs/cgroup/pids.max','utf8').trim(),'128');
const [quota,period]=fs.readFileSync('/sys/fs/cgroup/cpu.max','utf8').trim().split(/\\s+/).map(Number);
assert.equal(quota/period,1);
// Check open-for-write denial without changing any quota or process membership.
for(const file of ['memory.max','pids.max','cpu.max','cgroup.procs']) {
  try {
    const fd=fs.openSync('/sys/fs/cgroup/'+file,fs.constants.O_WRONLY);
    fs.closeSync(fd);throw Error('Writable resource control: '+file);
  } catch(error) {
    assert.ok(['EROFS','EACCES','EPERM'].includes(error.code),'Resource controls must deny write access: '+file);
  }
}
for(const file of ['/etc/foxory-escape','/work/escape','/root/escape']) {
  assert.throws(()=>fs.writeFileSync(file,'escape'));
}
assert.equal(fs.existsSync('/run/docker.sock'),false);
assert.equal(fs.existsSync('/var/run/docker.sock'),false);
assert.equal(process.env.FOXORY_SANDBOX_KEY,undefined);
assert.deepEqual(Object.keys(os.networkInterfaces()),['lo']);
fs.writeFileSync('/out/result.json',JSON.stringify({isolation_probe:'passed'}));
console.log('FOXORY_OCI_CONTROLS_OK');
'''
SITE = '''<!doctype html><html><body><input id="name"><button id="show"
onclick="document.querySelector('#result').textContent=document.querySelector('#name').value">Show</button>
<p id="result"></p><a download="report.txt" href="/report.txt">Download</a></body></html>'''


def run_probe(image: str, project: OCIProject, owner: str = "") -> dict:
    task_id = secrets.token_hex(32)
    with tempfile.TemporaryDirectory(prefix='foxory-oci-probe-') as temporary:
        root = Path(temporary)
        # The container's mapped manager UID must be able to traverse staging.
        root.chmod(0o700)
        source = root / 'source'
        source.mkdir()
        for name, text in project.files.items():
            target = source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
        request = root / 'request.json'
        request.write_text(project.model_dump_json())
        process = None
        try:
            # Output goes to bounded files, never unbounded communicate() buffers.
            # Container tmpfs/cgroup limits bound producer memory; parent also
            # caps file reads and rejects oversized envelope output.
            with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
                process = subprocess.Popen(command(image=image, task_id=task_id, source=source, request=request,
                                                   profile=project.profile, owner=owner),
                                           stdin=subprocess.DEVNULL, stdout=out, stderr=err)
                try:
                    process.wait(timeout=45)
                except subprocess.TimeoutExpired:
                    raise RuntimeError('OCI probe wall deadline exceeded') from None
                out.seek(0); stdout = out.read(100001)
                err.seek(0); stderr = err.read(8001)
                if len(stdout) > 100000:
                    raise RuntimeError('OCI probe output budget exceeded')
                if process.returncode:
                    raise RuntimeError('OCI probe failed: ' + stderr.decode('utf8', 'replace')[-8000:])
            frames=[json.loads(line) for line in stdout.splitlines() if line.strip()]
            results=[frame for frame in frames if frame.get('event')=='result']
            if len(results)!=1:raise RuntimeError('Expected one terminal worker frame')
            result=results[0]
            if result.get('exit_code') != 0:
                raise RuntimeError('Worker reported failed fixture')
            total = 0
            for name, item in result.get('artifacts', {}).items():
                if name not in {'result.json', 'result.txt', 'screenshot-1.png'}:
                    raise RuntimeError('Unexpected artifact')
                data = base64.b64decode(item['base64'], validate=True)
                total += len(data)
                if total > 20000 or len(data) != item['size'] or hashlib.sha256(data).hexdigest() != item['sha256']:
                    raise RuntimeError('Artifact integrity/budget failure')
            return result
        finally:
            # A stable manager-chosen name, never model/user-supplied runtime flags.
            cleanup = subprocess.run(['podman','--remote=false','rm','--force','--time=0','foxory-task-'+task_id],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
            if process and process.poll() is None:
                process.kill(); process.wait(timeout=5)
            # --rm may already have removed the container. Check actual absence.
            exists = subprocess.run(['podman','--remote=false','container','exists','foxory-task-'+task_id], timeout=10)
            if exists.returncode != 1:
                raise RuntimeError('Cannot establish sandbox cleanup')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', required=True, help='Reviewed local sha256 image ID')
    parser.add_argument('--owner', default='', help=argparse.SUPPRESS)
    args = parser.parse_args()
    host = inspect_host()
    if not host['static_requirements_met']:
        print(json.dumps({'status':'blocked', 'host':host}, indent=2)); return 2
    info = subprocess.run(['podman','--remote=false','info','--format','{{.Host.Security.Rootless}}'],
                          capture_output=True, text=True, timeout=10, check=True)
    if info.stdout.strip() != 'true':
        raise RuntimeError('Rootless Podman is required')
    evidence = []
    for profile, filename, code in [('javascript','probe.js',PROBE),
                                    ('typescript','probe.ts',PROBE+'\nconst value: number = 42;\nif(value!==42)throw Error("TS");')]:
        result = run_probe(args.image, OCIProject(profile=profile, files={filename:code}, entrypoint=filename), args.owner)
        if 'FOXORY_OCI_CONTROLS_OK' not in result['stdout']:
            raise RuntimeError('Missing controls attestation from fixed fixture')
        evidence.append({'profile':profile,'fixture_passed':True})
        print('FOXORY_PROBE_PASSED '+profile, file=sys.stderr, flush=True)
    browser = OCIProject(profile='browser', files={'index.html':SITE,'report.txt':'Controlled fixture download'}, actions=[
        {'action':'navigate','target':'/'}, {'action':'type','target':'#name','text':'FOXORY_BROWSER_OK'},
        {'action':'click','target':'#show'}, {'action':'inspect'}, {'action':'screenshot'},
        {'action':'download','target':'a'},
    ])
    result = run_probe(args.image, browser, args.owner)
    if 'FOXORY_BROWSER_OK' not in result['stdout']:
        raise RuntimeError('Browser interaction did not produce expected page content')
    artifacts = result['artifacts']
    png = base64.b64decode(artifacts['screenshot-1.png']['base64'], validate=True)
    if not png.startswith(b'\x89PNG\r\n\x1a\n'):
        raise RuntimeError('Missing PNG screenshot')
    if base64.b64decode(artifacts['result.txt']['base64']) != b'Controlled fixture download':
        raise RuntimeError('Download mismatch')
    evidence.append({'profile':'browser','fixture_passed':True})
    print('FOXORY_PROBE_PASSED browser', file=sys.stderr, flush=True)
    print(json.dumps({'status':'fixed_probes_passed','evidence':evidence,
                      'application_execution_enabled':False,
                      'warning':'Not comprehensive sandbox security assurance; complete the Ubuntu host acceptance checklist.'},indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
