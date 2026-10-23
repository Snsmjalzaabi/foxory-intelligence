"""Computer Mode uses existing agent state, tenant access and approvals."""
import base64
import hashlib
import json
import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import Literal
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from .db import Session, Record, get_record, audit
from .agent_api import TaskBody, add_task
from .agent_tools import SandboxPython, SandboxJavaScript, SandboxTypeScript, SandboxBrowser
from .sandbox_protocol import SANDBOX_TOOLS, PNG_NAMES, validate_artifacts
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
            if row.kind=='agent' and bool(SANDBOX_TOOLS.intersection(load_config(row.payload)['tools'])) and len(agents)<100:agents.append(row.public())
            if row.kind=='job' and data.get('computer_mode') and len(jobs)<100:jobs.append(row.public())
            if row.kind=='approval' and data.get('action')=='agent_tool' and len(approvals)<100:approvals.append(row.public())
        ids={job['id'] for job in jobs}
        return {'agents':agents,'jobs':jobs,'approvals':[a for a in approvals if a['data']['context']['job_id'] in ids]}

class ComputerTask(BaseModel):
    model_config=ConfigDict(extra='forbid')
    agent_id:str=Field(min_length=1,max_length=36)
    objective:str=Field(min_length=1,max_length=20000)
    idempotency_key:str=Field(min_length=8,max_length=100)
    profile:Literal['python','javascript','typescript','browser']='python'
    source:SandboxPython|SandboxJavaScript|SandboxTypeScript|SandboxBrowser|None=None
    @model_validator(mode='after')
    def check_profile(self):
        types={'python':SandboxPython,'javascript':SandboxJavaScript,'typescript':SandboxTypeScript,'browser':SandboxBrowser}
        if self.source is not None and type(self.source) is not types[self.profile]:raise ValueError('Source does not match execution profile')
        return self
    def snapshot(self):
        # Preserve legacy Python request snapshots for existing idempotency keys.
        return self.model_dump(mode='json',exclude={'profile'} if self.profile=='python' else set())

@router.post('/tasks',status_code=201)
def create(body:ComputerTask,request:Request):
    with Session() as session:
        agent=get_record(session,body.agent_id,'agent');cfg=load_config(agent.payload)
        if 'sandbox.'+body.profile not in cfg['tools'] or ('sandbox.browser' if body.profile=='browser' else 'sandbox.execute') not in cfg['permissions']:raise HTTPException(403,'Explicit sandbox tool grant is required')
        id=hashlib.sha256((workspace_id.get()+':'+body.idempotency_key).encode()).hexdigest()[:36]
        existing=session.get(Record,id)
        if existing:
            previous=json.loads(existing.payload)
            if existing.kind!='job' or not previous.get('computer_mode') or previous.get('computer_request')!=body.snapshot():
                raise HTTPException(409,'Idempotency key already belongs to different task inputs')
            # Do not rewrite a running claim for a semantically identical retry.
            return existing.public()
        plan=None
        if body.source:
            plan=[{'title':'Run reviewed '+body.profile+' project','tool':'sandbox.'+body.profile,'args':body.source.model_dump()}]
            if body.profile!='browser':plan.append({'title':'Package the matching source','tool':'source.package','args':{'title':body.source.title,'files':body.source.files},'depends_on':[0]})
        try:
            task=TaskBody(objective=body.objective,idempotency_key=body.idempotency_key,plan=plan)
            row=add_task(session,body.agent_id,task,request.state.identity['id'])
            data=json.loads(row.payload)
            if data.get('computer_request') not in (None,body.snapshot()):raise HTTPException(409,'Idempotency key reused with different computer inputs')
            data.update(computer_mode=True,computer_request=body.snapshot());row.payload=json.dumps(data)
            audit(session,'computer.submit',row.id);session.commit();return row.public()
        except (ValueError,PermissionError) as error:raise HTTPException(422,str(error))
        except IntegrityError:raise HTTPException(409,'Concurrent duplicate task; retry the same key')

@router.get('/jobs/{id}/execution')
async def execution(id:str):
    with Session() as session:
        data=json.loads(get_record(session,id,'job').payload)
        if not data.get('computer_mode'):raise HTTPException(404,'Computer task not found')
    grant=data.get('sandbox_authorizations',{}).get(str(data.get('cursor',0)))
    if not grant:return {'status':data['status']}
    try:
        sandbox_client.settings()
        remote=hashlib.sha256((workspace_id.get()+':agent:'+grant['approval_id']).encode()).hexdigest()
        async with sandbox_client.transport() as client:
            result=await client.get('/v1/jobs/'+remote)
            if result.status_code==404:return {'status':'dispatching'}
            result.raise_for_status();value=result.json()
            if value.get('id')!=remote or value.get('workspace')!=workspace_id.get():return {'status':'manager ownership mismatch'}
            return {'status':value['status'],'stdout':value.get('stdout','')[-8000:],'stderr':value.get('stderr','')[-8000:]}
    except (PermissionError,httpx.HTTPError):return {'status':'manager unavailable'}

@router.get('/jobs/{id}/artifacts/{index}/{name}')
def artifact(id:str,index:int,name:str):
    with Session() as session:
        data=json.loads(get_record(session,id,'job').payload)
        if not data.get('computer_mode'):raise HTTPException(404,'Computer task not found')
        output=next((o for o in data.get('outputs',[]) if o['index']==index and o['tool'] in SANDBOX_TOOLS),None)
        item=output['result'].get('artifacts',{}).get(name) if output else None
        if not item:raise HTTPException(404,'Artifact not found')
        result=output['result']
        grant=data.get('sandbox_authorizations',{}).get(str(index))
        if result.get('id') or output['tool']!='sandbox.python':
            if not grant:raise HTTPException(409,'Missing artifact execution grant')
            expected=hashlib.sha256((workspace_id.get()+':agent:'+grant['approval_id']).encode()).hexdigest()
            if result.get('id')!=expected or result.get('workspace')!=workspace_id.get():raise HTTPException(409,'Artifact ownership mismatch')
        try:
            checked=validate_artifacts(result.get('artifacts',{}),allow_png=output['tool']=='sandbox.browser')
            content=base64.b64decode(checked[name]['base64'],validate=True)
        except (ValueError,TypeError,KeyError,RecursionError):raise HTTPException(409,'Artifact integrity failure')
        audit(session,'computer.artifact.download',id,index=index,name=name);session.commit()
        return Response(content,media_type='image/png' if name in PNG_NAMES else 'text/plain',headers={
            'Content-Disposition':f'attachment; filename="{name}"','X-Content-Type-Options':'nosniff',
            'Cache-Control':'no-store','Content-Security-Policy':"default-src 'none'; sandbox"})
