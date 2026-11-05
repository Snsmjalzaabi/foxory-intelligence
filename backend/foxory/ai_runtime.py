"""Installation-wide local AI policy, private counters and foreground-first inference queues."""
import asyncio,json,os,secrets,weakref
from contextvars import ContextVar
from contextlib import asynccontextmanager
from datetime import datetime,timezone,timedelta
from typing import Literal
from fastapi import APIRouter,Request,HTTPException
from pydantic import BaseModel,ConfigDict,Field
from .config import DATA
BACKGROUND=ContextVar('ai_background',default=False)
router=APIRouter(prefix='/api/ai')
class Policy(BaseModel):
 model_config=ConfigDict(extra='forbid')
 mode:Literal['balanced','eco','quality']='balanced'
 background_enabled:bool=True
 background_daily_calls:int=Field(default=200,ge=1,le=10000)
 recover_readonly:bool=True

def policy():
 try:return Policy.model_validate_json((DATA/'ai-policy.json').read_text())
 except (OSError,ValueError):return Policy()
def write(path,data):
 temporary=path.with_name('.'+secrets.token_hex(8));temporary.write_text(json.dumps(data,indent=2));temporary.chmod(0o600);os.replace(temporary,path)
def usage():
 day=datetime.now(timezone.utc).date().isoformat()
 try:d=json.loads((DATA/'ai-usage.json').read_text())
 except (OSError,ValueError):d={}
 return d if d.get('date')==day else {'date':day,'foreground_calls':0,'background_calls':0,'failures':0,'providers':{}}
def record(provider,error=False):
 d=usage();key='background_calls' if BACKGROUND.get() else 'foreground_calls'
 if error:d['failures']=d.get('failures',0)+1
 else:d[key]=d.get(key,0)+1;d.setdefault('providers',{})[provider]=d.get('providers',{}).get(provider,0)+1
 write(DATA/'ai-usage.json',d)
def deferred():
 p=policy()
 return not p.background_enabled or usage().get('background_calls',0)>=p.background_daily_calls
class Deferred(RuntimeError):pass

def admin(request):
 if request.state.identity['role']!='admin' or request.state.identity['id'] not in {'bootstrap','initial-administrator'}:raise HTTPException(403,'Installation administrator required')
@router.put('/policy')
def save(body:Policy,request:Request):
 admin(request)
 from .db import Session,audit
 write(DATA/'ai-policy.json',body.model_dump())
 with Session() as s:audit(s,'ai.policy','installation',**body.model_dump());s.commit()
 notify_work();return body.model_dump()

class Gate:
 def __init__(self):self.condition=asyncio.Condition();self.busy=False;self.foreground=0;self.background=0
 @asynccontextmanager
 async def acquire(self):
  bg=BACKGROUND.get()
  async with self.condition:
   if bg:self.background+=1
   else:self.foreground+=1
   try:await self.condition.wait_for(lambda:not self.busy and (not bg or self.foreground==0));self.busy=True
   finally:
    if bg:self.background-=1
    else:self.foreground-=1
    self.condition.notify_all()
  try:yield
  finally:
   async with self.condition:self.busy=False;self.condition.notify_all()
_gates=weakref.WeakKeyDictionary()
def busy(provider):
 g=_gates.get(asyncio.get_running_loop(),{}).get(provider);return bool(g and g.busy)
def gate(provider):return _gates.setdefault(asyncio.get_running_loop(),{}).setdefault(provider,Gate())
_worker_loop=None;_wake=None
def bind_worker():
 global _worker_loop,_wake
 _worker_loop=asyncio.get_running_loop();_wake=asyncio.Event()
def notify_work():
 if _worker_loop and not _worker_loop.is_closed() and _wake:_worker_loop.call_soon_threadsafe(_wake.set)
async def wait_work(seconds):
 if not _wake:await asyncio.sleep(seconds);return
 try:await asyncio.wait_for(_wake.wait(),seconds)
 except asyncio.TimeoutError:pass
 _wake.clear()
@router.get('/status')
async def status():
 from . import inference,providers
 try:models=await inference.models()
 except Exception:models=[]
 queues={name:{'active':g.busy,'foreground_waiting':g.foreground,'background_waiting':g.background} for name,g in _gates.get(asyncio.get_running_loop(),{}).items()}
 return {'policy':policy().model_dump(),'usage':usage(),'background_deferred':deferred(),'models':[{'name':m['name'],'provider':m.get('provider','ollama'),'lightweight':m.get('lightweight',False),'bytes':m.get('size',0)} for m in models],'providers':{'ollama':{'available':any(not m['name'].startswith(providers.PREFIX) for m in models)},'llama.cpp':{'configured':bool(providers.LLAMA_URL),'available':any(m['name'].startswith(providers.PREFIX) for m in models)}},'queues':queues,'scope':'Installation-wide model inventory and counters only. UTC daily budget; no prompts. Active inference is not preempted. Works while your computer and Docker are running.'}
