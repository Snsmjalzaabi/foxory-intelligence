"""Keep documents in sync with one read-only folder the owner chose. Files are parsed in the isolated parser."""
import asyncio,hashlib,json,logging,os
from pathlib import Path
from fastapi import APIRouter,HTTPException,Request
from sqlalchemy import select
from .config import DATA,MAX_UPLOAD
from .db import Session,Record,audit,now
from .documents import EXTENSIONS
from .scope import workspace_id,actor_id

router=APIRouter(prefix='/api/watch')
log=logging.getLogger(__name__)
# Compose mounts FOXORY_WATCH_DIR read-only at /watch and sets FOXORY_WATCH_ENABLED=1 only when it is set.
ROOT=Path(os.getenv('FOXORY_WATCH_PATH','/watch')) if os.getenv('FOXORY_WATCH_ENABLED')=='1' else None
WORKSPACE='local'
MAX_FILES=500
status={'enabled':ROOT is not None,'files':0,'last_scan':None,'errors':[]}

def candidates(root:Path):
 """Supported, non-hidden regular files inside root; symlinks are never followed."""
 found={};too_long=0
 for folder,dirs,files in os.walk(root,followlinks=False):
  dirs[:]=sorted(d for d in dirs if not d.startswith('.'))
  for name in sorted(files):
   path=Path(folder)/name
   if name.startswith('.') or path.is_symlink() or not path.is_file() or path.suffix.lower() not in EXTENSIONS:continue
   if len(found)>=MAX_FILES:return found,True,too_long
   rel=path.relative_to(root).as_posix()
   # The record key holds at most 300 characters including the "watch:" prefix.
   if len(rel)>290:too_long+=1
   else:found[rel]=path
 return found,False,too_long

def scan():
 """One sync pass: import new or changed files, update titles, and remove documents whose file is gone."""
 if ROOT is None or not ROOT.is_dir():return status
 from .parsing import isolated_extract
 root=ROOT.resolve();found,capped,too_long=candidates(root)
 errors=[f'{too_long} file(s) skipped: path longer than 290 characters'] if too_long else []
 wt=workspace_id.set(WORKSPACE);at=actor_id.set('watcher')
 try:
  with Session() as s:
   existing={r.dedupe_key[6:]:r for r in s.scalars(select(Record).where(Record.kind=='document',Record.dedupe_key.like('watch:%')))}
   for rel,path in found.items():
    row=existing.get(rel);info=path.stat();old=json.loads(row.payload) if row else {}
    if row and old.get('mtime')==info.st_mtime and old.get('size')==info.st_size:continue
    if info.st_size>MAX_UPLOAD:errors.append(f'{rel}: larger than 10 MiB');continue
    raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
    if row and old.get('sha256')==digest:old.update(mtime=info.st_mtime);row.payload=json.dumps(old);continue
    try:text=isolated_extract(path.name,raw)
    except HTTPException as e:errors.append(f'{rel}: {e.detail}');continue
    if not row:row=Record(kind='document',title=path.name[:250],dedupe_key='watch:'+rel);s.add(row);s.flush()
    row.payload=json.dumps({'text':text,'size':len(raw),'characters':len(text),'source':'watch','path':rel,'sha256':digest,'mtime':info.st_mtime});row.updated_at=now()
    folder=DATA/'uploads';folder.mkdir(exist_ok=True,mode=0o700);(folder/row.id).write_bytes(raw);(folder/row.id).chmod(0o600)
    audit(s,'document.watch_import',row.id)
   for rel,row in existing.items():
    if rel not in found and not capped:
     (DATA/'uploads'/row.id).unlink(missing_ok=True);s.delete(row);audit(s,'document.watch_remove',row.id)
   s.commit()
 finally:workspace_id.reset(wt);actor_id.reset(at)
 if capped:errors.append(f'Only the first {MAX_FILES} files are synced; removals are paused until the folder is smaller')
 status.update(files=len(found),last_scan=now(),errors=errors[:20])
 return status

async def watch_loop():
 while ROOT is not None:
  try:await asyncio.to_thread(scan)
  except Exception:log.exception('watched folder scan failed')
  await asyncio.sleep(60)

@router.get('/status')
def watch_status(request:Request):
 if request.state.identity['workspace_id']!=WORKSPACE:return {'enabled':False,'workspace':WORKSPACE}
 return {**status,'workspace':WORKSPACE}
