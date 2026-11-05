import json
from datetime import datetime,timedelta,timezone
import pytest
from foxory.db import Session,Record
from foxory import performance,inference,jobs,skills,model_registry
@pytest.fixture(autouse=True)
def no_models(monkeypatch):
 async def models():return []
 monkeypatch.setattr(inference,'models',models)
def job(data):
 with Session() as s:
  r=Record(kind='job',title='Performance fixture',payload=json.dumps(data));s.add(r);s.commit();return r.id
def running(**kw):
 return {'type':'research','models':['fixture'],'status':'running','started_at':(datetime.now(timezone.utc)-timedelta(seconds=400)).isoformat(),'deadline_at':(datetime.now(timezone.utc)+timedelta(seconds=600)).isoformat(),'used':{'model_calls':2},'budget':{'max_seconds':900},**kw}
async def test_task_timing_is_saved_by_real_worker_checkpoint(client,monkeypatch):
 async def complete(*a,**kw):return 'Measured draft'
 monkeypatch.setattr(jobs,'complete',complete)
 id=job({'type':'draft','status':'queued','models':['fixture'],'prompt':'Test timing','creator_id':'bootstrap'})
 await jobs.run_one()
 with Session() as s:
  d=json.loads(s.get(Record,id).payload);assert d['status']=='completed' and d['timing']['active_seconds']>=0 and len(d['timing']['steps'])==1 and d['first_started_at'] and d['finished_at']
 x=(await client.get('/api/performance')).json()['jobs'][0];assert x['active_seconds'] is not None and 'prompt' not in x
async def test_overdue_recovery_preserves_limits_and_caps_attempts(client):
 id=job(running());original=running()
 for count in [1,2]:
  r=await client.post('/api/performance/jobs/'+id+'/recover');assert r.status_code==200
  with Session() as s:
   row=s.get(Record,id);d=json.loads(row.payload);assert d['recovery_count']==count and d['used']==original['used'] and d['budget']==original['budget'];d['status']='running';row.payload=json.dumps(d);s.commit()
 assert (await client.post('/api/performance/jobs/'+id+'/recover')).status_code==409
async def test_recovery_denies_active_expired_and_write_capable_jobs(client):
 for d in [running(started_at=datetime.now(timezone.utc).isoformat()),running(deadline_at='2000-01-01T00:00:00+00:00'),running(type='agent',agent_snapshot={'step_timeout':60,'tools':['project.create']},plan=[])]:
  id=job(d);assert (await client.post('/api/performance/jobs/'+id+'/recover')).status_code==409
async def test_monitor_is_scoped_and_stale_hardware_is_labelled(client,monkeypatch):
 from foxory.scope import system_scope
 with system_scope(),Session() as s:s.add(Record(kind='job',workspace='other',title='FOREIGN_PRIVATE',payload=json.dumps(running())));s.commit()
 monkeypatch.setattr('foxory.maintenance.state',lambda:{'controller':'connected','hardware':{'sampled_at':'2000-01-01T00:00:00+00:00','gpus':[]}})
 r=await client.get('/api/performance');assert r.status_code==200 and 'FOREIGN_PRIVATE' not in r.text and r.json()['hardware_fresh'] is False
async def test_model_choice_preserves_owner_policy(client,monkeypatch):
 async def require(*a,**kw):pass
 monkeypatch.setattr(skills,'require_model',require)
 assert (await client.put('/api/autonomy/policy',json={'model':'old','daily_job_limit':4,'max_projects':2,'paused':True,'focus':['writing'],'learn_skills':False})).status_code==200
 r=await client.post('/api/performance/select-model',json={'model':'new'});assert r.status_code==200;r=r.json();assert r['model']=='new' and r['daily_job_limit']==4 and r['paused'] and r['focus']==['writing'] and r['learn_skills'] is False
async def test_benchmark_saves_measurement_and_uses_measured_recommendation(client,monkeypatch):
 async def models():return [{'name':'small','size':10},{'name':'fast','size':20}]
 async def require(*a,**kw):pass
 async def catalog(models,**kw):return [{**x,'completion_supported':True} for x in models]
 async def stream(*a,**kw):yield {'done':True,'eval_duration':1_000_000_000,'eval_count':20,'load_duration':1_000_000_000}
 monkeypatch.setattr(inference,'models',models);monkeypatch.setattr(model_registry,'require',require);monkeypatch.setattr(model_registry,'catalog',catalog);monkeypatch.setattr(inference,'stream',stream)
 r=await client.post('/api/local-runtime/measure',json={'model':'fast','action':'benchmark'});assert r.status_code==200
 d=(await client.get('/api/performance')).json();assert len(d['measurements'])==1 and d['recommendation']['model']=='fast' and 'benchmarks' in d['recommendation']['basis']
async def test_viewer_cannot_recover_or_select_model(client,monkeypatch):
 monkeypatch.setattr('foxory.main.identity',lambda request:{'id':'reader','role':'viewer','workspace_id':'local'})
 assert (await client.post('/api/performance/select-model',json={'model':'fixture'})).status_code==403
 assert (await client.post('/api/performance/jobs/absent/recover')).status_code==403
