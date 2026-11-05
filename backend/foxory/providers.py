"""One additional trusted local llama.cpp endpoint; no cloud discovery or dynamic executable plugins."""
import json,os,time
import httpx
from urllib.parse import urlsplit
PREFIX='llama.cpp/'
LLAMA_URL=os.getenv('FOXORY_LLAMA_URL','').rstrip('/')
API_KEY=os.getenv('FOXORY_LLAMA_API_KEY','')
CONTEXT=max(2048,min(32768,int(os.getenv('FOXORY_LLAMA_CONTEXT','8192'))))
MODEL_BYTES=int(os.getenv('FOXORY_LLAMA_MODEL_BYTES','1117320736'))
ALIAS=os.getenv('FOXORY_LLAMA_MODEL','qwen2.5-1.5b-instruct-q4_k_m')
if LLAMA_URL:
 p=urlsplit(LLAMA_URL)
 if p.scheme!='http' or p.hostname not in {'127.0.0.1','localhost','::1','llama'} or p.username or p.password or p.query or p.fragment or p.path:raise ValueError('FOXORY_LLAMA_URL must be a trusted local HTTP origin')
circuits={}
def backend(model):return 'llama.cpp' if model.startswith(PREFIX) else 'ollama'
def available(name):return circuits.get(name,{}).get('retry_at',0)<=time.monotonic()
def success(name):circuits[name]={'failures':0,'retry_at':0}
def failure(name):
 d=circuits.setdefault(name,{'failures':0,'retry_at':0});d['failures']+=1
 if d['failures']>=3:d['retry_at']=time.monotonic()+30
async def models():
 if not LLAMA_URL or not available('llama.cpp'):return []
 try:
  async with httpx.AsyncClient(timeout=2,trust_env=False) as c:
   r=await c.get(LLAMA_URL+'/v1/models',headers={'Authorization':'Bearer '+API_KEY} if API_KEY else {});r.raise_for_status();data=r.json().get('data',[])
  if not any(x.get('id')==ALIAS for x in data):return []
  return [{'name':PREFIX+ALIAS,'size':MODEL_BYTES,'provider':'llama.cpp','lightweight':True,'details':{'parameter_size':'1.5B','quantization_level':'Q4_K_M'},**metadata()}]
 except (httpx.HTTPError,ValueError):return []
def metadata():return {'capabilities':['completion'],'completion_supported':True,'embedding_supported':False,'capability_status':'reported','source':'Configured local llama.cpp completion adapter; active alias verified via /v1/models','context_length':CONTEXT,'provider':'llama.cpp','lightweight':True}
async def stream(model,messages,temperature,context,max_output,output_format=None):
 if not LLAMA_URL or model!=PREFIX+ALIAS:raise ValueError('This local llama.cpp model is not configured')
 payload={'model':ALIAS,'messages':messages,'stream':True,'stream_options':{'include_usage':True},'temperature':temperature,'max_tokens':min(max_output,CONTEXT//2),'cache_prompt':True}
 if output_format is not None:payload['response_format']={'type':'json_object','schema':output_format}
 started=time.monotonic();tokens=0
 async with httpx.AsyncClient(timeout=httpx.Timeout(180,connect=3),trust_env=False) as c:
  async with c.stream('POST',LLAMA_URL+'/v1/chat/completions',json=payload,headers={'Authorization':'Bearer '+API_KEY} if API_KEY else {}) as r:
   r.raise_for_status()
   async for line in r.aiter_lines():
    if not line.startswith('data: '):continue
    text=line[6:]
    if text=='[DONE]':break
    data=json.loads(text)
    if data.get('error'):raise RuntimeError('Local llama.cpp inference failed')
    if data.get('usage'):tokens=data['usage'].get('completion_tokens',tokens)
    for choice in data.get('choices',[]):
     delta=choice.get('delta',{}).get('content','') or ''
     if delta:yield {'message':{'content':delta}}
     if choice.get('finish_reason'):finish=choice['finish_reason']
 elapsed=time.monotonic()-started
 yield {'done':True,'done_reason':'length' if locals().get('finish')=='length' else 'stop','eval_count':tokens,'total_duration':int(elapsed*1e9),'eval_duration':int(elapsed*1e9),'load_duration':0}
