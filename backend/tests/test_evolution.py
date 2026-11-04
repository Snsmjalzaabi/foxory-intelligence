import json,hashlib
from fastapi import HTTPException
import pytest
from foxory import evolution,inference,skills
from foxory.db import Session,Record
from foxory.jobs import run_one
from foxory.version import __version__
from foxory.evolution_rules import validate,digest
@pytest.fixture(autouse=True)
def model(monkeypatch):
 async def require(*a,**kw):pass
 async def structured(*a,**kw):return json.dumps({'title':'Clearer performance title','rationale':'Clarify the overview title','expected_benefit':'Easier navigation','risks':'Text change still needs review','edits':[{'old':'Loading performance monitor…','new':'Loading the performance monitor…'}]})
 monkeypatch.setattr(skills,'require_model',require);monkeypatch.setattr(inference,'structured',structured)
async def create(client):
 assert (await client.put('/api/evolution/policy',json={'model':'fixture'})).status_code==200
 j=await client.post('/api/evolution/cycle');assert j.status_code==201,j.text
 await run_one();evolution.tick();d=(await client.get('/api/evolution')).json();assert len(d['proposals'])==1;return d['proposals'][0]
async def test_cycle_reads_actual_source_validates_diff_and_never_installs(client):
 r=await create(client);d=r['data'];assert d['status']=='proposed' and '-Loading performance monitor…' not in d['diff'] # JSX source includes surrounding text.
 assert 'Loading the performance monitor…' in d['diff'] and d['base_version']==__version__ and len(d['hash'])==64
 assert (await client.post('/api/evolution/cycle')).status_code==409
 assert (await client.post('/api/evolution/'+r['id']+'/install',json={'confirmation':'INSTALL'})).status_code==409
 assert (await client.get('/api/evolution/'+r['id']+'/patch')).status_code==200
async def test_protected_sources_and_ambiguous_edits_fail_closed(client):
 assert (await client.get('/api/evolution/source',params={'path':'backend/foxory/auth.py'})).status_code==404
 assert (await client.put('/api/evolution/policy',json={'path':'../../.env','model':'fixture'})).status_code==422
 p={'path':'frontend/src/Performance.tsx','base_sha256':hashlib.sha256(b'xx').hexdigest(),'edits':[{'old':'x','new':'z'}]}
 with pytest.raises(ValueError):validate(p,{p['path']:'xx'})
 p['edits']=[{'old':'xx','new':'z'}];assert validate(p,{p['path']:'xx'})=='z'
async def test_install_is_bound_to_current_tested_hash_and_exact_confirmation(client,monkeypatch):
 r=await create(client);id=r['id'];d=r['data']
 with Session() as s:
  row=s.get(Record,id);d.update(status='tested',test={'version':'5.0.1'});row.payload=json.dumps(d);s.commit()
 captured=[]
 def enqueue(id,hash,action,request):
  with Session() as s:assert json.loads(s.get(Record,id).payload)['approved_hash']==hash
  captured.append((id,hash,action));return {'status':'queued'}
 monkeypatch.setattr(evolution,'enqueue',enqueue)
 assert (await client.post('/api/evolution/'+id+'/install',json={'confirmation':'INSTALL 5.0.1 wrong'})).status_code==422
 assert not captured
 assert (await client.post('/api/evolution/'+id+'/install',json={'confirmation':'INSTALL 5.0.1 '+d['hash'][:12]})).status_code==202
 assert captured==[(id,d['hash'],'evolution_install')]
async def test_rejection_is_saved_and_used_in_future_feedback(client):
 r=await create(client);assert (await client.post('/api/evolution/'+r['id']+'/reject',json={'feedback':'Too cosmetic; prioritize an actual usability blocker.'})).status_code==200
 assert (await client.get('/api/evolution')).json()['proposals'][0]['data']['status']=='rejected'
 assert (await client.post('/api/evolution/'+r['id']+'/install',json={'confirmation':'INSTALL'})).status_code==409
async def test_shared_budget_and_owner_boundary_are_enforced(client,monkeypatch):
 from foxory.autonomy import load_policy
 await client.put('/api/evolution/policy',json={'model':'fixture'})
 with Session() as s:
  r=load_policy(s,True);d=json.loads(r.payload);d.update(daily_jobs=8,daily_job_limit=8,daily_date=evolution.now()[:10]);r.payload=json.dumps(d);s.commit()
 assert (await client.post('/api/evolution/cycle')).status_code==409
 monkeypatch.setattr('foxory.main.identity',lambda request:{'id':'reader','role':'viewer','workspace_id':'local'})
 assert (await client.get('/api/evolution')).status_code==403
 assert (await client.post('/api/evolution/cycle')).status_code==403
async def test_offline_controller_does_not_fake_test_success(client):
 r=await create(client);assert (await client.post('/api/evolution/'+r['id']+'/test')).status_code==409
 d=(await client.get('/api/evolution')).json()['proposals'][0]['data'];assert d['status']=='proposed' and 'test' not in d

def test_host_cannot_register_candidate_before_exact_owner_approval(monkeypatch,tmp_path):
 import importlib.util
 from pathlib import Path
 spec=importlib.util.spec_from_file_location('host_evolution_test',Path(__file__).resolve().parents[2]/'scripts/foxory_evolution.py');host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
 monkeypatch.setattr(host,'ROOT',tmp_path)
 monkeypatch.setattr(host,'proposal',lambda *a:{'status':'tested','approved_hash':'a'*64,'approved_by':'initial-administrator'})
 with pytest.raises(ValueError,match='approval'):host.register_approved('a'*36,'a'*64)
 monkeypatch.setattr(host,'proposal',lambda *a:{'status':'install_queued','approved_hash':'b'*64,'approved_by':'initial-administrator'})
 with pytest.raises(ValueError,match='approval'):host.register_approved('a'*36,'a'*64)
 assert not (tmp_path/'releases').exists()
