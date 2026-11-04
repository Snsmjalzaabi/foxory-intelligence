"""Signed local/GitHub release channel and isolated candidate acceptance. Host only."""
import argparse,base64,hashlib,json,os,re,secrets,shutil,subprocess,tarfile,tempfile,time,urllib.request,urllib.parse,urllib.error,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ALLOWED={'github.com','objects.githubusercontent.com','release-assets.githubusercontent.com','raw.githubusercontent.com'}
def run(args,**kw):return subprocess.run(args,cwd=ROOT,check=True,**kw)
def cap(args):return subprocess.check_output(args,cwd=ROOT,text=True).strip()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def config():return json.loads((ROOT/'update-policy.json').read_text())
def write(path,value):
 temp=path.with_name('.'+path.name+'.tmp');temp.write_text(json.dumps(value,indent=2)+'\n');temp.chmod(0o600);os.replace(temp,path)
def initialize():
 trust=ROOT/'update-trust';trust.mkdir(exist_ok=True,mode=0o700);channel=ROOT/'release-channel';channel.mkdir(exist_ok=True,mode=0o700)
 if not (trust/'signing-key.pem').exists():
  run(['openssl','genpkey','-algorithm','ED25519','-out',str(trust/'signing-key.pem')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);(trust/'signing-key.pem').chmod(0o600)
  run(['openssl','pkey','-in',str(trust/'signing-key.pem'),'-pubout','-out',str(trust/'release.pub')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 if not (ROOT/'update-policy.json').exists():write(ROOT/'update-policy.json',{'enabled':False,'auto_activate':True,'interval_minutes':360,'channel':str(channel/'channel.json'),'trusted_public_key':str(trust/'release.pub'),'require_security_scan':True})
 return config()
def fetch(url,dest,limit):
 parsed=urllib.parse.urlsplit(url)
 if parsed.scheme!='https' or parsed.hostname not in ALLOWED or parsed.port not in {None,443} or parsed.username or parsed.password:raise ValueError('Update downloads require an allowed public GitHub HTTPS origin')
 class NoRedirect(urllib.request.HTTPRedirectHandler):
  def redirect_request(self,*args,**kw):return None
 opener=urllib.request.build_opener(NoRedirect())
 for _ in range(6):
  parsed=urllib.parse.urlsplit(url)
  if parsed.scheme!='https' or parsed.hostname not in ALLOWED or parsed.port not in {None,443} or parsed.username:raise ValueError('Untrusted update redirect')
  try:
   with opener.open(urllib.request.Request(url,headers={'User-Agent':'FOXORY-Trusted-Local-Updater'}),timeout=30) as response,dest.open('wb') as out:
    size=0
    while True:
     chunk=response.read(65536)
     if not chunk:break
     size+=len(chunk)
     if size>limit:raise ValueError('Update download exceeds size limit')
     out.write(chunk)
   return
  except urllib.error.HTTPError as e:
   if e.code not in {301,302,303,307,308}:raise
   url=urllib.parse.urljoin(url,e.headers['Location'])
 raise ValueError('Too many update redirects')
def read_envelope(policy):
 channel=policy['channel'];cache=ROOT/'update-cache';cache.mkdir(exist_ok=True,mode=0o700)
 if channel.startswith('https://'):
  path=cache/'channel.json';fetch(channel,path,128000)
 else:
  path=Path(channel).resolve()
  if not path.is_relative_to((ROOT/'release-channel').resolve()):raise ValueError('Local update channel must remain in the release-channel folder')
  if path.stat().st_size>128000:raise ValueError('Channel too large')
 envelope=json.loads(path.read_text());payload=envelope.get('payload')
 if not isinstance(payload,dict) or payload.get('schema')!=1 or not re.fullmatch(r'\d+\.\d+\.\d+',str(payload.get('version',''))):raise ValueError('Invalid channel schema/version')
 with tempfile.TemporaryDirectory(prefix='verify-',dir=cache) as folder:
  p=Path(folder);(p/'message').write_bytes(canonical(payload))
  try:(p/'signature').write_bytes(base64.b64decode(envelope['signature'],validate=True))
  except (KeyError,ValueError):raise ValueError('Invalid release signature')
  public=Path(policy['trusted_public_key']).resolve()
  if not public.is_file():raise ValueError('Trusted public key is unavailable')
  result=subprocess.run(['openssl','pkeyutl','-verify','-pubin','-inkey',str(public),'-rawin','-in',str(p/'message'),'-sigfile',str(p/'signature')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  if result.returncode:raise ValueError('Release signature does not match the pinned trusted key')
 return payload

def version_tuple(v):return tuple(int(x) for x in v.split('.'))
def current_version():
 with urllib.request.urlopen('http://127.0.0.1:3636/api/health',timeout=5) as r:return json.load(r)['version']
def check():
 policy=config();payload=read_envelope(policy);version=payload['version'];current=current_version()
 return {'status':'available' if version_tuple(version)>version_tuple(current) else 'current','current_version':current,'candidate_version':version,'checked_at':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),'signature':'verified','key_fingerprint':hashlib.sha256(Path(policy['trusted_public_key']).read_bytes()).hexdigest(),'channel_kind':'https_github' if policy['channel'].startswith('https://') else 'local_signed','manifest_hash':hashlib.sha256(canonical(payload)).hexdigest()}

def ensure_scanner():
 folder=ROOT/'security-tools';folder.mkdir(exist_ok=True,mode=0o700);binary=folder/'trivy'
 if not binary.exists():
  tool=json.loads((ROOT/'deployment/security-tools.json').read_text())['trivy'];archive=folder/'trivy.tar.gz';fetch(tool['url'],archive,100_000_000)
  if hashlib.sha256(archive.read_bytes()).hexdigest()!=tool['sha256']:raise ValueError('Security scanner checksum mismatch')
  with tarfile.open(archive) as tar:
   member=tar.getmember('trivy')
   if not member.isfile():raise ValueError('Invalid scanner archive')
   binary.write_bytes(tar.extractfile(member).read());binary.chmod(0o700)
 return binary

def smoke(image,version):
 name='foxory-update-smoke-'+secrets.token_hex(6);volume=name+'-data';token=secrets.token_urlsafe(40)
 try:
  run(['docker','volume','create',volume],stdout=subprocess.DEVNULL)
  run(['docker','run','-d','--pull=never','--name',name,'--network','none','--read-only','--tmpfs','/tmp:size=64m,mode=1777','--cap-drop','ALL','--security-opt','no-new-privileges:true','--pids-limit','128','--memory','512m','-e','FOXORY_TOKEN='+token,'-e','FOXORY_DATA_DIR=/data','-e','DATABASE_URL=sqlite:////data/smoke.db','-e','OLLAMA_URL=http://127.0.0.1:1','-e','FOXORY_ENABLE_SANDBOX=0','-v',volume+':/data',image],stdout=subprocess.DEVNULL)
  for _ in range(60):
   probe=subprocess.run(['docker','exec',name,'python','-c',"import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/api/ready',timeout=2)"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   if probe.returncode==0:break
   time.sleep(1)
  else:raise ValueError('Isolated candidate did not become ready')
  code=r"""import urllib.request,http.cookiejar,json,os
jar=http.cookiejar.CookieJar();client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar));base='http://127.0.0.1:8000/api';csrf=''
def call(path,body=None):
 headers={'Content-Type':'application/json'}
 if csrf:headers['X-CSRF-Token']=csrf
 req=urllib.request.Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers=headers)
 with client.open(req,timeout=5) as r:return json.load(r)
assert call('/health')['version']==VERSION
import re
html=client.open('http://127.0.0.1:8000/').read().decode()
asset=re.search(r'src="([^"]+\.js)"',html).group(1)
assert VERSION in client.open('http://127.0.0.1:8000'+asset).read().decode()
setup=call('/auth/setup',{'username':'candidate-smoke-owner','password':'isolated-test-password-1234','bootstrap_token':os.environ['FOXORY_TOKEN']});csrf=setup['csrf']
space=call('/spaces',{'title':'Disposable candidate check','kind':'general'})
assert call('/spaces/'+space['id'])['space']['id']==space['id']
assert isinstance(call('/skills'),list)
assert 'policy' in call('/autonomy')
assert call('/maintenance')['installed_version']==VERSION
if tuple(map(int,VERSION.split('.'))) >= (4,0,0):
 assert call('/operations')['projects'][0]['id']==space['id']
 assert call('/operations/projects/'+space['id']+'/context')['project_id']==space['id']
if tuple(map(int,VERSION.split('.'))) >= (4,1,0):
 assert isinstance(call('/performance')['jobs'],list)
if tuple(map(int,VERSION.split('.'))) >= (5,0,0):
 assert call('/evolution')['version']==VERSION
 assert len(call('/evolution')['paths'])==4
if tuple(map(int,VERSION.split('.'))) >= (6,0,0):
 c=call('/records/conversation',{'title':'Disposable chat learning check'})
 assert call('/conversations/'+c['id']+'/command',{'content':'from now on keep acceptance checks concise'})['handled']
 assert len(call('/chat-learning'))==1
 assert call('/chat-learning/reviews')==[]
if tuple(map(int,VERSION.split('.'))) >= (6,2,0):
 from foxory.model_routing import category
 assert category('Debug a Python function')=='coding'
 assert category('continue',[{'role':'user','content':'Write a chapter'}])=='writing'
if tuple(map(int,VERSION.split('.'))) >= (7,0,0):
 assert call('/ai/status')['policy']['mode']=='balanced'
 assert call('/conversations/'+c['id']+'/command',{'content':'use eco mode'})['handled']
 assert call('/ai/status')['policy']['mode']=='eco'
 assert call('/conversations/'+c['id']+'/command',{'content':'use balanced mode'})['handled']
print('candidate routes/auth/storage passed')
""".replace('VERSION',repr(version))
  run(['docker','exec',name,'python','-c',code],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  return {'status':'passed','network':'none','published_ports':False,'owner_data_mounted':False}
 finally:
  subprocess.run(['docker','rm','-f',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);subprocess.run(['docker','volume','rm',volume],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

def stage():
 import foxory_control as control
 policy=config();payload=read_envelope(policy);version=payload['version']
 if version_tuple(version)<=version_tuple(current_version()):return {'status':'current','version':version}
 uri=payload.get('archive');expected=payload.get('sha256')
 if not isinstance(uri,str) or not re.fullmatch('[a-f0-9]{64}',str(expected)):raise ValueError('Invalid signed artifact declaration')
 cache=ROOT/'update-cache';cache.mkdir(exist_ok=True,mode=0o700);download=cache/('FOXORY-Local-v'+version+'.zip')
 if uri.startswith('https://'):fetch(uri,download,100_000_000)
 else:
  if Path(uri).name!=uri:raise ValueError('Invalid local channel artifact name')
  path=(ROOT/'release-channel'/uri).resolve()
  if not path.is_relative_to((ROOT/'release-channel').resolve()) or path.stat().st_size>100_000_000:raise ValueError('Invalid local artifact')
  shutil.copy2(path,download)
 if hashlib.sha256(download.read_bytes()).hexdigest()!=expected:raise ValueError('Signed release checksum mismatch')
 releases=ROOT/'releases';releases.mkdir(exist_ok=True);target=releases/download.name
 if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest()!=expected:raise ValueError('An immutable registered version already has different bytes')
 shutil.copy2(download,target);target.with_suffix('.sha256').write_text(expected+'  '+target.name+'\n');control.validate_archive(version)
 with zipfile.ZipFile(target) as candidate:
  if candidate.read('FOXORY-Local/compose.local.yaml')!=(ROOT/'compose.local.yaml').read_bytes():raise ValueError('Automatic updates cannot change the host Compose profile; review service/volume/network changes manually.')
 image='foxory-local-app:'+version
 present=subprocess.run(['docker','image','inspect',image],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
 if not present:
  with tempfile.TemporaryDirectory(prefix='foxory-release-build-') as folder:
   with zipfile.ZipFile(target) as archive:archive.extractall(folder)
   run(['docker','build','-t',image,str(Path(folder)/'FOXORY-Local')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=1200)
 image_id=cap(['docker','image','inspect',image,'--format','{{.Id}}'])
 if payload.get('image_id') and payload['image_id']!=image_id:raise ValueError('Signed image identity mismatch')
 actual=cap(['docker','run','--rm','--network','none','--read-only','--entrypoint','python',image,'-c','from foxory.version import __version__;print(__version__)'])
 if actual!=version:raise ValueError('Candidate image version mismatch')
 binary=ensure_scanner();report=cache/('scan-'+version+'.json')
 run([str(binary),'image','--cache-dir',str(ROOT/'security-tools/cache'),'--severity','HIGH,CRITICAL','--format','json','--output',str(report),image],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=600)
 scan=json.loads(report.read_text());findings=sum(len(x.get('Vulnerabilities',[]))+len(x.get('Secrets',[])) for x in scan.get('Results',[]))
 if findings:raise ValueError('Candidate failed HIGH/CRITICAL or secret scan')
 acceptance=smoke(image,version)
 return {'status':'staged','version':version,'image_id':image_id,'manifest_hash':hashlib.sha256(canonical(payload)).hexdigest(),'signature':'verified','scan_findings':findings,'isolated_acceptance':acceptance}

def publish(version):
 initialize();archive=ROOT/'releases'/('FOXORY-Local-v'+version+'.zip')
 import foxory_control as control
 control.validate_archive(version);dest=ROOT/'release-channel'/archive.name;shutil.copy2(archive,dest)
 payload={'schema':1,'version':version,'archive':dest.name,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'image_id':cap(['docker','image','inspect','foxory-local-app:'+version,'--format','{{.Id}}'])}
 trust=ROOT/'update-trust'
 with tempfile.TemporaryDirectory(prefix='sign-',dir=trust) as folder:
  p=Path(folder);(p/'message').write_bytes(canonical(payload));run(['openssl','pkeyutl','-sign','-inkey',str(trust/'signing-key.pem'),'-rawin','-in',str(p/'message'),'-out',str(p/'signature')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);signature=base64.b64encode((p/'signature').read_bytes()).decode()
 write(ROOT/'release-channel/channel.json',{'payload':payload,'signature':signature});return payload

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['init','check','publish','stage']);parser.add_argument('version',nargs='?');args=parser.parse_args()
 if args.action=='init':initialize();print('Local update trust initialized. Private signing key remains host-only.')
 elif args.action=='publish':print(json.dumps(publish(args.version)))
 elif args.action=='check':print(json.dumps(check()))
 else:print(json.dumps(stage()))
if __name__=='__main__':main()
