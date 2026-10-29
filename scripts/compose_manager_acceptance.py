#!/usr/bin/env python3
"""Opt-in ephemeral GitHub Ubuntu: real Compose + systemd/rootless manager.

Provisioner requires Docker/sudo; the separate manager account never receives
Docker access. No generated code executes in the controller or application.
Only its own fixture approvals/resources are used. Not an owner deployment.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import pwd
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import zipfile

import httpx
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker-image',required=True)
    parser.add_argument('--ipc',required=True,type=Path)
    parser.add_argument('--evidence',required=True,type=Path)
    args=parser.parse_args()
    if os.environ.get('GITHUB_ACTIONS')!='true' or os.environ.get('RUNNER_ENVIRONMENT')!='github-hosted':
        raise PermissionError('This provisioner is only for the disposable hosted fixture VM')
    import re
    if not re.fullmatch(r'sha256:[a-f0-9]{64}',args.worker_image):raise ValueError('Immutable worker required')
    account='foxory-ci-sandbox';user=pwd.getpwnam(account)
    groups=subprocess.check_output(['id','-Gn',account],text=True).split()
    if user.pw_uid==0 or set(groups)&{'docker','sudo','wheel','root'}:raise PermissionError('Manager account must be dedicated/unprivileged')
    import stat
    if (args.ipc.parent!=Path('/run') or not args.ipc.name.startswith('foxory-fixture-') or args.ipc.is_symlink()
            or args.ipc.stat().st_uid!=user.pw_uid or stat.S_IMODE(args.ipc.stat().st_mode)!=0o750):
        raise PermissionError('Dedicated private fixture IPC directory required')
    os.umask(0o077);args.evidence.mkdir(mode=0o700,parents=True,exist_ok=False)
    key=secrets.token_urlsafe(40);token=secrets.token_urlsafe(40);password=secrets.token_hex(30)
    project='foxory-host-'+secrets.token_hex(6)
    manager_home=Path(user.pw_dir);manager_source=manager_home/'foxory-intelligence'
    manager_env={
        'FOXORY_SANDBOX_ENABLED':'1','FOXORY_SANDBOX_OCI_ENABLED':'1',
        'FOXORY_SANDBOX_KEY':key,'FOXORY_SANDBOX_OCI_IMAGE':args.worker_image,
        'FOXORY_SANDBOX_DATA':str(manager_home/'fixture-state')}
    summary={'status':'failed','project':project,'checks':[],'model':'qwen2.5:0.5b',
             'worker_image':args.worker_image,'gpu_verified':False,'owner_data_accessed':False}
    manager_prefix=['sudo','-u',account,'-H','env','-i','HOME='+user.pw_dir,'USER='+account,'LOGNAME='+account,
        'PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
        'XDG_RUNTIME_DIR=/run/user/'+str(user.pw_uid),'DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/'+str(user.pw_uid)+'/bus']
    def manager(*cmd,**kwargs):
        kwargs.setdefault('check',True);kwargs.setdefault('timeout',200)
        return subprocess.run([*manager_prefix,*cmd],**kwargs)
    def passed(name,**details):
        summary['checks'].append({'name':name,'passed':True,**details});print('PASS '+name,flush=True)
    with socket.socket() as reservation:
        reservation.bind(('127.0.0.1',0));port=reservation.getsockname()[1]
    env={**os.environ,'FOXORY_TOKEN':token,'POSTGRES_PASSWORD':password,'FOXORY_PORT':str(port),
        'FOXORY_DATABASE_LAYOUT':'modern','FOXORY_SANDBOX_KEY':key,'FOXORY_SANDBOX_GID':str(user.pw_gid),
        'FOXORY_SANDBOX_SOCKET_DIR':str(args.ipc),'FOXORY_ENABLE_SANDBOX':'1',
        'FOXORY_SANDBOX_URL':'','FOXORY_SANDBOX_SOCKET':'','SEARXNG_URL':''}
    for name in ['DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH']:env.pop(name,None)
    command=['docker','--host=unix:///var/run/docker.sock','compose','--env-file',os.devnull,'-p',project,
        '-f',str(ROOT/'compose.yaml'),'-f',str(ROOT/'compose.sandbox-socket.yaml')]
    started=False;socket_started=False
    def compose(*parts,**kwargs):
        kwargs.setdefault('check',True);kwargs.setdefault('timeout',900)
        return subprocess.run([*command,*parts],env=env,**kwargs)
    try:
        manager('mkdir','-p',str(manager_home/'.config/foxory'),str(manager_home/'.config/systemd/user/foxory-sandbox-oci-uds.socket.d'))
        # Pass the new test key on stdin, never argv/stdout; refuse existing env.
        manager(str(manager_source/'.venv/bin/python'),'-c',
            'import os,sys; fd=os.open(sys.argv[1],os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.write(fd,sys.stdin.buffer.read());os.close(fd)',
            str(manager_home/'.config/foxory/sandbox.env'),input=''.join(k+'='+v+'\n' for k,v in manager_env.items()),text=True)
        for unit in ['foxory-sandbox-oci-uds.socket','foxory-sandbox-oci-uds.service']:
            manager('cp',str(manager_source/'deployment'/unit),str(manager_home/'.config/systemd/user'/unit))
        override='[Socket]\nListenStream=\nListenStream='+str(args.ipc/'manager.sock')+'\n'
        manager(str(manager_source/'.venv/bin/python'),'-c','from pathlib import Path;import sys;Path(sys.argv[1]).write_text(sys.stdin.read())',
            str(manager_home/'.config/systemd/user/foxory-sandbox-oci-uds.socket.d/path.conf'),input=override,text=True)
        manager('systemctl','--user','daemon-reload')
        manager('systemctl','--user','start','foxory-sandbox-oci-uds.socket');socket_started=True
        started=True;compose('up','-d','--build','--wait','--wait-timeout','240')
        deadline=time.monotonic()+90
        while time.monotonic()<deadline:
            probe=compose('exec','-T','ollama','ollama','list',check=False,capture_output=True,text=True)
            if probe.returncode==0:break
            time.sleep(1)
        else:raise TimeoutError('Canonical Ollama startup')
        compose('exec','-T','ollama','ollama','pull','qwen2.5:0.5b',stdout=subprocess.DEVNULL)
        with httpx.Client(base_url=f'http://127.0.0.1:{port}/api',trust_env=False,timeout=180) as client:
            def call(method,path,**kwargs):
                response=client.request(method,path,**kwargs);response.raise_for_status()
                return response.json() if 'application/json' in response.headers.get('content-type','') else response
            identity=call('POST','/auth/setup',json={'username':'host-fixture-owner','password':secrets.token_urlsafe(30),'bootstrap_token':token})
            client.headers['X-CSRF-Token']=identity['csrf'];me=call('GET','/auth/me');workspace=me['workspace_id']
            client.headers['X-Workspace-ID']=workspace
            deadline=time.monotonic()+200
            while time.monotonic()<deadline:
                caps=call('GET','/computer/capabilities')
                if all(caps.get('profiles',{}).get(p,{}).get('enabled') for p in ['javascript','typescript','browser']):break
                time.sleep(1)
            else:raise RuntimeError('Native manager active probes failed: '+json.dumps(caps))
            passed('canonical Compose authentication and socket-activated rootless profiles')
            def agent(name,tools,permissions,**extra):
                return call('POST','/agents',json={'name':name,'config':{'model':'qwen2.5:0.5b','tools':tools,'permissions':permissions,
                    'max_steps':8,'max_model_calls':12,'step_timeout':180,'max_seconds':1200,'max_retries':0,**extra}})
            coder=agent('Coder',['sandbox.javascript','source.package'],['sandbox.execute','documents.write'])
            browser=agent('Browser',['sandbox.browser'],['sandbox.browser'])
            writer=agent('Writer',['document.generate','source.package'],['documents.write'])
            upload=call('POST','/documents',files={'file':('fixture.csv',b'team,revenue\nA,10\nA,20\nB,5\n','text/csv')})
            analyst=agent('Analyst',['data.csv_document'],['documents.read','calculate'],document_ids=[upload['id']])
            coordinator=agent('Coordinator',[],[],delegate_ids=[a['id'] for a in [coder,browser,writer,analyst]])
            approved=set()
            def finish(id,expected='completed'):
                deadline=time.monotonic()+1200
                while time.monotonic()<deadline:
                    data=next(row['data'] for row in call('GET','/records/job') if row['id']==id)
                    if data['status']=='awaiting_approval':
                        approval=next(row['data'] for row in call('GET','/records/approval') if row['id']==data['approval_id'])
                        assert approval['context']['job_id']==id and approval['context']['effect']['tool'] in {
                            'sandbox.javascript','sandbox.browser','source.package','document.generate'}
                        assert data['approval_id'] not in approved
                        call('POST','/approvals/'+data['approval_id']+'/approve');approved.add(data['approval_id'])
                    elif data['status'] in {'completed','failed','cancelled'}:
                        assert data['status']==expected,{k:data.get(k) for k in ['status','error','error_detail','stage']}
                        return data
                    time.sleep(.5)
                raise TimeoutError('Bounded fixture task')
            tests="import assert from 'node:assert/strict';import {add} from './app.js';import fs from 'node:fs';assert.equal(add(2,3),5);assert.equal(add(-1,1),0);assert.equal(add(0.5,1.5),2);fs.writeFileSync('/out/result.json',JSON.stringify({passed:3}));console.log('THREE_TESTS_PASSED');"
            files={'package.json':'{"type":"module"}','app.js':'export function add(a,b){return a-b;}','test.js':tests}
            source={'title':'Verified local-model adder','files':files,'entrypoint':'test.js'}
            failed=call('POST','/computer/tasks',json={'agent_id':coder['id'],'profile':'javascript','objective':'Run deliberately failing public fixture',
                'idempotency_key':'controlled-failure','source':source})
            failure=finish(failed['id'],'failed')
            assert failure['outputs'][0]['result']['status']=='failed'
            assert not any(item['tool']=='source.package' for item in failure['outputs'])
            passed('actual failed tests block source packaging')
            conversation=call('POST','/records/conversation',json={'title':'Actual model repair'})
            response=call('POST',f'/conversations/{conversation["id"]}/chat',json={'model':'qwen2.5:0.5b','context':2048,'max_output':256,
                'temperature':0,'content':'Fix this JavaScript ES module: export function add(a,b){return a-b;}. Actual tests failed: add(2,3) must be 5; add(-1,1) must be 0. Return only the complete corrected ES module exporting add, no markdown.'})
            code=''
            for block in response.text.split('\n\n'):
                event=next((line[7:] for line in block.splitlines() if line.startswith('event: ')),'')
                value=next((line[6:] for line in block.splitlines() if line.startswith('data: ')),'')
                assert event!='error',block
                if event=='delta':code+=json.loads(value)
            if '```' in code:
                code=code.split('```',2)[1];code='\n'.join(code.splitlines()[1:])
            assert 'export' in code and len(code.encode())<10000,'Model did not produce bounded ES module'
            files={**files,'app.js':code};source={**source,'files':files}
            task={'agent_id':coder['id'],'profile':'javascript','objective':'Run actual model repair and package matching source',
                'idempotency_key':'model-repair','source':source}
            repaired=call('POST','/computer/tasks',json=task);result=finish(repaired['id'])
            assert 'THREE_TESTS_PASSED' in result['outputs'][0]['result']['stdout']
            assert call('POST','/computer/tasks',json=task)['id']==repaired['id']
            archive_id=next(item['result']['record_id'] for item in result['outputs'] if item['tool']=='source.package')
            archive=call('GET','/artifacts/'+archive_id+'/export?format=zip')
            with zipfile.ZipFile(io.BytesIO(archive.content)) as zipped:
                assert zipped.testzip() is None and zipped.read('app.js').decode()==code
            passed('actual local-model repair, three tests, independent approvals and matching ZIP',source_sha256=hashlib.sha256(code.encode()).hexdigest())
            site={'index.html':'<!doctype html><html><body><input id="a"><input id="b"><button id="sum">Sum</button><p id="result"></p><a download="report.txt" href="/report.txt">Download</a><script type="module" src="/ui.js"></script></body></html>',
                'app.js':code,'ui.js':"import {add} from './app.js';document.querySelector('#sum').onclick=()=>{document.querySelector('#result').textContent='SUM='+add(Number(document.querySelector('#a').value),Number(document.querySelector('#b').value));};",
                'report.txt':'Public fixture; JavaScript tests independently verified.'}
            actions=[{'action':'type','target':'#a','text':'2'},{'action':'type','target':'#b','text':'3'},
                {'action':'click','target':'#sum'},{'action':'inspect'},{'action':'screenshot'},{'action':'download','target':'a'}]
            plan=[{'title':'Run reviewed generated code','tool':'sandbox.javascript','agent_id':coder['id'],'args':source},
                {'title':'Browser interaction','tool':'sandbox.browser','agent_id':browser['id'],'args':{'title':'Browser fixture','files':site,'actions':actions},'depends_on':[0]},
                {'title':'Analyze authorized CSV','tool':'data.csv_document','agent_id':analyst['id'],'args':{'document_id':upload['id'],'column':'revenue','group_by':'team'}},
                {'title':'Create actual-data report','tool':'document.generate','agent_id':writer['id'],'args':{'title':'Verified CSV report','content':{'$step':2,'path':['report']}},'depends_on':[2]},
                {'title':'Export chart and data','tool':'source.package','agent_id':writer['id'],'args':{'title':'Verified charts','files':{'chart.svg':{'$step':2,'path':['chart_svg']},'results.csv':{'$step':2,'path':['csv']}}},'depends_on':[2]}]
            job=call('POST','/agents/'+coordinator['id']+'/tasks',json={'objective':'Execute authorized coding/browser/data/report collaboration with actual tools',
                'idempotency_key':'real-delegation','plan':plan})
            data=finish(job['id'])
            assert data.get('model_trace') and all(t['model']=='qwen2.5:0.5b' for t in data['model_trace'])
            browser_output=data['outputs'][1]['result'];assert 'SUM=5' in browser_output['stdout']
            png=base64.b64decode(browser_output['artifacts']['screenshot-1.png']['base64'],validate=True)
            assert png.startswith(b'\x89PNG\r\n\x1a\n');(args.evidence/'actual-browser.png').write_bytes(png)
            assert base64.b64decode(browser_output['artifacts']['result.txt']['base64'])==site['report.txt'].encode()
            table=data['outputs'][2]['result'];assert table['groups'][0]['sum']==30 and table['groups'][1]['sum']==5
            report_id=data['outputs'][3]['result']['record_id']
            pdf=call('GET','/artifacts/'+report_id+'/export?format=pdf').content
            assert '30' in ''.join(page.extract_text() for page in PdfReader(io.BytesIO(pdf)).pages)
            (args.evidence/'actual-report.pdf').write_bytes(pdf)
            passed('actual delegated coding/browser/CSV/PDF workflow with local-model review',agents=4,approved_effects=len(approved))
            artifact_path='/computer/jobs/'+repaired['id']+'/artifacts/0/result.json'
            assert call('GET',artifact_path).content
            foreign=call('POST','/auth/workspaces',json={'name':'Foreign test workspace'})
            client.headers['X-Workspace-ID']=foreign['id']
            assert client.get(artifact_path).status_code==404
            client.headers['X-Workspace-ID']=workspace
            first_approval=next(iter(approved));assert client.post('/approvals/'+first_approval+'/approve').status_code==409
            passed('real download workspace isolation and consumed-approval reuse denial')
            manager('systemctl','--user','restart','foxory-sandbox-oci-uds.service')
            compose('restart','app',stdout=subprocess.DEVNULL)
            deadline=time.monotonic()+90
            while time.monotonic()<deadline:
                try:
                    if client.get('/auth/me',timeout=3).status_code==200:break
                except httpx.HTTPError:pass
                time.sleep(.5)
            else:raise TimeoutError('Restored app/session startup')
            assert call('GET',artifact_path).content
            assert next(row['data'] for row in call('GET','/records/job') if row['id']==repaired['id'])['status']=='completed'
            passed('real app/manager restart preserves session, completed job and artifact')
            summary['status']='passed'
    finally:
        errors=[]
        if started:
            try:
                compose('logs','--no-color','--tail','50','app',check=False,timeout=20)
                compose('down','--volumes','--remove-orphans',timeout=180)
            except Exception as error:errors.append('Compose cleanup: '+type(error).__name__)
        try:
            if socket_started:manager('systemctl','--user','stop','foxory-sandbox-oci-uds.socket','foxory-sandbox-oci-uds.service')
            owner=hashlib.sha256((str(manager_home/'fixture-state')+':'+str(user.pw_uid)).encode()).hexdigest()[:32]
            remaining=manager('podman','--remote=false','ps','--all','--filter','label=io.foxory.manager='+owner,'--format','json',capture_output=True,text=True)
            if json.loads(remaining.stdout):errors.append('Manager-owned worker remains')
            manager('journalctl','--user','-u','foxory-sandbox-oci-uds.service','--no-pager','-n','60',check=False)
        except Exception as error:errors.append('Manager cleanup: '+type(error).__name__)
        summary['cleanup_verified']=not errors
        if errors:summary.update(status='failed',cleanup_errors=errors)
        (args.evidence/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    if summary['status']!='passed':raise RuntimeError('Host acceptance/cleanup failed; inspect retained evidence')


if __name__=='__main__':main()
