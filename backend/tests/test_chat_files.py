import json
from foxory.db import Session,Record
from foxory.chat_files import attachments
from foxory.scope import system_scope

async def test_selected_files_are_bounded_and_scope_checked(client):
 with Session() as s:
  r=Record(kind='document',title='brief.txt',payload=json.dumps({'text':'Evidence '*2000}));s.add(r);s.commit();rid=r.id
  result=attachments(s,[rid,rid],budget=500)
  assert len(result['files'])==1 and result['files'][0]['truncated']
  assert result['files'][0]['characters_used']<500
  assert 'untrusted reference' in result['text']
 with system_scope(),Session() as s:
  r=Record(kind='document',workspace='other',title='Private',payload='{}');s.add(r);s.commit();foreign=r.id
 id=(await client.post('/api/records/conversation',json={'title':'Files'})).json()['id']
 response=await client.post('/api/conversations/'+id+'/chat',json={'content':'Summarize','model':'fixture','document_ids':[foreign]})
 assert response.status_code==404
 assert (await client.get('/api/conversations/'+id+'/messages')).json()==[]

async def test_explicit_file_used_with_saved_context_disabled(client,monkeypatch):
 from foxory import inference
 captured=[]
 async def choose(*a,**kw):return {'model':'fixture','automatic':False,'context':4096,'category':'documents','reason':'fixture'}
 async def stream(model,messages,*args,**kw):
  captured.extend(messages);yield {'message':{'content':'Read attached evidence'},'done':True}
 monkeypatch.setattr('foxory.model_routing.choose',choose);monkeypatch.setattr(inference,'chat_stream',stream)
 with Session() as s:
  r=Record(kind='document',title='brief.txt',payload=json.dumps({'text':'BLUE-FOX-UNIQUE-EVIDENCE'}));s.add(r);s.commit();rid=r.id
 id=(await client.post('/api/records/conversation',json={'title':'Files'})).json()['id']
 response=await client.post('/api/conversations/'+id+'/chat',json={'content':'What is in this file?','model':'fixture','document_ids':[rid],'use_workspace_context':False})
 assert response.status_code==200,response.text
 assert any('BLUE-FOX-UNIQUE-EVIDENCE' in m['content'] for m in captured)
 messages=(await client.get('/api/conversations/'+id+'/messages')).json()
 assert messages[0]['metadata']['attachments'][0]['id']==rid
 assert messages[-1]['metadata']['attachments'][0]['characters_used']==len('BLUE-FOX-UNIQUE-EVIDENCE')

async def test_artifact_listing_is_exact_and_conversation_scoped(client):
 a=(await client.post('/api/records/conversation',json={'title':'A'})).json()['id']
 b=(await client.post('/api/records/conversation',json={'title':'B'})).json()['id']
 with Session() as s:
  s.add_all([Record(kind='artifact',title='Own',payload=json.dumps({'source_conversation':a,'body':'# Done'})),Record(kind='artifact',title='Other',payload=json.dumps({'source_conversation':b,'body':a}))]);s.commit()
 rows=(await client.get('/api/conversations/'+a+'/artifacts')).json()
 assert [r['title'] for r in rows]==['Own']
 assert (await client.get('/api/conversations/missing/artifacts')).status_code==404

async def test_file_reader_returns_complete_body_and_rejects_non_files(client):
 with Session() as s:
  r=Record(kind='artifact',title='Complete',payload=json.dumps({'body':'# Title\n'+'x'*15000}));s.add(r);s.commit();rid=r.id
 response=await client.get('/api/chat-files/'+rid)
 assert response.status_code==200 and len(response.json()['data']['body'])>15000
 id=(await client.post('/api/records/conversation',json={'title':'Private type'})).json()['id']
 assert (await client.get('/api/chat-files/'+id)).status_code==404

async def test_project_chat_rejects_unlinked_file_before_writing_message(client):
 space=(await client.post('/api/spaces',json={'title':'Bounded'})).json()['id']
 chat=(await client.post('/api/spaces/'+space+'/conversation')).json()['id']
 with Session() as s:
  r=Record(kind='document',title='Unlinked',payload=json.dumps({'text':'outside project'}));s.add(r);s.commit();rid=r.id
 response=await client.post('/api/conversations/'+chat+'/chat',json={'content':'Summarize this file','model':'fixture','document_ids':[rid]})
 assert response.status_code==404
 assert (await client.get('/api/conversations/'+chat+'/messages')).json()==[]
