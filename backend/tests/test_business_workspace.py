import json
import pytest
from foxory.db import Session, Record
from foxory.scope import workspace_id, system_scope
from foxory import inference, model_registry, local_runtime
from foxory.config import DATA

@pytest.fixture(autouse=True)
def preferences_cleanup():
    path=DATA/'inference-preferences.json'
    path.unlink(missing_ok=True);local_runtime.recent.clear()
    yield
    path.unlink(missing_ok=True);local_runtime.recent.clear()

async def test_opportunity_persists_validates_exports_and_isolates(client):
    body={'title':'=Untrusted title','audience':'Independent authors','offer':'Manuscript formatting','stage':'validating','currency':'AED','estimated_value':250,'next_action':'Talk to one author','due_date':'2026-11-01','actions':[{'title':'Prepare sample','done':False}]}
    r=await client.post('/api/business/opportunities',json=body);assert r.status_code==201,r.text
    id=r.json()['id']
    assert (await client.get('/api/business/opportunities')).json()[0]['data']['actions'][0]['done'] is False
    body['stage']='outreach';body['actions'][0]['done']=True
    assert (await client.put('/api/business/opportunities/'+id,json=body)).status_code==200
    assert (await client.get('/api/business/opportunities')).json()[0]['data']['actions'][0]['done']
    export=await client.get('/api/business/export');assert "'=Untrusted title" in export.text
    assert (await client.post('/api/business/opportunities',json={**body,'estimated_value':-1})).status_code==422
    assert (await client.post('/api/business/opportunities',json={**body,'stage':'guaranteed-profit'})).status_code==422
    with system_scope(), Session() as s:
        row=Record(kind='opportunity',workspace='other',title='Private',payload='{}');s.add(row);s.commit();other=row.id
    assert len((await client.get('/api/business/opportunities')).json())==1
    assert (await client.put('/api/business/opportunities/'+other,json=body)).status_code==404
    assert (await client.delete('/api/records/'+id)).status_code==204
    assert (await client.get('/api/business/opportunities')).json()==[]

async def test_starter_team_is_idempotent_and_preserves_customizations(client,monkeypatch):
    async def models():return [{'name':'test-chat'}]
    async def require(*args,**kwargs):pass
    monkeypatch.setattr(inference,'models',models);monkeypatch.setattr(model_registry,'require',require)
    body={'model':'test-chat','roles':['planner','writer','builder']}
    response=await client.post('/api/agents/starter-team',json=body);assert response.status_code==200,response.text
    created=response.json()['created'];assert len(created)==3
    for row in created:
        assert row['data']['document_ids']==[] and row['data']['delegate_ids']==[]
        assert not any(t.endswith('.create') for t in row['data']['tools'])
    row=created[0];row['data']['purpose']='My custom purpose'
    assert (await client.put('/api/agents/'+row['id'],json={'name':row['title'],'config':row['data']})).status_code==200
    again=(await client.post('/api/agents/starter-team',json=body)).json()
    assert again['created']==[] and len(again['preserved'])==3
    assert again['preserved'][0]['data']['purpose']=='My custom purpose'
    assert (await client.post('/api/agents/starter-team',json={'model':'missing','roles':['writer']})).status_code==422
    assert (await client.post('/api/agents/starter-team',json={'model':'test-chat','roles':['writer','writer']})).status_code==422

async def test_viewer_cannot_mutate_business_or_team(client):
    from test_accounts import setup
    await setup(client)
    assert (await client.post('/api/auth/members',json={'username':'read-only','password':'viewer-password-123','role':'viewer'})).status_code==201
    await client.post('/api/auth/logout')
    r=await client.post('/api/auth/login',json={'username':'read-only','password':'viewer-password-123'})
    client.headers['x-csrf-token']=r.json()['csrf']
    assert (await client.get('/api/business/opportunities')).status_code==200
    assert (await client.post('/api/business/opportunities',json={'title':'No write'})).status_code==403
    assert (await client.post('/api/agents/starter-team',json={'model':'a','roles':['writer']})).status_code==403
    assert (await client.put('/api/local-runtime/preferences',json={'keep_alive_minutes':30})).status_code==403

async def test_inference_preferences_validate_and_are_installation_scoped(client):
    response=await client.put('/api/local-runtime/preferences',json={'keep_alive_minutes':30,'thinking':False})
    assert response.status_code==200,response.text
    assert local_runtime.preferences().keep_alive_minutes==30
    assert (DATA/'inference-preferences.json').stat().st_mode & 0o777==0o600
    assert (await client.put('/api/local-runtime/preferences',json={'keep_alive_minutes':999})).status_code==422
    from test_accounts import setup
    await setup(client)
    assert (await client.post('/api/auth/members',json={'username':'second-admin','password':'second-admin-password','role':'admin'})).status_code==201
    await client.post('/api/auth/logout')
    r=await client.post('/api/auth/login',json={'username':'second-admin','password':'second-admin-password'})
    client.headers['x-csrf-token']=r.json()['csrf']
    assert (await client.put('/api/local-runtime/preferences',json={'keep_alive_minutes':2})).status_code==403

async def test_thinking_and_keepalive_reach_actual_protocol(client,monkeypatch):
    import httpx
    await client.put('/api/local-runtime/preferences',json={'keep_alive_minutes':15,'thinking':False})
    seen=[]
    def handler(request):
        if request.url.path=='/api/show':return httpx.Response(200,json={'capabilities':['completion','thinking']})
        seen.append(json.loads(request.content))
        return httpx.Response(200,text=json.dumps({'message':{'content':'done'},'done':True,'eval_count':10,'eval_duration':1000000000,'total_duration':2000000000})+'\n')
    real=httpx.AsyncClient
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kwargs:real(transport=httpx.MockTransport(handler),timeout=10))
    result=''
    async for item in inference.stream('thinking-test',[{'role':'user','content':'Check'}]):result+=item.get('message',{}).get('content','')
    assert result=='done'
    assert seen[0]['think'] is False and seen[0]['keep_alive']=='15m'
    assert local_runtime.recent[-1]['tokens_per_second']==10
    assert 'messages' not in local_runtime.recent[-1]

async def test_business_tasks_are_linked_idempotent_and_keep_context(client):
    agent=(await client.post('/api/agents',json={'name':'Business reviewer','config':{'model':'test-chat'}})).json()
    body={'title':'Small service','offer':'A fixed deliverable','notes':'Confirmed owner facts'}
    opportunity=(await client.post('/api/business/opportunities',json=body)).json()
    request={'agent_id':agent['id'],'objective':'Identify one validation step','idempotency_key':'business-click-123'}
    response=await client.post('/api/business/opportunities/'+opportunity['id']+'/tasks',json=request)
    assert response.status_code==201,response.text
    task=response.json();assert task['data']['opportunity_id']==opportunity['id']
    assert 'Fixed deliverable'.lower() in task['data']['prompt'].lower()
    await client.put('/api/business/opportunities/'+opportunity['id'],json={**body,'notes':'Edited after submission'})
    again=await client.post('/api/business/opportunities/'+opportunity['id']+'/tasks',json=request)
    assert again.json()['id']==task['id']
    assert 'Edited after submission' not in again.json()['data']['prompt']
    linked=(await client.get('/api/business/opportunities/'+opportunity['id']+'/tasks')).json()
    assert [r['id'] for r in linked]==[task['id']]
    conflict=await client.post('/api/business/opportunities/'+opportunity['id']+'/tasks',json={**request,'objective':'Changed objective'})
    assert conflict.status_code==409
    rows=(await client.get('/api/business/opportunities')).json()
    assert rows[0]['data']['linked_jobs']==[task['id']]

async def test_incomplete_generation_is_not_accepted_as_a_finished_report(monkeypatch):
    async def truncated(*args,**kwargs):
        yield {'message':{'content':'This report is unfinished'},'done':True,'done_reason':'length'}
    monkeypatch.setattr(inference,'stream',truncated)
    with pytest.raises(inference.IncompleteResponse) as result:
        await inference.complete('model',[{'role':'user','content':'Write report'}])
    assert result.value.partial=='This report is unfinished'

async def test_background_budget_rejects_unusable_output_window(client):
    assert (await client.put('/api/local-runtime/preferences',json={'background_context':2048,'background_output':2048})).status_code==422
    assert (await client.put('/api/local-runtime/preferences',json={'background_context':8192,'background_output':2048})).status_code==200
    assert inference.background_limits()==(8192,2048)

async def test_chat_truncation_is_saved_with_visible_warning(client,monkeypatch):
    async def truncated(*args,**kwargs):
        yield {'message':{'content':'Partial answer'},'done':True,'done_reason':'length','eval_count':3}
    monkeypatch.setattr(inference,'stream',truncated)
    conversation=(await client.post('/api/records/conversation',json={'title':'Limit test'})).json()
    response=await client.post('/api/conversations/'+conversation['id']+'/chat',json={'content':'Tell me something','model':'model'})
    assert '"status": "truncated"' in response.text
    saved=(await client.get('/api/conversations/'+conversation['id']+'/messages')).json()[-1]
    assert saved['metadata']['status']=='truncated'
    assert 'incomplete' in saved['metadata']['warning']
