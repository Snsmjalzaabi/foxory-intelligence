"""Install the pinned, local-only CPU AI companion. Does not replace existing Ollama models."""
import argparse,hashlib,json,os,re,secrets,subprocess,time,urllib.request
from foxory_compose import compose
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def metadata():return json.loads((ROOT/'deployment/llama/manifest.json').read_text())
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  while block:=f.read(1024*1024):h.update(block)
 return h.hexdigest()
def download():return download_pinned(metadata()['model'])
def download_pinned(m):
 """Download a pinned Hugging Face file into .local-ai/models, verifying size and SHA-256."""
 folder=ROOT/'.local-ai/models';folder.mkdir(parents=True,exist_ok=True)
 assert re.fullmatch(r'[a-zA-Z0-9_.-]+\.(gguf|bin)',m['filename']) and re.fullmatch('[0-9a-f]{40}',m['revision']) and re.fullmatch('[0-9a-f]{64}',m['sha256'])
 target=folder/m['filename']
 if target.exists() and target.stat().st_size==m['bytes'] and sha(target)==m['sha256']:print('Pinned model '+m['filename']+' is verified.');return target
 temporary=target.with_suffix('.part');url='https://huggingface.co/'+m['repository']+'/resolve/'+m['revision']+'/'+m['filename']
 h=hashlib.sha256();size=0
 with urllib.request.urlopen(url,timeout=60) as r,temporary.open('wb') as f:
  while block:=r.read(1024*1024):
   size+=len(block)
   if size>m['bytes']:raise ValueError('Model download exceeds its pinned size')
   f.write(block);h.update(block)
 if size!=m['bytes'] or h.hexdigest()!=m['sha256']:raise ValueError('Model size/hash verification failed')
 temporary.chmod(0o644);temporary.replace(target)
 license_url='https://huggingface.co/'+m['repository']+'/resolve/'+m['revision']+'/'+m.get('license_file','LICENSE')
 (folder/(m['filename']+'.LICENSE' if m['filename'].endswith('.bin') else 'LICENSE')).write_bytes(urllib.request.urlopen(license_url,timeout=20).read(100000));print('Downloaded and verified '+str(size)+' bytes; model license '+m['license']);return target
def build():
 version=(ROOT/'VERSION').read_text().strip()
 if not re.fullmatch(r'\d+\.\d+\.\d+',version):raise ValueError('Invalid source version')
 image='foxory-local-app:'+version
 if subprocess.run(['docker','image','inspect',image],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
  subprocess.run(['docker','build','--target','application','-t',image,'.'],cwd=ROOT,check=True)
 subprocess.run(['docker','build','-f','deployment/llama/Dockerfile','--build-arg','FOXORY_APP_IMAGE='+image,'-t','foxory-llama-cpu:'+version,'.'],cwd=ROOT,check=True)
def enable():
 if not (ROOT/'.env').exists():raise ValueError('Use the existing FOXORY installation and its private .env')
 download();build()
 values={'FOXORY_LLAMA_URL':'http://127.0.0.1:11436','FOXORY_LLAMA_MODEL':metadata()['model']['alias'],'FOXORY_LLAMA_IMAGE':'foxory-llama-cpu:'+(ROOT/'VERSION').read_text().strip(),'FOXORY_AI_APP_IMAGE':'foxory-local-app:'+(ROOT/'VERSION').read_text().strip()}
 if not any(l.startswith('FOXORY_LLAMA_API_KEY=') and len(l.split('=',1)[1].strip())>=32 for l in (ROOT/'.env').read_text().splitlines()):values['FOXORY_LLAMA_API_KEY']=secrets.token_hex(32)
 update_env(values,'lite')
 subprocess.run([*compose(),'up','-d','llama'],cwd=ROOT,check=True)
 wait_ready('http://127.0.0.1:11436/health','CPU companion')
 subprocess.run([*compose(),'up','-d','--no-build','app'],cwd=ROOT,check=True)
 print('CPU companion enabled and app configuration reloaded locally. No account or API key entry is required.')
def update_env(values,profile=None):
 """Set keys in the private .env atomically and optionally add a Compose profile."""
 path=ROOT/'.env';lines=path.read_text().splitlines();values={**({'COMPOSE_PROFILES':profile} if profile else {}),**values}
 for key,value in values.items():
  old=next((i for i,l in enumerate(lines) if l.startswith(key+'=')),None)
  if key=='COMPOSE_PROFILES' and old is not None:
   current=lines[old].split('=',1)[1].strip().strip('"\'');value=','.join(dict.fromkeys([p for p in current.split(',') if p]+[profile]))
  if old is None:lines.append(key+'='+value)
  else:lines[old]=key+'='+value
 temp=path.with_suffix('.ai-tmp');temp.write_text('\n'.join(lines)+'\n');temp.chmod(0o600);temp.replace(path)
def wait_ready(url,name):
 for _ in range(60):
  try:
   with urllib.request.urlopen(url,timeout=2) as response:
    if response.status==200:return
  except Exception:time.sleep(1)
 raise ValueError(name+' did not become ready; inspect its local service logs')
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['download','build','enable']);args=p.parse_args()
 {'download':download,'build':build,'enable':enable}[args.action]()
if __name__=='__main__':main()
