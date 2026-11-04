"""Fixed host-side candidate builds. Never signs or publishes before owner approval."""
import hashlib,importlib.util,json,re,shutil,subprocess,sys,zipfile
from foxory_compose import compose
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ACTIVE_FOLDER=None
def run(args,**kw):
 if ACTIVE_FOLDER:
  with (ACTIVE_FOLDER/'build.log').open('a') as log:
   kw.update(stdout=log,stderr=log);return subprocess.run(args,cwd=ROOT,check=True,**kw)
 return subprocess.run(args,cwd=ROOT,check=True,**kw)
def app(args,payload=None):
 return subprocess.check_output([*compose(),'exec','-T','app','python','-m','foxory.evolution',*args],input=json.dumps(payload) if payload is not None else None,text=True,cwd=ROOT,stderr=subprocess.DEVNULL).strip()
def load_rules():
 spec=importlib.util.spec_from_file_location('trusted_evolution_rules',ROOT/'backend/foxory/evolution_rules.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def proposal(id,hash):
 if not re.fullmatch('[a-f0-9]{36}',str(id)) or not re.fullmatch('[a-f0-9]{64}',str(hash)):raise ValueError('Invalid proposal identity')
 p=json.loads(app(['export',id,hash]));rules=load_rules();core={k:p[k] for k in ['title','rationale','expected_benefit','risks','edits','path','base_version','base_sha256']}
 if rules.digest(core)!=hash:raise ValueError('Proposal digest mismatch')
 if p['base_version']!=(ROOT/'VERSION').read_text().strip():raise ValueError('Base release changed; generate a fresh candidate')
 return p

def report(id,hash,**kw):app(['report',id],{'hash':hash,**kw})
def test(id,hash):
 global ACTIVE_FOLDER
 import foxory_control as control,foxory_updates as updates
 p=proposal(id,hash)
 if p['status'] not in {'proposed','test_queued','test_failed','install_failed'}:raise ValueError('Candidate is not awaiting tests')
 archive=control.validate_archive(p['base_version']);folder=ROOT/'evolution-work'/(id+'-'+hash[:12]);folder.mkdir(parents=True,exist_ok=True,mode=0o700)
 ACTIVE_FOLDER=folder
 source=folder/'FOXORY-Local'
 if source.exists():shutil.rmtree(source)
 with zipfile.ZipFile(archive) as z:z.extractall(folder)
 path=source/p['path'];original=path.read_text();path.write_text(load_rules().validate(p,{p['path']:original}))
 base=[int(x) for x in p['base_version'].split('.')];base[2]+=1;version='.'.join(map(str,base))
 while (ROOT/'releases'/('FOXORY-Local-v'+version+'.zip')).exists() or any((ROOT/'evolution-work').glob('*/FOXORY-Local-v'+version+'.zip')):base[2]+=1;version='.'.join(map(str,base))
 run([sys.executable,str(source/'scripts/release_version.py'),version],stdout=subprocess.DEVNULL)
 # Build a trusted baseline UI toolchain first. Generated code never changes install scripts or dependencies.
 ui='foxory-evolution-ui:'+p['base_version'];run(['docker','build','--target','ui','-t',ui,str(ROOT)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=1200)
 dockerfile=folder/'Candidate.Dockerfile';dockerfile.write_text('FROM '+ui+' AS ui\nWORKDIR /build\nCOPY frontend/ ./\nRUN --network=none npm run build\nFROM foxory-local-app:'+p['base_version']+'\nCOPY --chown=10001:10001 backend/ /app/backend/\nCOPY --from=ui --chown=10001:10001 /build/dist /app/frontend/dist/\nCOPY --from=ui --chown=10001:10001 /build/src/Operations.tsx /build/src/Performance.tsx /app/evolution-source/\n')
 image='foxory-evolution:'+id;run(['docker','build','--network=none','-f',str(dockerfile),'-t',image,str(source)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=1200)
 # The candidate has no owner data, network, host mounts, devices or published ports during acceptance.
 run(['docker','run','--rm','--network','none','--read-only','--tmpfs','/tmp:size=64m','--cap-drop','ALL','--security-opt','no-new-privileges:true','--memory','512m','--entrypoint','python',image,'-c',"import ast,pathlib;[ast.parse(p.read_text()) for p in pathlib.Path('/app/backend/foxory').glob('*.py')]"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 acceptance=updates.smoke(image,version);scanner=updates.ensure_scanner();scan=folder/'scan.json';run([str(scanner),'image','--cache-dir',str(ROOT/'security-tools/cache'),'--severity','HIGH,CRITICAL','--format','json','--output',str(scan),image],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=600)
 findings=sum(len(x.get('Vulnerabilities',[]))+len(x.get('Secrets',[])) for x in json.loads(scan.read_text()).get('Results',[]))
 if findings:raise ValueError('Candidate has blocking security findings')
 package=folder/('FOXORY-Local-v'+version+'.zip');run([sys.executable,str(source/'scripts/package_release.py'),'--root',str(source),'--output',str(package)],stdout=subprocess.DEVNULL)
 image_id=subprocess.check_output(['docker','image','inspect',image,'--format','{{.Id}}'],text=True).strip();result={'version':version,'image':image,'image_id':image_id,'archive':str(package.relative_to(ROOT)),'archive_sha256':hashlib.sha256(package.read_bytes()).hexdigest(),'proposal_hash':hash,'scan_findings':0,'build':'passed','typescript':'passed','python_syntax':'passed','isolated_acceptance':acceptance,'quality':'Technical gates only. Expected benefit remains unverified until owner review and use.'}
 (folder/'tested.json').write_text(json.dumps(result,indent=2));report(id,hash,status='tested',test=result);return result

def register_approved(id,hash):
 p=proposal(id,hash)
 if p['status']!='install_queued' or p.get('approved_hash')!=hash or p.get('approved_by') not in {'initial-administrator','bootstrap'}:raise ValueError('Exact owner approval is required')
 folder=ROOT/'evolution-work'/(id+'-'+hash[:12]);test=json.loads((folder/'tested.json').read_text());archive=ROOT/test['archive']
 if test['proposal_hash']!=hash or hashlib.sha256(archive.read_bytes()).hexdigest()!=test['archive_sha256']:raise ValueError('Tested candidate changed')
 actual=subprocess.check_output(['docker','image','inspect',test['image'],'--format','{{.Id}}'],text=True).strip()
 if actual!=test['image_id']:raise ValueError('Tested image changed')
 version=test['version'];dest=ROOT/'releases'/archive.name
 if dest.exists():raise ValueError('Release version already registered')
 shutil.copy2(archive,dest);dest.with_suffix('.sha256').write_text(test['archive_sha256']+'  '+dest.name+'\n');run(['docker','tag',test['image'],'foxory-local-app:'+version])
 import foxory_updates as updates
 updates.publish(version);return version

def failure(id,hash,error,status):
 detail=str(error)[:300]
 if re.fullmatch('[a-f0-9]{36}',str(id)) and re.fullmatch('[a-f0-9]{64}',str(hash)):
  path=ROOT/'evolution-work'/(id+'-'+hash[:12])/'build.log'
  if path.is_file():
   with path.open('rb') as f:f.seek(max(0,path.stat().st_size-4000));detail+='\n'+f.read(4000).decode(errors='replace')
 report(id,hash,status=status,last_error=detail)
