"""Bounded project automation, pinned skills, durable missions and draft capture."""
import asyncio,hashlib,json,sys
from datetime import datetime,timedelta,timezone
from typing import Literal
from fastapi import APIRouter,HTTPException,Request
from pydantic import BaseModel,ConfigDict,Field
from sqlalchemy import select
from .db import Session,Record,Membership,get_record,audit,now
from .scope import workspace_id,actor_id,system_scope
from . import skills
from .agent_api import add_task,TaskBody
from .profile import active
router=APIRouter(prefix='/api/autonomy')
class Policy(BaseModel):
 model_config=ConfigDict(extra='forbid')
 enabled:bool=False
 paused:bool=False
 model:str=Field(default_factory=lambda:active().default_model,min_length=1,max_length=100)
 project_ids:list[str]=Field(default_factory=list,max_length=20)
 focus:list[Literal['business','writing','general']]=Field(default_factory=lambda:['business','writing','general'],min_length=1,max_length=3)
 max_projects:int=Field(default=6,ge=1,le=6)
 daily_job_limit:int=Field(default=8,ge=1,le=12)
 interval_minutes:int=Field(default=360,ge=60,le=1440)
 allow_web:bool=False
 learn_skills:bool=True
 auto_activate_generated:bool=True
class Command(BaseModel):
 model_config=ConfigDict(extra='forbid')
 command:str=Field(default='automate',min_length=1,max_length=1000)
 continuous:bool=True
 idempotency_key:str=Field(min_length=8,max_length=100)

def key():return hashlib.sha256((workspace_id.get()+':autonomy-policy').encode()).hexdigest()[:36]
def load_policy(s,create=False):
 row=s.scalar(select(Record).where(Record.id==key()).with_for_update())
 if row is None and create:
  row=Record(id=key(),kind='automation_policy',title='Automation policy',payload=json.dumps({**Policy().model_dump(),'daily_jobs':0,'daily_date':'','creator_id':actor_id.get()}));s.add(row);s.flush()
 return row

def admin(request):
 if request.state.identity['role']!='admin':raise HTTPException(403,'Workspace administrator required')
def active_missions(s):return [r for r in s.scalars(select(Record).where(Record.kind=='mission')) if json.loads(r.payload)['status'] in {'queued','running','waiting_skill','waiting_budget','paused'}]
def reserve(d):
 day=now()[:10]
 if d.get('daily_date')!=day:d.update(daily_date=day,daily_jobs=0,daily_skill_drafts=0)
 if d['daily_jobs']>=d['daily_job_limit']:return False
 d['daily_jobs']+=1;return True

RETIRED_BUNDLED=['FOXORY Emberbound Revision']  # renamed to 'FOXORY Writing Revision' in 7.1.2
def ensure_bundled(s):
 for name in RETIRED_BUNDLED:
  old=s.get(Record,hashlib.sha256((workspace_id.get()+':bundled-skill:'+name).encode()).hexdigest()[:36])
  if old and old.kind=='skill':skills.delete_skill(s,old,remember=False)
 known={skills.digest(skills.validate_definition(x)):x for x in skills.BUNDLED}
 for hash,definition in known.items():
  id=hashlib.sha256((workspace_id.get()+':bundled-skill:'+definition['name']).encode()).hexdigest()[:36]
  if not s.get(Record,id) and not s.scalar(select(Record).where(Record.kind=='skill_removed',Record.dedupe_key==id)):s.add(Record(id=id,kind='skill',title=definition['name'],payload=json.dumps({'definition':skills.validate_definition(definition),'hash':hash,'revision':0,'status':'draft','origin':{'type':'bundled','version':1},'history':[]})))
 s.flush();return set(known)

def queue_test(s,row,policy,project_id,creator):
 d=json.loads(row.payload)
 if not policy['allow_web'] and 'web.search' in skills.tools_for(d['definition']):return None
 if d.get('test_job_id') and d.get('test_model')==policy['model']:
  old=s.get(Record,d['test_job_id'])
  if old:return old
 if not reserve(policy):return None
 agent=skills.agent_for(s,row,d,policy['model']);objective='Test this data-only skill using the selected project. Keep unknown facts unset. Return a concise draft only.'
 job=add_task(s,agent.id,TaskBody(objective=objective,idempotency_key='autonomy-test:'+row.id+':'+d['hash'][:20]+':'+hashlib.sha256(policy['model'].encode()).hexdigest()[:8]+':'+now()[:10],plan=skills.plan_for(d['definition'],objective,project_id)),creator)
 j=json.loads(job.payload);j.update(skill_id=row.id,skill_hash=d['hash'],skill_test=True,space_id=project_id,automation=True);job.payload=json.dumps(j);d.update(test_job_id=job.id,test_model=policy['model'],status='draft');row.payload=json.dumps(d);return job

def promote(s,row,policy,known):
 d=json.loads(row.payload)
 permitted=(d.get('origin',{}).get('type')=='bundled' and d['hash'] in known) or (d.get('origin',{}).get('auto_candidate') and policy['auto_activate_generated'])
 if not permitted or d.get('status') in {'active','revoked'}:return
 if not policy['allow_web'] and 'web.search' in skills.tools_for(d['definition']):return
 test=s.get(Record,d.get('test_job_id',''))
 if not test:return
 j=json.loads(test.payload)
 if j.get('status')!='completed' or j.get('skill_hash')!=d['hash'] or d.get('test_model')!=policy['model']:return
 agent=skills.agent_for(s,row,d,policy['model']);cfg=json.loads(agent.payload);cfg['enabled']=True;agent.payload=json.dumps(cfg);d.update(status='active',agent_id=agent.id,activated_at=now(),activated_by='automation:tested-readonly-policy');row.payload=json.dumps(d);audit(s,'skill.auto_activate',row.id,hash=d['hash'])

def create_mission(s,policy,command,creator,idempotency):
 existing=active_missions(s)
 if existing:return existing[0]
 from .operations import ranked_projects
 projects=ranked_projects(s,policy)[:policy['max_projects']]
 if not projects:raise HTTPException(409,'Create or select a matching project space first')
 id=hashlib.sha256((workspace_id.get()+':mission:'+idempotency).encode()).hexdigest()[:36]
 old=s.get(Record,id)
 if old:return old
 row=Record(id=id,kind='mission',title=command[:120],payload=json.dumps({'status':'queued','creator_id':creator,'command':command,'created_at':now(),'cursor':0,'projects':[{'id':r.id,'title':r.title,'status':'queued'} for r in projects],'events':[]}));s.add(row);audit(s,'mission.start',id,projects=len(projects));policy['next_run_at']=(datetime.now(timezone.utc)+timedelta(minutes=policy['interval_minutes'])).isoformat();return row
@router.get('')
def status():
 with Session() as s:
  p=load_policy(s);policy=json.loads(p.payload) if p else {**Policy().model_dump(),'daily_jobs':0}
  missions=[r.public() for r in s.scalars(select(Record).where(Record.kind=='mission').order_by(Record.created_at.desc()).limit(30))]
  learning=s.get(Record,policy.get('learning_job_id') or policy.get('last_learning_job_id') or '')
  if learning is None and policy.get('last_learned_skill_id'):
   learned=s.get(Record,policy['last_learned_skill_id'])
   if learned:learning=s.get(Record,json.loads(learned.payload).get('origin',{}).get('proposal_job_id',''))
  return {'policy':policy,'missions':missions,'learning':learning.public() if learning else None,'bounds':{'actions':'Saved drafts and read-only registered tools only. No shell, sending, publishing or spending.','projects':'Selected project context only.','skills':'Exact validated/tested skill revisions; imported skills require owner activation.'}}
@router.put('/policy')
async def save_policy(body:Policy,request:Request):
 admin(request);await skills.require_model(body.model)
 with Session() as s:
  row=load_policy(s,True);old=json.loads(row.payload)
  for id in body.project_ids:get_record(s,id,'space')
  if not body.allow_web:
   for job in s.scalars(select(Record).where(Record.kind=='job')):
    j=json.loads(job.payload)
    if j.get('automation') and j.get('status') in {'queued','running','paused'} and 'web.search' in j.get('agent_snapshot',{}).get('tools',[]):j.update(status='cancelled',error='Automatic public research permission removed');job.payload=json.dumps(j)
  old.update(body.model_dump(),creator_id=request.state.identity['id']);row.payload=json.dumps(old);audit(s,'automation.policy',row.id);s.commit();return old
def transition_automation_jobs(s, statuses, target):
 for job in s.scalars(select(Record).where(Record.kind=='job').with_for_update()):
  d=json.loads(job.payload)
  if d.get('automation') and d.get('status') in statuses:
   d['status']=target;job.payload=json.dumps(d)

@router.post('/command',status_code=201)
async def command(body:Command,request:Request):
 admin(request)
 with Session() as s:
  p=load_policy(s,True);d=json.loads(p.payload);model=d['model']
 await skills.require_model(model)
 with Session() as s:
  p=load_policy(s,True);d=json.loads(p.payload);d.update(enabled=body.continuous,paused=False,creator_id=request.state.identity['id']);ensure_bundled(s);row=create_mission(s,d,body.command,request.state.identity['id'],body.idempotency_key)
  transition_automation_jobs(s,{'paused'},'queued')
  mission=json.loads(row.payload)
  if mission['status']=='paused':
   mission['status']='queued'
   ids={x.get(k) for x in mission['projects'] for k in ['job_id','test_job_id']}|{d.get('learning_job_id')}
   for job_id in ids-{None}:
    job=s.get(Record,job_id)
    if job:
     j=json.loads(job.payload)
     if j.get('status')=='paused':j['status']='queued';job.payload=json.dumps(j)
   row.payload=json.dumps(mission)
  p.payload=json.dumps(d);s.commit();return row.public()
@router.post('/stop')
def stop(request:Request):
 admin(request)
 with Session() as s:
  p=load_policy(s,True);d=json.loads(p.payload);d.update(enabled=False,paused=True);p.payload=json.dumps(d)
  for row in active_missions(s):
   mission=json.loads(row.payload);mission['status']='paused';row.payload=json.dumps(mission)
   ids={x.get(k) for x in mission['projects'] for k in ['job_id','test_job_id']}|{d.get('learning_job_id')}
   for id in ids- {None}:
    job=s.get(Record,id)
    if job:
     j=json.loads(job.payload)
     if j.get('status') in {'queued','running'}:j['status']='paused';job.payload=json.dumps(j)
  transition_automation_jobs(s,{'queued','running'},'paused')
  audit(s,'automation.stop',p.id);s.commit();return {'paused':True}
@router.post('/missions/{id}/resume')
def resume(id:str,request:Request):
 admin(request)
 with Session() as s:
  row=get_record(s,id,'mission');m=json.loads(row.payload);p=load_policy(s,True);d=json.loads(p.payload);d['paused']=False;p.payload=json.dumps(d)
  if m['status']=='paused':m['status']='queued'
  ids={x.get(k) for x in m['projects'] for k in ['job_id','test_job_id']}|{d.get('learning_job_id')}
  for job_id in ids-{None}:
   job=s.get(Record,job_id)
   if job:
    j=json.loads(job.payload)
    if j.get('status')=='paused':j['status']='queued';job.payload=json.dumps(j)
  transition_automation_jobs(s,{'paused'},'queued')
  row.payload=json.dumps(m);s.commit();return row.public()

def step_mission(s,row,p,known):
 m=json.loads(row.payload)
 if m['status']=='paused':return
 m['status']='running'
 if m['cursor']>=len(m['projects']):m.update(status='completed',completed_at=now());row.payload=json.dumps(m);return
 item=m['projects'][m['cursor']]
 try:space=get_record(s,item['id'],'space')
 except HTTPException:
  item.update(status='failed',error='Project was removed');m['cursor']+=1;row.payload=json.dumps(m);return
 sd=json.loads(space.payload)
 all_skills=list(s.scalars(select(Record).where(Record.kind=='skill')))
 for skill in all_skills:promote(s,skill,p,known)
 if item.get('job_id'):
  job=s.get(Record,item['job_id']);j=json.loads(job.payload) if job else {'status':'failed','error':'Task removed'}
  skill=s.get(Record,item['skill_id']);current=json.loads(skill.payload) if skill else {}
  if current.get('status')!='active' or current.get('hash')!=item['skill_hash']:
   if job and j['status'] in {'queued','running'}:j.update(status='cancelled',error='Pinned skill was changed or revoked');job.payload=json.dumps(j)
   item.update(status='failed',error='Pinned skill changed or was revoked');m['cursor']+=1
  elif j['status']=='completed':
   from .project_spaces import payload
   key=space.id+':mission:'+job.id;old=s.scalar(select(Record).where(Record.kind=='space_item',Record.dedupe_key==key))
   if not old:
    result=j.get('result','');draft=Record(kind='space_item',dedupe_key=key,title=('Automation draft: '+space.title)[:200],payload=json.dumps({'kind':'deliverable','space_id':space.id,'status':'draft','body':result[:30000],'source':'Automation task '+job.id,'origin_job_id':job.id,'original_sha256':hashlib.sha256(result.encode()).hexdigest(),'review':['Check evidence and source coverage','Remove unsupported claims','Confirm usable next action'],'review_done':[],'revision':0,'mission_id':row.id}));s.add(draft);s.flush();item['deliverable_id']=draft.id
   item.update(status='completed');m['cursor']+=1
  elif j['status'] in {'failed','cancelled'}:item.update(status='failed',error=j.get('error_detail') or j.get('error','Task failed'));m['cursor']+=1
  elif j['status']=='paused':m['status']='paused'
  row.payload=json.dumps(m);return
 matches=[x for x in all_skills if json.loads(x.payload).get('status')=='active' and json.loads(x.payload).get('test_model')==p['model'] and sd['kind'] in json.loads(x.payload)['definition']['project_kinds'] and (not json.loads(x.payload).get('origin',{}).get('project_id') or json.loads(x.payload)['origin']['project_id']==space.id) and (p['allow_web'] or 'web.search' not in skills.tools_for(json.loads(x.payload)['definition']))]
 if not matches:
  candidates=[x for x in all_skills if sd['kind'] in json.loads(x.payload)['definition']['project_kinds'] and json.loads(x.payload)['hash'] in known and (json.loads(x.payload).get('status')=='draft' or json.loads(x.payload).get('status')=='active' and json.loads(x.payload).get('test_model')!=p['model'])]
  if candidates:
   test=queue_test(s,candidates[0],p,space.id,m['creator_id'])
   if test and json.loads(test.payload).get('status') in {'failed','cancelled'}:item.update(status='failed',error='Bundled skill test failed; inspect its task or create a corrected skill.');m['cursor']+=1
   else:item.update(status='waiting_skill',test_job_id=test.id if test else None);m['status']='waiting_skill' if test else 'waiting_budget'
  else:item.update(status='failed',error='No active tested skill matches this project');m['cursor']+=1
  row.payload=json.dumps(m);return
 # Prefer a specialized skill over a generic fallback, stable across repeated ticks.
 skill=sorted(matches,key=lambda x:(len(json.loads(x.payload)['definition']['project_kinds']),-datetime.fromisoformat(x.created_at).timestamp()))[0];d=json.loads(skill.payload)
 from .operations import controls
 from .project_spaces import all_items
 owner_objective=controls(s).get(space.id,{}).get('objective','')
 inputs=[]
 for record in all_items(s,space.id):
  value=json.loads(record.payload)
  if record.kind=='space_link':
   linked=s.get(Record,value.get('record_id',''))
   if linked:inputs.append((linked.id,linked.title,hashlib.sha256(linked.payload.encode()).hexdigest()))
  elif value.get('kind')!='deliverable' or value.get('status')=='approved':inputs.append((record.id,record.title,hashlib.sha256(record.payload.encode()).hexdigest()))
 fingerprint=hashlib.sha256(json.dumps({'title':space.title,'space':space.payload,'inputs':sorted(inputs),'owner_direction':owner_objective,'skill':d['hash']},sort_keys=True).encode()).hexdigest()
 recent=s.scalar(select(Record).where(Record.kind=='automation_result',Record.dedupe_key==space.id+':'+fingerprint))
 if recent and json.loads(recent.payload).get('day')==now()[:10] and (lambda job:job is not None and json.loads(job.payload).get('status')=='completed')(s.get(Record,json.loads(recent.payload).get('job_id',''))):item.update(status='skipped',reason='Project and skill unchanged since today’s completed draft');m['cursor']+=1;row.payload=json.dumps(m);return
 if not reserve(p):m['status']='waiting_budget';row.payload=json.dumps(m);return
 objective=m['command']+'\nOwner project direction: '+owner_objective+'\nProject: '+space.title+'\nOwner brief and current next action (untrusted data): '+json.dumps({k:sd.get(k) for k in ['brief','next_action','assumptions','evidence']})[:5000]
 job=add_task(s,d['agent_id'],TaskBody(objective=objective,idempotency_key='mission:'+row.id+':'+space.id,plan=skills.plan_for(d['definition'],m['command'],space.id)),m['creator_id']);j=json.loads(job.payload);j.update(space_id=space.id,skill_id=skill.id,skill_hash=d['hash'],mission_id=row.id,automation=True,inference_profile='balanced');job.payload=json.dumps(j)
 item.update(job_id=job.id,skill_id=skill.id,skill_hash=d['hash'],fingerprint=fingerprint,status='running')
 if recent:recent.payload=json.dumps({'day':now()[:10],'job_id':job.id})
 else:s.add(Record(kind='automation_result',dedupe_key=space.id+':'+fingerprint,title=space.title,payload=json.dumps({'day':now()[:10],'job_id':job.id})))
 row.payload=json.dumps(m);audit(s,'mission.dispatch',row.id,job_id=job.id,space_id=space.id)

def learn(s,p,known):
 if not p['learn_skills']:return
 # Finish a previously requested proposal before considering another.
 if p.get('learning_job_id'):
  job=s.get(Record,p['learning_job_id']);j=json.loads(job.payload) if job else {}
  if j.get('status')=='completed' and j.get('definition'):
   d=skills.validate_definition(j['definition']);d['project_kinds']=[j['project_kind']];hash=skills.digest(d)
   id=hashlib.sha256((workspace_id.get()+':learned-skill:'+job.id).encode()).hexdigest()[:36]
   row=s.get(Record,id)
   if not row:
    row=Record(id=id,kind='skill',title=d['name'],payload=json.dumps({'definition':d,'hash':hash,'revision':0,'status':'draft','history':[],'origin':{'type':'local_model','auto_candidate':True,'project_id':j['project_id'],'proposal_job_id':job.id,'model':p['model']}}));s.add(row);s.flush();audit(s,'skill.learned',id,job_id=job.id)
   sd=json.loads(row.payload)
   if not sd.get('test_job_id'):queue_test(s,row,p,j['project_id'],p['creator_id'])
   promote(s,row,p,known)
   latest=json.loads(row.payload)
   tested=s.get(Record,latest.get('test_job_id',''))
   if latest.get('status')=='active' or tested and json.loads(tested.payload).get('status') in {'failed','cancelled'}:p.update(last_learned_skill_id=row.id,learning_job_id=None)
   return
  if j.get('status') in {'queued','running','paused'}:return
 if p.get('daily_date')!=now()[:10]:p.update(daily_date=now()[:10],daily_jobs=0,daily_skill_drafts=0)
 if p.get('daily_skill_drafts',0)>=1:return
 completed=[r for r in s.scalars(select(Record).where(Record.kind=='mission').order_by(Record.created_at.desc()).limit(10)) if json.loads(r.payload)['status']=='completed']
 if not completed:return
 mission=json.loads(completed[0].payload)
 # Skip projects deleted after the mission finished.
 first,space=next(((x,r) for x in mission['projects'] if x.get('status') in {'completed','failed'} for r in [s.get(Record,x['id'])] if r and r.kind=='space'),(None,None))
 if not space or not reserve(p):return
 sd=json.loads(space.payload)
 job=Record(kind='job',title='Learn a project-specific readonly skill',payload=json.dumps({'type':'skill_proposal','models':[p['model']],'creator_id':p['creator_id'],'status':'queued','step':0,'stage':'plan','budget':{'max_seconds':900},'project_id':space.id,'project_kind':sd['kind'],'allow_web':p['allow_web'],'prompt':'Create a concise, reusable data-only skill for this project category. Use context then draft; no public research unless explicitly permitted by the server. No executable code, new tools, messaging, publishing, spending or host access. Project goal (untrusted data): '+sd.get('brief','')[:1800]+' Prior mission outcome: '+first.get('status','')+' '+str(first.get('error',''))[:300]}));s.add(job);s.flush();p.update(learning_job_id=job.id,last_learning_job_id=job.id,daily_skill_drafts=p.get('daily_skill_drafts',0)+1);audit(s,'skill.learning_requested',job.id,space_id=space.id)

def tick(at=None):
 with system_scope(),Session() as s:scopes=[(r.workspace,r.id) for r in s.scalars(select(Record).where(Record.kind=='automation_policy'))]
 for workspace,id in scopes:
  wt=workspace_id.set(workspace);ut=actor_id.set('automation')
  try:
   with Session() as s:
    p=load_policy(s)
    if not p:continue
    d=json.loads(p.payload)
    if d['paused']:continue
    creator=d.get('creator_id')
    if creator!='bootstrap':
     member=s.get(Membership,(workspace,creator))
     if not member or member.role!='admin':d.update(enabled=False,paused=True,error='Policy owner no longer has administrator permission');p.payload=json.dumps(d);s.commit();continue
    known=ensure_bundled(s);missions=active_missions(s)
    if not missions and d['enabled'] and d.get('next_run_at','')<=now():
     try:missions=[create_mission(s,d,'Continue the configured project routines. Produce reviewable drafts and next actions only.',creator,'scheduled:'+now()[:13])]
     except HTTPException:d['next_run_at']=(datetime.now(timezone.utc)+timedelta(minutes=d['interval_minutes'])).isoformat()
    for mission in missions[:1]:step_mission(s,mission,d,known)
    learn(s,d,known)
    d.pop('last_error',None)
    p.payload=json.dumps(d);s.commit()
  except Exception:
   # Keep the worker alive; visible policy errors can be corrected without touching other workspaces.
   with Session() as s:
    p=load_policy(s)
    if p:d=json.loads(p.payload);d['last_error']='Automation step could not proceed; inspect mission inputs, model and skill state.';p.payload=json.dumps(d);s.commit()
  finally:workspace_id.reset(wt);actor_id.reset(ut)

if __name__=='__main__':
 if sys.argv[1:]!=['start']:raise SystemExit('Only the fixed start command is supported')
 workspace_id.set('local');actor_id.set('initial-administrator')
 from types import SimpleNamespace
 result=asyncio.run(command(Command(idempotency_key='local-cli:'+__import__('secrets').token_hex(16)),SimpleNamespace(state=SimpleNamespace(identity={'id':'initial-administrator','role':'admin'}))))
 print(json.dumps({'mission_id':result['id'],'status':result['data']['status'],'message':'Project automation started. Review progress and drafts in Automation.'}))

@router.post('/missions/{id}/cancel')
def cancel(id:str,request:Request):
 admin(request)
 with Session() as s:
  row=get_record(s,id,'mission');m=json.loads(row.payload);m['status']='cancelled';row.payload=json.dumps(m)
  for item in m['projects']:
   for k in ['job_id','test_job_id']:
    job=s.get(Record,item.get(k,''))
    if job:
     d=json.loads(job.payload)
     if d.get('status') in {'queued','running','paused'}:d.update(status='cancelled',error='Mission cancelled by owner');job.payload=json.dumps(d)
  audit(s,'mission.cancel',id);s.commit();return row.public()
