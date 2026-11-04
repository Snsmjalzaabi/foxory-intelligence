"""Task-aware local routing. Scores are transparent heuristics, not quality benchmarks."""
import asyncio,json,re
import httpx
from fastapi import HTTPException
from . import inference,model_registry,model_catalog,model_eval
GIB=1024**3

def category(prompt,history=(),project_kind=None,mode='chat',task=None):
 if task:return task
 def detect(text):
  if re.search(r'\b(code|coding|debug|bug|python|javascript|typescript|html|css|sql|react|api|script|repository|refactor|program|web app|website|build.*app|app.*build|stack trace|csv export)\b|```|برمج|كود|تطبيق|موقع',text):return 'coding'
  if re.search(r'\b(analy[sz]e|reason|compare|trade.?offs|research|strategy|solve|proof|mathemat|calculate|complex|business plan)\b|حلل|قارن|استراتيج',text):return 'reasoning'
  if re.search(r'\b(chapter|novel|story|manuscript|rewrite|proofread|translate|translation|poem|email|copywriting|draft|write)\b|رواية|فصل|ترجم|اكتب',text):return 'writing'
  return None
 text=prompt.lower().strip();direct=detect(text)
 if direct:return direct
 if mode in {'research','documents'}:return 'reasoning'
 follow=len(text.split())<=18 and bool(re.search(r'\b(yes|it|this|that|continue|go ahead|add|change|fix|again|same|what about|also)\b|اكمل|كمل|عدله',text))
 if follow:
  for m in reversed(history[-6:]):
   if m.get('role')=='user':
    previous=detect(m.get('content','')[-1800:].lower())
    if previous:return previous
 return 'writing' if project_kind=='writing' else 'chat'

def complexity(prompt):
 if len(prompt)>600 or re.search(r'\b(deep|thorough|architecture|complete|complex|optimi[sz]e|multi|full|debug)\b',prompt,re.I):return 'deep'
 if len(prompt)<120 and not re.search(r'\b(build|write|implement|create|solve|compare)\b',prompt,re.I):return 'quick'
 return 'standard'

def score(model,kind,observations,effort='standard'):
 name=model['name'].lower();size=model.get('size',0)/GIB
 known=model_catalog.strengths(model['name']);caps=model.get('capabilities') or []
 code='coding' in known or any(x in name for x in ['coder','codestral','starcoder','codegemma','codeqwen','codellama','devstral','granite-code'])
 # Reported thinking support and catalogue roles generalize beyond the name list.
 reasoning='reasoning' in known or 'thinking' in caps or any(x in name for x in ['qwen3','deepseek-r1','qwq','reason','phi4-mini','cogito','magistral'])
 value=0
 if kind=='coding':value+=60 if code else 18 if reasoning else 0
 elif kind=='reasoning':value+=50 if reasoning else -15 if code else 10
 elif kind=='writing':value+=25 if not code and not reasoning else 12 if reasoning else -25
 else:value+=20 if not code and not reasoning else -10 if code else 0
 # Avoid maximum-size-by-default; prefer interactive local weights within each task family.
 value-=min(size,100)*1.5
 if not size:value-=8
 if effort!='quick':
  params=re.search(r'(\d+(?:\.\d+)?)\s*[bB]',str(model.get('details',{}).get('parameter_size','')))
  if params:value+=min(float(params[1]),14)*(2 if effort=='deep' else 1.2)
 speeds=[x['tokens_per_second'] for x in observations if x.get('model')==model['name'] and isinstance(x.get('tokens_per_second'),(int,float)) and x['tokens_per_second']>0 and x.get('output_tokens',0)>=16]
 if speeds:value+=min(5,sum(speeds)/len(speeds)/10)
 if model.get('completion_supported') is True:value+=5
 # Measured results on this PC outweigh name-based guesses: 50% is neutral, 0% and 100% move it 40 points.
 measured=model_eval.quality(model['name'],kind)
 if measured is not None:value+=(measured-0.5)*80
 return round(value,3)

async def choose(prompt,*,requested='auto',history=(),project_kind=None,mode='chat',context=4096,task=None):
 if requested!='auto':
  from .providers import PREFIX,CONTEXT
  effective=min(context,CONTEXT) if requested.startswith(PREFIX) else context
  return {'model':requested,'automatic':False,'category':category(prompt,history,project_kind,mode,task),'reason':'Your manual model selection applies to this turn and its new actions.'+(' Context reduced to the configured CPU runtime limit.' if effective<context else ''),'context':effective,'basis':'manual override'}
 try:installed=await inference.models()
 except (httpx.HTTPError,OSError):raise HTTPException(503,'Local model inventory is unavailable. Check Ollama and try again.')
 catalog=await model_registry.catalog(installed,endpoint=inference.OLLAMA_URL)
 from . import providers
 from .ai_runtime import policy,busy,BACKGROUND
 strategy=policy().mode
 cpu_busy=not BACKGROUND.get() and busy('llama.cpp')
 choices=[m for m in catalog if providers.available(providers.backend(m['name'])) and m.get('completion_supported') is not False and not re.search(r'embed|embedding|rerank|bge-|e5-',m['name'],re.I)]
 if not choices:raise HTTPException(422,'No installed text-generation model is available. Install one in Settings; embedding models cannot answer chat.')
 kind=category(prompt,history,project_kind,mode,task);effort=complexity(prompt)
 if kind=='vision':
  choices=[m for m in choices if 'vision' in (m.get('capabilities') or []) or 'vision' in model_catalog.strengths(m['name'])]
  if not choices:raise HTTPException(422,'No installed model can read images. Install one such as gemma3:4b from Settings → Recommended local models.')
 from .local_runtime import recent
 observations=list(recent)
 budget=model_catalog.memory_budget()
 def policy_score(m):
  value=score(m,kind,observations,effort)
  if m.get('lightweight'):
   if strategy=='quality':value-=30
   elif strategy=='balanced' and cpu_busy:value-=12
   elif strategy=='eco' and effort!='deep' and kind in {'chat','writing'}:value+=20
  return value
 ranked=sorted(choices,key=lambda m:(-policy_score(m),m['name']))
 estimate=lambda m:model_catalog.required_bytes(m.get('size',0),context)
 fitting=[m for m in ranked if not budget or estimate(m)<=budget]
 # Prefer reported full context support, then unknown support, before explicitly smaller windows.
 pool=fitting or sorted(ranked,key=lambda m:(m.get('size',0),m['name']))
 matching=[m for m in pool if not m.get('context_length') or m['context_length']>=context]
 selected=(matching or pool)[0]
 effective=min(context,selected.get('context_length') or context)
 reason={'coding':'Coding task: prefer an installed code-specialized model.','reasoning':'Analysis task: prefer an installed reasoning-oriented model.','writing':'Writing task: prefer a general language model.','chat':'Conversation: prefer an interactive general model.','vision':'Image attached: only models that report image input are considered.'}[kind]
 if cpu_busy and not selected.get('lightweight') and kind=='chat':reason+=' The CPU companion is busy; a larger available model avoids its current queue.'
 if selected.get('lightweight'):reason+=' Lightweight CPU runtime; no GPU residency required.'
 if strategy!='balanced':reason+=' '+strategy.title()+' AI policy applied.'
 if budget:reason+=' Estimated model/context memory fit considered.'
 if model_eval.quality(selected['name'],kind) is not None:reason+=f" Measured {kind if kind!='vision' else 'chat'} quality on this PC: {int(model_eval.quality(selected['name'],kind)*100)}%."
 if not fitting:reason+=' No model fits the available memory estimate; chose the smallest installed completion model. It may still be slow.'
 if effective<context:reason+=' Context reduced to the model’s reported limit.'
 return {'model':selected['name'],'automatic':True,'category':kind,'complexity':effort,'provider':selected.get('provider','ollama'),'strategy':strategy,'reason':reason,'context':effective,'basis':'Installed capability metadata, task/name heuristics, model size and available timing/memory observations; not a measured task-quality ranking.','alternatives':[m['name'] for m in (matching or pool) if m['name']!=selected['name'] and (not m.get('context_length') or m['context_length']>=effective)][:3]}
