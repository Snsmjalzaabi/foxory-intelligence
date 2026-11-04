import hashlib,importlib.util,json,zipfile
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('foxory_control_test',Path(__file__).resolve().parents[2]/'scripts/foxory_control.py');control=importlib.util.module_from_spec(spec);spec.loader.exec_module(control)
def archive(root,extra=None):
 folder=root/'releases';folder.mkdir(exist_ok=True);p=folder/'FOXORY-Local-v2.0.0.zip';files={'VERSION':b'2.0.0\n','README.md':b'Local source'}
 manifest={'version':'2.0.0','files':[{'path':k,'sha256':hashlib.sha256(v).hexdigest()} for k,v in files.items()]}
 with zipfile.ZipFile(p,'w') as z:
  for k,v in files.items():z.writestr('FOXORY-Local/'+k,v)
  z.writestr('FOXORY-Local/SOURCE-MANIFEST.json',json.dumps(manifest))
  if extra:z.writestr(*extra)
 p.with_suffix('.sha256').write_text(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name)
 return p
@pytest.mark.parametrize('extra',[('FOXORY-Local/../../outside','bad'),('FOXORY-Local/.env','private'),('FOXORY-Local/extra.py','unmanifested')])
def test_controller_rejects_unsafe_or_unmanifested_release(tmp_path,monkeypatch,extra):
 monkeypatch.setattr(control,'ROOT',tmp_path);archive(tmp_path,extra)
 with pytest.raises(ValueError):control.validate_archive('2.0.0')
def test_controller_validates_file_hashes_before_installing(tmp_path,monkeypatch):
 monkeypatch.setattr(control,'ROOT',tmp_path);p=archive(tmp_path);control.validate_archive('2.0.0');control.install_source('2.0.0');assert (tmp_path/'VERSION').read_text()=='2.0.0\n'
 p.write_bytes(p.read_bytes()+b'tamper')
 with pytest.raises(ValueError):control.validate_archive('2.0.0')

def test_stale_controller_request_never_runs_host_commands(tmp_path,monkeypatch):
 monkeypatch.setattr(control,'ROOT',tmp_path);monkeypatch.setattr(control,'PUBLIC',tmp_path/'state.json')
 calls=[];monkeypatch.setattr(control,'run',lambda *a,**k:calls.append(a));monkeypatch.setattr(control,'exec_app',lambda *a,**k:'');monkeypatch.setattr(control,'backup_info',lambda:None)
 state={'epoch':'current-epoch','operations':[]}
 control.process({'id':'a'*32,'action':'backup','actor_id':'initial-administrator','epoch':'old-epoch'},state)
 assert not calls and state['operations'][0]['status']=='failed'
