"""Owner project controls and an evidence-based operations overview; no inference."""
import hashlib,json
from datetime import date
from fastapi import APIRouter,Request
from pydantic import BaseModel,ConfigDict,Field
from sqlalchemy import select
from .db import Session,Record,get_record,audit,now
from .scope import workspace_id
router=APIRouter(prefix='/api/operations')
class Control(BaseModel):
 model_config=ConfigDict(extra='forbid')
 enabled:bool=True
 priority:int=Field(default=3,ge=1,le=5)
 objective:str=Field(default='',max_length=1500)
 revision:int=Field(default=0,ge=0)
def control_id(id):return hashlib.sha256((workspace_id.get()+':project-control:'+id).encode()).hexdigest()[:36]
def controls(s):return {json.loads(r.payload)['project_id']:json.loads(r.payload) for r in s.scalars(select(Record).where(Record.kind=='project_control'))}
def defaults():return Control().model_dump()
def ranked_projects(s,policy):
 settings=controls(s);served={}
 for r in s.scalars(select(Record).where(Record.kind=='mission')):
  d=json.loads(r.payload)
  if d.get('status')=='cancelled':continue
  for p in d.get('projects',[]):served[p['id']]=max(served.get(p['id'],''),d.get('created_at',r.created_at))
 projects=[r for r in s.scalars(select(Record).where(Record.kind=='space')) if (not policy['project_ids'] or r.id in policy['project_ids']) and json.loads(r.payload).get('kind') in policy['focus'] and settings.get(r.id,{}).get('enabled',True)]
 # Least recently selected first. Priority breaks ties; a high priority cannot starve old work.
 return sorted(projects,key=lambda r:(served.get(r.id,''),-settings.get(r.id,{}).get('priority',3),r.created_at,r.id))
@router.put('/projects/{id}')
def save(id:str,body:Control,request:Request):
 from .autonomy import admin
 from fastapi import HTTPException
 from .project_spaces import lock_space
 admin(request)
 with Session() as s:
  lock_space(s,id);row=s.get(Record,control_id(id));old=json.loads(row.payload) if row else defaults()
  if old.get('revision',0)!=body.revision:raise HTTPException(409,'Project controls changed. Reload before saving.')
  d={**body.model_dump(),'project_id':id,'revision':body.revision+1}
  if not row:row=Record(id=control_id(id),kind='project_control',title='Automation project controls');s.add(row)
  row.payload=json.dumps(d);row.updated_at=now();audit(s,'project_control.save',id,enabled=body.enabled,priority=body.priority);s.commit();return d
@router.get('/projects/{id}/context')
def context(id:str):
 from .workspace_context import retrieve_context
 with Session() as s:
  row=get_record(s,id,'space');d=json.loads(row.payload)
 return retrieve_context(row.title+' '+d.get('brief','')[:500],project_id=id,budget=5000)
@router.get('')
def overview():
 from .autonomy import load_policy,Policy,active_missions
 with Session() as s:
  row=load_policy(s);policy=json.loads(row.payload) if row else Policy().model_dump();settings=controls(s)
  eligible=ranked_projects(s,policy);selected={r.id:i+1 for i,r in enumerate(eligible[:policy['max_projects']])};projects=[];inbox=[];today=date.fromisoformat(now()[:10])
  items={}
  for r in s.scalars(select(Record).where(Record.kind.in_({'space_item','space_link'}))):
   d=json.loads(r.payload);items.setdefault(d.get('space_id'),[]).append((r,d))
  for r in s.scalars(select(Record).where(Record.kind=='space').order_by(Record.title)):
   d=json.loads(r.payload);children=items.get(r.id,[]);facts=[x for _,x in children if x.get('kind')=='fact' and x.get('status')!='superseded'];keys={};conflicts=[]
   for f in facts:
    k=f.get('fact_key','').strip().casefold()
    if k:keys.setdefault(k,set()).add(f.get('body','').strip())
   conflicts=[k for k,v in keys.items() if len(v)>1]
   counts={k:sum(1 for _,x in children if x.get('kind')==k) for k in ['fact','chapter','action','deliverable']};counts['approved_facts']=sum(x.get('status')=='approved' for x in facts);counts['linked_sources']=sum(c.kind=='space_link' for c,_ in children)
   warnings=[]
   if not d.get('brief','').strip():warnings.append('Add a project brief')
   if d.get('kind')=='writing' and not counts['chapter']:warnings.append('No manuscript chapters saved')
   if d.get('kind')=='business' and not d.get('evidence','').strip():warnings.append('Customer or market evidence is missing')
   if not counts['approved_facts']:warnings.append('No approved project facts')
   if conflicts:warnings.append('Conflicting fact keys need review: '+', '.join(conflicts[:10]))
   for c,x in children:
    if x.get('kind')=='deliverable' and x.get('status') not in {'approved','done','superseded'}:
     inbox.append({'id':c.id,'project_id':r.id,'project_title':r.title,'title':c.title,'status':x.get('status'),'pending_checks':[v for v in x.get('review',[]) if v not in x.get('review_done',[])],'origin_job_id':x.get('origin_job_id'),'created_at':c.created_at})
    if x.get('kind')=='action' and x.get('status') not in {'done','superseded'} and x.get('due_date') and x['due_date']<today.isoformat():warnings.append('Overdue action: '+c.title)
   control={**defaults(),**settings.get(r.id,{})};projects.append({'id':r.id,'title':r.title,'kind':d.get('kind'),'next_action':d.get('next_action',''),'counts':counts,'warnings':warnings,'control':control,'next_mission_position':selected.get(r.id),'eligible':any(p.id==r.id for p in eligible)})
  used=policy.get('daily_jobs',0) if policy.get('daily_date')==now()[:10] else 0
  return {'generated_at':now(),'projects':projects,'review_inbox':sorted(inbox,key=lambda x:x['created_at'],reverse=True),'preview':{'next_project_ids':[r.id for r in eligible[:policy['max_projects']]],'eligible_projects':len(eligible),'deferred_projects':max(0,len(eligible)-policy['max_projects']),'remaining_jobs':max(0,policy['daily_job_limit']-used),'active_mission_ids':[r.id for r in active_missions(s)],'enabled':policy['enabled'],'paused':policy['paused'],'next_run_at':policy.get('next_run_at'),'model':policy['model'],'notes':'Planning snapshot only; no model calls or tasks started. Budget also covers skill tests and learning. Active missions keep their original project selection. Future missions rotate least recently selected projects first; priority breaks ties.'}}
