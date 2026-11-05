"""Package only source into a versioned FOXORY release ZIP with per-file hashes."""
import argparse,hashlib,json,re,zipfile
from pathlib import Path
EXCLUDE={'evolution-work','.git','.venv','node_modules','__pycache__','.pytest_cache','test-results','playwright-report','data','backups','releases','update-trust','release-channel','update-cache','security-tools','.maintenance-inbox','.ollama','.local-ai'}
PRIVATE={'.env','SOURCE-MANIFEST.json','update-policy.json','maintenance-state.json','maintenance-state.tmp','.maintenance-controller.lock','foxory_control_backup.py','.coverage'}
def package(root,out):
 root=root.resolve();version=(root/'VERSION').read_text().strip()
 if not re.fullmatch(r'\d+\.\d+\.\d+',version):raise ValueError('Invalid source release version')
 files=[]
 for p in sorted(root.rglob('*')):
  parts=p.relative_to(root).parts
  if any(x in EXCLUDE or x.endswith('.egg-info') for x in parts) or p.name in PRIVATE or p.name.endswith(('.pyc','.tsbuildinfo','.gguf','.safetensors')) or p.name.startswith('.env.') and p.name!='.env.example':continue
  if p.is_symlink():raise ValueError('Release source cannot contain symlinks: '+str(p.relative_to(root)))
  if p.is_file() and p.resolve()!=out.resolve():files.append(p)
 manifest={'version':version,'upstream':'https://github.com/Snsmjalzaabi/foxory-intelligence','commit':'ed7356e5b24883c718349a97134b88e291a72bcd','files':[{'path':str(p.relative_to(root)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]}
 m=root/'SOURCE-MANIFEST.json';m.write_text(json.dumps(manifest,indent=2)+'\n');out.parent.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
  for p in files+[m]:z.write(p,'FOXORY-Local/'+str(p.relative_to(root)))
 with zipfile.ZipFile(out) as z:
  if z.testzip() is not None:raise ValueError('ZIP integrity failed')
 digest=hashlib.sha256(out.read_bytes()).hexdigest();out.with_suffix('.sha256').write_text(digest+'  '+out.name+'\n');return {'version':version,'files':len(files)+1,'sha256':digest}
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();print(json.dumps(package(args.root,args.output)))
if __name__=='__main__':main()
