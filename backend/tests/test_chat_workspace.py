import json
import pytest
from foxory import inference
from foxory.db import Session,Record,Message
from foxory.scope import actor_id
async def conversation(client):return (await client.post('/api/records/conversation',json={'title':'Chat-first test'})).json()['id']
async def test_chat_command_saves_durable_preference_and_receipt_without_model(client):
 id=await conversation(client);r=await client.post('/api/conversations/'+id+'/command',json={'content':'from now on use concise checklists'});assert r.status_code==200,r.text
 d=r.json();assert d['handled'] and d['status']=='completed' and len(d['messages'])==2
 notes=(await client.get('/api/chat-learning')).json();assert len(notes)==1 and notes[0]['data']['kind']=='preference'
 assert len((await client.get('/api/conversations/'+id+'/messages')).json())==2
 assert (await client.post('/api/conversations/'+id+'/command',json={'content':'show my skills'})).json()['tab']=='Skills'
 assert (await client.post('/api/conversations/'+id+'/command',json={'content':'How does memory work?'})).json()=={'handled':False}
async def test_personal_learning_is_injected_and_context_off_disables_it(client,monkeypatch):
 id=await conversation(client);await client.post('/api/chat-learning',json={'body':'PREFER_MARKER concise checklists','kind':'preference'})
 systems=[]
 async def stream(model,messages,*args,**kw):systems.append(messages[0]['content']);yield {'message':{'content':'Reply'},'done':True}
 monkeypatch.setattr(inference,'stream',stream)
 r=await client.post('/api/conversations/'+id+'/chat',json={'content':'Plan my work','model':'fixture'});assert r.status_code==200
 assert 'PREFER_MARKER' in systems[-1]
 await client.post('/api/conversations/'+id+'/chat',json={'content':'Give an independent answer','model':'fixture','use_workspace_context':False})
 assert 'PREFER_MARKER' not in systems[-1]
async def test_other_members_cannot_read_or_export_personal_learning(client,monkeypatch):
 r=await client.post('/api/chat-learning',json={'body':'PERSONAL_NOTE_SECRET','kind':'note'});id=r.json()['id']
 monkeypatch.setattr('foxory.main.identity',lambda request:{'id':'other-member','role':'editor','workspace_id':'local'})
 assert (await client.get('/api/chat-learning')).json()==[]
 assert 'PERSONAL_NOTE_SECRET' not in (await client.get('/api/workspace/export')).text
 assert (await client.delete('/api/chat-learning/'+id)).status_code==404
async def test_project_notes_do_not_leak_into_other_project_context(client):
 a=(await client.post('/api/spaces',json={'title':'A'})).json();b=(await client.post('/api/spaces',json={'title':'B'})).json()
 await client.post('/api/chat-learning',json={'body':'PROJECT_A_SECRET','project_id':a['id']})
 await client.post('/api/chat-learning',json={'body':'GLOBAL_NOTE_SECRET'})
 await client.post('/api/chat-learning',json={'body':'Use clear paragraphs','kind':'preference'})
 from foxory.chat_workspace import context
 token=actor_id.set('bootstrap')
 try:
  assert 'PROJECT_A_SECRET' in context('bootstrap',project_id=a['id'])['text']
  value=context('bootstrap',project_id=b['id'])['text'];assert 'PROJECT_A_SECRET' not in value and 'GLOBAL_NOTE_SECRET' not in value and 'clear paragraphs' in value
 finally:actor_id.reset(token)
async def test_forget_requires_an_unambiguous_match_and_preserves_history(client):
 id=await conversation(client)
 for note in ['Remember the red manuscript','Remember the blue manuscript']:
  await client.post('/api/conversations/'+id+'/command',json={'content':'/remember '+note})
 r=await client.post('/api/conversations/'+id+'/command',json={'content':'/forget manuscript'});assert r.json()['status']=='needs_selection'
 assert len((await client.get('/api/chat-learning')).json())==2
 await client.post('/api/conversations/'+id+'/command',json={'content':'/forget red manuscript'})
 assert len((await client.get('/api/chat-learning')).json())==1
 assert len((await client.get('/api/conversations/'+id+'/messages')).json())==8
async def test_skill_from_chat_uses_recent_excerpts_and_starts_test(client,monkeypatch):
 from foxory import skills
 async def require(*a,**kw):pass
 captured=[]
 async def structured(model,messages,schema,**kw):captured.append(messages);return json.dumps(skills.BUNDLED[0])
 monkeypatch.setattr(skills,'require_model',require);monkeypatch.setattr(inference,'structured',structured)
 id=await conversation(client)
 with Session() as s:s.add(Message(conversation_id=id,role='user',content='WORKFLOW_MARKER: list missing evidence before drafting'));s.commit()
 r=await client.post('/api/conversations/'+id+'/command',json={'content':'Save this as a skill','model':'fixture'});assert r.status_code==200,r.text
 assert r.json()['status']=='testing' and 'WORKFLOW_MARKER' in json.dumps(captured)
 assert (await client.get('/api/skills')).json()[0]['data']['status']=='draft'
async def test_idle_review_is_quota_bound_staged_and_quote_grounded(client,monkeypatch):
 from foxory.chat_reflection import queue
 from foxory.jobs import run_one
 id=await conversation(client)
 with Session() as s:
  for i in range(6):s.add(Message(conversation_id=id,role='user',content='Keep answers concise please. '+str(i),metadata_json=json.dumps({'actor_id':'bootstrap'})))
  s.commit()
 token=actor_id.set('bootstrap')
 try:queue(id,'fixture','bootstrap');queue(id,'fixture','bootstrap')
 finally:actor_id.reset(token)
 with Session() as s:
  rows=s.query(Record).filter(Record.kind=='job').all();assert len(rows)==1
 assert await run_one() is False
 with Session() as s:
  r=s.get(Record,rows[0].id);d=json.loads(r.payload);d['not_before']='2000-01-01T00:00:00+00:00';r.payload=json.dumps(d);s.commit()
 async def structured(*a,**kw):return json.dumps({'notes':[{'kind':'preference','body':'Be concise','source_turn':0},{'kind':'note','body':'Unsupported claim','source_turn':7}],'skill_goal':'','reason':'Repeated request for concise answers'})
 monkeypatch.setattr(inference,'structured',structured);await run_one()
 assert (await client.get('/api/chat-learning')).json()==[]
 reviews=(await client.get('/api/chat-learning/reviews')).json();assert len(reviews)==1 and len(reviews[0]['data']['notes'])==1
 assert (await client.post('/api/chat-learning/reviews/'+reviews[0]['id']+'/accept',json={'index':0})).status_code==200
 assert (await client.get('/api/chat-learning')).json()[0]['data']['body']=='Be concise'

async def test_running_a_skill_from_chat_needs_an_active_tested_revision(client):
 id=await conversation(client)
 r=await client.post('/api/conversations/'+id+'/command',json={'content':'run skill Missing :: Draft a checklist'})
 assert r.status_code==200 and r.json()['status']=='needs_selection'
 assert not (await client.get('/api/records/job')).json()
async def test_active_skill_runs_from_chat_with_existing_model_and_grants(client,monkeypatch):
 from foxory import skills
 from foxory.jobs import run_one
 async def require(*a,**kw):pass
 async def complete(*a,**kw):return 'A bounded reviewable draft.'
 monkeypatch.setattr(skills,'require_model',require);monkeypatch.setattr(inference,'complete',complete)
 skill=(await client.post('/api/skills',json={'definition':skills.BUNDLED[0]})).json()
 assert (await client.post('/api/skills/'+skill['id']+'/test',json={'model':'fixture','idempotency_key':'chat-active-skill-test'})).status_code==201
 for _ in range(10):await run_one()
 assert (await client.post('/api/skills/'+skill['id']+'/activate')).status_code==200
 id=await conversation(client);r=await client.post('/api/conversations/'+id+'/command',json={'content':'run skill '+skill['title']+' :: Draft the next evidence checklist'})
 assert r.status_code==200,r.text
 assert r.json()['status']=='queued' and r.json()['draft']['task_id']==r.json()['record_id']
 with Session() as s:
  d=json.loads(s.get(Record,r.json()['record_id']).payload);assert d['skill_hash']==skill['data']['hash'] and d['agent_snapshot']['model']=='fixture'
async def test_downgrade_does_not_expose_private_learning_to_older_software(client,monkeypatch):
 await client.post('/api/chat-learning',json={'body':'Personal preference','kind':'preference'})
 monkeypatch.setattr('foxory.maintenance.state',lambda:{'controller':'connected','epoch':'test','releases':[{'version':'5.0.0','available':True}]})
 r=await client.post('/api/maintenance/operations',json={'action':'activate','target_version':'5.0.0','confirmation':'ACTIVATE 5.0.0'})
 assert r.status_code==409 and 'Personal conversational learning' in r.text
