import asyncio
import json
import os
from pathlib import Path
import httpx
from .config import OLLAMA_URL

async def models():
    async with httpx.AsyncClient(timeout=5, trust_env=False) as c:
        r = await c.get(f"{OLLAMA_URL}/api/tags")
        r.raise_for_status()
        return r.json().get("models", [])

def thread_budget():
    try:
        quota,period=Path('/sys/fs/cgroup/cpu.max').read_text().split()
        detected=max(1,int(quota)//int(period)) if quota!='max' else min(4,os.cpu_count() or 1)
    except (OSError,ValueError):detected=min(4,os.cpu_count() or 1)
    return max(1,min(16,int(os.getenv('FOXORY_INFERENCE_THREADS',str(detected)))))

inference_lock = asyncio.Semaphore(1)

async def stream(model, messages, temperature=0.7, context=4096, max_output=2048):
    async with inference_lock:
        async for item in _stream(model, messages, temperature, context, max_output):
            yield item

async def _stream(model, messages, temperature=0.7, context=4096, max_output=2048):
    async with httpx.AsyncClient(timeout=httpx.Timeout(180, connect=5), trust_env=False) as c:
        async with c.stream("POST", f"{OLLAMA_URL}/api/chat", json={"model":model,"messages":messages,"stream":True,"keep_alive":"2m","options":{"temperature":temperature,"num_ctx":context,"num_predict":max_output,"num_thread":thread_budget()}}) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if line:
                    data = json.loads(line)
                    if data.get("error"): raise RuntimeError(data["error"])
                    yield data

def background_limits():
    context=max(1024,min(16384,int(os.getenv('FOXORY_BACKGROUND_CONTEXT','4096'))))
    output=max(64,min(2048,int(os.getenv('FOXORY_BACKGROUND_OUTPUT','512'))))
    return context,min(output,context//2)

async def complete(model, messages):
    result = ""
    context,output=background_limits()
    async for event in stream(model, messages, context=context,max_output=output): result += event.get("message", {}).get("content", "")
    return result
