"""Conservative, opt-in CPU-memory guard. No GPU-capacity inference is made."""
import os
from pathlib import Path
from . import inference

def available_memory():
    try:
        fields=dict(line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())
        available=int(fields['MemAvailable'].strip().split()[0])*1024
        maximum=Path('/sys/fs/cgroup/memory.max').read_text().strip()
        if maximum!='max':available=min(available,int(maximum)-int(Path('/sys/fs/cgroup/memory.current').read_text()))
        return max(0,available)
    except (OSError,ValueError,KeyError):return 0

async def parallel_capacity(models:list[str]):
    available=available_memory()
    result={'parallel_allowed':False,'available_bytes':available,'max_parallel':2,'reason':'Operator opt-in and conservative memory headroom required; sequential remains default'}
    if os.getenv('FOXORY_ALLOW_PARALLEL_COUNCIL')!='1':return result
    installed={m['name']:m.get('size',0) for m in await inference.models()}
    if not models or any(not installed.get(m) for m in models):return {**result,'reason':'Every selected model must have known installed size'}
    required=sum(sorted((installed[m] for m in models),reverse=True)[:2])*2+4*1024**3
    if available>=max(8*1024**3,required):return {**result,'parallel_allowed':True,'reason':'Operator enabled; conservative CPU memory estimate fits. Inference server concurrency must also be configured.'}
    return {**result,'reason':'Insufficient measured memory headroom; use sequential execution'}
