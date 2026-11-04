import base64,hashlib,importlib.util,json,subprocess
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('foxory_updates_test',Path(__file__).resolve().parents[2]/'scripts/foxory_updates.py');updates=importlib.util.module_from_spec(spec);spec.loader.exec_module(updates)
def signed(tmp_path,monkeypatch):
 monkeypatch.setattr(updates,'ROOT',tmp_path);policy=updates.initialize();payload={'schema':1,'version':'3.0.1','archive':'release.zip','sha256':'a'*64}
 message=tmp_path/'message';signature=tmp_path/'signature';message.write_bytes(updates.canonical(payload))
 subprocess.run(['openssl','pkeyutl','-sign','-inkey',str(tmp_path/'update-trust/signing-key.pem'),'-rawin','-in',str(message),'-out',str(signature)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 envelope={'payload':payload,'signature':base64.b64encode(signature.read_bytes()).decode()};(tmp_path/'release-channel/channel.json').write_text(json.dumps(envelope));return policy,envelope

def test_real_ed25519_signature_is_required_and_payload_is_bound(tmp_path,monkeypatch):
 policy,envelope=signed(tmp_path,monkeypatch);assert updates.read_envelope(policy)['version']=='3.0.1'
 envelope['payload']['version']='99.0.0';(tmp_path/'release-channel/channel.json').write_text(json.dumps(envelope))
 with pytest.raises(ValueError,match='signature'):updates.read_envelope(policy)
def test_wrong_pinned_key_and_private_network_downloads_are_denied(tmp_path,monkeypatch):
 policy,envelope=signed(tmp_path,monkeypatch)
 other=tmp_path/'other.pem';subprocess.run(['openssl','genpkey','-algorithm','ED25519','-out',str(other)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 public=tmp_path/'other.pub';subprocess.run(['openssl','pkey','-in',str(other),'-pubout','-out',str(public)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);policy['trusted_public_key']=str(public)
 with pytest.raises(ValueError,match='signature'):updates.read_envelope(policy)
 for url in ['http://github.com/release','https://127.0.0.1/private','https://github.com.evil.test/x','https://user:password@github.com/x']:
  with pytest.raises(ValueError):updates.fetch(url,tmp_path/'out',100)
def test_old_version_is_not_an_automatic_upgrade(tmp_path,monkeypatch):
 policy,envelope=signed(tmp_path,monkeypatch);monkeypatch.setattr(updates,'current_version',lambda:'3.0.1')
 assert updates.check()['status']=='current';monkeypatch.setattr(updates,'current_version',lambda:'3.0.0');assert updates.check()['status']=='available'
def test_local_channel_cannot_escape_its_directory(tmp_path,monkeypatch):
 policy,envelope=signed(tmp_path,monkeypatch);policy['channel']=str(tmp_path/'outside.json')
 with pytest.raises(ValueError):updates.read_envelope(policy)
