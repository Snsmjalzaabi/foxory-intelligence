"""Test-only Ollama protocol fixture and real application server. Never used in production."""
import json
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
class OllamaFixture(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers()
        self.wfile.write(json.dumps({'models':[{'name':n,'size':1000000,'details':{'parameter_size':'test fixture','quantization_level':'fixture'}} for n in ['fixture-a','fixture-b']]}).encode())
    def do_POST(self):
        request=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.send_response(200);self.send_header('Content-Type','application/x-ndjson');self.end_headers()
        if self.path=='/api/show':self.wfile.write(json.dumps({'capabilities':['completion'],'details':{'fixture':True}}).encode());return
        content='Test fixture response: '+request.get('messages',[{}])[-1].get('content','')[:100]
        for text in [content[:20],content[20:]]:
            self.wfile.write((json.dumps({'message':{'content':text}})+'\n').encode());self.wfile.flush()
        self.wfile.write((json.dumps({'done':True,'eval_count':12})+'\n').encode())
server=ThreadingHTTPServer(('127.0.0.1',11435),OllamaFixture)
threading.Thread(target=server.serve_forever,daemon=True).start()
subprocess.run([sys.executable,'-m','alembic','upgrade','head'],cwd=root/'backend',check=True)
os.chdir(root/'backend')
import uvicorn
uvicorn.run('foxory.main:app',host='127.0.0.1',port=8001,workers=1)
