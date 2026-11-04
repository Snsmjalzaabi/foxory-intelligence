import json
from sqlalchemy import select
from foxory.db import Session,Record
from foxory import autonomy
from foxory.scope import system_scope
async def project(client,title='Project',kind='business'):
 r=await client.post('/api/spaces',json={'title':title,'kind':kind});assert r.status_code==201;return r.json()
async def test_overview_is_readonly_and_surfaces_gaps_reviews_and_overdue_actions(client):
 p=await project(client)
 await client.post('/api/spaces/'+p['id']+'/items',json={'kind':'deliverable','title':'Draft offer','review':['Verify evidence'],'status':'draft'})
 await client.post('/api/spaces/'+p['id']+'/items',json={'kind':'action','title':'Call prospect','due_date':'2000-01-01'})
 for body in ['First version','Conflicting version']:
  await client.post('/api/spaces/'+p['id']+'/items',json={'kind':'fact','title':'Audience','body':body,'fact_key':'audience'})
 with Session() as s:before=s.query(Record).count()
 r=await client.get('/api/operations');assert r.status_code==200;d=r.json();x=d['projects'][0]
 assert any('evidence' in w for w in x['warnings']) and any('Conflicting' in w for w in x['warnings']) and any('Overdue' in w for w in x['warnings'])
 assert d['review_inbox'][0]['pending_checks']==['Verify evidence']
 with Session() as s:assert before==s.query(Record).count()
async def test_controls_hold_priority_revision_and_workspace_scope(client):
 p=await project(client);r=await client.put('/api/operations/projects/'+p['id'],json={'enabled':False,'priority':5,'objective':'Use my actual interview notes'});assert r.status_code==200
 assert (await client.put('/api/operations/projects/'+p['id'],json={'enabled':True,'revision':0})).status_code==409
 d=(await client.get('/api/operations')).json();assert d['preview']['eligible_projects']==0
 assert (await client.put('/api/operations/projects/'+p['id'],json={'priority':6})).status_code==422
 with system_scope(),Session() as s:s.add(Record(id='foreign-project',kind='space',workspace='other',title='PRIVATE_FOREIGN',payload='{}'));s.commit()
 assert 'PRIVATE_FOREIGN' not in (await client.get('/api/operations')).text
 assert (await client.get('/api/operations/projects/foreign-project/context')).status_code==404
 assert (await client.put('/api/operations/projects/foreign-project',json={})).status_code==404
async def test_preview_rotates_more_projects_than_one_mission_and_preserves_idempotency(client):
 projects=[await project(client,str(i)) for i in range(8)]
 await client.put('/api/operations/projects/'+projects[-1]['id'],json={'priority':5})
 from foxory.scope import workspace_id
 with Session() as s:
  policy={**autonomy.Policy().model_dump(),'max_projects':6};a=autonomy.create_mission(s,policy,'First','bootstrap','first');s.commit();first=json.loads(a.payload);assert first['projects'][0]['id']==projects[-1]['id']
  first['status']='completed';a.payload=json.dumps(first);s.commit()
  b=autonomy.create_mission(s,policy,'Second','bootstrap','second');s.commit();second=json.loads(b.payload)
  first_ids={p['id'] for p in first['projects']};assert all(p['id'] not in first_ids for p in second['projects'][:2])
  assert autonomy.create_mission(s,policy,'Retry','bootstrap','second').id==b.id
async def test_context_preview_contains_only_selected_project(client):
 p=await project(client,'Primary project');other=await project(client,'UNRELATED_PRIVATE_PROJECT')
 r=await client.get('/api/operations/projects/'+p['id']+'/context');assert r.status_code==200,r.text
 assert 'UNRELATED_PRIVATE_PROJECT' not in r.text and r.json()['project_id']==p['id']
async def test_viewer_cannot_change_project_control(client,monkeypatch):
 p=await project(client);monkeypatch.setattr('foxory.main.identity',lambda request:{'id':'reader','role':'viewer','workspace_id':'local'})
 assert (await client.put('/api/operations/projects/'+p['id'],json={'enabled':False})).status_code==403
async def test_changed_owner_direction_restarts_work_with_exact_new_instruction(client,monkeypatch):
 from test_autonomy import configure,command,finish
 from foxory import skills,inference
 async def require(model):pass
 async def complete(*a,**kw):return 'Draft based on actual supplied data.'
 monkeypatch.setattr(skills,'require_model',require);monkeypatch.setattr(inference,'complete',complete)
 p=await project(client);await configure(client);first=await command(client,'before-owner-direction');await finish(client,first['id'])
 await client.put('/api/operations/projects/'+p['id'],json={'objective':'OWNER_DIRECTION_MARKER: identify missing evidence only.'})
 second=await command(client,'after-owner-direction');done=await finish(client,second['id']);assert done['projects'][0]['status']=='completed'
 with Session() as s:
  job=s.get(Record,done['projects'][0]['job_id']);assert 'OWNER_DIRECTION_MARKER' in json.loads(job.payload)['prompt']
