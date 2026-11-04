"""A small local quality check per task type. Answers are checked by rules, never by another model."""
import asyncio,json,re,time
from fastapi import APIRouter,HTTPException,Request
from . import inference
from .config import DATA
from .db import now

router=APIRouter(prefix='/api/models/quality')
RESULTS=DATA/'model-quality.json'
# Two short, automatically checkable questions per routing category.
CASES=[
 ('chat','Reply with exactly one word: ready',lambda a:re.fullmatch(r'\W*ready\W*',a.strip(),re.I) is not None),
 ('chat','What is the capital of Japan? Answer in one word.',lambda a:'tokyo' in a.lower() and len(a)<60),
 ('reasoning','A train leaves at 14:20 and arrives at 16:05. How many minutes is the trip? Answer with just the number.',lambda a:re.search(r'\b105\b',a) is not None and not re.search(r'\b(95|115|145)\b',a)),
 ('reasoning','All bloops are razzies and all razzies are lazzies. Are all bloops lazzies? Answer yes or no.',lambda a:re.match(r'\W*yes\b',a.strip(),re.I) is not None),
 ('coding','Write a Python function named add that returns the sum of its two arguments. Reply with only the code.',lambda a:re.search(r'def\s+add\s*\(\s*\w+[^,)]*,\s*\w+[^)]*\)[^:]*:[\s\S]*return\s+\w+\s*\+\s*\w+',a) is not None),
 ('coding','What does this Python print? print(sorted([3, 1, 2])[-1]) Answer with just the output.',lambda a:re.fullmatch(r'\W*3\W*',a.strip().strip('`')) is not None),
 ('writing',"Rewrite in formal English, one sentence: 'gonna be late, sorry'",lambda a:'gonna' not in a.lower() and 'late' in a.lower() and len(a)<240),
 ('writing','Translate into Arabic: Thank you very much',lambda a:re.search('شكر',a) is not None),
]
state={'running':False,'model':None,'done':0,'total':0,'error':None}
_cache={'mtime':None,'data':{}}
_task=None  # kept so the running check is not garbage-collected

def load():
 """Saved results, re-read only when the file changes (routing calls this for every reply)."""
 try:mtime=RESULTS.stat().st_mtime
 except OSError:return {}
 if _cache['mtime']!=mtime:
  try:_cache.update(mtime=mtime,data=json.loads(RESULTS.read_text()))
  except (OSError,ValueError):return {}
 return _cache['data']

def quality(model,category):
 """Measured share of passed checks for a category (vision uses chat), or None if not measured."""
 entry=load().get(model);bucket='chat' if category=='vision' else category
 return entry['categories'].get(bucket) if entry and bucket in entry.get('categories',{}) else None

async def evaluate(models):
 results=dict(load());state.update(running=True,done=0,total=len(models)*len(CASES),error=None)
 try:
  for model in models:
   state['model']=model;passed={};total={};seconds=0.0
   for category,prompt,check in CASES:
    started=time.monotonic();answer=''
    try:
     async for event in inference.stream(model,[{'role':'user','content':prompt}],temperature=0,context=2048,max_output=200):answer+=event.get('message',{}).get('content','')
    except Exception:answer=''
    seconds+=time.monotonic()-started
    # Thinking models may prefix hidden reasoning; only the final answer is checked.
    answer=re.sub(r'<think>[\s\S]*?</think>','',answer).strip()
    total[category]=total.get(category,0)+1;passed[category]=passed.get(category,0)+bool(answer and check(answer))
    state['done']+=1
   results[model]={'categories':{c:round(passed[c]/total[c],2) for c in total},'passed':sum(passed.values()),'total':sum(total.values()),'seconds':round(seconds,1),'measured_at':now()}
   RESULTS.write_text(json.dumps(results,indent=1));RESULTS.chmod(0o600)
 except Exception as e:state['error']=type(e).__name__
 finally:state.update(running=False,model=None)

def owner(request):
 if request.state.identity['id'] not in {'initial-administrator','bootstrap'}:raise HTTPException(403,'Installation owner required')

@router.get('')
def results(): return {'results':load(),'status':state,'cases':len(CASES)}

@router.post('',status_code=202)
async def start(request:Request):
 owner(request)
 if state['running']:raise HTTPException(409,'A quality check is already running')
 try:installed=await inference.models()
 except Exception:raise HTTPException(503,'Local models are unavailable')
 from .model_registry import catalog
 models=[m['name'] for m in await catalog(installed,endpoint=inference.OLLAMA_URL) if m.get('completion_supported') is not False and not re.search(r'embed|rerank',m['name'],re.I)]
 if not models:raise HTTPException(422,'No installed chat model to check')
 global _task
 state.update(running=True,done=0,total=len(models)*len(CASES))
 _task=asyncio.create_task(evaluate(models))
 return {'models':models,'questions':len(CASES)}
