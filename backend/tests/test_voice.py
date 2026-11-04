import struct
import httpx
import pytest
from fastapi import HTTPException
from foxory import voice

def wav(seconds=1.0,rate=16000,channels=1,bits=16,fmt=1):
 data=b'\0\0'*int(rate*seconds)*channels
 header=struct.pack('<4sI4s4sIHHIIHH4sI',b'RIFF',36+len(data),b'WAVE',b'fmt ',16,fmt,channels,rate,rate*channels*bits//8,channels*bits//8,bits,b'data',len(data))
 return header+data

def test_only_16k_mono_pcm_wav_is_accepted():
 assert voice.check_wav(wav(2.5))==2.5
 for bad,code in [(b'OggS'+b'\0'*60,415),(wav(rate=44100),415),(wav(channels=2),415),(wav(bits=8),415),(wav(fmt=3),415),(wav(0),422)]:
  with pytest.raises(HTTPException) as e:voice.check_wav(bad)
  assert e.value.status_code==code

class FakeWhisper:
 calls=[]
 def __init__(self,*a,**kw):pass
 async def __aenter__(self):return self
 async def __aexit__(self,*a):pass
 async def get(self,url):return httpx.Response(200,request=httpx.Request('GET',url))
 async def post(self,url,files=None,data=None):
  FakeWhisper.calls.append((url,files['file'][1][:4],data))
  return httpx.Response(200,json={'text':' Hello from\n the microphone. '},request=httpx.Request('POST',url))

async def test_status_and_transcription(client,monkeypatch):
 monkeypatch.setattr(voice,'WHISPER_URL','')
 assert (await client.get('/api/voice/status')).json()['available'] is False
 assert (await client.post('/api/voice/transcribe',files={'file':('a.wav',wav(),'audio/wav')})).status_code==503
 monkeypatch.setattr(voice,'WHISPER_URL','http://127.0.0.1:11437');monkeypatch.setattr(voice.httpx,'AsyncClient',FakeWhisper)
 assert (await client.get('/api/voice/status')).json()['available'] is True
 r=await client.post('/api/voice/transcribe',files={'file':('a.wav',wav(1.5),'audio/wav')},data={'language':'ar'})
 assert r.status_code==200 and r.json()=={'text':'Hello from the microphone.','seconds':1.5}
 url,head,data=FakeWhisper.calls[-1]
 assert url.endswith('/inference') and head==b'RIFF' and data['language']=='ar' and data['response_format']=='json'
 assert (await client.post('/api/voice/transcribe',files={'file':('a.wav',wav(),'audio/wav')},data={'language':'../x'})).status_code==422
 assert (await client.post('/api/voice/transcribe',files={'file':('a.wav',wav(301),'audio/wav')})).status_code==413
