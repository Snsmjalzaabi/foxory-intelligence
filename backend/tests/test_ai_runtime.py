import asyncio,json
from types import SimpleNamespace
import httpx,pytest
from foxory import ai_runtime as ai,inference,providers,model_registry,maintenance
from foxory.db import Session,Record
from sqlalchemy import select

def transport(monkeypatch,handler):
 original=httpx.AsyncClient
 monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handler),**kw))

async def test_llama_adapter_maps_stream_schema_and_private_auth(monkeypatch):
 monkeypatch.setattr(providers,'LLAMA_URL','http://localhost:11436');monkeypatch.setattr(providers,'API_KEY','private-test-key')
 seen=[]
 def handler(request):
  seen.append(request)
  if request.url.path=='/v1/models':return httpx.Response(200,json={'data':[{'id':providers.ALIAS}]})
  return httpx.Response(200,text='data: '+json.dumps({'choices':[{'delta':{'content':'{"ok":true}'},'finish_reason':None}]})+'\n\ndata: '+json.dumps({'choices':[{'delta':{},'finish_reason':'stop'}],'usage':{'completion_tokens':5}})+'\n\ndata: [DONE]\n\n')
 transport(monkeypatch,handler)
 assert (await providers.models())[0]['name']==providers.PREFIX+providers.ALIAS
 events=[x async for x in inference.stream(providers.PREFIX+providers.ALIAS,[{'role':'user','content':'Status'}],max_output=32)]
 assert events[-1]['eval_count']==5 and events[-1]['done']
 raw=await inference.structured(providers.PREFIX+providers.ALIAS,[{'role':'user','content':'Status'}],{'type':'object','properties':{'ok':{'type':'boolean'}}})
 assert json.loads(raw)=={'ok':True}
 assert all(r.headers['Authorization']=='Bearer private-test-key' for r in seen)
 assert json.loads(seen[-1].content)['response_format']['schema']['type']=='object'
async def test_inventory_survives_ollama_outage_if_companion_is_available(monkeypatch):
 monkeypatch.setattr(providers,'LLAMA_URL','http://localhost:11436')
 def handler(request):
  return httpx.Response(503) if request.url.path=='/api/tags' else httpx.Response(200,json={'data':[{'id':providers.ALIAS}]})
 transport(monkeypatch,handler)
 models=await inference.models();assert len(models)==1 and models[0]['provider']=='llama.cpp'
async def test_foreground_overtakes_waiting_background_and_cancellation_is_clean():
 gate=ai.Gate();order=[];release=asyncio.Event();entered=asyncio.Event()
 async def task(name,bg,hold=False):
  token=ai.BACKGROUND.set(bg)
  try:
   async with gate.acquire():
    order.append(name)
    if hold:entered.set();await release.wait()
  finally:ai.BACKGROUND.reset(token)
 first=asyncio.create_task(task('active',True,True));await entered.wait()
 background=asyncio.create_task(task('background',True));await asyncio.sleep(0)
 foreground=asyncio.create_task(task('foreground',False));await asyncio.sleep(0)
 release.set();await asyncio.gather(first,background,foreground)
 assert order==['active','foreground','background'] and not gate.busy
async def test_cpu_and_gpu_model_queues_are_independent():
 async with ai.gate('llama.cpp').acquire():
  async with asyncio.timeout(.1):
   async with ai.gate('ollama').acquire():pass
async def test_policy_commands_are_actual_and_counters_do_not_include_prompts(client):
 id=(await client.post('/api/records/conversation',json={'title':'Runtime policy'})).json()['id']
 for text,mode in [('use eco mode','eco'),('use quality mode','quality'),('use balanced mode','balanced')]:
  r=await client.post('/api/conversations/'+id+'/command',json={'content':text});assert r.json()['handled'] and ai.policy().mode==mode
 await client.post('/api/conversations/'+id+'/command',json={'content':'pause background AI'});assert ai.deferred()
 await client.post('/api/conversations/'+id+'/command',json={'content':'resume background AI'});assert not ai.deferred()
 ai.record('llama.cpp');assert ai.usage()['foreground_calls']==1 and 'prompt' not in json.dumps(ai.usage())
 with pytest.raises(Exception):ai.admin(SimpleNamespace(state=SimpleNamespace(identity={'id':'other','role':'admin'})))
async def test_background_budget_defers_without_failing_or_spending_more(client,monkeypatch):
 ai.write(ai.DATA/'ai-policy.json',{'background_daily_calls':1})
 token=ai.BACKGROUND.set(True)
 try:
  ai.record('ollama');assert ai.deferred()
  with pytest.raises(ai.Deferred):await anext(inference._stream('fixture',[]))
 finally:ai.BACKGROUND.reset(token)
 assert ai.usage()['background_calls']==1
async def test_readonly_connection_failure_has_bounded_backoff(client,monkeypatch):
 from foxory import jobs
 response=await client.post('/api/jobs',json={'type':'research','prompt':'Brief research question','models':['fixture'],'idempotency_key':'v7-background-recovery'})
 id=response.json()['id']
 async def fail(data):raise httpx.ConnectError('Local backend restarted')
 monkeypatch.setattr(jobs,'execute_step',fail)
 for n in range(3):
  if n:
   with Session() as s:r=s.get(Record,id);d=json.loads(r.payload);d['not_before']='2000-01-01T00:00:00+00:00';r.payload=json.dumps(d);s.commit()
  await jobs.run_one()
  with Session() as s:d=json.loads(s.get(Record,id).payload)
  assert d['status']==('queued' if n<2 else 'failed')
 assert d['backend_recoveries']==2
async def test_chat_fallback_only_before_any_output_and_only_in_auto(monkeypatch):
 used=[]
 async def stream(model,*a,**kw):
  used.append(model)
  if model=='bad':raise httpx.ConnectError('offline')
  yield {'message':{'content':'Actual fallback response'},'done':True}
 monkeypatch.setattr(inference,'stream',stream)
 events=[x async for x in inference.chat_stream('bad',[],0,4096,32,{'automatic':True,'alternatives':['good']})]
 assert events[0]['_foxory_fallback_model']=='good' and used==['bad','good']
 used.clear()
 with pytest.raises(httpx.ConnectError):[x async for x in inference.chat_stream('bad',[],0,4096,32,{'automatic':False,'alternatives':['good']})]
 assert used==['bad']
 async def partial(*a,**kw):yield {'message':{'content':'Partial'}};raise httpx.ConnectError('interrupted')
 monkeypatch.setattr(inference,'stream',partial)
 with pytest.raises(httpx.ConnectError):[x async for x in inference.chat_stream('bad',[],0,4096,32,{'automatic':True,'alternatives':['good']})]
async def test_managed_cpu_model_is_not_sent_to_ollama_delete_or_pull(client):
 model=providers.PREFIX+providers.ALIAS
 for path in ['remove','pull']:
  r=await client.post('/api/models/'+path,json={'model':model,'confirmation':model});assert r.status_code==422
async def test_light_routes_routine_work_and_policy_preserves_specialists(monkeypatch):
 from foxory.model_routing import choose
 models=[{'name':providers.PREFIX+providers.ALIAS,'size':1117320736,'lightweight':True,'provider':'llama.cpp','completion_supported':True,'details':{'parameter_size':'1.5B'}},{'name':'qwen2.5:7b','size':4_500_000_000,'completion_supported':True,'details':{'parameter_size':'7B'}},{'name':'qwen2.5-coder:7b','size':4_500_000_000,'completion_supported':True,'details':{'parameter_size':'7B'}},{'name':'qwen3:8b','size':5_000_000_000,'completion_supported':True,'details':{'parameter_size':'8B'}}]
 async def inventory():return models
 async def catalog(values,**kw):return values
 monkeypatch.setattr(inference,'models',inventory);monkeypatch.setattr(model_registry,'catalog',catalog);monkeypatch.setattr(maintenance,'state',lambda:{})
 assert (await choose('Hello'))['model'].startswith(providers.PREFIX)
 assert (await choose('Debug Python code'))['model']=='qwen2.5-coder:7b'
 assert (await choose('Analyze a complex strategy'))['model']=='qwen3:8b'
 ai.write(ai.DATA/'ai-policy.json',{'mode':'eco'})
 assert (await choose('Write a short project draft'))['model'].startswith(providers.PREFIX)
 ai.write(ai.DATA/'ai-policy.json',{'mode':'quality'})
 assert (await choose('Hello'))['model']=='qwen2.5:7b'
 ai.write(ai.DATA/'ai-policy.json',{'mode':'balanced'})
 async with ai.gate('llama.cpp').acquire():assert (await choose('Hello'))['model']=='qwen2.5:7b'

async def test_cancelled_waiter_does_not_starve_background():
 gate=ai.Gate()
 async with gate.acquire():
  async def wait(bg):
   token=ai.BACKGROUND.set(bg)
   try:
    async with gate.acquire():return True
   finally:ai.BACKGROUND.reset(token)
  foreground=asyncio.create_task(wait(False));await asyncio.sleep(0);foreground.cancel()
  with pytest.raises(asyncio.CancelledError):await foreground
  background=asyncio.create_task(wait(True));await asyncio.sleep(0)
 assert await asyncio.wait_for(background,.2)
 assert gate.foreground==0 and gate.background==0 and not gate.busy
async def test_manual_light_context_is_clamped_to_runtime_limit():
 from foxory.model_routing import choose
 r=await choose('Hello',requested=providers.PREFIX+providers.ALIAS,context=32768)
 assert r['context']==providers.CONTEXT and not r['automatic']
def test_backend_circuit_has_bounded_cooldown(monkeypatch):
 for _ in range(3):providers.failure('llama.cpp')
 assert not providers.available('llama.cpp')
 timestamp=providers.circuits['llama.cpp']['retry_at'];monkeypatch.setattr(providers.time,'monotonic',lambda:timestamp+1)
 assert providers.available('llama.cpp');providers.success('llama.cpp');assert providers.circuits['llama.cpp']['failures']==0

async def test_local_skill_generation_never_adds_unrequested_external_research(client,monkeypatch):
 from foxory import skills
 async def require(*a,**kw):pass
 schemas=[]
 async def structured(model,messages,schema,**kw):
  schemas.append(schema)
  return json.dumps({'name':'Local checklist','purpose':'Prepare a checklist','instructions':'Use only supplied facts','steps':[{'action':'research'},{'action':'draft'}]})
 monkeypatch.setattr(skills,'require_model',require);monkeypatch.setattr(inference,'structured',structured)
 r=await client.post('/api/skills/generate',json={'goal':'Prepare a checklist from saved project context','model':'fixture'})
 assert r.status_code==201 and not any(x['action']=='research' for x in r.json()['data']['definition']['steps'])
 assert all('research' not in x['$defs']['RecipeStep']['properties']['action']['enum'] for x in schemas)

async def test_actual_chat_persists_fallback_model_and_provider(client,monkeypatch):
 from foxory import model_routing
 async def choose(*a,**kw):return {'model':'llama.cpp/offline','automatic':True,'category':'chat','reason':'Small local model','context':4096,'alternatives':['working-model']}
 async def stream(model,*a,**kw):
  if model.startswith('llama.cpp/'):raise httpx.ConnectError('offline')
  yield {'message':{'content':'Reply from the actual fallback'},'done':True}
 monkeypatch.setattr(model_routing,'choose',choose);monkeypatch.setattr(inference,'stream',stream)
 id=(await client.post('/api/records/conversation',json={'title':'Fallback'})).json()['id']
 await client.post('/api/conversations/'+id+'/chat',json={'content':'Hello','model':'auto'})
 m=(await client.get('/api/conversations/'+id+'/messages')).json()[-1]
 assert m['content']=='Reply from the actual fallback' and m['metadata']['model']=='working-model'
 assert m['metadata']['model_route']['provider']=='ollama' and m['metadata']['model_route']['fallback_from']=='llama.cpp/offline'
