"""Workspace APIs for fixed-registry agents, schedules and approved memory."""
import json
import hashlib
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
from typing import Literal
from fastapi import APIRouter,HTTPException,Request
from fastapi.responses import Response
from pydantic import BaseModel,Field,ConfigDict,model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from .db import Record,Session,get_record,audit,now,uid
from .scope import workspace_id,actor_id
from .agents import AgentConfig,templates,validate_plan,load_config
from .agent_tools import catalogue
router=APIRouter(prefix='/api')
class AgentBody(BaseModel):
    model_config=ConfigDict(extra='forbid')
    name:str=Field(min_length=1,max_length=200)
    config:AgentConfig

def validate_resources(s,config):
    for id in config.document_ids:get_record(s,id,'document')
    for id in config.delegate_ids:get_record(s,id,'agent')

@router.get('/agents/overview')
def workforce_overview():
    # One scoped refresh instead of six polling requests. Document bodies and
    # complete artifact bodies are unnecessary for permission selectors.
    groups={key:[] for key in ['agents','jobs','schedules','approvals','documents','artifacts']}
    names={'agent':'agents','job':'jobs','schedule':'schedules','approval':'approvals','document':'documents','artifact':'artifacts'}
    with Session() as s:
        for row in s.scalars(select(Record).where(Record.kind.in_(names)).order_by(Record.updated_at.desc())):
            value=row.public();d=value['data']
            if row.kind=='job' and d.get('type')!='agent':continue
            if row.kind=='approval' and d.get('action')!='agent_tool':continue
            if row.kind in {'document','artifact'}:value['data']={k:v for k,v in d.items() if k in {'size','characters','job_id'}}
            if row.kind=='artifact':value['data']['source_archive_available']='source_project' in d
            key=names[row.kind]
            if len(groups[key])<200:groups[key].append(value)
    return groups

@router.get('/agents/templates')
def template_list():return templates()
@router.get('/agents/tools')
def tool_list():return catalogue()
@router.post('/agents',status_code=201)
def create_agent(body:AgentBody):
    with Session() as s:
        validate_resources(s,body.config)
        row=Record(kind='agent',title=body.name,payload=body.config.model_dump_json());s.add(row);s.flush();audit(s,'agent.create',row.id);s.commit();return row.public()
@router.put('/agents/{id}')
def update_agent(id:str,body:AgentBody):
    with Session() as s:
        row=get_record(s,id,'agent');validate_resources(s,body.config)
        if id in body.config.delegate_ids:raise HTTPException(422,'Self-delegation is not permitted')
        row.title=body.name;row.payload=body.config.model_dump_json();row.updated_at=now();audit(s,'agent.configure',id);s.commit();return row.public()

class TaskBody(BaseModel):
    model_config=ConfigDict(extra='forbid')
    objective:str=Field(min_length=1,max_length=20000)
    idempotency_key:str=Field(min_length=8,max_length=100)
    plan:list[dict]|None=Field(default=None,max_length=12)

def task_data(s,agent_id,objective,creator,plan=None):
    agent=get_record(s,agent_id,'agent');cfg=load_config(agent.payload)
    if not cfg['enabled']:raise HTTPException(409,'Agent paused')
    if not cfg['model']:raise HTTPException(422,'Assign a local model')
    delegates={}
    for id in cfg['delegate_ids']:
        row=get_record(s,id,'agent');d=load_config(row.payload)
        if not d['enabled'] or not d['model']:raise HTTPException(422,'Delegates need an active configured model')
        delegates[id]=d
    data={'type':'agent','agent_id':agent_id,'agent_snapshot':cfg,'delegates':delegates,'models':[cfg['model']],'prompt':objective,'creator_id':creator,'status':'queued','stage':'plan','step':0,'attempts':0,'agent_model_calls':0,'budget':{'max_seconds':cfg['max_seconds']},'timeline':[]}
    if plan is not None:data.update(plan=validate_plan(data,{'steps':plan}),stage='execute',cursor=0)
    return data

def add_task(s,agent_id,body,creator):
    id=hashlib.sha256((workspace_id.get()+':'+body.idempotency_key).encode()).hexdigest()[:36]
    existing=s.get(Record,id)
    if existing:
        old=json.loads(existing.payload)
        if existing.kind!='job' or old.get('agent_id')!=agent_id or old.get('prompt')!=body.objective:raise HTTPException(409,'Idempotency key already used for another objective')
        return existing
    data=task_data(s,agent_id,body.objective,creator,body.plan)
    row=Record(id=id,kind='job',title=body.objective[:120],payload=json.dumps(data));s.add(row);audit(s,'agent.task.create',id,agent_id=agent_id);return row

@router.post('/agents/{id}/tasks',status_code=201)
def submit_task(id:str,body:TaskBody,request:Request):
    with Session() as s:
        try:
            row=add_task(s,id,body,request.state.identity['id']);s.commit();return row.public()
        except (ValueError,PermissionError) as e:raise HTTPException(422,str(e))
        except IntegrityError:raise HTTPException(409,'Concurrent duplicate task; retry same key')

class Fact(BaseModel):
    body:str=Field(min_length=1,max_length=10000)
    title:str=Field(min_length=1,max_length=200)
    retention_days:int=Field(default=30,ge=1,le=365)
@router.post('/agents/{id}/memory',status_code=201)
def save_fact(id:str,body:Fact):
    with Session() as s:
        get_record(s,id,'agent')
        row=Record(kind='agent_memory',title=body.title,payload=json.dumps({'agent_id':id,'body':body.body,'approved_fact':True,'verified':False,'approved_by':actor_id.get(),'expires_at':(datetime.now(timezone.utc)+timedelta(days=body.retention_days)).isoformat()}));s.add(row);s.flush();audit(s,'agent.memory.user_approve',row.id);s.commit();return row.public()
@router.put('/agent-memory/{id}')
def edit_fact(id:str,body:Fact):
    with Session() as s:
        row=get_record(s,id,'agent_memory');d=json.loads(row.payload)
        if not d.get('approved_fact'):raise HTTPException(403,'Generated summaries are immutable; delete or save an explicit fact')
        d.update(body=body.body,approved_by=actor_id.get(),expires_at=(datetime.now(timezone.utc)+timedelta(days=body.retention_days)).isoformat());row.title=body.title;row.payload=json.dumps(d);row.updated_at=now();audit(s,'agent.memory.update',id);s.commit();return row.public()
@router.get('/agents/{id}/memory')
def memories(id:str,q:str=''):
    from .agent_memory import search_memory
    with Session() as s:get_record(s,id,'agent')
    if q:return search_memory(id,q)
    with Session() as s:return [r.public() for r in s.scalars(select(Record).where(Record.kind=='agent_memory')) if json.loads(r.payload).get('agent_id')==id and json.loads(r.payload).get('expires_at','9999')>=now()]

class ScheduleBody(BaseModel):
    model_config=ConfigDict(extra='forbid')
    agent_id:str
    objective:str=Field(min_length=1,max_length=20000)
    start_at:datetime
    timezone:str=Field(default='UTC',max_length=80)
    every_minutes:int|None=Field(default=None,ge=5,le=525600)
    missed_policy:Literal['skip','run_once']='run_once'
    max_runs:int=Field(default=10,ge=1,le=1000)
    retry_limit:int=Field(default=1,ge=0,le=2)
    @model_validator(mode='after')
    def valid_time(self):
        try:zone=ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError:raise ValueError('Unknown IANA timezone')
        if self.start_at.tzinfo is None:
            local=self.start_at
            aware=local.replace(tzinfo=zone)
            if aware.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None)!=local:raise ValueError('Nonexistent local time; choose a valid time')
            if aware.utcoffset()!=local.replace(tzinfo=zone,fold=1).utcoffset():raise ValueError('Ambiguous local time; provide an explicit UTC offset')
            self.start_at=aware
        self.start_at=self.start_at.astimezone(timezone.utc)
        return self
@router.post('/agent-schedules',status_code=201)
def schedule(body:ScheduleBody,request:Request):
    with Session() as s:
        task_data(s,body.agent_id,body.objective,request.state.identity['id'])
        d=body.model_dump(mode='json');d.update(next_run_at=body.start_at.isoformat(),enabled=True,runs=0,creator_id=request.state.identity['id'],history=[])
        row=Record(kind='schedule',title=body.objective[:120],payload=json.dumps(d));s.add(row);s.flush();audit(s,'schedule.create',row.id);s.commit();return row.public()
@router.post('/agent-schedules/{id}/{action}')
def schedule_control(id:str,action:Literal['pause','resume']):
    with Session() as s:
        row=get_record(s,id,'schedule');d=json.loads(row.payload)
        if action=='resume' and d['runs']>=d['max_runs']:raise HTTPException(409,'Schedule run budget exhausted')
        d['enabled']=action=='resume';d['paused']=action=='pause';row.payload=json.dumps(d);row.updated_at=now();audit(s,'schedule.'+action,id);s.commit();return row.public()

@router.get('/artifacts/{id}/export')
def artifact(id:str,format:Literal['md','pdf','docx','xlsx','json','csv','zip']='md'):
    from .reports import report
    with Session() as s:
        row=get_record(s,id,'artifact');d=json.loads(row.payload)
        if format=='zip':
            from .advanced_files import source_zip
            if 'source_project' not in d: raise HTTPException(422,'Artifact is not a source project')
            content,mime=source_zip(d['source_project']),'application/zip'
        elif format in ('json','csv'):
            from .advanced_files import text_export
            content,mime=text_export(row.title,d['body'],format)
        elif format=='md':content,mime=d['body'].encode(),'text/markdown'
        else:content,mime=report(row.title,d['body'],[],format)
        return Response(content,media_type=mime,headers={'Content-Disposition':f'attachment; filename="artifact.{format}"'})
