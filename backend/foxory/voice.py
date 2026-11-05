"""Local speech-to-text through the optional whisper.cpp service. Audio is never stored or sent off this PC."""
import asyncio,os,struct
import httpx
from fastapi import APIRouter,File,Form,HTTPException,UploadFile

router=APIRouter(prefix='/api/voice')
WHISPER_URL=os.getenv('FOXORY_WHISPER_URL','').rstrip('/')
SAMPLE_RATE=16000
MAX_SECONDS=300
MAX_BYTES=44+SAMPLE_RATE*2*MAX_SECONDS
# One transcription at a time keeps the 2-CPU service responsive.
slot=asyncio.Semaphore(1)

def check_wav(raw:bytes):
 """Accept only 16 kHz mono 16-bit PCM WAV (what the browser recorder produces); return seconds."""
 if len(raw)<44 or raw[:4]!=b'RIFF' or raw[8:12]!=b'WAVE':raise HTTPException(415,'Send a WAV recording')
 i,fmt,size=12,None,None
 while i+8<=len(raw):
  chunk,length=raw[i:i+4],struct.unpack('<I',raw[i+4:i+8])[0]
  if chunk==b'fmt ':fmt=struct.unpack('<HHIIHH',raw[i+8:i+24])
  if chunk==b'data':size=min(length,len(raw)-i-8);break
  i+=8+length+(length&1)
 if not fmt or fmt[0]!=1 or fmt[1]!=1 or fmt[2]!=SAMPLE_RATE or fmt[5]!=16:raise HTTPException(415,'Recording must be 16 kHz mono 16-bit PCM')
 if not size:raise HTTPException(422,'The recording is empty')
 return size/(SAMPLE_RATE*2)

@router.get('/status')
async def status():
 if not WHISPER_URL:return {'available':False,'reason':'Voice is not enabled. Run python3 scripts/foxory_voice.py enable on this PC.'}
 try:
  async with httpx.AsyncClient(timeout=3,trust_env=False) as client:(await client.get(WHISPER_URL+'/health')).raise_for_status()
  return {'available':True,'max_seconds':MAX_SECONDS}
 except httpx.HTTPError:return {'available':False,'reason':'The local voice service is not responding. Check it with python3 scripts/foxory.py status.'}

@router.post('/transcribe')
async def transcribe(file:UploadFile=File(...),language:str=Form('auto',pattern=r'^(auto|[a-z]{2,3})$')):
 if not WHISPER_URL:raise HTTPException(503,'Voice is not enabled on this PC')
 raw=await file.read(MAX_BYTES+1)
 if len(raw)>MAX_BYTES:raise HTTPException(413,'Recordings are limited to five minutes')
 seconds=check_wav(raw)
 async with slot:
  try:
   async with httpx.AsyncClient(timeout=httpx.Timeout(max(60,seconds*4),connect=3),trust_env=False) as client:
    r=await client.post(WHISPER_URL+'/inference',files={'file':('speech.wav',raw,'audio/wav')},data={'response_format':'json','temperature':'0.0','language':language})
    r.raise_for_status();data=r.json()
  except (httpx.HTTPError,ValueError):raise HTTPException(502,'Local transcription failed; check the voice service logs')
 if 'error' in data:raise HTTPException(502,'Local transcription failed: '+str(data['error'])[:200])
 # Whisper separates segments with newlines; a dictated message reads as one paragraph.
 return {'text':' '.join(str(data.get('text','')).split()),'seconds':round(seconds,1)}
