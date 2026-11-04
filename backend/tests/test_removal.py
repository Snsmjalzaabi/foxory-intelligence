import json
import httpx
from foxory.db import Session,Record,Message,Workspace,Membership
from foxory.main import app
from foxory.scope import workspace_id,system_scope
from tests.test_accounts import setup
from tests.test_project_spaces import space,item

async def login(name,password):
 c=httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://testserver')
 r=await c.post('/api/auth/login',json={'username':name,'password':password});assert r.status_code==200,r.text
 c.headers['x-csrf-token']=r.json()['csrf'];return c

async def test_space_delete_removes_items_and_links_but_keeps_sources(client):
 p=await space(client);other=await space(client,'Other','business')
 chapter=await item(client,p['id']);kept=await item(client,other['id'])
 doc=(await client.post('/api/records/memory',json={'title':'Linked note'})).json()
 assert (await client.post('/api/spaces/'+p['id']+'/links',json={'record_id':doc['id']})).status_code==201
 chat=(await client.post('/api/spaces/'+p['id']+'/conversation')).json()
 # Items are scoped to their own space.
 assert (await client.delete('/api/spaces/'+p['id']+'/items/'+kept['id'])).status_code==404
 assert (await client.delete('/api/spaces/'+p['id']+'/items/'+chapter['id'])).status_code==204
 assert (await client.get('/api/spaces/'+p['id'])).json()['items']==[]
 await item(client,p['id'],title='Chapter Two')
 assert (await client.delete('/api/spaces/'+p['id'])).status_code==204
 assert (await client.get('/api/spaces/'+p['id'])).status_code==404
 with Session() as s:
  left=[r for r in s.query(Record).filter(Record.kind.in_(['space_item','space_link'])) if (r.dedupe_key or '').startswith(p['id']+':')]
  assert left==[] and s.get(Record,doc['id']) is not None and s.get(Record,kept['id']) is not None
  assert 'space_id' not in json.loads(s.get(Record,chat['id']).payload)
 # The generic record endpoint cascades the same way.
 await item(client,other['id'],title='Second')
 assert (await client.delete('/api/records/'+other['id'])).status_code==204
 with Session() as s:assert not [r for r in s.query(Record).filter(Record.kind=='space_item')]

async def test_skill_delete_removes_agent_and_bundled_stays_removed_until_restored(client):
 await setup(client)
 rows=(await client.post('/api/skills/bundled')).json();bundled=rows[0]
 with Session() as s:
  row=s.get(Record,bundled['id']);d=json.loads(row.payload)
  agent=Record(kind='agent',title='Skill agent',payload='{"enabled":true}');s.add(agent);s.flush();d['agent_id']=agent.id;row.payload=json.dumps(d);s.commit();agent_id=agent.id
 assert (await client.delete('/api/skills/'+bundled['id'])).status_code==204
 from foxory.autonomy import ensure_bundled
 with Session() as s:
  ensure_bundled(s);s.commit()
  assert s.get(Record,bundled['id']) is None and s.get(Record,agent_id) is None
 titles=[r['title'] for r in (await client.get('/api/skills')).json()]
 assert bundled['title'] not in titles
 await client.post('/api/skills/bundled')
 assert bundled['title'] in [r['title'] for r in (await client.get('/api/skills')).json()]

async def test_member_removal_rules(client):
 me=await setup(client)
 editor=(await client.post('/api/auth/members',json={'username':'editor','password':'editor-password-123','role':'editor'})).json()
 other=await login('editor','editor-password-123')
 assert (await other.delete('/api/auth/members/'+me['id'])).status_code==403
 assert (await client.delete('/api/auth/members/'+me['id'])).status_code==409
 assert (await client.delete('/api/auth/members/'+editor['id'])).status_code==204
 assert (await other.get('/api/overview')).status_code==403
 assert (await client.delete('/api/auth/members/'+editor['id'])).status_code==404
 assert editor['id'] not in [m['id'] for m in (await client.get('/api/auth/members')).json()]
 await other.aclose()

async def test_workspace_delete_requires_admin_name_and_idle_jobs(client):
 await setup(client)
 assert (await client.post('/api/auth/workspaces/local/delete',json={'confirmation':'Local workspace'})).status_code==409
 w=(await client.post('/api/auth/workspaces',json={'name':'Scratch'})).json()
 scoped={'x-workspace-id':w['id']}
 conv=(await client.post('/api/records/conversation',json={'title':'Temp chat'},headers=scoped)).json()
 with system_scope(),Session() as s:
  s.add(Message(conversation_id=conv['id'],role='user',content='hello'))
  job=Record(kind='job',title='Busy',workspace=w['id'],payload='{"status":"running"}');s.add(job);s.commit();job_id=job.id
 assert (await client.post('/api/auth/workspaces/'+w['id']+'/delete',json={'confirmation':'wrong'})).status_code==422
 assert (await client.post('/api/auth/workspaces/'+w['id']+'/delete',json={'confirmation':'Scratch'})).status_code==409
 with system_scope(),Session() as s:r=s.get(Record,job_id);r.payload='{"status":"completed"}';s.commit()
 r=await client.post('/api/auth/workspaces/'+w['id']+'/delete',json={'confirmation':'Scratch'})
 assert r.status_code==200 and r.json()['records']==2
 with system_scope(),Session() as s:
  assert s.get(Workspace,w['id']) is None and s.query(Record).filter(Record.workspace==w['id']).count()==0
  assert s.query(Message).filter(Message.conversation_id==conv['id']).count()==0 and s.query(Membership).filter(Membership.workspace_id==w['id']).count()==0
 assert w['id'] not in [x['id'] for x in (await client.get('/api/auth/me')).json()['workspaces']]

async def test_space_delete_frees_unlinked_project_chat(client):
 p=await space(client)
 chat=(await client.post('/api/spaces/'+p['id']+'/conversation')).json()
 link=next(l for l in (await client.get('/api/spaces/'+p['id'])).json()['links'] if l['id']==chat['id'])
 assert (await client.delete('/api/spaces/'+p['id']+'/links/'+link['link_id'])).status_code==204
 assert (await client.delete('/api/spaces/'+p['id'])).status_code==204
 with Session() as s:assert 'space_id' not in json.loads(s.get(Record,chat['id']).payload)

async def test_generic_record_delete_follows_skill_rules(client):
 me=await setup(client)
 skill=(await client.post('/api/skills/bundled')).json()[0]
 with Session() as s:
  row=s.get(Record,skill['id']);d=json.loads(row.payload)
  agent=Record(kind='agent',title='Skill agent',payload='{"enabled":true}');s.add(agent);s.flush();d['agent_id']=agent.id;row.payload=json.dumps(d);s.commit();agent_id=agent.id
 await client.post('/api/auth/members',json={'username':'editor','password':'editor-password-123','role':'editor'})
 editor=await login('editor','editor-password-123')
 assert (await editor.delete('/api/records/'+skill['id'])).status_code==403
 assert (await editor.post('/api/skills/bundled')).status_code==403
 assert (await client.delete('/api/records/'+skill['id'])).status_code==204
 from foxory.autonomy import ensure_bundled
 with Session() as s:
  ensure_bundled(s);s.commit()
  assert s.get(Record,skill['id']) is None and s.get(Record,agent_id) is None
 await editor.aclose()

async def test_renamed_bundled_skill_is_retired_not_duplicated(client):
 import hashlib
 from foxory.autonomy import ensure_bundled
 old_id=hashlib.sha256(('local:bundled-skill:FOXORY Emberbound Revision').encode()).hexdigest()[:36]
 with Session() as s:
  s.add(Record(id=old_id,kind='skill',title='FOXORY Emberbound Revision',payload=json.dumps({'definition':{},'hash':'old','status':'active','origin':{'type':'bundled','version':1}})));s.commit()
  ensure_bundled(s);s.commit()
  titles=[r.title for r in s.query(Record).filter(Record.kind=='skill')]
 assert 'FOXORY Emberbound Revision' not in titles and titles.count('FOXORY Writing Revision')==1
