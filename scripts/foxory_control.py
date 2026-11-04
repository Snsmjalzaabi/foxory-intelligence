"""Separate local owner controller. Fixed backup/verify/activate actions; no shell API."""
import fcntl,argparse,datetime,hashlib,json,os,re,shutil,subprocess,sys,tempfile,time,urllib.request,zipfile
from foxory_compose import compose
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
COMPOSE=compose()
PUBLIC=ROOT/'maintenance-state.json'
def run(args,**kw):return subprocess.run(args,cwd=ROOT,check=True,**kw)
def capture(args):return subprocess.check_output(args,cwd=ROOT,text=True).strip()
def exec_app(command,payload=None):
 return subprocess.check_output(COMPOSE+['exec','-T','app','python','-m','foxory.maintenance',*command],cwd=ROOT,input=json.dumps(payload) if payload is not None else None,text=True,stderr=subprocess.DEVNULL).strip()
def validate_archive(version):
 if not re.fullmatch(r'\d+\.\d+\.\d+',version):raise ValueError('Invalid release version')
 path=ROOT/'releases'/('FOXORY-Local-v'+version+'.zip');expected=path.with_suffix('.sha256').read_text().split()[0]
 if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError('Release archive checksum failed')
 with zipfile.ZipFile(path) as z:
  if sum(x.file_size for x in z.infolist())>100_000_000:raise ValueError('Release exceeds local size budget')
  for info in z.infolist():
   p=PurePosixPath(info.filename)
   if p.is_absolute() or '..' in p.parts or len(p.parts)<2 or p.parts[0]!='FOXORY-Local' or (info.external_attr>>16)&0o170000==0o120000:raise ValueError('Unsafe release member')
   if any(x in {'.env','backups','releases','data','node_modules','.git','update-trust','release-channel','update-cache','security-tools','update-policy.json','evolution-work'} for x in p.parts):raise ValueError('Private/runtime files are not release source')
  manifest=json.loads(z.read('FOXORY-Local/SOURCE-MANIFEST.json'))
  if manifest['version']!=version or z.read('FOXORY-Local/VERSION').decode().strip()!=version:raise ValueError('Release metadata mismatch')
  names={x['path'] for x in manifest['files']}|{'SOURCE-MANIFEST.json'}
  if any('/'.join(PurePosixPath(x.filename).parts[1:]) not in names for x in z.infolist() if not x.is_dir()):raise ValueError('Unmanifested release file')
  for x in manifest['files']:
   if hashlib.sha256(z.read('FOXORY-Local/'+x['path'])).hexdigest()!=x['sha256']:raise ValueError('Release source hash mismatch')
 return path

def catalogue():
 values=[]
 for archive in sorted((ROOT/'releases').glob('FOXORY-Local-v*.zip')):
  version=archive.stem.removeprefix('FOXORY-Local-v')
  try:
   try:blocked=json.loads(PUBLIC.read_text()).get('failed_updates',{})
   except (OSError,ValueError):blocked={}
   if version in blocked:values.append({'version':version,'available':False,'reason':'Rejected update candidate'});continue
   validate_archive(version)
   image=capture(['docker','image','inspect','foxory-local-app:'+version,'--format','{{.Id}}'])
   actual=capture(['docker','run','--rm','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges:true','--entrypoint','python','foxory-local-app:'+version,'-c','from foxory.version import __version__;print(__version__)'])
   if actual!=version:raise ValueError('Image version mismatch')
   values.append({'version':version,'image':image,'available':True,'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()})
  except (OSError,ValueError,subprocess.SubprocessError):values.append({'version':version,'available':False})
 return values

def install_source(version):
 archive=validate_archive(version)
 with zipfile.ZipFile(archive) as z:
  for info in z.infolist():
   if info.is_dir():continue
   relative=PurePosixPath(info.filename).parts[1:];dest=ROOT.joinpath(*relative)
   # Existing private runtime files are never members of a verified source package.
   dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(info));os.chmod(dest,0o755 if (info.external_attr>>16)&0o111 else 0o644)

def backup_info():
 dirs=sorted((ROOT/'backups').glob('foxory-*'))
 if not dirs:return None
 p=dirs[-1];return {'name':p.name,'has_checksums':(p/'checksums.json').is_file(),'created_at':datetime.datetime.fromtimestamp(p.stat().st_mtime,datetime.timezone.utc).isoformat()}
def publish(state):
 temp=PUBLIC.with_suffix('.tmp');temp.write_text(json.dumps(state,indent=2)+'\n');temp.chmod(0o600);os.replace(temp,PUBLIC)
 try:exec_app(['publish'],state)
 except subprocess.SubprocessError:pass

def healthy(version,timeout=90):
 for _ in range(timeout):
  try:
   with urllib.request.urlopen('http://127.0.0.1:3636/api/health',timeout=2) as response:
    if json.load(response)['version']==version:return
  except (OSError,ValueError):pass
  time.sleep(1)
 raise RuntimeError('Selected application version did not become healthy')

def process(request,state):
 action=request.get('action');version=request.get('target_version')
 if action not in {'backup','verify','activate','check_updates','upgrade','updates_on','updates_off','evolution_test','evolution_install'} or request.get('actor_id') not in {'initial-administrator','bootstrap'} or not re.fullmatch('[a-f0-9]{32}',request.get('id','')):raise ValueError('Invalid local operation request')
 record={k:request.get(k) for k in ['id','action','target_version','created_at']};record.update(status='running',phase='Preparing');state.setdefault('operations',[]).insert(0,record);state['operations']=state['operations'][:20];publish(state)
 try:
  if request.get('epoch')!=state.get('epoch') or not state.get('epoch'):raise ValueError('Controller restarted or request expired. Review and request the operation again.')
  if action in {'evolution_test','evolution_install'}:
   import foxory_evolution as evolution
   proposal_id=request.get('proposal_id');proposal_hash=request.get('proposal_hash')
   if action=='evolution_test':
    record['phase']='Building and checking isolated code candidate';publish(state);evolution.test(proposal_id,proposal_hash)
   else:
    target=evolution.register_approved(proposal_id,proposal_hash)
    nested={'id':__import__('secrets').token_hex(16),'action':'upgrade','actor_id':request['actor_id'],'epoch':state['epoch'],'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    process(nested,state)
    if state['operations'][0]['status']!='completed':raise ValueError('Approved candidate failed activation; inspect Recovery')
    evolution.report(proposal_id,proposal_hash,status='installed',installed_version=target)
  if action in {'check_updates','upgrade','updates_on','updates_off'}:
   import foxory_updates as updates
   cfg=updates.initialize()
   if action in {'updates_on','updates_off'}:
    cfg['enabled']=action=='updates_on';state['last_update_check_epoch']=0;updates.write(ROOT/'update-policy.json',cfg);state['updates']={**state.get('updates',{}),'enabled':cfg['enabled']}
   else:
    record['phase']='Verifying signed update channel';publish(state)
    checked=updates.check();state['updates']={**checked,'enabled':cfg['enabled'],'auto_activate':cfg.get('auto_activate',True)};publish(state)
    blocked=state.get('failed_updates',{})
    if action=='upgrade' and checked['status']=='available':
     if blocked.get(checked['candidate_version'])==checked['manifest_hash']:raise ValueError('This exact candidate already failed; publish a corrected release or explicitly review it before retrying.')
     record['phase']='Scanning and testing isolated candidate';publish(state)
     candidate=updates.stage();state['updates']['candidate_acceptance']=candidate
     nested={'id':__import__('secrets').token_hex(16),'action':'activate','target_version':candidate['version'],'actor_id':request['actor_id'],'epoch':state['epoch'],'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
     process(nested,state)
     if state['operations'][0]['status']!='completed':raise ValueError('Candidate activation failed; preceding application/source was restored.')
     state['updates'].update(status='installed',installed_version=candidate['version'])
  if action in {'backup','activate'}:
   record['phase']='Coordinated private backup';publish(state);run([sys.executable,'scripts/foxory_control_backup.py' if (ROOT/'scripts/foxory_control_backup.py').is_file() else 'scripts/foxory_backup.py'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  if action=='verify':
   latest=backup_info()
   if not latest:raise ValueError('Create a private backup first')
   record['phase']='Restoring into disposable offline volumes';publish(state)
   report=ROOT/'backups'/'last-verification.json';run([sys.executable,'scripts/verify_backup_restore.py',str(ROOT/'backups'/latest['name']),'--report',str(report)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   d=json.loads(report.read_text());state['verification']={'status':d['status'],'backup':latest['name'],'application_files':d['verified_application_files'],'at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
  if action=='activate':
   if version not in {x['version'] for x in catalogue() if x['available']}:raise ValueError('Release is not registered and verified locally')
   with urllib.request.urlopen('http://127.0.0.1:3636/api/health',timeout=5) as r:old=json.load(r)['version']
   validate_archive(old)
   if int(old.split('.')[0])>=6 and int(version.split('.')[0])<6:
    count=capture(COMPOSE+['exec','-T','db','psql','-U','foxory','-d','foxory','-At','-c',"SELECT COUNT(*) FROM records WHERE kind IN ('chat_learning','chat_review')"])
    if int(count):raise ValueError('Personal conversational learning requires V6 or newer; use a reviewed matching data restore for a pre-V6 rollback')
   def migrations(v):
    with zipfile.ZipFile(validate_archive(v)) as archive:
     return {x['path']:x['sha256'] for x in json.loads(archive.read('FOXORY-Local/SOURCE-MANIFEST.json'))['files'] if x['path'].startswith('backend/migrations/')}
   if migrations(old)!=migrations(version):raise ValueError('Database migration files differ; use a reviewed manual migration/restore plan instead of automatic activation')
   record['phase']='Activating local application image '+version;publish(state)
   try:
    install_source(version);run(['docker','tag','foxory-local-app:'+version,'foxory-local-app:latest']);run(COMPOSE+['up','-d','--no-build','--wait','--wait-timeout','120','app'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);healthy(version)
   except Exception:
    install_source(old);run(['docker','tag','foxory-local-app:'+old,'foxory-local-app:latest']);run(COMPOSE+['up','-d','--no-build','--wait','--wait-timeout','120','app'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);healthy(old);raise
   record['rollback_version']=old
  record.update(status='completed',phase='Completed',finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
 except Exception as error:
  record.update(status='failed',phase='Stopped',error=type(error).__name__+': '+str(error)[:300])
  if action in {'evolution_test','evolution_install'}:
   try:
    import foxory_evolution as evolution
    evolution.failure(request.get('proposal_id'),request.get('proposal_hash'),record['error'],'test_failed' if action=='evolution_test' else 'install_failed')
   except Exception:pass
  if action=='upgrade':
   u=state.setdefault('updates',{});u.update(status='failed',last_error=record['error'])
   if u.get('candidate_version') and u.get('manifest_hash'):state.setdefault('failed_updates',{})[u['candidate_version']]=u['manifest_hash']
 state['backup']=backup_info();publish(state)
 try:exec_app(['finish',request['id']])
 except subprocess.SubprocessError:pass

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['run','once','status','backup','verify','activate','install','check_updates','upgrade','updates_on','updates_off']);parser.add_argument('version',nargs='?');args=parser.parse_args()
 if args.action=='install':
  unit=Path.home()/'.config/systemd/user/foxory-control.service';unit.parent.mkdir(parents=True,exist_ok=True)
  unit.write_text('[Unit]\nDescription=FOXORY fixed local maintenance controller\nAfter=default.target\n\n[Service]\nType=simple\nWorkingDirectory='+str(ROOT)+'\nExecStart='+json.dumps(sys.executable)+' '+json.dumps(str(ROOT/'scripts/foxory_control.py'))+' run\nRestart=on-failure\nRestartSec=10\n\n[Install]\nWantedBy=default.target\n')
  run(['systemctl','--user','daemon-reload']);run(['systemctl','--user','enable','--now','foxory-control.service'])
  try:old=json.loads(PUBLIC.read_text())
  except (OSError,ValueError):old={}
  if old.get('controller_source_hash')!=hashlib.sha256(Path(__file__).read_bytes()).hexdigest():
   if any(x.get('status')=='running' for x in old.get('operations',[])):raise SystemExit('Maintenance is running; retry automation after it finishes.')
   run(['systemctl','--user','restart','foxory-control.service'])
  print('FOXORY local controller installed for this user.');return
 if args.action=='status':print(PUBLIC.read_text() if PUBLIC.exists() else 'Controller has not published state');return
 lock=(ROOT/'.maintenance-controller.lock').open('a')
 try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 except BlockingIOError:
  if args.action not in {'backup','verify','activate','check_updates','upgrade','updates_on','updates_off'}:raise SystemExit('The local controller is already running')
  if args.action=='activate' and not re.fullmatch(r'\d+\.\d+\.\d+',args.version or ''):parser.error('Choose a registered version')
  inbox=ROOT/'.maintenance-inbox';inbox.mkdir(exist_ok=True,mode=0o700)
  request={'id':__import__('secrets').token_hex(16),'action':args.action,'target_version':args.version,'actor_id':'initial-administrator','created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'epoch':json.loads(PUBLIC.read_text()).get('epoch')}
  path=inbox/(request['id']+'.json');temp=inbox/('.'+request['id']);temp.write_text(json.dumps(request));temp.chmod(0o600);temp.replace(path)
  print('Queued local maintenance operation '+request['id']+'. Use status to inspect progress.');return
 try:state=json.loads(PUBLIC.read_text())
 except (OSError,ValueError):state={'operations':[]}
 helper=ROOT/'scripts/foxory_backup.py'
 if '--exclude=./maintenance' in helper.read_text():shutil.copy2(helper,ROOT/'scripts/foxory_control_backup.py')
 release_version=(ROOT/'VERSION').read_text().strip()
 source_hash=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
 state.update(controller='connected',controller_source_hash=source_hash,releases=catalogue(),backup=backup_info(),epoch=__import__('secrets').token_hex(24));publish(state)
 if args.action in {'backup','verify','activate','check_updates','upgrade','updates_on','updates_off'}:
  if args.action=='activate' and not args.version:parser.error('Choose a registered version')
  request={'id':__import__('secrets').token_hex(16),'action':args.action,'target_version':args.version,'actor_id':'initial-administrator','created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'epoch':state['epoch']}
  process(request,state)
  if state['operations'][0]['status']!='completed':raise SystemExit('Maintenance operation failed; inspect maintenance-state.json')
  return
 while True:
  if time.time()-state.get('hardware_sample_epoch',0)>30:
   from foxory_hardware import collect
   state['hardware']=collect();state['hardware_sample_epoch']=time.time()
  state['heartbeat_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();publish(state)
  try:
   inbox=ROOT/'.maintenance-inbox';inbox.mkdir(exist_ok=True,mode=0o700)
   paths=sorted(inbox.glob('*.json'))
   path=paths[0] if paths else None
   request=json.loads(path.read_text()) if path else json.loads(exec_app(['next']))
   if request:
    prior=next((x for x in state.get('operations',[]) if x.get('id')==request['id']),None)
    if prior and prior.get('status') in {'completed','failed'}:
     try:exec_app(['finish',request['id']])
     except subprocess.SubprocessError:pass
    else:process(request,state)
    if path:path.unlink(missing_ok=True)
  except (subprocess.SubprocessError,ValueError,OSError):pass
  if args.action=='once':break
  try:
   import foxory_updates as updates
   cfg=updates.config()
   if cfg.get('enabled') and time.time()-state.get('last_update_check_epoch',0)>=max(60,cfg.get('interval_minutes',360))*60:
    state['last_update_check_epoch']=time.time()
    request={'id':__import__('secrets').token_hex(16),'action':'upgrade' if cfg.get('auto_activate',True) else 'check_updates','actor_id':'initial-administrator','epoch':state['epoch'],'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    process(request,state)
  except (OSError,ValueError):pass
  if hashlib.sha256(Path(__file__).read_bytes()).hexdigest()!=source_hash or (ROOT/'VERSION').read_text().strip()!=release_version:
   publish(state);os.execv(sys.executable,[sys.executable,str(Path(__file__).resolve()),'run'])
  time.sleep(5)
if __name__=='__main__':main()
