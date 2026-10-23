import asyncio
import json
import httpx
from .config import OLLAMA_URL

async def models():
    async with httpx.AsyncClient(timeout=5, trust_env=False) as c:
        r = await c.get(f"{OLLAMA_URL}/api/tags")
        r.raise_for_status()
        return r.json().get("models", [])

inference_lock = asyncio.Semaphore(1)

async def stream(model, messages, temperature=0.7, context=4096):
    async with inference_lock:
        async for item in _stream(model, messages, temperature, context):
            yield item

async def _stream(model, messages, temperature=0.7, context=4096):
    async with httpx.AsyncClient(timeout=httpx.Timeout(180, connect=5), trust_env=False) as c:
        async with c.stream("POST", f"{OLLAMA_URL}/api/chat", json={"model":model,"messages":messages,"stream":True,"keep_alive":"2m","options":{"temperature":temperature,"num_ctx":context,"num_predict":2048}}) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if line:
                    data = json.loads(line)
                    if data.get("error"): raise RuntimeError(data["error"])
                    yield data

async def complete(model, messages):
    result = ""
    async for event in stream(model, messages): result += event.get("message", {}).get("content", "")
    return result
