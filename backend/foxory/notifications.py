"""Notifications derived from the caller's tasks, plus optional push to a self-hosted ntfy server."""
import asyncio,json,logging,os
from datetime import datetime,timedelta,timezone
import httpx
from fastapi import APIRouter,Request
from sqlalchemy import select
from .config import DATA
from .db import Session,Record,now
from .scope import system_scope

router=APIRouter(prefix='/api/notifications')
log=logging.getLogger(__name__)
# Set only in the private .env by the owner; a self-hosted ntfy topic URL keeps pushes on your network.
NTFY_URL=os.getenv('FOXORY_NTFY_URL','').strip()
NOTIFY={'completed','failed','awaiting_approval','cancelled'}
STATE=DATA/'notify-state.json'

def origin(d):
 if d.get('schedule_id'):return 'schedule'
 if d.get('automation'):return 'automation'
 return 'task'

def entry(row,d):
 summary=d.get('error') if d.get('status')=='failed' else (d.get('result') or '') if d.get('status')=='completed' else 'Waiting for your approval' if d.get('status')=='awaiting_approval' else ''
 return {'id':row.id,'title':row.title,'status':d['status'],'origin':origin(d),'at':row.updated_at,'summary':str(summary)[:160]}

@router.get('')
def listing(request:Request):
 """The caller's tasks that finished, failed or need approval in the last seven days, newest first."""
 me=request.state.identity['id'];since=(datetime.now(timezone.utc)-timedelta(days=7)).isoformat();result=[]
 with Session() as s:
  for row in s.scalars(select(Record).where(Record.kind=='job',Record.updated_at>=since).order_by(Record.updated_at.desc()).limit(300)):
   d=json.loads(row.payload)
   if d.get('status') in NOTIFY and d.get('creator_id')==me:result.append(entry(row,d))
   if len(result)>=30:break
 return {'items':result,'push':bool(NTFY_URL)}

async def push_pending():
 """Send title and status only (never task content) for scheduled and automated work that finished."""
 if not NTFY_URL:return 0
 try:last=json.loads(STATE.read_text())['pushed_until']
 except (OSError,ValueError,KeyError):
  # First run: start from now so older history is not pushed, and remember that point.
  last=now();STATE.write_text(json.dumps({'pushed_until':last}));STATE.chmod(0o600);return 0
 sent,newest=0,last
 with system_scope(),Session() as s:
  rows=[(r.title,r.updated_at,json.loads(r.payload)) for r in s.scalars(select(Record).where(Record.kind=='job',Record.updated_at>last).order_by(Record.updated_at).limit(50))]
 async with httpx.AsyncClient(timeout=10,trust_env=True) as client:
  for title,at,d in rows:
   if d.get('status') in NOTIFY and origin(d)!='task':
    label={'completed':'finished','failed':'failed','awaiting_approval':'needs your approval','cancelled':'was cancelled'}[d['status']]
    try:(await client.post(NTFY_URL,content=f'{title[:120]} {label}.'.encode(),headers={'Title':'FOXORY','Tags':'fox'})).raise_for_status();sent+=1
    except httpx.HTTPError as e:log.warning('ntfy push failed: %s',type(e).__name__);break
   newest=max(newest,at)
 # Progress is saved up to the last item handled, so a failed push is retried and none repeats.
 STATE.write_text(json.dumps({'pushed_until':newest}));STATE.chmod(0o600)
 return sent

async def push_loop():
 while NTFY_URL:
  try:await push_pending()
  except Exception:log.exception('notification push loop error')
  await asyncio.sleep(30)
