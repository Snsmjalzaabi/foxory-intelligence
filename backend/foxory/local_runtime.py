"""Local service health and installation-scoped inference preferences. No prompt logging."""
import asyncio
from collections import deque
import json
import os
from pathlib import Path
import secrets
import time
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, model_validator
from typing import Literal
from sqlalchemy import text
import httpx
from .config import DATA, OLLAMA_URL, SEARXNG_URL
from .db import Session, audit

router=APIRouter(prefix='/api/local-runtime')
recent=deque(maxlen=20)

class Preferences(BaseModel):
    model_config=ConfigDict(extra='forbid')
    keep_alive_minutes: Literal[0,2,5,15,30] = 15
    thinking: bool = False
    background_context: Literal[2048,4096,8192] = 4096
    background_output: Literal[256,512,1024,2048] = 1024
    @model_validator(mode="after")
    def budget(self):
        if self.background_output > self.background_context // 2:raise ValueError("Research output budget must be at most half the context window")
        return self


def preferences():
    try:return Preferences.model_validate_json((DATA/'inference-preferences.json').read_text())
    except (OSError,ValueError):return Preferences()


def record_metrics(model, event):
    def number(key):return max(0,int(event.get(key) or 0))
    try:
        duration=number('eval_duration')/1e9
        recent.append({'model':model,'at':time.time(),'total_seconds':round(number('total_duration')/1e9,2),'load_seconds':round(number('load_duration')/1e9,2),'prompt_seconds':round(number('prompt_eval_duration')/1e9,2),'output_tokens':number('eval_count'),'tokens_per_second':round(number('eval_count')/duration,1) if duration else None})
    except (TypeError,ValueError):pass

@router.put('/preferences')
def save(body:Preferences, request:Request):
    actor=request.state.identity
    if actor['role']!='admin' or actor['id'] not in {'bootstrap','initial-administrator'}:
        raise HTTPException(403,'Only the installation administrator can change inference settings')
    path=DATA/'inference-preferences.json';temporary=path.with_name('.preferences-'+secrets.token_hex(8))
    try:
        fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as stream:stream.write(body.model_dump_json())
        os.replace(temporary,path)
    finally:temporary.unlink(missing_ok=True)
    with Session() as s:audit(s,'inference.preferences','installation',**body.model_dump());s.commit()
    return body.model_dump()

@router.get('')
async def status():
    async with httpx.AsyncClient(timeout=3,trust_env=False) as client:
        async def fetch(url):
            try:
                response=await client.get(url);response.raise_for_status();return response
            except (httpx.HTTPError,ValueError):return None
        version,loaded,search=await asyncio.gather(fetch(OLLAMA_URL+'/api/version'),fetch(OLLAMA_URL+'/api/ps'),fetch(SEARXNG_URL+'/') if SEARXNG_URL else asyncio.sleep(0,result=None))
    try:
        with Session() as s:s.execute(text('SELECT 1'))
        database=True
    except Exception:database=False
    try:models=[{'name':m.get('name'),'size':m.get('size',0),'size_vram':m.get('size_vram',0)} for m in loaded.json().get('models',[])] if loaded is not None else []
    except (ValueError,TypeError,AttributeError):models=[]
    return {'database':database,'ollama':version is not None,'search':search is not None,'search_provider':'SearXNG' if SEARXNG_URL else 'Wikipedia','loaded_models':models,'preferences':preferences().model_dump(),'recent':list(reversed(recent))}

class Measure(BaseModel):
    model_config=ConfigDict(extra='forbid')
    model:str=__import__('pydantic').Field(min_length=1,max_length=100)
    action:Literal['warm','benchmark']='warm'
@router.post('/measure')
async def measure(body:Measure,request:Request):
    if request.state.identity['role']!='admin' or request.state.identity['id'] not in {'bootstrap','initial-administrator'}:raise HTTPException(403,'Installation administrator required')
    from . import inference,model_registry
    try:
        installed=await inference.models()
        if body.model not in {x['name'] for x in installed}:raise HTTPException(422,'Choose an installed model')
        await model_registry.require(body.model,'completion',endpoint=OLLAMA_URL)
        start=time.monotonic();final={}
        from .providers import PREFIX
        if body.action=='warm' and not body.model.startswith(PREFIX):
            async with inference.inference_lock,httpx.AsyncClient(timeout=180,trust_env=False) as client:
                r=await client.post(OLLAMA_URL+'/api/generate',json={'model':body.model,'prompt':'','stream':False,'keep_alive':str(preferences().keep_alive_minutes)+'m','options':{'num_ctx':2048,'num_predict':0}});r.raise_for_status();final=r.json()
        else:
            async for event in inference.stream(body.model,[{'role':'user','content':'Reply with exactly READY.'}],temperature=0,context=2048,max_output=32):
                if event.get('done'):final=event
        duration=float(final.get('eval_duration') or 0)/1e9
        result={'model':body.model,'action':body.action,'elapsed_seconds':round(time.monotonic()-start,2),'load_seconds':round(float(final.get('load_duration') or 0)/1e9,2),'output_tokens':int(final.get('eval_count') or 0),'tokens_per_second':round(int(final.get('eval_count') or 0)/duration,1) if duration else None,'done_reason':final.get('done_reason'),'meaning':'Measured local connectivity/load/generation; not task-quality verification.'}
        with Session() as s:
            from .db import Record
            s.add(Record(kind='model_measure',title=body.model,payload=json.dumps(result)))
            audit(s,'model.measure',body.model,measurement=body.action);s.commit()
        return result
    except (httpx.HTTPError,model_registry.CapabilityError):raise HTTPException(503,'Local model measurement failed; check model availability and service health')
