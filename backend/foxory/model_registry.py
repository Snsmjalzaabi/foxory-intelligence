"""Bounded Ollama capability metadata; unknown never means verified support."""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import httpx

CATALOG_SECONDS = 3.0
MAX_INSPECTIONS = 32
_cache: dict[tuple[str, str], tuple[float, str | None, dict[str, Any]]] = {}


class CapabilityError(ValueError):
    pass


def clear() -> None:
    _cache.clear()


def unknown() -> dict[str, Any]:
    return {'capabilities':None, 'completion_supported':None, 'embedding_supported':None,
            'capability_status':'unknown', 'source':'Ollama metadata unavailable or not reported; support is unknown'}


async def inspect(model: str, *, endpoint: str, digest: str | None = None,
                  refresh: bool = False) -> dict[str, Any]:
    key = (endpoint, model)
    previous = _cache.get(key)
    if previous and not refresh and previous[0] > time.monotonic() and (digest is None or digest==previous[1]):
        return dict(previous[2])
    result = unknown()
    try:
        async with asyncio.timeout(3), httpx.AsyncClient(timeout=3, trust_env=False) as client:
            async with client.stream('POST',endpoint+'/api/show',json={'model':model,'verbose':False}) as response:
                response.raise_for_status();payload=bytearray()
                async for chunk in response.aiter_bytes():
                    payload.extend(chunk)
                    if len(payload)>2_000_000:raise ValueError('Metadata budget')
                data = json.loads(payload)
        caps = data.get('capabilities') if isinstance(data, dict) else None
        if isinstance(caps, list) and caps and len(caps)<=32 and all(isinstance(c,str) and len(c)<=100 for c in caps):
            result = {'capabilities':caps, 'completion_supported':'completion' in caps,
                      'embedding_supported':'embedding' in caps, 'capability_status':'reported',
                      'details':data.get('details',{}) if isinstance(data.get('details',{}),dict) else {},
                      'source':'Ollama /api/show; reported capability is not a quality benchmark'}
    except (httpx.HTTPError, ValueError, TypeError, TimeoutError):
        pass  # Older/unavailable inspection must not make tags or core startup fail.
    if len(_cache)>=128 and key not in _cache:
        _cache.pop(next(iter(_cache)))
    _cache[key] = (time.monotonic()+(30 if result['capability_status']=='reported' else 5),digest,result)
    return dict(result)


async def catalog(models: list[dict[str, Any]], *, endpoint: str) -> list[dict[str, Any]]:
    results = [{**model,**unknown()} for model in models]
    slots = asyncio.Semaphore(4)
    async def one(index: int) -> None:
        async with slots:
            model = models[index]
            metadata = await inspect(model['name'],endpoint=endpoint,digest=model.get('digest'))
            # Tag details include size/quantization; show details supplement them.
            results[index] = {**model,**metadata,'details':{**model.get('details',{}),**metadata.get('details',{})}}
    tasks = [asyncio.create_task(one(i)) for i in range(min(len(models),MAX_INSPECTIONS))]
    if tasks:
        try:
            await asyncio.wait(tasks,timeout=CATALOG_SECONDS)
        finally:
            for task in tasks:
                if not task.done():task.cancel()
            await asyncio.gather(*tasks,return_exceptions=True)
    return results


async def require(model: str, capability: str, *, endpoint: str) -> None:
    metadata = await inspect(model,endpoint=endpoint)
    if metadata['capability_status']=='reported' and capability not in metadata['capabilities']:
        raise CapabilityError(f'The selected model does not report {capability} support. Choose a compatible local model in Settings.')
