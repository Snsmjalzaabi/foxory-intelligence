"""Chat image uploads for local vision models. Images are validated from their headers and never decoded here."""
import base64,hashlib,json,struct
from pathlib import Path
from fastapi import APIRouter,File,HTTPException,UploadFile
from fastapi.responses import FileResponse
from .config import DATA
from .db import Session,Record,get_record,audit,uid

router=APIRouter(prefix='/api/images')
MAX_BYTES=8*1024*1024
MAX_SIDE=8192
MAX_PIXELS=40_000_000
MAX_PER_MESSAGE=4

def dimensions(raw:bytes):
 """Return (mime,width,height) from the file signature and header, or raise ValueError."""
 if raw.startswith(b'\x89PNG\r\n\x1a\n') and raw[12:16]==b'IHDR':
  width,height=struct.unpack('>II',raw[16:24]);return 'image/png',width,height
 if raw.startswith(b'\xff\xd8'):
  i=2
  while i+9<len(raw):
   if raw[i]!=0xff:raise ValueError('Malformed JPEG')
   marker=raw[i+1]
   if marker in (0xd8,0x01) or 0xd0<=marker<=0xd7:i+=2;continue
   length=struct.unpack('>H',raw[i+2:i+4])[0]
   # Start-of-frame markers carry the size; C4/C8/CC are tables, not frames.
   if 0xc0<=marker<=0xcf and marker not in (0xc4,0xc8,0xcc):
    height,width=struct.unpack('>HH',raw[i+5:i+9]);return 'image/jpeg',width,height
   i+=2+length
  raise ValueError('JPEG size not found')
 if raw[:4]==b'RIFF' and raw[8:12]==b'WEBP':
  chunk=raw[12:16]
  if chunk==b'VP8 ' and raw[23:26]==b'\x9d\x01\x2a':
   width,height=struct.unpack('<HH',raw[26:30]);return 'image/webp',width&0x3fff,height&0x3fff
  if chunk==b'VP8L' and raw[20]==0x2f:
   bits=int.from_bytes(raw[21:25],'little');return 'image/webp',(bits&0x3fff)+1,((bits>>14)&0x3fff)+1
  if chunk==b'VP8X':
   return 'image/webp',int.from_bytes(raw[24:27],'little')+1,int.from_bytes(raw[27:30],'little')+1
 raise ValueError('Use a PNG, JPEG or WebP image')

def validate(raw:bytes):
 if len(raw)>MAX_BYTES:raise HTTPException(413,'Images are limited to 8 MiB')
 try:mime,width,height=dimensions(raw)
 except (ValueError,struct.error,IndexError) as e:raise HTTPException(415,str(e) if isinstance(e,ValueError) else 'Unreadable image header')
 if not width or not height or width>MAX_SIDE or height>MAX_SIDE or width*height>MAX_PIXELS:raise HTTPException(422,'Image dimensions are too large (up to 8192 px per side)')
 return mime,width,height

@router.post('',status_code=201)
async def upload(file:UploadFile=File(...)):
 raw=await file.read(MAX_BYTES+1);mime,width,height=validate(raw)
 id=uid();folder=DATA/'uploads';folder.mkdir(exist_ok=True,mode=0o700);dest=folder/id
 dest.write_bytes(raw);dest.chmod(0o600)
 try:
  with Session() as s:
   r=Record(id=id,kind='image',title=Path(file.filename or 'image').name[:250],payload=json.dumps({'mime':mime,'width':width,'height':height,'size':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}))
   s.add(r);audit(s,'image.upload',id);s.commit();return r.public()
 except Exception:
  dest.unlink(missing_ok=True);raise

@router.get('/{id}')
def view(id:str):
 with Session() as s:
  r=get_record(s,id,'image');return FileResponse(DATA/'uploads'/id,media_type=json.loads(r.payload)['mime'],filename=r.title)

def for_message(session,ids):
 """Load images for one chat turn: metadata to store, base64 data for the model."""
 ids=list(dict.fromkeys(ids))
 if len(ids)>MAX_PER_MESSAGE:raise HTTPException(422,'Attach up to four images per message')
 info,data=[],[]
 for id in ids:
  r=get_record(session,id,'image');d=json.loads(r.payload)
  info.append({'id':r.id,'title':r.title,'width':d['width'],'height':d['height']})
  data.append(base64.b64encode((DATA/'uploads'/id).read_bytes()).decode())
 return info,data
