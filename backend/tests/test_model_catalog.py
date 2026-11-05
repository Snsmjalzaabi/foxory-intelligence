import pytest
from foxory import inference,model_registry,maintenance
from foxory.db import now
from foxory.model_catalog import CATALOG,LICENSES,ROLES,entry
from foxory.model_routing import choose
from tests.test_accounts import setup

GIB=1024**3

def test_catalogue_is_consistent():
 names=[c[0] for c in CATALOG]
 assert len(names)==len(set(names))
 for name,family,roles,download,context,license,summary in CATALOG:
  assert license in LICENSES and roles and set(roles)<={'chat','writing','reasoning','coding','tools','vision','embedding'}
  assert 0<download<6 and context>=2048 and summary
 # Every role has at least one model under an unrestricted open license.
 for role in ROLES:assert any(role in c[2] and LICENSES[c[5]][1] for c in CATALOG),role
 assert entry('nomic-embed-text:latest')[0]=='nomic-embed-text' and entry('qwen3:8b')[0]=='qwen3:8b' and entry('qwen3:latest') is None

async def test_recommended_marks_installed_fit_and_starter(client,monkeypatch):
 await setup(client)
 async def models():return [{'name':'qwen3:8b'},{'name':'nomic-embed-text:latest'}]
 monkeypatch.setattr(inference,'models',models)
 monkeypatch.setattr(maintenance,'state',lambda:{'controller':'connected','hardware':{'sampled_at':now(),'gpus':[{'total_bytes':12*GIB}]}})
 data=(await client.get('/api/models/recommended')).json()
 rows={r['name']:r for r in data['models']}
 assert data['available'] and data['memory_budget_bytes']==pytest.approx(12*GIB*.85)
 assert rows['qwen3:8b']['installed'] and rows['nomic-embed-text']['installed'] and not rows['gemma3:4b']['installed']
 assert all(r['fits'] for r in rows.values())
 assert rows['gemma3:4b']['open_license'] is False and rows['qwen3:4b']['license_url'].startswith('https://')
 starter={n for n,r in rows.items() if r['starter']}
 # Known memory: the largest fitting open model per role; qwen3:8b covers chat and reasoning.
 assert starter=={'qwen3:8b','qwen2.5-coder:7b','nomic-embed-text'}

async def test_recommended_with_small_memory_and_unknown_hardware(client,monkeypatch):
 await setup(client)
 async def models():return []
 monkeypatch.setattr(inference,'models',models)
 monkeypatch.setattr(maintenance,'state',lambda:{'controller':'connected','hardware':{'sampled_at':now(),'memory':{'available_bytes':4*GIB}}})
 rows={r['name']:r for r in (await client.get('/api/models/recommended')).json()['models']}
 assert rows['qwen3:1.7b']['fits'] and not rows['qwen3:8b']['fits']
 assert all(rows[n]['fits'] for n in rows if rows[n]['starter'])
 # Unknown hardware: never claim a fit; start with the smallest open model per role.
 monkeypatch.setattr(maintenance,'state',lambda:{})
 data=(await client.get('/api/models/recommended')).json();rows={r['name']:r for r in data['models']}
 assert data['memory_budget_bytes'] is None and all(r['fits'] is None for r in rows.values())
 assert {n for n,r in rows.items() if r['starter']}=={'qwen3:1.7b','qwen2.5-coder:1.5b','deepseek-r1:1.5b','nomic-embed-text'}

async def test_recommended_when_ollama_is_down(client,monkeypatch):
 await setup(client)
 async def down():raise OSError('offline')
 monkeypatch.setattr(inference,'models',down);monkeypatch.setattr(maintenance,'state',lambda:{})
 data=(await client.get('/api/models/recommended')).json()
 assert not data['available'] and not any(r['installed'] for r in data['models'])

def routing(monkeypatch,models):
 async def inventory():return models
 async def catalog(values,**kw):return values
 monkeypatch.setattr(inference,'models',inventory);monkeypatch.setattr(model_registry,'catalog',catalog);monkeypatch.setattr(maintenance,'state',lambda:{})

async def test_reported_thinking_capability_routes_reasoning(monkeypatch):
 general={'name':'house-general:4b','size':2.5*GIB,'completion_supported':True,'details':{'parameter_size':'4B'}}
 thinker={'name':'house-thinker:4b','size':2.5*GIB,'completion_supported':True,'capabilities':['completion','thinking'],'details':{'parameter_size':'4B'}}
 routing(monkeypatch,[general,thinker])
 assert (await choose('Compare a complex strategy'))['model']=='house-thinker:4b'
 assert (await choose('Hi there'))['model']=='house-general:4b'

async def test_catalogue_roles_route_newer_models(monkeypatch):
 models=[{'name':'granite3.3:2b','size':1.5*GIB,'completion_supported':True,'details':{'parameter_size':'2B'}},
  {'name':'phi4-mini:3.8b','size':2.5*GIB,'completion_supported':True,'details':{'parameter_size':'3.8B'}},
  {'name':'qwen2.5-coder:1.5b','size':1*GIB,'completion_supported':True,'details':{'parameter_size':'1.5B'}}]
 routing(monkeypatch,models)
 assert (await choose('Debug this Python bug'))['model']=='qwen2.5-coder:1.5b'
 assert (await choose('Compare a complex strategy'))['model']=='phi4-mini:3.8b'
 assert (await choose('Write a complete chapter'))['model']=='granite3.3:2b'
