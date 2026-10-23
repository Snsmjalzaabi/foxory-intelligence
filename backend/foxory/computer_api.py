"""Computer Mode uses existing agent state, tenant access and approvals."""
import base64
import hashlib
import json
import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from .db import Session, Record, get_record, audit
from .agent_api import TaskBody, add_task
from .agent_tools import SandboxPython
from .agents import load_config
from .scope import workspace_id
from . import sandbox_client
router=APIRouter(prefix='/api/computer')

@router.get('/capabilities')
async def capabilities():return await sandbox_client.capabilities()

@router.get('/overview')
def overview():
    with Session() as session:
        rows=session.scalars(select(Record).where(Record.kind.in_(['agent','job','approval'])).order_by(Record.updated_at.desc())).all()
        agents=[];jobs=[];approvals=[]
        for row in rows:
            data=json.loads(row.payload)
            if row.kind=='agent' and 'sandbox.python' in load_config(row.payload)['tools'] and len(agents)<100:agents.append(row.public())
            if row.kind=='job' and data.get('computer_mode') and len(jobs)<100:jobs.append(row.public())
            if row.kind=='approval' and data.get('action')=='agent_tool' and len(approvals)<100:approvals.append(row.public())
        ids={job['id'] for job in jobs}
        return {'agents':agents,'jobs':jobs,'approvals':[a for a in approvals if a['data']['context']['job_id'] in ids]}

class ComputerTask(BaseModel):
    model_config=ConfigDict(extra='forbid')
    agent_id:str=Field(min_length=1,max_length=36)
    objective:str=Field(min_length=1,max_length=20000)
    idempotency_key:str=Field(min_length=8,max_length=100)
    source:SandboxPython|None=None

@router.post('/tasks',status_code=201)
def create(body:ComputerTask,request:Request):
    with Session() as session:
        agent=get_record(session,body.agent_id,'agent');cfg=load_config(agent.payload)
        if 'sandbox.python' not in cfg['tools'] or 'sandbox.execute' not in cfg['permissions']:raise HTTPException(403,'Explicit sandbox tool grant is required')
        id=hashlib.sha256((workspace_id.get()+':'+body.idempotency_key).encode()).hexdigest()[:36]
        existing=session.get(Record,id)
        if existing:
            previous=json.loads(existing.payload)
            if existing.kind!='job' or not previous.get('computer_mode') or previous.get('computer_request')!=body.model_dump(mode='json'):
                raise HTTPException(409,'Idempotency key already belongs to different task inputs')
            # Do not rewrite a running claim for a semantically identical retry.
            return existing.public()
        plan=None
        if body.source:
            plan=[{'title':'Run reviewed Python project','tool':'sandbox.python','args':body.source.model_dump()},
                  {'title':'Package the matching source','tool':'source.package','args':{'title':body.source.title,'files':body.source.files},'depends_on':[0]}]
        try:
            task=TaskBody(objective=body.objective,idempotency_key=body.idempotency_key,plan=plan)
            row=add_task(session,body.agent_id,task,request.state.identity['id'])
            data=json.loads(row.payload)
            if data.get('computer_request') not in (None,body.model_dump(mode='json')):raise HTTPException(409,'Idempotency key reused with different computer inputs')
            data.update(computer_mode=True,computer_request=body.model_dump(mode='json'));row.payload=json.dumps(data)
            audit(session,'computer.submit',row.id);session.commit();return row.public()
        except (ValueError,PermissionError) as error:raise HTTPException(422,str(error))
        except IntegrityError:raise HTTPException(409,'Concurrent duplicate task; retry the same key')

@router.get('/jobs/{id}/execution')
async def execution(id:str):
    with Session() as session:
        data=json.loads(get_record(session,id,'job').payload)
        if not data.get('computer_mode'):raise HTTPException(404,'Computer task not found')
    grant=data.get('sandbox_authorizations',{}).get(str(data.get('cursor',0)))
    if not grant or data['status'] not in {'queued','running'}:return {'status':data['status']}
    try:
        sandbox_client.settings()
        remote=hashlib.sha256((workspace_id.get()+':agent:'+grant['approval_id']).encode()).hexdigest()
        async with sandbox_client.transport() as client:
            result=await client.get('/v1/jobs/'+remote)
            if result.status_code==404:return {'status':'dispatching'}
            result.raise_for_status();value=result.json()
            return {'status':value['status'],'stdout':value.get('stdout','')[-8000:],'stderr':value.get('stderr','')[-8000:]}
    except (PermissionError,httpx.HTTPError):return {'status':'manager unavailable'}

@router.get('/jobs/{id}/artifacts/{index}/{name}')
def artifact(id:str,index:int,name:str):
    with Session() as session:
        data=json.loads(get_record(session,id,'job').payload)
        if not data.get('computer_mode'):raise HTTPException(404,'Computer task not found')
        output=next((o for o in data.get('outputs',[]) if o['index']==index and o['tool']=='sandbox.python'),None)
        item=output['result'].get('artifacts',{}).get(name) if output else None
        if not item or name not in {'result.txt','result.json','result.csv','result.md'}:raise HTTPException(404,'Artifact not found')
        content=base64.b64decode(item['base64'],validate=True)
        if len(content)>20000 or hashlib.sha256(content).hexdigest()!=item['sha256']:raise HTTPException(409,'Artifact integrity failure')
        return Response(content,media_type='text/plain',headers={'Content-Disposition':f'attachment; filename="{name}"'})
