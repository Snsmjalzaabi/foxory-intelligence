"""Disposable native services + real Ollama generation, approvals, execution and ZIP.

Never connects to the owner's application/database. Linux Bubblewrap required.
Usage: .venv/bin/python scripts/phase4_integration.py --ollama-url http://LOCAL:11434
"""
import argparse
import base64
import io
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time
import zipfile
import httpx

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--ollama-url',required=True);parser.add_argument('--model',default='qwen2.5:0.5b');args=parser.parse_args()

with tempfile.TemporaryDirectory(prefix='foxory-phase4-integration-') as directory:
    private=Path(directory);key=secrets.token_urlsafe(40);token=secrets.token_urlsafe(40)
    env={**os.environ,'FOXORY_TOKEN':token,'FOXORY_DATA_DIR':str(private/'app'),'DATABASE_URL':'sqlite:///'+str(private/'app.db'),'OLLAMA_URL':args.ollama_url,
         'FOXORY_ENABLE_SANDBOX':'1','FOXORY_SANDBOX_URL':'http://127.0.0.1:8105','FOXORY_SANDBOX_KEY':key,
         'FOXORY_SANDBOX_ENABLED':'1','FOXORY_SANDBOX_DATA':str(private/'manager'),
         'FOXORY_BACKGROUND_CONTEXT':'2048','FOXORY_BACKGROUND_OUTPUT':'256','FOXORY_INFERENCE_THREADS':'2'}
    subprocess.run([sys.executable,'-m','alembic','upgrade','head'],cwd=ROOT/'backend',env=env,check=True,stdout=subprocess.DEVNULL)
    services=[]
    try:
        for module,port,cwd in [('sandbox_manager.service:app',8105,ROOT),('foxory.main:app',8005,ROOT/'backend')]:
            log=(private/(str(port)+'.log')).open('w')
            services.append(subprocess.Popen([sys.executable,'-m','uvicorn',module,'--host','127.0.0.1','--port',str(port)],cwd=cwd,env=env,stdout=log,stderr=log))
            log.close()
        with httpx.Client(base_url='http://127.0.0.1:8005',timeout=30,trust_env=False) as client:
            for _ in range(200):
                try:
                    if client.get('/api/health').status_code==200:break
                except httpx.HTTPError:pass
                time.sleep(.1)
            else:raise RuntimeError('Disposable app did not start')
            response=client.post('/api/auth/setup',json={'username':'phase4-reviewer','password':secrets.token_urlsafe(30),'bootstrap_token':token});response.raise_for_status()
            me=client.get('/api/auth/me').json();client.headers.update({'X-CSRF-Token':me['csrf'],'X-Workspace-ID':me['workspace_id']})
            for _ in range(200):
                health=client.get('/api/computer/capabilities').json()
                if health['enabled']:break
                time.sleep(.1)
            else:raise RuntimeError('Manager isolation preflight failed: '+str(health))
            # Actual local-model code generation. Small models handled plain code
            # more reliably than two source strings under a JSON grammar here.
            def generate(prompt):
                with httpx.Client(timeout=180,trust_env=False) as ollama:
                    response=ollama.post(args.ollama_url+'/api/chat',json={'model':args.model,'stream':False,'options':{'temperature':0,'num_ctx':2048,'num_predict':256,'num_thread':2},'messages':[{'role':'user','content':prompt+' Output only Python code, without markdown.'}]})
                    response.raise_for_status();text=response.json()['message']['content'].strip()
                if '```' in text:
                    block=text.split('```',2)[1]
                    lines=block.splitlines()
                    if lines and lines[0].strip().lower() in {'python','py',''}:lines=lines[1:]
                    text='\n'.join(lines)+'\n'
                return text
            # Reviewed acceptance tests are deterministic. The 0.5B model did
            # not reliably generate a complete unittest scaffold in earlier runs.
            files={'app.py':generate('Write a Python function add(a,b) that returns a+b.'),
                   'test_app.py':'import unittest\nfrom app import add\nclass TestAdd(unittest.TestCase):\n def test_add(self):self.assertEqual(add(2,3),5)\n def test_negative(self):self.assertEqual(add(-1,1),0)\nunittest.main()\n'}
            assert 'def add' in files['app.py'],'Local model did not produce executable source'
            # Add a deterministic independent validation to catch an inadequate generated test.
            files['verify.py']='from app import add\nassert add(2,3)==5\nassert add(-1,1)==0\nimport runpy\nrunpy.run_path("/work/test_app.py",run_name="__main__")\n'
            config={'role':'Coding Agent','model':args.model,'tools':['sandbox.python','source.package'],'permissions':['sandbox.execute','documents.write'],'max_steps':6,'max_retries':0,'step_timeout':180}
            response=client.post('/api/agents',json={'name':'Disposable local-model coder','config':config});response.raise_for_status();agent=response.json()
            # First demonstrate an actual failing project, then repair with the model-produced code.
            bad={**files,'app.py':'def add(a,b):return a-b\n'}
            evidence=[]
            for attempt,sources in [('failing',bad),('repaired',files)]:
                response=client.post('/api/computer/tasks',json={'agent_id':agent['id'],'objective':'Test and package a Python addition app','idempotency_key':'real-model-'+attempt,'source':{'title':'Local model adder','files':sources,'entrypoint':'verify.py'}});response.raise_for_status();id=response.json()['id'];approvals=set()
                deadline=time.monotonic()+360
                while time.monotonic()<deadline:
                    job=next(j for j in client.get('/api/computer/overview').json()['jobs'] if j['id']==id);data=job['data']
                    if data['status']=='awaiting_approval' and data['approval_id'] not in approvals:
                        # Explicit authorization by this disposable test owner for these supplied files.
                        check=client.post('/api/approvals/'+data['approval_id']+'/approve');check.raise_for_status();approvals.add(data['approval_id'])
                    if data['status'] in {'completed','failed','cancelled'}:break
                    time.sleep(1)
                else:raise RuntimeError('Integration task timeout')
                run=data.get('outputs',[{}])[0].get('result',{})
                if attempt=='failing':
                    assert run['status']=='failed' and not any(o.get('tool')=='source.package' for o in data.get('outputs',[])),data
                    files['app.py']=generate('Fix this Python implementation based on the actual failed test. Current app.py: '+bad['app.py']+'\nTest error: '+run['stderr']+'\nThe function add(a,b) must return their sum. Return the complete corrected app.py.')
                else:
                    assert data['status']=='completed' and run['status']=='completed' and 'OK' in run['stderr'] and 'Ran 0 tests' not in run['stderr'],data
                    artifact=next(o['result']['record_id'] for o in data['outputs'] if o['tool']=='source.package')
                    archive=client.get('/api/artifacts/'+artifact+'/export?format=zip');archive.raise_for_status()
                    with zipfile.ZipFile(io.BytesIO(archive.content)) as zipped:
                        assert zipped.testzip() is None and zipped.read('app.py').decode()==files['app.py']
                    report=client.get('/api/jobs/'+id+'/export');report.raise_for_status();assert report.content
                evidence.append({'attempt':attempt,'task_status':data['status'],'execution_status':run.get('status'),'exit_code':run.get('exit_code'),'approval_count':len(approvals)})
            # Restart app only; account/session/task state must remain intact in SQLite.
            services[1].terminate();services[1].wait(timeout=10)
            log=(private/'restart.log').open('w')
            services[1]=subprocess.Popen([sys.executable,'-m','uvicorn','foxory.main:app','--host','127.0.0.1','--port','8005'],cwd=ROOT/'backend',env=env,stdout=log,stderr=log);log.close()
            for _ in range(150):
                try:
                    if client.get('/api/auth/me').status_code==200:break
                except httpx.HTTPError:pass
                time.sleep(.1)
            else:raise RuntimeError('Account/session did not survive restart')
            assert any(j['id']==id and j['data']['status']=='completed' for j in client.get('/api/computer/overview').json()['jobs'])
            print(json.dumps({'model':args.model,'real_ollama':True,'reviewed_deterministic_tests':True,'profile':health['profile'],'evidence':evidence,'zip_integrity':True,'session_and_task_restart':True}))
    except Exception:
        for log in private.glob('*.log'):print(log.name+':\n'+log.read_text()[-4000:],file=sys.stderr)
        raise
    finally:
        for service in services:
            if service.poll() is None:service.terminate()
        for service in services:
            try:service.wait(timeout=15)
            except subprocess.TimeoutExpired:service.kill();service.wait()
