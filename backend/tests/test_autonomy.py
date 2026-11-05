import json
import pytest
from foxory import skills,autonomy,inference
from foxory.db import Session,Record
from foxory.jobs import run_one
from foxory.scope import workspace_id
@pytest.fixture(autouse=True)
def models(monkeypatch):
 async def require(model):return None
 async def complete(*a,**kw):return 'Reviewable local draft. Unknown price and deadline remain unset.'
 async def structured(*a,**kw):return json.dumps(skills.BUNDLED[0])
 monkeypatch.setattr(skills,'require_model',require);monkeypatch.setattr(inference,'complete',complete);monkeypatch.setattr(inference,'structured',structured)
async def project(client):
 r=await client.post('/api/spaces',json={'title':'Test business','kind':'business','brief':'Validate a fictional idea; no demand or price supplied.'});assert r.status_code==201;return r.json()
async def configure(client,**values):
 r=await client.put('/api/autonomy/policy',json={'model':'fixture','learn_skills':False,**values});assert r.status_code==200,r.text
async def command(client,key='test-mission-key'):
 r=await client.post('/api/autonomy/command',json={'command':'Prepare a useful project draft','continuous':False,'idempotency_key':key});assert r.status_code==201,r.text;return r.json()
async def finish(client,id):
 for _ in range(60):
  autonomy.tick();await run_one()
  d=next(x['data'] for x in (await client.get('/api/autonomy')).json()['missions'] if x['id']==id)
  if d['status']=='completed':return d
 raise AssertionError(d)
async def test_one_command_bootstraps_tested_skills_and_captures_one_draft(client):
 p=await project(client);await configure(client)
 m=await command(client);assert (await command(client))['id']==m['id']
 d=await finish(client,m['id']);assert d['projects'][0]['status']=='completed'
 detail=(await client.get('/api/spaces/'+p['id'])).json();drafts=[x for x in detail['items'] if x['data']['kind']=='deliverable'];assert len(drafts)==1 and drafts[0]['data']['status']=='draft'
 assert any(x['data']['status']=='active' for x in (await client.get('/api/skills')).json())
 m2=await command(client,'second-mission-key');d2=await finish(client,m2['id']);assert d2['projects'][0]['status']=='skipped'
async def test_pause_resume_stops_bootstrap_work_and_preserves_progress(client):
 await project(client);await configure(client);m=await command(client);autonomy.tick()
 await client.post('/api/autonomy/stop')
 with Session() as s:assert all(json.loads(r.payload)['status']=='paused' for r in s.query(Record).filter(Record.kind=='job'))
 assert (await client.post('/api/autonomy/missions/'+m['id']+'/resume')).status_code==200
 d=await finish(client,m['id']);assert d['status']=='completed'
async def test_daily_budget_stops_instead_of_spinning_model_calls(client):
 await project(client);await configure(client,daily_job_limit=1);m=await command(client)
 for _ in range(15):autonomy.tick();await run_one()
 d=(await client.get('/api/autonomy')).json();assert d['policy']['daily_jobs']==1 and d['missions'][0]['data']['status']=='waiting_budget'
async def test_skill_schema_activation_gate_and_revision_pinning(client):
 r=await client.post('/api/skills',json={'definition':{**skills.BUNDLED[0],'steps':[{'action':'shell','instruction':'id'}]}});assert r.status_code==422
 row=(await client.post('/api/skills',json={'definition':skills.BUNDLED[0]})).json();assert (await client.post('/api/skills/'+row['id']+'/activate')).status_code in {404,409}
 job=(await client.post('/api/skills/'+row['id']+'/test',json={'model':'fixture','idempotency_key':'skill-first-test'})).json()
 for _ in range(10):await run_one()
 assert (await client.post('/api/skills/'+row['id']+'/activate')).status_code==200
 new={**skills.BUNDLED[0],'instructions':'Changed guidance; needs another test.'}
 changed=(await client.put('/api/skills/'+row['id'],json={'definition':new,'revision':0})).json();assert changed['data']['status']=='draft' and changed['data']['hash']!=row['data']['hash']
 assert (await client.post('/api/skills/'+row['id']+'/activate')).status_code in {404,409}
async def test_policy_rejects_unknown_writes_and_viewer_controls(client,monkeypatch):
 assert (await client.put('/api/autonomy/policy',json={'model':'fixture','shell':True})).status_code==422
 monkeypatch.setattr('foxory.main.identity',lambda request:{'id':'reader','role':'viewer','workspace_id':'local'})
 assert (await client.post('/api/autonomy/command',json={'idempotency_key':'not-allowed'})).status_code==403
async def test_self_learning_creates_and_tests_readonly_recipe(client):
 await project(client);await configure(client,learn_skills=True);m=await command(client);await finish(client,m['id'])
 for _ in range(25):autonomy.tick();await run_one()
 library=(await client.get('/api/skills')).json();learned=[x for x in library if x['data']['origin'].get('auto_candidate')];assert len(learned)==1 and learned[0]['data']['status']=='active'
 assert all(x['action'] in {'context','draft','research','calculate'} for x in learned[0]['data']['definition']['steps'])
async def test_project_scope_prevents_skills_from_reading_other_project_data(client):
 p=await project(client);other=(await client.post('/api/spaces',json={'title':'Other project','kind':'business','brief':'UNRELATED_SECRET_MARKER'})).json()
 await configure(client,project_ids=[p['id']]);m=await command(client);await finish(client,m['id'])
 with Session() as s:
  jobs=[json.loads(r.payload) for r in s.query(Record).filter(Record.kind=='job')]
  assert all('UNRELATED_SECRET_MARKER' not in json.dumps(x.get('outputs',[])) for x in jobs)

async def test_pause_stops_learning_after_mission_already_completed(client):
 await project(client);await configure(client,learn_skills=True);m=await command(client);await finish(client,m['id'])
 for _ in range(3):autonomy.tick()
 with Session() as s:
  jobs=[r for r in s.query(Record).filter(Record.kind=='job') if json.loads(r.payload).get('automation') and json.loads(r.payload).get('status')=='queued']
  assert jobs
  ids=[r.id for r in jobs]
 await client.post('/api/autonomy/stop')
 with Session() as s:assert all(json.loads(s.get(Record,id).payload)['status']=='paused' for id in ids)
 await command(client,'restart-learning-after-pause')
 with Session() as s:assert all(json.loads(s.get(Record,id).payload)['status']=='queued' for id in ids)

async def test_learning_skips_project_deleted_after_mission(client):
 p=await project(client);await configure(client,learn_skills=True);m=await command(client);await finish(client,m['id'])
 proposals=lambda:[r.id for r in Session().query(Record).filter(Record.kind=='job') if json.loads(r.payload).get('type')=='skill_proposal']
 with Session() as s:
  for r in s.query(Record).filter(Record.kind=='job'):
   d=json.loads(r.payload)
   if d.get('type')=='skill_proposal':s.delete(r)
  pol=s.get(Record,autonomy.key());d=json.loads(pol.payload);d.update(learning_job_id=None,daily_skill_drafts=0);pol.payload=json.dumps(d);s.commit()
 assert (await client.delete('/api/spaces/'+p['id'])).status_code==204
 for _ in range(3):autonomy.tick()
 # A deleted project must not make every later automation step fail and roll back.
 with Session() as s:assert 'last_error' not in json.loads(s.get(Record,autonomy.key()).payload)
 assert proposals()==[]
