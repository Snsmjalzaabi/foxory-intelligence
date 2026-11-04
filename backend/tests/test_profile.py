import json
import pytest
from foxory import profile
from tests.test_accounts import setup

@pytest.fixture
def folder(tmp_path,monkeypatch):
 monkeypatch.setattr(profile,'FOLDER',tmp_path);monkeypatch.delenv('FOXORY_PROFILE',raising=False);profile.active.cache_clear()
 base=json.loads((profile.Path(__file__).resolve().parents[2]/'profiles'/'default.json').read_text())
 (tmp_path/'default.json').write_text(json.dumps(base));yield tmp_path,base
 profile.active.cache_clear()

def test_shipped_profiles_are_valid():
 for path in (profile.Path(__file__).resolve().parents[2]/'profiles').glob('*.json'):
  p=profile.Profile.model_validate(json.loads(path.read_text()));assert p.currency in p.currencies and p.name==path.stem

def test_selection_prefers_personal_then_default(folder,monkeypatch):
 tmp,base=folder
 assert profile.active().name=='default' and profile.active().timezone=='UTC'
 (tmp/'personal.json').write_text(json.dumps({**base,'name':'personal','machine_name':'MyPC','timezone':'Europe/Berlin','currency':'EUR'}))
 profile.active.cache_clear();assert profile.active().machine_name=='MyPC'
 monkeypatch.setenv('FOXORY_PROFILE','default');profile.active.cache_clear();assert profile.active().name=='default'
 monkeypatch.setenv('FOXORY_PROFILE','../etc/passwd');profile.active.cache_clear()
 with pytest.raises(RuntimeError):profile.active()

def test_invalid_profile_fails_loudly(folder):
 tmp,base=folder
 (tmp/'default.json').write_text(json.dumps({**base,'currency':'XYZ'}));profile.active.cache_clear()
 with pytest.raises(RuntimeError):profile.active()
 (tmp/'default.json').write_text(json.dumps({**base,'unknown_field':1}));profile.active.cache_clear()
 with pytest.raises(Exception):profile.active()

async def test_api_and_defaults_follow_the_profile(client,folder):
 await setup(client)
 data=(await client.get('/api/profile')).json()
 assert data['name']=='default' and data['currency']=='USD' and len(data['starters'])==4
 opp=(await client.post('/api/business/opportunities',json={'title':'Pilot'})).json()
 assert opp['data']['currency']=='USD'
 from foxory.autonomy import Policy
 assert Policy().model=='qwen3:4b'
