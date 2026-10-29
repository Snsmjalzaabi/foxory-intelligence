"""Verify a pristine core Compose installation in uniquely owned resources.

No owner .env/volumes/application is used. No models or sandbox workers are
downloaded/started. --build uses the canonical Dockerfile; alternatively provide
an already reviewed --image. All test containers/volumes are removed afterward.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import tempfile
import time

import httpx

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument('--build', action='store_true')
    selection.add_argument('--image', help='Existing local application image; does not count as a canonical build')
    parser.add_argument('--evidence', type=Path)
    args = parser.parse_args()
    project = 'foxory-acceptance-'+secrets.token_hex(6)
    token, password = secrets.token_urlsafe(40), secrets.token_hex(30)
    with socket.socket() as reservation:
        reservation.bind(('127.0.0.1', 0)); port = reservation.getsockname()[1]
    env = {**os.environ, 'FOXORY_TOKEN':token, 'POSTGRES_PASSWORD':password,
           'FOXORY_PORT':str(port), 'FOXORY_DATABASE_LAYOUT':'modern', 'SEARXNG_URL':'', 'FOXORY_ENABLE_SANDBOX':'0',
           'FOXORY_SANDBOX_URL':'', 'FOXORY_SANDBOX_KEY':''}
    evidence = {'canonical_build':args.build, 'project':project, 'checks':[], 'sandbox_enabled':False}
    with tempfile.TemporaryDirectory(prefix=project+'-') as directory:
        override = Path(directory)/'override.json'
        override.write_text(json.dumps({'services':{'app':{'image':args.image or project+':test'}}}))
        command = ['docker','--host=unix:///var/run/docker.sock','compose','--env-file',os.devnull,
                   '-p',project,'-f',str(ROOT/'compose.yaml'),'-f',str(override)]
        def compose(*parts, **kwargs):
            return subprocess.run([*command,*parts],env=env,cwd=ROOT,check=True,**kwargs)
        def passed(check):
            evidence['checks'].append(check); print('PASS: '+check,flush=True)
        started = False
        try:
            started = True  # Even a partially successful up needs owned cleanup.
            compose('up','-d','--wait','--wait-timeout','180','--build' if args.build else '--no-build')
            image=subprocess.run(['docker','--host=unix:///var/run/docker.sock','image','inspect',
                                  args.image or project+':test','--format','{{.Id}}'],
                                 env=env,check=True,capture_output=True,text=True).stdout.strip()
            evidence['application_image']=image
            with httpx.Client(base_url=f'http://127.0.0.1:{port}/api',trust_env=False,timeout=30) as client:
                def call(method, path, **kwargs):
                    response = client.request(method,path,**kwargs);response.raise_for_status()
                    return response.json() if 'application/json' in response.headers.get('content-type','') else response
                assert call('GET','/health')['status']=='ok'
                assert client.get('/overview').status_code==401
                identity = call('POST','/auth/setup',json={'username':'compose-test-owner',
                    'password':secrets.token_urlsafe(32),'bootstrap_token':token})
                client.headers['X-CSRF-Token']=identity['csrf']
                me = call('GET','/auth/me');client.headers['X-Workspace-ID']=me['workspace_id']
                passed('pristine Compose startup, health, account and authentication')
                for notice in ['LICENSE','NOTICE','THIRD_PARTY_NOTICES.txt']:
                    actual=compose('exec','-T','app','sha256sum','/usr/share/doc/foxory/'+notice,
                                   capture_output=True,text=True).stdout.split()[0]
                    assert actual==hashlib.sha256((ROOT/notice).read_bytes()).hexdigest()
                passed('canonical image contains readable source license and dependency notices')
                models = call('GET','/models')
                assert models['available'] and models['models']==[]
                assert not call('GET','/computer/capabilities')['enabled']
                passed('Ollama available with no automatic weight download; sandbox absent/disabled')
                memory = call('POST','/records/memory',json={'title':'Disposable persisted fact','data':{'body':'Test only'}})
                doc = call('POST','/documents',files={'file':('compose.txt',b'Fictional Compose installation evidence.','text/plain')})
                assert call('GET',f'/documents/{doc["id"]}/download').content==b'Fictional Compose installation evidence.'
                assert client.post('/documents',files={'file':('invalid.json',b'{','application/json')}).status_code==422
                passed('restricted document parsing, authorized original and invalid-file rejection')
                other = call('POST','/auth/workspaces',json={'name':'Isolated Compose workspace'})
                client.headers['X-Workspace-ID']=other['id']
                assert client.get(f'/documents/{doc["id"]}/download').status_code==404
                client.headers['X-Workspace-ID']=me['workspace_id']
                passed('workspace download isolation')
                compose('restart','app',stdout=subprocess.DEVNULL)
                deadline=time.monotonic()+90
                while time.monotonic()<deadline:
                    try:
                        if client.get('/auth/me',timeout=3).status_code==200:break
                    except httpx.HTTPError:pass
                    time.sleep(.5)
                else:raise RuntimeError('Session did not recover after application restart')
                assert any(row['id']==memory['id'] for row in call('GET','/records/memory'))
                assert call('GET',f'/documents/{doc["id"]}/download').content==b'Fictional Compose installation evidence.'
                version = compose('exec','-T','db','psql','-U','foxory','-d','foxory','-At',
                                  '-c','SELECT version_num FROM alembic_version',capture_output=True,text=True).stdout.strip()
                assert version=='0003',version
                passed('PostgreSQL migrations, account/session, records and originals persist across app restart')
                call('POST','/auth/logout'); assert client.get('/overview').status_code==401
                passed('persisted session can be revoked')
                evidence['status']='passed'
        except Exception as error:
            evidence.update(status='failed',error=type(error).__name__)
            if started:
                logs=subprocess.run([*command,'logs','--no-color','--tail','40'],env=env,cwd=ROOT,
                                    capture_output=True,text=True,timeout=30)
                print(logs.stdout.replace(token,'[REDACTED]').replace(password,'[REDACTED]'))
            raise
        finally:
            if started:
                # Project name is generated here, never accepted as a CLI argument.
                compose('down','--volumes','--remove-orphans',stdout=subprocess.DEVNULL)
                evidence['owned_resources_removed']=True
            payload=json.dumps(evidence,indent=2)
            if args.evidence:args.evidence.write_text(payload+'\n')
            print(payload,flush=True)


if __name__=='__main__':main()
