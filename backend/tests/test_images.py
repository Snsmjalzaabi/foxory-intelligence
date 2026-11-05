import base64,io,json,struct,zlib
import pytest
from fastapi import HTTPException
from foxory import inference,model_registry,maintenance
from foxory.images import dimensions,validate

def png(width=4,height=3):
 ihdr=struct.pack('>IIBBBBB',width,height,8,2,0,0,0)
 chunk=lambda kind,data:struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))
 return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',ihdr)+chunk(b'IDAT',zlib.compress(b'\0'*(width*3+1)*height))+chunk(b'IEND',b'')

def jpeg(width=640,height=480):
 app0=b'\xff\xe0'+struct.pack('>H',16)+b'JFIF\0'+b'\x01\x01\0\0\x01\0\x01\0\0'
 sof=b'\xff\xc0'+struct.pack('>HBHHB',11,8,height,width,1)+b'\x01\x11\0'
 return b'\xff\xd8'+app0+b'\xff\xc4'+struct.pack('>H',3)+b'\0'+sof+b'\xff\xd9'

def test_headers_are_parsed_without_decoding():
 assert dimensions(png(4,3))==('image/png',4,3)
 assert dimensions(jpeg(640,480))==('image/jpeg',640,480)
 vp8x=b'RIFF'+b'\0'*4+b'WEBPVP8X'+b'\0'*8+(1023).to_bytes(3,'little')+(767).to_bytes(3,'little')
 assert dimensions(vp8x)==('image/webp',1024,768)
 bits=(99)|(49<<14)
 vp8l=b'RIFF'+b'\0'*4+b'WEBPVP8L'+b'\0'*4+b'\x2f'+bits.to_bytes(4,'little')
 assert dimensions(vp8l)==('image/webp',100,50)
 for bad in [b'GIF89a'+b'\0'*30,b'plain text',b'<svg xmlns="http://www.w3.org/2000/svg"/>']:
  with pytest.raises(HTTPException) as e:validate(bad)
  assert e.value.status_code==415
 with pytest.raises(HTTPException) as e:validate(png(9000,10))
 assert e.value.status_code==422
 with pytest.raises(HTTPException) as e:validate(b'\x89PNG'+b'\0'*(8*1024*1024))
 assert e.value.status_code==413

async def upload(client,raw=None,name='photo.png'):
 r=await client.post('/api/images',files={'file':(name,raw or png(),'image/png')});assert r.status_code==201,r.text;return r.json()

async def test_upload_view_and_delete(client):
 row=await upload(client)
 assert row['kind']=='image' and row['data']['width']==4 and row['data']['mime']=='image/png'
 view=await client.get('/api/images/'+row['id'])
 assert view.status_code==200 and view.content==png() and view.headers['content-type']=='image/png'
 assert (await client.post('/api/images',files={'file':('x.png',b'not an image','image/png')})).status_code==415
 assert (await client.delete('/api/records/'+row['id'])).status_code==204
 assert (await client.get('/api/images/'+row['id'])).status_code==404

def inventory(monkeypatch,models):
 async def installed():return models
 async def catalog(values,**kw):return values
 monkeypatch.setattr(inference,'models',installed);monkeypatch.setattr(model_registry,'catalog',catalog);monkeypatch.setattr(maintenance,'state',lambda:{})

async def test_image_routes_to_vision_model_and_is_sent_once(client,monkeypatch):
 inventory(monkeypatch,[{'name':'qwen3:8b','size':5*1024**3,'completion_supported':True},{'name':'gemma3:4b','size':3*1024**3,'completion_supported':True,'capabilities':['completion','vision']}])
 calls=[]
 async def stream(model,messages,*a,**kw):
  calls.append((model,messages));yield {'message':{'content':'A small test image.'},'done':True}
 monkeypatch.setattr(inference,'chat_stream',stream)
 row=await upload(client)
 conv=(await client.post('/api/records/conversation',json={'title':'Vision'})).json()['id']
 r=await client.post('/api/conversations/'+conv+'/chat',json={'content':'What is in this picture?','image_ids':[row['id']],'use_workspace_context':False})
 assert r.status_code==200,r.text
 model,messages=calls[-1]
 assert model=='gemma3:4b' and messages[-1]['images']==[base64.b64encode(png()).decode()]
 saved=(await client.get('/api/conversations/'+conv+'/messages')).json()
 # Images belong to the user's message, not the reply.
 assert saved[0]['metadata']['images'][0]['title']=='photo.png' and 'images' not in saved[-1]['metadata']
 # A follow-up without images does not resend the old image.
 await client.post('/api/conversations/'+conv+'/chat',json={'content':'Thanks, hi','use_workspace_context':False})
 model,messages=calls[-1]
 assert not any('images' in m for m in messages)
 # A non-vision model is never chosen while an image is attached.
 inventory(monkeypatch,[{'name':'qwen3:1.7b','size':1*1024**3,'completion_supported':True},{'name':'gemma3:4b','size':3*1024**3,'completion_supported':True,'capabilities':['completion','vision']}])
 await client.post('/api/conversations/'+conv+'/chat',json={'content':'Hi, quick look?','image_ids':[row['id']],'use_workspace_context':False})
 assert calls[-1][0]=='gemma3:4b'
 # Regenerating the image turn keeps its image.
 assert (await client.post('/api/conversations/'+conv+'/chat',json={'content':'x','regenerate':True,'use_workspace_context':False})).status_code==200

async def test_images_need_a_vision_model_and_chat_mode(client,monkeypatch):
 inventory(monkeypatch,[{'name':'qwen3:8b','size':5*1024**3,'completion_supported':True,'capabilities':['completion']}])
 row=await upload(client)
 conv=(await client.post('/api/records/conversation',json={'title':'Vision'})).json()['id']
 r=await client.post('/api/conversations/'+conv+'/chat',json={'content':'Describe','image_ids':[row['id']]})
 assert r.status_code==422 and 'gemma3:4b' in r.text
 async def inspect(model,**kw):return {'capabilities':['completion'],'capability_status':'reported'}
 monkeypatch.setattr(model_registry,'inspect',inspect)
 r=await client.post('/api/conversations/'+conv+'/chat',json={'content':'Describe','model':'qwen3:8b','image_ids':[row['id']]})
 assert r.status_code==422 and 'cannot read images' in r.text
 r=await client.post('/api/conversations/'+conv+'/chat',json={'content':'Describe','model':'llama.cpp/qwen2.5-1.5b-instruct-q4_k_m','image_ids':[row['id']]})
 assert r.status_code==422 and 'cannot read images' in r.text
 r=await client.post('/api/conversations/'+conv+'/chat',json={'content':'Describe','model':'qwen3:8b','mode':'research','image_ids':[row['id']]})
 assert r.status_code==422
 assert (await client.get('/api/conversations/'+conv+'/messages')).json()==[]
 r=await client.post('/api/conversations/'+conv+'/chat',json={'content':'Describe','image_ids':[row['id']]*1+['a','b','c','d']})
 assert r.status_code==422
