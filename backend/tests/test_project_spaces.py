import io,json,zipfile
import pytest
from foxory.db import Session,Record
from foxory.scope import workspace_id
from foxory.workspace_context import retrieve_context
async def space(client,title='Larkspur',kind='writing'):
 r=await client.post('/api/spaces',json={'title':title,'kind':kind,'brief':'Finish the last book','stage':'planning' if kind=='writing' else 'idea'});assert r.status_code==201,r.text;return r.json()
async def item(client,id,**data):
 r=await client.post('/api/spaces/'+id+'/items',json={'kind':'chapter','title':'Chapter One','body':'Asha enters the city.',**data});assert r.status_code==201,r.text;return r.json()
async def test_project_context_excludes_unlinked_knowledge_and_pending_facts(client):
 a=await space(client);b=await space(client,'Different business','business')
 await item(client,a['id'],kind='fact',title='Asha eyes',fact_key='asha.eyes',body='Asha has green eyes.',status='approved',source='Owner canon')
 await item(client,a['id'],kind='fact',title='Asha pending',fact_key='asha.age',body='Asha is 999 years old.',status='pending')
 await item(client,b['id'],body='Asha secret unrelated project')
 with Session() as s:s.add(Record(kind='memory',title='Asha global note',payload='{"body":"unlinked global private value"}'));s.commit()
 result=retrieve_context('Asha',project_id=a['id']);text=json.dumps(result)
 assert 'green eyes' in text and '999 years' not in text and 'secret unrelated' not in text and 'unlinked global' not in text
 assert result['project_id']==a['id']
async def test_fact_approval_conflicts_and_explicit_supersession_keep_history(client):
 p=await space(client);a=await item(client,p['id'],kind='fact',fact_key='asha.eyes',title='Eye color',body='Green',status='approved',source='Owner statement')
 body={'kind':'fact','fact_key':'asha.eyes','title':'Corrected eyes','body':'Blue','status':'approved','source':'Owner correction'}
 assert (await client.post('/api/spaces/'+p['id']+'/items',json=body)).status_code==409
 body['supersedes']=[a['id']];r=await client.post('/api/spaces/'+p['id']+'/items',json=body);assert r.status_code==201
 old=(await client.get('/api/spaces/'+p['id']+'/items/'+a['id'])).json()
 assert old['data']['status']=='superseded' and old['data']['revisions'][0]['data']['body']=='Green'
 assert 'Green' not in json.dumps(retrieve_context('eyes',project_id=p['id'])['items'])
async def test_chapter_revision_conflict_and_manuscript_export(client):
 p=await space(client);a=await item(client,p['id'])
 body={'kind':'chapter','title':a['title'],'body':'Revised manuscript','revision':0}
 assert (await client.put('/api/spaces/'+p['id']+'/items/'+a['id'],json=body)).status_code==200
 assert (await client.put('/api/spaces/'+p['id']+'/items/'+a['id'],json=body)).status_code==409
 old=(await client.get('/api/spaces/'+p['id']+'/items/'+a['id'])).json();assert old['data']['revisions'][0]['data']['body']=='Asha enters the city.'
 z=await client.get('/api/spaces/'+p['id']+'/export')
 with zipfile.ZipFile(io.BytesIO(z.content)) as archive:assert 'Revised manuscript' in archive.read('manuscript.md').decode()
async def test_project_links_and_conversation_context_are_scoped(client,monkeypatch):
 p=await space(client)
 with Session() as s:
  doc=Record(kind='document',title='Linked source',payload='{"text":"Larkspur canonical city is Redhaven"}');s.add(doc);s.commit();doc_id=doc.id
 assert (await client.post('/api/spaces/'+p['id']+'/links',json={'record_id':doc_id})).status_code==201
 chat=(await client.post('/api/spaces/'+p['id']+'/conversation')).json();calls=[]
 async def stream(model,messages,*a,**kw):calls.append(messages);yield {'message':{'content':'Redhaven'},'done':True}
 monkeypatch.setattr('foxory.inference.stream',stream)
 response=await client.post('/api/conversations/'+chat['id']+'/chat',json={'model':'fixture','content':'Which Larkspur city?'});assert response.status_code==200
 assert 'Redhaven' in calls[0][0]['content'] and 'Selected project only' in response.text
 token=workspace_id.set('different')
 with Session() as s:other=Record(kind='document',title='Other workspace',payload='{"text":"secret"}');s.add(other);s.commit();other_id=other.id
 workspace_id.reset(token)
 assert (await client.post('/api/spaces/'+p['id']+'/links',json={'record_id':other_id})).status_code==404
async def test_launch_needs_evidence_and_reviewed_deliverable(client):
 p=await space(client,'Income idea','business');body={'title':p['title'],'kind':'business','stage':'launch','evidence':'Five supplied interview notes','revision':0}
 assert (await client.put('/api/spaces/'+p['id'],json=body)).status_code==409
 assert (await client.post('/api/spaces/'+p['id']+'/items',json={'kind':'deliverable','title':'Offer','status':'approved','review':['Check facts']})).status_code==409
 await item(client,p['id'],kind='deliverable',title='Offer',body='A bounded draft',status='approved',review=['Check facts'],review_done=['Check facts'])
 assert (await client.put('/api/spaces/'+p['id'],json=body)).status_code==200
async def test_agent_capture_preserves_original_provenance_after_edit(client):
 p=await space(client)
 with Session() as s:job=Record(kind='job',title='Useful task',payload='{"status":"completed","result":"Original output"}');s.add(job);s.commit();jid=job.id
 row=(await client.post('/api/spaces/'+p['id']+'/capture',json={'job_id':jid})).json()
 body={'kind':'deliverable','title':'Edited result','body':'Reviewed text','revision':0}
 updated=(await client.put('/api/spaces/'+p['id']+'/items/'+row['id'],json=body)).json()
 assert updated['data']['origin_job_id']==jid and updated['data']['original_sha256']==row['data']['original_sha256']
 assert updated['data']['revisions'][0]['data']['body']=='Original output'
async def test_layout_validation_and_named_layouts(client):
 p=await space(client);url='/api/spaces/'+p['id']+'/layout'
 assert (await client.put(url,json={'widgets':['Brief','Brief']})).status_code==422
 assert (await client.put(url,json={'name':'Writing desk','widgets':['Manuscript','Brief'],'sizes':{'Manuscript':2},'heights':{'Brief':300}})).status_code==200
 d=(await client.get('/api/spaces/'+p['id'])).json();assert 'Writing desk' in d['space']['data']['layouts']

async def test_viewer_cannot_change_project_or_approve_a_fact(client,monkeypatch):
 p=await space(client)
 monkeypatch.setattr('foxory.main.identity',lambda request:{'id':'reader','role':'viewer','workspace_id':'local'})
 assert (await client.get('/api/spaces/'+p['id'])).status_code==200
 assert (await client.post('/api/spaces/'+p['id']+'/items',json={'kind':'fact','title':'No write'})).status_code==403
 assert (await client.post('/api/maintenance/operations',json={'action':'backup','confirmation':'BACKUP'})).status_code==403

async def test_project_task_rejects_foreign_project_sources_and_records_coverage(client):
 from foxory.agents import AgentConfig
 a=await space(client);b=await space(client,'Other')
 source=await item(client,a['id']);foreign=await item(client,b['id'])
 with Session() as s:agent=Record(kind='agent',title='Writing helper',payload=AgentConfig(model='fixture').model_dump_json());s.add(agent);s.commit();aid=agent.id
 body={'agent_id':aid,'objective':'Check continuity','purpose':'continuity','item_ids':[foreign['id']],'idempotency_key':'project-source-key'}
 assert (await client.post('/api/spaces/'+a['id']+'/tasks',json=body)).status_code==404
 body['item_ids']=[source['id']]
 r=await client.post('/api/spaces/'+a['id']+'/tasks',json=body);assert r.status_code==201,r.text
 d=r.json()['data'];assert d['space_id']==a['id'] and d['project_sources'][0]['id']==source['id'] and d['inference_profile']=='balanced'
