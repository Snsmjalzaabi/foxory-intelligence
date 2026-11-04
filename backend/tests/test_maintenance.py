import json
from datetime import datetime,timezone
from foxory import maintenance

def connected():
 maintenance.write(maintenance.folder()/'state.json',{'controller':'connected','heartbeat_at':datetime.now(timezone.utc).isoformat(),'releases':[{'version':'1.0.0','available':True}],'operations':[]})
async def test_fixed_maintenance_queue_requires_exact_confirmation_and_registered_release(client,tmp_path,monkeypatch):
 monkeypatch.setattr(maintenance,'DATA',tmp_path);connected()
 r=await client.post('/api/maintenance/operations',json={'action':'activate','target_version':'9.9.9','confirmation':'ACTIVATE 9.9.9'});assert r.status_code==422
 r=await client.post('/api/maintenance/operations',json={'action':'backup','confirmation':'wrong'});assert r.status_code==422
 r=await client.post('/api/maintenance/operations',json={'action':'backup','confirmation':'BACKUP'});assert r.status_code==202
 assert maintenance.host_next()['action']=='backup'
 assert (await client.post('/api/maintenance/operations',json={'action':'verify','confirmation':'VERIFY'})).status_code==409
 assert maintenance.host_next()['status']=='running' # restart can resume a fixed safe operation
async def test_offline_controller_cannot_accept_a_queue(client,tmp_path,monkeypatch):
 monkeypatch.setattr(maintenance,'DATA',tmp_path)
 assert (await client.post('/api/maintenance/operations',json={'action':'backup','confirmation':'BACKUP'})).status_code==409
async def test_arbitrary_shell_or_image_names_are_rejected(client,tmp_path,monkeypatch):
 monkeypatch.setattr(maintenance,'DATA',tmp_path);connected()
 for body in [{'action':'shell','confirmation':'SHELL'},{'action':'activate','target_version':'x;touch /tmp/x','confirmation':'ACTIVATE x'},{'action':'backup','confirmation':'BACKUP','command':'id'}]:
  assert (await client.post('/api/maintenance/operations',json=body)).status_code==422

async def test_speed_measurement_uses_installed_model_and_real_metrics_contract(client,monkeypatch):
 from foxory import inference,model_registry
 async def models():return [{'name':'fixture'}]
 async def require(*a,**kw):return {}
 async def stream(*a,**kw):yield {'done':True,'eval_count':20,'eval_duration':2_000_000_000,'load_duration':100_000_000}
 monkeypatch.setattr(inference,'models',models);monkeypatch.setattr(model_registry,'require',require);monkeypatch.setattr(inference,'stream',stream)
 assert (await client.post('/api/local-runtime/measure',json={'model':'missing','action':'benchmark'})).status_code==422
 r=await client.post('/api/local-runtime/measure',json={'model':'fixture','action':'benchmark'});assert r.status_code==200,r.text
 assert r.json()['tokens_per_second']==10 and r.json()['load_seconds']==0.1
