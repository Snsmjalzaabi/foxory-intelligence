import json
import pytest
from foxory import inference,model_eval,model_registry,maintenance
from foxory.model_routing import choose
from tests.test_accounts import setup

GOOD=['Ready','Tokyo','105','Yes','def add(a, b):\n    return a + b','3','I apologise; I will be late.','شكراً جزيلاً']
BAD=['I am ready to help you today!','Kyoto','95','No','print(1+2)','[1, 2, 3]','gonna be late, sorry','Thank you very much']

def test_each_check_accepts_right_and_rejects_wrong():
 for (category,prompt,check),good,bad in zip(model_eval.CASES,GOOD,BAD):
  assert check(good),prompt
  assert not check(bad),prompt

@pytest.fixture
def results(tmp_path,monkeypatch):
 monkeypatch.setattr(model_eval,'RESULTS',tmp_path/'model-quality.json');model_eval._cache.update(mtime=None,data={});yield
 model_eval._cache.update(mtime=None,data={})

async def test_evaluate_saves_per_category_scores(results,monkeypatch):
 prompts=[c[1] for c in model_eval.CASES]
 async def stream(model,messages,*a,**kw):
  i=prompts.index(messages[0]['content']);answer=GOOD[i] if model=='smart:4b' else BAD[i]
  if model=='smart:4b' and i==2:answer='<think>16:05 minus 14:20</think>105'
  yield {'message':{'content':answer},'done':True}
 monkeypatch.setattr(inference,'stream',stream)
 await model_eval.evaluate(['smart:4b','weak:1b'])
 saved=json.loads(model_eval.RESULTS.read_text())
 assert saved['smart:4b']['passed']==8 and saved['weak:1b']['passed']==0
 assert saved['smart:4b']['categories']=={'chat':1.0,'reasoning':1.0,'coding':1.0,'writing':1.0}
 assert model_eval.quality('smart:4b','vision')==1.0 and model_eval.quality('unknown','chat') is None
 assert not model_eval.state['running']

async def test_measured_quality_steers_routing(results,monkeypatch):
 models=[{'name':'house-coder:7b','size':4.5*1024**3,'completion_supported':True,'details':{'parameter_size':'7B'}},
  {'name':'house-general:7b','size':4.5*1024**3,'completion_supported':True,'details':{'parameter_size':'7B'}}]
 async def inventory():return models
 async def catalog(values,**kw):return values
 monkeypatch.setattr(inference,'models',inventory);monkeypatch.setattr(model_registry,'catalog',catalog);monkeypatch.setattr(maintenance,'state',lambda:{})
 assert (await choose('Debug this Python bug'))['model']=='house-coder:7b'
 model_eval.RESULTS.write_text(json.dumps({'house-coder:7b':{'categories':{'coding':0.0}},'house-general:7b':{'categories':{'coding':1.0}}}))
 route=await choose('Debug this Python bug')
 assert route['model']=='house-general:7b' and 'Measured coding quality on this PC: 100%' in route['reason']

async def test_only_the_owner_starts_a_check(client,results,monkeypatch):
 await setup(client)
 await client.post('/api/auth/members',json={'username':'editor','password':'editor-password-123','role':'editor'})
 from tests.test_removal import login
 editor=await login('editor','editor-password-123')
 assert (await editor.post('/api/models/quality')).status_code==403
 await editor.aclose()
 model_eval.state['running']=True
 try:assert (await client.post('/api/models/quality')).status_code==409
 finally:model_eval.state['running']=False
 assert (await client.get('/api/models/quality')).json()['cases']==8
