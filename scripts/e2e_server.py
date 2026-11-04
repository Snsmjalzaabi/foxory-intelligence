"""Test-only Ollama protocol fixture and real application server. Never used in production."""
import json
import secrets
import signal
import atexit
import time
import os
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

root=Path(__file__).resolve().parents[1]
os.environ.update(FOXORY_TOKEN='e2e-only-token-with-at-least-24-chars',FOXORY_DATA_DIR=tempfile.mkdtemp(prefix='foxory-e2e-'),OLLAMA_URL='http://127.0.0.1:11435')
os.environ.pop('DATABASE_URL',None)
if os.getenv('FOXORY_E2E_SANDBOX')=='1':
    manager_key=secrets.token_urlsafe(40)
    os.environ.update(FOXORY_ENABLE_SANDBOX='1',FOXORY_SANDBOX_URL='http://127.0.0.1:8104',FOXORY_SANDBOX_KEY=manager_key)
    manager_env={**os.environ,'FOXORY_SANDBOX_ENABLED':'1','FOXORY_SANDBOX_DATA':tempfile.mkdtemp(prefix='foxory-e2e-manager-')}
    manager_command=[sys.executable,'-m','scripts.e2e_oci_manager'] if os.getenv('FOXORY_E2E_OCI')=='1' else [sys.executable,'-m','uvicorn','sandbox_manager.service:app','--host','127.0.0.1','--port','8104']
    manager=subprocess.Popen(manager_command,cwd=root,env=manager_env)
    def stop_manager():
        manager.terminate()
        try:manager.wait(timeout=10)
        except subprocess.TimeoutExpired:manager.kill();manager.wait()
    atexit.register(stop_manager)
    def terminate_fixture(signum,frame):
        stop_manager()
        raise SystemExit(0)
    signal.signal(signal.SIGTERM,terminate_fixture)
    import httpx
    for attempt in range(150):
        try:
            if manager.poll() is not None:raise RuntimeError('Disposable test manager exited during startup; check its port and preflight logs')
            response=httpx.get('http://127.0.0.1:8104/v1/health',headers={'Authorization':'Bearer '+manager_key,'X-Foxory-Workspace':'local'},trust_env=False)
            response.raise_for_status();health=response.json()
            if not health['enabled']:raise RuntimeError(str(health))
            break
        except httpx.HTTPError:time.sleep(.1)
    else:raise RuntimeError('Test manager failed to start')

class OllamaFixture(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers()
        self.wfile.write(json.dumps({'models':[{'name':n,'size':1000000,'details':{'parameter_size':'test fixture','quantization_level':'fixture'}} for n in ['fixture-a','fixture-b']]}).encode())
    def do_POST(self):
        request=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.send_response(200);self.send_header('Content-Type','application/x-ndjson');self.end_headers()
        if self.path=='/api/embed':
            self.wfile.write(json.dumps({'embeddings':[[1.0,0.0] for _ in request['input']]}).encode());return
        if self.path=='/api/show':self.wfile.write(json.dumps({'capabilities':['completion','embedding'],'details':{'fixture':True}}).encode());return
        if request.get('format') and 'actions' in request['format'].get('properties',{}):
            prompt=json.loads(request['messages'][-1]['content']);text=prompt['current_request']
            actions=[{'tool':'artifact.write','title':'Finished browser offer','goal':'Write the complete offer document'}] if 'EXECUTION_BROWSER' in text else []
            if 'SOURCE_BROWSER' in text:actions=[{'tool':'source.package','title':'Browser source fixture','goal':'Create a complete tiny app'}]
            self.wfile.write((json.dumps({'message':{'content':json.dumps({'actions':actions,'reply':''})},'done':True})+'\n').encode());return
        if request.get('format') and 'files' in request['format'].get('properties',{}):
            files=[{'path':'index.html','content':'<!doctype html><title>Fixture app</title><h1>Local source preview fixture</h1>'},{'path':'README.md','content':'# Fixture app\nOpen index.html in your browser. Test-only source.'}]
            self.wfile.write((json.dumps({'message':{'content':json.dumps({'files':files})},'done':True})+'\n').encode());return
        if request.get('format') and 'edits' in request['format'].get('properties',{}):
            proposal={'title':'Fixture performance clarity improvement','rationale':'Clarify the displayed title.','expected_benefit':'Easier navigation; owner review needed.','risks':'Text change; check layout.','edits':[{'old':'your computer performance','new':'your computer performance overview'}]}
            self.wfile.write((json.dumps({'message':{'content':json.dumps(proposal)},'done':True})+'\n').encode());return
        if request.get('format') and 'project_kinds' in request['format'].get('properties',{}):
            definition={'name':'Fixture learned skill','purpose':'Create a useful project checklist','instructions':'Draft only from actual supplied project facts.','project_kinds':['business'],'steps':[{'action':'context'},{'action':'draft','instruction':'Create a concise checklist with unknown facts unset.'}]}
            self.wfile.write((json.dumps({'message':{'content':json.dumps(definition)},'done':True})+'\n').encode());return
        if request.get('format'):
            data=json.loads(request['messages'][-1]['content'])
            delegates=data.get('delegates',{})
            if 'approval' in data['objective'].lower():
                steps=[{'title':'Create approved project','tool':'project.create','args':{'title':'Browser agent project','content':'Fixture-labeled approved local project'}}]
            else:
                target=next(iter(delegates),None)
                steps=[{'title':'Calculate actual arithmetic','agent_id':target,'tool':'math.calculate','args':{'expression':'6*7'}}]
            text=json.dumps({'steps':steps})
            self.wfile.write((json.dumps({'message':{'content':text},'done':True})+'\n').encode());return
        content='Test fixture response: '+request.get('messages',[{}])[-1].get('content','')[:100]
        for text in [content[:20],content[20:]]:
            self.wfile.write((json.dumps({'message':{'content':text}})+'\n').encode());self.wfile.flush()
        self.wfile.write((json.dumps({'done':True,'eval_count':12})+'\n').encode())
server=ThreadingHTTPServer(('127.0.0.1',11435),OllamaFixture)
threading.Thread(target=server.serve_forever,daemon=True).start()
subprocess.run([sys.executable,'-m','alembic','upgrade','head'],cwd=root/'backend',check=True)
os.chdir(root/'backend')
# Test-only GitHub protocol fixture. Production startup never imports this script.
from foxory import repositories
import base64,hashlib
_source_files={'README.md':b'# Fixture project\nA local business workspace with documented architecture.','src/main.py':b'print("source preview fixture")\n','.env':b'SECRET=test-only'}
def _git_sha(raw):return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
async def _repository_fixture(client,path):
    from fastapi import HTTPException
    if not path.startswith('/repos/fixture-owner/fixture-repo'):raise HTTPException(404,'Test fixture repository not found')
    if '/commits/' in path:return {'sha':'a'*40}
    if '/git/trees/' in path:return {'truncated':False,'tree':[{'path':name,'type':'blob','size':len(raw),'sha':_git_sha(raw)} for name,raw in _source_files.items()]}
    if '/git/blobs/' in path:
        for raw in _source_files.values():
            if path.endswith(_git_sha(raw)):return {'encoding':'base64','content':base64.b64encode(raw).decode()}
        raise HTTPException(404,'Test blob not found')
    return {'default_branch':'main','description':'Explicit test-only source fixture','license':{'spdx_id':'Apache-2.0'}}
repositories.github=_repository_fixture
import uvicorn
uvicorn.run('foxory.main:app',host='127.0.0.1',port=8001,workers=1)
