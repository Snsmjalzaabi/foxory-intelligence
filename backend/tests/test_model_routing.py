import json
import pytest
from fastapi import HTTPException
from foxory import inference,model_registry,maintenance
from foxory.model_routing import choose,category

MODELS=[{'name':'nomic-embed-text:latest','size':.3*1024**3,'completion_supported':False},{'name':'qwen2.5:3b','size':2*1024**3,'completion_supported':True,'details':{'parameter_size':'3B'}},{'name':'qwen2.5:7b','size':4.5*1024**3,'completion_supported':True,'details':{'parameter_size':'7B'}},{'name':'qwen2.5-coder:7b','size':4.5*1024**3,'completion_supported':True,'details':{'parameter_size':'7B'}},{'name':'qwen3:8b','size':5*1024**3,'completion_supported':True,'details':{'parameter_size':'8B'}}]
def setup(monkeypatch,models=None):
 async def inventory():return MODELS if models is None else models
 async def catalog(values,**kw):return values
 monkeypatch.setattr(inference,'models',inventory);monkeypatch.setattr(model_registry,'catalog',catalog);monkeypatch.setattr(maintenance,'state',lambda:{})
async def test_tasks_choose_installed_models_and_exclude_embeddings(monkeypatch):
 setup(monkeypatch)
 for prompt,expected in [('Hi there','qwen2.5:3b'),('Debug this Python bug','qwen2.5-coder:7b'),('Compare a complex strategy','qwen3:8b'),('Write a complete chapter','qwen2.5:7b')]:
  route=await choose(prompt);assert route['model']==expected and route['automatic'],route
async def test_manual_override_does_not_load_inventory(monkeypatch):
 async def fail():raise AssertionError('manual must not auto-select')
 monkeypatch.setattr(inference,'models',fail)
 r=await choose('Build a Python app',requested='my-model');assert r['model']=='my-model' and not r['automatic']
def test_short_followup_retains_topic_but_new_task_wins():
 h=[{'role':'user','content':'Build a Python application'}]
 assert category('Add dark mode',h)=='coding'
 assert category('Write an email to a customer',h)=='writing'
 assert category('continue',[{'role':'user','content':'Write my next chapter'}])=='writing'
 assert category('ابني تطبيق')=='coding'
async def test_memory_estimate_avoids_large_specialist(monkeypatch):
 setup(monkeypatch,MODELS+[{'name':'qwen2.5-coder:32b','size':20*1024**3,'details':{'parameter_size':'32B'},'completion_supported':True}])
 from foxory.db import now
 monkeypatch.setattr(maintenance,'state',lambda:{'controller':'connected','hardware':{'sampled_at':now(),'gpus':[{'total_bytes':12*1024**3}]}})
 assert (await choose('Build a complete Python app'))['model']=='qwen2.5-coder:7b'
async def test_reported_context_limit_is_respected(monkeypatch):
 setup(monkeypatch,[{'name':'tiny','size':100,'completion_supported':True,'context_length':2048}])
 r=await choose('Hello',context=8192);assert r['context']==2048 and 'reduced' in r['reason']
async def test_only_embeddings_and_inventory_outage_have_clear_failures(monkeypatch):
 setup(monkeypatch,[{'name':'nomic-embed-text:latest','size':100}])
 with pytest.raises(HTTPException,match='No installed'):await choose('hello')
 import httpx
 async def fail():raise httpx.ConnectError('offline')
 monkeypatch.setattr(inference,'models',fail)
 with pytest.raises(HTTPException) as e:await choose('hello')
 assert e.value.status_code==503
async def test_chat_auto_uses_actual_model_and_persists_route(client,monkeypatch):
 setup(monkeypatch)
 passed=[]
 async def stream(model,*a,**kw):passed.append(model);yield {'message':{'content':'Actual routed reply'},'done':True}
 monkeypatch.setattr(inference,'stream',stream)
 id=(await client.post('/api/records/conversation',json={'title':'Routing'})).json()['id']
 r=await client.post('/api/conversations/'+id+'/chat',json={'content':'Compare tradeoffs of two business strategies','model':'auto'});assert r.status_code==200
 m=(await client.get('/api/conversations/'+id+'/messages')).json()[-1]
 assert passed==['qwen3:8b'] and m['metadata']['model']=='qwen3:8b' and m['metadata']['model_route']['automatic']
async def test_auto_failure_does_not_append_orphan_user_turn(client,monkeypatch):
 setup(monkeypatch,[])
 id=(await client.post('/api/records/conversation',json={'title':'Unavailable'})).json()['id']
 r=await client.post('/api/conversations/'+id+'/chat',json={'content':'hello','model':'auto'});assert r.status_code==422
 assert (await client.get('/api/conversations/'+id+'/messages')).json()==[]
 from foxory.main import active_chats
 assert id not in active_chats

async def test_missing_timing_values_do_not_break_selection(monkeypatch):
 setup(monkeypatch)
 from foxory.local_runtime import recent
 before=list(recent);recent.clear();recent.append({'model':'qwen2.5:7b','tokens_per_second':None,'output_tokens':16})
 try:assert (await choose('Write a complete chapter'))['model']=='qwen2.5:7b'
 finally:recent.clear();recent.extend(before)

@pytest.mark.parametrize('enabled,expected',[(True,'qwen2.5-coder:7b'),(False,'qwen2.5:3b')])
async def test_project_brief_routes_ambiguous_followups_only_when_context_enabled(client,monkeypatch,enabled,expected):
 setup(monkeypatch)
 async def stream(*a,**kw):yield {'message':{'content':'Project answer'},'done':True}
 monkeypatch.setattr(inference,'stream',stream)
 space=(await client.post('/api/spaces',json={'title':'A prototype','brief':'Build a Python application'})).json()
 id=(await client.post('/api/spaces/'+space['id']+'/conversation')).json()['id']
 await client.post('/api/conversations/'+id+'/chat',json={'content':'What about this?','model':'auto','use_workspace_context':enabled})
 m=(await client.get('/api/conversations/'+id+'/messages')).json()[-1]
 assert m['metadata']['model']==expected
async def test_skill_command_auto_routes_and_pins_the_chosen_model(client,monkeypatch):
 setup(monkeypatch)
 from foxory import skills
 async def require(*a,**kw):pass
 used=[]
 async def structured(model,*a,**kw):used.append(model);return json.dumps(skills.BUNDLED[0])
 monkeypatch.setattr(skills,'require_model',require);monkeypatch.setattr(inference,'structured',structured)
 id=(await client.post('/api/records/conversation',json={'title':'New skill'})).json()['id']
 r=await client.post('/api/conversations/'+id+'/command',json={'content':'Create a skill to prepare a concise project draft','model':'auto'});assert r.status_code==200,r.text
 assert r.json()['messages'][-1]['metadata']['model_route']['model']=='qwen3:8b' and used==['qwen3:8b']

async def test_multi_action_generation_routes_each_deliverable(client,monkeypatch):
 setup(monkeypatch)
 calls=[]
 async def structured(model,messages,schema,**kw):
  calls.append(model)
  if 'files' in schema['properties']:return json.dumps({'files':[{'path':'index.html','content':'<button>Working prototype</button>'}]})
  return json.dumps({'actions':[{'tool':'source.package','title':'App','goal':'Build a Python application'},{'tool':'artifact.write','title':'Pitch','goal':'Write a complete sales email'}],'reply':''})
 async def complete(model,*a,**kw):calls.append(model);return 'A finished sales email.'
 monkeypatch.setattr(inference,'structured',structured);monkeypatch.setattr(inference,'complete',complete)
 id=(await client.post('/api/records/conversation',json={'title':'Mixed work'})).json()['id']
 await client.post('/api/conversations/'+id+'/chat',json={'content':'Build an app and write its pitch','model':'auto'})
 m=(await client.get('/api/conversations/'+id+'/messages')).json()[-1];results=m['metadata']['execution_results']
 assert results[0]['model']=='qwen2.5-coder:7b' and results[1]['model']=='qwen2.5:7b',m
 assert calls.count('qwen2.5-coder:7b')==3 and calls[-1]=='qwen2.5:7b'
