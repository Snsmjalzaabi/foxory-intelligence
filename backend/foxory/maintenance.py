"""Admin-only fixed-operation queue. Docker is never exposed to the web app."""
import json,os,secrets,sys
from datetime import datetime,timezone
from pathlib import Path
from typing import Literal
from fastapi import APIRouter,HTTPException,Request
from pydantic import BaseModel,ConfigDict,Field
from .config import DATA
from .db import Session,audit,now
from .version import __version__
router=APIRouter(prefix='/api/maintenance')
def folder():
 p=DATA/'maintenance';p.mkdir(exist_ok=True,mode=0o700);return p
def write(path,data):
 temp=path.with_name('.'+secrets.token_hex(12));temp.write_text(json.dumps(data));temp.chmod(0o600);os.replace(temp,path)
def state():
 try:
  value=json.loads((folder()/'state.json').read_text())
  if (datetime.now(timezone.utc)-datetime.fromisoformat(value.get('heartbeat_at','2000-01-01T00:00:00+00:00'))).total_seconds()>45:value['controller']='not_connected'
  return value
 except (OSError,ValueError):return {'controller':'not_connected','releases':[],'operations':[],'backup':None}
class Operation(BaseModel):
 model_config=ConfigDict(extra='forbid')
 action:Literal['backup','verify','activate','check_updates','upgrade','updates_on','updates_off','evolution_test','evolution_install']
 target_version:str|None=Field(default=None,pattern=r'^\d+\.\d+\.\d+$')
 proposal_id:str|None=Field(default=None,pattern='^[a-f0-9]{36}$')
 proposal_hash:str|None=Field(default=None,pattern='^[a-f0-9]{64}$')
 confirmation:str=Field(max_length=100)
@router.get('')
def status(request:Request):
 value=state();value['installed_version']=__version__;value['can_manage']=request.state.identity['id'] in {'bootstrap','initial-administrator'} and request.state.identity['role']=='admin'
 if not value['can_manage']:return {'installed_version':__version__,'controller':value.get('controller'),'can_manage':False,'pending':[],'operations':[],'releases':[],'backup':None}
 value['pending']=[json.loads(p.read_text()) for p in sorted(folder().glob('request-*.json'))[:10]]
 return value
@router.post('/operations',status_code=202)
def submit(body:Operation,request:Request):
 actor=request.state.identity
 if actor['id'] not in {'bootstrap','initial-administrator'} or actor['role']!='admin':raise HTTPException(403,'Installation administrator required')
 if body.confirmation!=body.action.upper()+(' '+str(body.target_version) if body.action=='activate' else ''):raise HTTPException(422,'Confirm the exact maintenance action')
 value=state()
 if value.get('controller')!='connected':raise HTTPException(409,'Local maintenance controller is not connected. Start the controller on this computer.')
 if body.action=='activate' and int((body.target_version or '0').split('.')[0])<6 and int(__version__.split('.')[0])>=6:
  from .scope import system_scope
  from .db import Record
  from sqlalchemy import select,func
  with system_scope(),Session() as s:private_count=s.scalar(select(func.count()).select_from(Record).where(Record.kind.in_(['chat_learning','chat_review'])))
  if private_count:raise HTTPException(409,'Personal conversational learning requires V6 or newer. A pre-V6 rollback needs a reviewed matching data restore.')
 if body.action=='activate' and body.target_version not in {r['version'] for r in value.get('releases',[]) if r.get('available')}:raise HTTPException(422,'Only a registered local image and verified matching release package can be activated')
 if list(folder().glob('request-*.json')):raise HTTPException(409,'Another maintenance request is queued or running')
 id=secrets.token_hex(16);data={'id':id,'action':body.action,'target_version':body.target_version,'actor_id':actor['id'],'created_at':now(),'status':'queued','epoch':value.get('epoch'),'proposal_id':body.proposal_id,'proposal_hash':body.proposal_hash}
 write(folder()/('request-'+id+'.json'),data)
 with Session() as s:audit(s,'maintenance.request',id,operation=body.action,version=body.target_version);s.commit()
 return data

def host_next():
 for path in sorted(folder().glob('request-*.json')):
  d=json.loads(path.read_text())
  if d['status'] in {'queued','running'}:d['status']='running';write(path,d);return d
 return None
if __name__=='__main__':
 if sys.argv[1:] == ['next']:print(json.dumps(host_next()))
 elif sys.argv[1:] == ['publish']:
  d=json.load(sys.stdin);write(folder()/'state.json',d)
 elif len(sys.argv)==3 and sys.argv[1]=='finish' and __import__('re').fullmatch('[a-f0-9]{32}',sys.argv[2]):(folder()/('request-'+sys.argv[2]+'.json')).unlink(missing_ok=True)
 else:raise SystemExit('Unknown maintenance controller command')
