"""Workspace-scoped chunk retrieval, with optional local Ollama embedding vectors."""
import hashlib
import json
import math
import re
import httpx
from .config import OLLAMA_URL
from .db import Session,Record
from sqlalchemy import select

def chunks(text:str,size:int=1000):
    for offset in range(0,len(text),size):yield offset,text[offset:offset+1400]

async def embed(model:str,texts:list[str]):
    from .inference import inference_lock
    from .model_registry import require
    await require(model,'embedding',endpoint=OLLAMA_URL)
    async with inference_lock, httpx.AsyncClient(timeout=90,trust_env=False) as client:
        response=await client.post(OLLAMA_URL+'/api/embed',json={'model':model,'input':texts,'truncate':True,'keep_alive':'0'})
        response.raise_for_status();vectors=response.json()['embeddings']
        if len(vectors)!=len(texts) or any(not v or len(v)>8192 or not all(isinstance(n,(int,float)) and math.isfinite(n) for n in v) for v in vectors):raise ValueError('Invalid embedding response')
        return vectors

def cosine(a,b):
    if len(a)!=len(b):return 0.
    return sum(x*y for x,y in zip(a,b))/max(1e-12,math.sqrt(sum(x*x for x in a)*sum(y*y for y in b)))

async def index_document(record:Record,model:str):
    data=json.loads(record.payload);parts=list(chunks(data['text']))
    if len(parts)>200:raise ValueError('Embedding index budget: at most 200 chunks per document')
    vectors=[]
    for i in range(0,len(parts),8):vectors.extend(await embed(model,[text for _,text in parts[i:i+8]]))
    data['embedding_index']={'model':model,'text_hash':hashlib.sha256(data['text'].encode()).hexdigest(),'chunks':[{'offset':offset,'vector':v} for (offset,_),v in zip(parts,vectors)]}
    return data

async def document_evidence(query:str,ids:list[str]|None=None,model:str|None=None,limit:int=6):
    from .documents import retrieve
    with Session() as s:
        records=list(s.scalars(select(Record).where(Record.kind=='document')))
    if ids is not None:records=[r for r in records if r.id in ids]
    if model:
        vector=(await embed(model,[query]))[0];found=[]
        for r in records:
            d=json.loads(r.payload);index=d.get('embedding_index',{})
            if index.get('model')!=model or index.get('text_hash')!=hashlib.sha256(d['text'].encode()).hexdigest():continue
            for part in index['chunks']:
                text=d['text'][part['offset']:part['offset']+1400]
                found.append({'document_id':r.id,'title':r.title,'offset':part['offset'],'text':text,'score':cosine(vector,part['vector']),'retrieval':'local_embedding'})
        found=sorted(found,key=lambda x:x['score'],reverse=True)[:limit]
    else:found=retrieve(records,query,limit)
    for i,item in enumerate(found):
        item.update(id=i+1,url='/api/documents/'+item['document_id']+'/download',evidence_type='document_excerpt',content_hash=hashlib.sha256(item['text'].encode()).hexdigest(),retrieval=item.get('retrieval','keyword'))
    return found
