"""Scoped timing, local resource observations, explicit model choice and bounded recovery."""
import json
from datetime import datetime,timezone
from fastapi import APIRouter,HTTPException,Request
from pydantic import BaseModel,ConfigDict,Field
from sqlalchemy import select,update
from .db import Session,Record,get_record,audit,now
router=APIRouter(prefix='/api/performance')
def age(value):
 try:return max(0,(datetime.now(timezone.utc)-datetime.fromisoformat(value)).total_seconds())
 except (ValueError,TypeError):return None
def readonly(d):
 if d.get('type') in {'research','council','skill_proposal','evolution_proposal','chat_reflection'}:return True
 if d.get('type')!='agent':return False
 from .agent_tools import TOOLS
 configs=[d.get('agent_snapshot',{}),*d.get('delegates',{}).values()]
 tools=set(t for cfg in configs for t in cfg.get('tools',[]))|{p['tool'] for p in d.get('plan',[]) if p.get('tool')}
 return all(t in TOOLS and not TOOLS[t].approval for t in tools)
def recovery(d):
 seconds=age(d.get('started_at'));limit=d.get('agent_snapshot',{}).get('step_timeout',240)+60
 if d.get('status')!='running':return False,'Only an overdue running step can be recovered here.'
 if seconds is None or seconds<=limit:return False,'Still inside its step timeout and grace period; wait or pause the task.'
 if not readonly(d):return False,'Task has write or execution capabilities; inspect it in Tasks instead of replaying it.'
 if d.get('recovery_count',0)>=2:return False,'Recovery limit reached; inspect the cause before creating a new task.'
 active=d.get('agent_usage',{}).get(d.get('active_agent_id'),{})
 if active.get('deadline_at') and active['deadline_at']<=now():return False,'Assigned agent budget expired; create a new bounded task.'
 if d.get('deadline_at','')<=now():return False,'Wall-clock budget expired; create a new bounded task rather than extending this one.'
 return True,'Overdue readonly step can return to its saved checkpoint; budgets and grants remain unchanged.'
def advice(d):
 text=str(d.get('error',''))+' '+str(d.get('error_detail',''))
 if d.get('status')=='awaiting_approval':return 'Inspect the proposed action in Approvals. No approval is granted by this monitor.'
 if 'budget' in text.lower() or 'deadline' in text.lower():return 'The task reached a configured limit. Narrow the objective or create a new bounded task.'
 if 'permission' in text.lower() or 'grant' in text.lower():return 'Inspect the agent permissions and current membership. Recovery does not add grants.'
 if 'Incomplete' in text or 'incomplete' in text:return 'Output was cut short. Inspect partial output and narrow the request before retrying.'
 if 'TimeoutError' in text:return 'A step exceeded its time limit. Check model load and GPU use, reduce context/output, then inspect whether retry is appropriate.'
 if d.get('status')=='failed':return 'Inspect the task error and local model/service health. Do not assume a retry will fix the cause.'
 if d.get('status')=='queued':return 'Waiting for the local worker or a previous inference call; queued does not mean stalled.'
 return 'Timing measures execution, not factual accuracy or task quality.'
class Selection(BaseModel):
 model_config=ConfigDict(extra='forbid')
 model:str=Field(min_length=1,max_length=100)
@router.post('/select-model')
async def select_model(body:Selection,request:Request):
 from .autonomy import admin,load_policy,Policy,save_policy
 admin(request)
 with Session() as s:
  row=load_policy(s);old=json.loads(row.payload) if row else Policy().model_dump()
 chosen={k:old[k] for k in Policy.model_fields if k in old};chosen['model']=body.model
 return await save_policy(Policy(**chosen),request)
@router.post('/jobs/{id}/recover')
def recover(id:str,request:Request):
 from .autonomy import admin
 admin(request)
 with Session() as s:
  row=get_record(s,id,'job');original=row.payload;d=json.loads(original);allowed,reason=recovery(d)
  if not allowed:raise HTTPException(409,reason)
  d.update(status='queued',recovery_count=d.get('recovery_count',0)+1,last_recovered_at=now())
  changed=s.execute(update(Record).where(Record.id==id,Record.payload==original).values(payload=json.dumps(d),updated_at=now())).rowcount
  if not changed:raise HTTPException(409,'Task changed; refresh before recovery.')
  audit(s,'job.recover',id,attempt=d['recovery_count']);s.commit();return {'id':id,'status':'queued','reason':reason}
@router.get('')
async def overview():
 from . import inference,model_registry
 from .maintenance import state
 from .resources import available_memory
 from .local_runtime import recent
 try:models=await model_registry.catalog(await inference.models(),endpoint=inference.OLLAMA_URL)
 except Exception:models=[]
 with Session() as s:
  measurements=[r.public() for r in s.scalars(select(Record).where(Record.kind=='model_measure').order_by(Record.created_at.desc()).limit(100))];jobs=[]
  for r in s.scalars(select(Record).where(Record.kind=='job').order_by(Record.created_at.desc()).limit(100)):
   d=json.loads(r.payload);allowed,reason=recovery(d);jobs.append({'id':r.id,'title':r.title,'status':d.get('status'),'stage':d.get('stage'),'model':d.get('models',[None])[0] if d.get('models') else None,'active_seconds':d.get('timing',{}).get('active_seconds'),'current_step_seconds':round(age(d.get('started_at')) or 0,1) if d.get('status')=='running' else None,'created_at':r.created_at,'first_started_at':d.get('first_started_at'),'last_checkpoint_at':d.get('last_checkpoint_at'),'finished_at':d.get('finished_at'),'can_recover':allowed,'recovery_reason':reason,'recovery_count':d.get('recovery_count',0),'restart_recoveries':d.get('restart_recoveries',0),'advice':advice(d),'error':d.get('error'),'error_detail':d.get('error_detail')})
 candidates=[m for m in models if m.get('completion_supported') is True]
 measured={}
 for row in measurements:
  m=row['data']
  if m.get('action')=='benchmark' and m.get('tokens_per_second') and m['model'] not in measured:measured[m['model']]=m
 timed=[m for m in candidates if m['name'] in measured]
 recommended=max(timed,key=lambda m:measured[m['name']]['tokens_per_second'])['name'] if timed else min(candidates,key=lambda m:m.get('size') or float('inf'))['name'] if candidates else None
 host=state();hardware=host.get('hardware');sample_age=age(hardware.get('sampled_at')) if hardware else None;fresh=sample_age is not None and sample_age<90 and host.get('controller')=='connected'
 return {'jobs':jobs,'models':models,'measurements':measurements,'recent_inference':list(reversed(recent)),'recommendation':{'model':recommended,'basis':'Latest saved short benchmarks in this workspace; warm-cache and workload dependent.' if timed else 'Smallest installed model with reported completion support; size is only a speed heuristic. Benchmark to compare.','quality':'Not a task-quality rating. Selection is explicit and only changes future automation tasks.'},'hardware':hardware if hardware else {'gpu_status':'unavailable','gpus':[]},'hardware_fresh':fresh,'application_available_bytes':available_memory(),'scope':'Latest 100 current-workspace tasks and measurements. Older tasks may lack timing; resource counters are installation-wide. No prompt bodies included.'}
