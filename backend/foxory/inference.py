import asyncio
import json
import os
from pathlib import Path
import httpx
from .config import OLLAMA_URL
from . import model_registry

async def models():
    from . import providers
    async def ollama():
        async with httpx.AsyncClient(timeout=5,trust_env=False) as c:
            r=await c.get(OLLAMA_URL+'/api/tags');r.raise_for_status();return r.json().get('models',[])
    if not providers.LLAMA_URL:return await ollama()
    a,b=await asyncio.gather(ollama(),providers.models(),return_exceptions=True)
    if isinstance(a,Exception) and (isinstance(b,Exception) or not b):raise a
    return ([] if isinstance(a,Exception) else a)+([] if isinstance(b,Exception) else b)

def thread_budget():
    try:
        quota,period=Path('/sys/fs/cgroup/cpu.max').read_text().split()
        detected=max(1,int(quota)//int(period)) if quota!='max' else min(4,os.cpu_count() or 1)
    except (OSError,ValueError):detected=min(4,os.cpu_count() or 1)
    return max(1,min(16,int(os.getenv('FOXORY_INFERENCE_THREADS',str(detected)))))



class LegacyLock:
    """Compatibility for existing Ollama embeddings/measurements and guarded councils."""
    def __init__(self):
        from contextvars import ContextVar
        self.stack=ContextVar('ollama_gate_stack',default=())
    async def __aenter__(self):
        from .ai_runtime import gate
        manager=gate('ollama').acquire();await manager.__aenter__();self.stack.set(self.stack.get()+(manager,));return self
    async def __aexit__(self,*args):
        values=self.stack.get();self.stack.set(values[:-1]);return await values[-1].__aexit__(*args)
inference_lock=LegacyLock()

async def stream(model, messages, temperature=0.7, context=4096, max_output=2048):
    from .ai_runtime import gate
    from .providers import backend
    async with (inference_lock if backend(model)=='ollama' else gate(backend(model)).acquire()):
        async for item in _stream(model, messages, temperature, context, max_output):
            yield item

async def _ollama_stream(model, messages, temperature=0.7, context=4096, max_output=2048, output_format=None):
    await model_registry.require(model,'completion',endpoint=OLLAMA_URL)
    from .local_runtime import preferences, record_metrics
    settings=preferences()
    metadata=await model_registry.inspect(model,endpoint=OLLAMA_URL)
    thinking={'think':settings.thinking} if 'thinking' in (metadata.get('capabilities') or []) else {}
    async with httpx.AsyncClient(timeout=httpx.Timeout(180, connect=5), trust_env=False) as c:
        async with c.stream("POST", f"{OLLAMA_URL}/api/chat", json={**thinking,**({'format':output_format} if output_format is not None else {}),"model":model,"messages":messages,"stream":True,"keep_alive":str(settings.keep_alive_minutes)+"m","options":{"temperature":temperature,"num_ctx":context,"num_predict":max_output,"num_thread":thread_budget()}}) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if line:
                    data = json.loads(line)
                    if data.get("error"): raise RuntimeError(data["error"])
                    if data.get("done"):record_metrics(model,data)
                    yield data

async def _stream(model,messages,temperature=0.7,context=4096,max_output=2048,output_format=None):
    from . import providers
    from .ai_runtime import BACKGROUND,deferred,Deferred,record
    name=providers.backend(model)
    if BACKGROUND.get() and deferred():raise Deferred('Background AI is paused or its UTC daily call budget is exhausted')
    if not providers.available(name):raise httpx.ConnectError('Local backend is cooling down after repeated failures')
    source=providers.stream if name=='llama.cpp' else _ollama_stream
    record(name)
    try:
        async for event in source(model,messages,temperature,context,max_output,output_format):
            if name=='llama.cpp' and event.get('done'):
                from .local_runtime import record_metrics
                record_metrics(model,event)
            yield event
        providers.success(name)
    except (httpx.HTTPError,RuntimeError) as error:
        providers.failure(name);record(name,error=True);raise

async def chat_stream(model,messages,temperature,context,max_output,route):
    candidates=[model]+(route.get('alternatives',[])[:1] if route.get('automatic') else [])
    for index,candidate in enumerate(candidates):
        emitted=False
        try:
            async for data in stream(candidate,messages,temperature,context,max_output=max_output):
                if index and not emitted:yield {'_foxory_fallback_model':candidate}
                if data.get('message',{}).get('content'):emitted=True
                yield data
            return
        except (httpx.HTTPError,RuntimeError,model_registry.CapabilityError):
            if emitted or index==len(candidates)-1:raise

class IncompleteResponse(ValueError):
    def __init__(self, partial):
        super().__init__('Model output reached its token limit. Increase the research/agent response budget in Settings, or narrow the task, then retry.')
        self.partial = partial

def background_limits():
    from .local_runtime import preferences
    settings=preferences()
    return settings.background_context, settings.background_output

async def complete(model, messages, *, context=None, max_output=None):
    result = ""
    default_context,default_output=background_limits()
    context=context or default_context;output=max_output or default_output
    async for event in stream(model, messages, context=context,max_output=output):
        result += event.get("message", {}).get("content", "")
        if event.get("done_reason")=="length":raise IncompleteResponse(result)
    return result

async def structured(model, messages, schema, *, context=None, max_output=None):
    """Ollama structured-output protocol; server still validates every plan."""
    result=''
    default_context,output=background_limits()
    context=context or default_context;output=max_output or output
    from .ai_runtime import gate
    from .providers import backend
    async with (inference_lock if backend(model)=='ollama' else gate(backend(model)).acquire()):
        async for event in _stream(model,messages,temperature=0,context=context,max_output=output,output_format=schema):
            result+=event.get('message',{}).get('content','')
            if event.get('done_reason')=='length':raise IncompleteResponse(result)
    return result
