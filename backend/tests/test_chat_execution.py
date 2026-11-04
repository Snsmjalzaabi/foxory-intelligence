import json,io,zipfile
from datetime import datetime,timedelta,timezone
from sqlalchemy import select
from foxory import inference
from foxory.db import Session,Record
from foxory.chat_execution import wants_action

async def conversation(client):return (await client.post('/api/records/conversation',json={'title':'Do the work'})).json()['id']
def plan(monkeypatch,actions,source=None):
 async def structured(model,messages,schema,**kw):return json.dumps({'files':source} if 'files' in schema['properties'] else {'actions':actions,'reply':''})
 async def complete(*a,**kw):return '# Completed proposal\n\nA usable finished draft.'
 async def models():return []
 monkeypatch.setattr(inference,'models',models)
 monkeypatch.setattr(inference,'structured',structured);monkeypatch.setattr(inference,'complete',complete)
async def run(client,id,text='Create it now'):
 r=await client.post('/api/conversations/'+id+'/chat',json={'content':text,'model':'fixture'});assert r.status_code==200,r.text
 return (await client.get('/api/conversations/'+id+'/messages')).json()[-1]
async def test_compound_request_creates_project_task_and_downloadable_document(client,monkeypatch):
 plan(monkeypatch,[{'tool':'project.create','title':'Launch','goal':'Sell a small local app'},{'tool':'project.task','title':'Validate offer','goal':'Interview three prospects','project_id':'$last'},{'tool':'artifact.write','title':'Offer','goal':'Write the full offer','project_id':'$last'}])
 id=await conversation(client);m=await run(client,id)
 results=m['metadata']['execution_results'];assert len(results)==3 and all(r['status']=='created' for r in results)
 assert (await client.get('/api/artifacts/'+results[-1]['id']+'/export?format=md')).text.startswith('# Completed')
 detail=(await client.get('/api/spaces/'+results[0]['id'])).json();assert detail
 assert 'Created: Offer.' in m['content'] and 'Working on it' not in m['content']
async def test_source_request_creates_real_zip_and_rejects_traversal(client,monkeypatch):
 plan(monkeypatch,[{'tool':'source.package','title':'Counter','goal':'Build a working counter'}],[{'path':'index.html','content':'<button onclick="this.textContent=Number(this.textContent)+1">0</button>'}])
 id=await conversation(client);m=await run(client,id,'Build a counter app');rid=m['metadata']['execution_results'][0]['id']
 r=await client.get('/api/artifacts/'+rid+'/export?format=zip');assert r.status_code==200
 with zipfile.ZipFile(io.BytesIO(r.content)) as z:assert any(x.endswith('index.html') for x in z.namelist())
 plan(monkeypatch,[{'tool':'source.package','title':'Bad','goal':'Build it'}],[{'path':'../oops','content':'bad'}])
 m=await run(client,id);assert m['metadata']['execution_results'][0]['status']=='failed'
 with Session() as s:assert len(list(s.scalars(select(Record).where(Record.kind=='artifact'))))==1
async def test_partial_failure_keeps_receipt_for_successful_action(client,monkeypatch):
 plan(monkeypatch,[{'tool':'project.create','title':'Saved','goal':'A new project'},{'tool':'source.package','title':'Bad','goal':'Build'}],[{'path':'/bad','content':'bad'}])
 m=await run(client,await conversation(client));results=m['metadata']['execution_results'];assert results[0]['status']=='created' and results[1]['status']=='failed'
async def test_schedule_is_saved_without_manual_agent_setup(client,monkeypatch):
 start=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()
 plan(monkeypatch,[{'tool':'schedule.create','title':'Daily draft','goal':'Prepare a daily local project summary','start_at':start,'timezone':'Europe/Berlin','every_minutes':1440}])
 m=await run(client,await conversation(client),'Schedule a daily project draft tomorrow');result=m['metadata']['execution_results'][0];assert result['status']=='scheduled'
 with Session() as s:
  r=s.get(Record,result['id']);d=json.loads(r.payload);assert d['enabled'] and d['every_minutes']==1440 and d['timezone']=='Europe/Berlin'
async def test_project_chat_cannot_create_elsewhere(client,monkeypatch):
 a=(await client.post('/api/spaces',json={'title':'One'})).json();b=(await client.post('/api/spaces',json={'title':'Two'})).json()
 id=(await client.post('/api/spaces/'+a['id']+'/conversation')).json()['id']
 plan(monkeypatch,[{'tool':'project.task','title':'Wrong','goal':'Do it','project_id':b['id']}])
 m=await run(client,id);assert m['metadata']['execution_results'][0]['status']=='failed'
 with Session() as s:assert not list(s.scalars(select(Record).where(Record.kind=='space_item')))
async def test_user_requested_skill_tests_then_activates_exact_revision(client,monkeypatch):
 from foxory import skills,jobs
 async def require(*a,**kw):pass
 async def structured(*a,**kw):return json.dumps(skills.BUNDLED[0])
 monkeypatch.setattr(skills,'require_model',require);monkeypatch.setattr(inference,'structured',structured)
 id=await conversation(client);r=await client.post('/api/conversations/'+id+'/command',json={'content':'Create a skill to write concise drafts','model':'fixture'});assert r.json()['status']=='testing'
 async def finish(data):return dict(data,status='completed',result='Test draft completed')
 monkeypatch.setattr(jobs,'execute_step',finish)
 assert await jobs.run_one()
 row=(await client.get('/api/skills')).json()[0];assert row['data']['status']=='active'
 activity=(await client.get('/api/conversations/'+id+'/activity')).json();assert activity[0]['skill_status']=='active'
async def test_changed_skill_revision_is_not_auto_activated(client,monkeypatch):
 from foxory import skills,jobs
 async def require(*a,**kw):pass
 async def structured(*a,**kw):return json.dumps(skills.BUNDLED[0])
 monkeypatch.setattr(skills,'require_model',require);monkeypatch.setattr(inference,'structured',structured)
 id=await conversation(client);r=(await client.post('/api/conversations/'+id+'/command',json={'content':'Create a skill to draft a checklist','model':'fixture'})).json()
 with Session() as s:
  row=s.get(Record,r['record_id']);d=json.loads(row.payload);d['hash']='changed';row.payload=json.dumps(d);s.commit()
 async def finish(data):return dict(data,status='completed',result='Old revision')
 monkeypatch.setattr(jobs,'execute_step',finish);await jobs.run_one()
 assert (await client.get('/api/skills')).json()[0]['data']['status']=='draft'
def test_action_trigger_leaves_tutorials_and_negation_as_chat():
 assert wants_action('can you build a useful app?') and wants_action('go ahead')
 assert not wants_action('how can I create a project?') and not wants_action('do not create a project')

async def test_coding_uses_an_installed_coder_without_downloading(monkeypatch):
 from foxory.chat_execution import coding_model
 async def models():return [{'name':'qwen2.5:7b','size':4},{'name':'qwen2.5-coder:7b','size':4},{'name':'big-coder:32b','size':20}]
 monkeypatch.setattr(inference,'models',models)
 assert await coding_model('qwen2.5:7b')=='qwen2.5-coder:7b'
 assert await coding_model('chosen-coder:7b')=='chosen-coder:7b'
async def test_failed_skill_test_never_activates(client,monkeypatch):
 from foxory import skills,jobs
 async def require(*a,**kw):pass
 async def structured(*a,**kw):return json.dumps(skills.BUNDLED[0])
 monkeypatch.setattr(skills,'require_model',require);monkeypatch.setattr(inference,'structured',structured)
 id=await conversation(client);await client.post('/api/conversations/'+id+'/command',json={'content':'Create a skill to draft a checklist','model':'fixture'})
 async def fail(data):return dict(data,status='failed',error='Test failed')
 monkeypatch.setattr(jobs,'execute_step',fail);await jobs.run_one()
 assert (await client.get('/api/skills')).json()[0]['data']['status']=='draft'

async def test_new_skill_does_not_reuse_a_previously_revoked_recipe_agent(client,monkeypatch):
 from foxory import skills
 async def require(*a,**kw):pass
 async def structured(*a,**kw):return json.dumps(skills.BUNDLED[0])
 monkeypatch.setattr(skills,'require_model',require);monkeypatch.setattr(inference,'structured',structured)
 id=await conversation(client)
 first=(await client.post('/api/conversations/'+id+'/command',json={'content':'Create a skill to draft a checklist','model':'fixture'})).json()
 with Session() as s:
  row=s.get(Record,first['record_id']);d=json.loads(row.payload);job=s.get(Record,d['test_job_id']);agent=s.get(Record,json.loads(job.payload)['agent_id']);cfg=json.loads(agent.payload);cfg['enabled']=False;agent.payload=json.dumps(cfg);s.commit()
 second=await client.post('/api/conversations/'+id+'/command',json={'content':'Create a skill to draft another checklist','model':'fixture'})
 assert second.status_code==200 and second.json()['status']=='testing'
 with Session() as s:
  row=s.get(Record,second.json()['record_id']);d=json.loads(row.payload);job=s.get(Record,d['test_job_id']);assert json.loads(job.payload)['agent_id']!=agent.id
