"""Read-only public GitHub snapshots. Never clone, execute code or read SSH keys."""
import asyncio
import base64
import hashlib
import json
from pathlib import PurePosixPath
import re
from urllib.parse import quote
import httpx
from fastapi import APIRouter,HTTPException
from pydantic import BaseModel,ConfigDict,Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from .config import DATA
from .db import Session,Record,audit,now,uid,get_record

router=APIRouter(prefix='/api/repositories')
MAX_FILE=100_000
MAX_TOTAL=600_000
EXTENSIONS={'.md','.txt','.py','.js','.ts','.tsx','.jsx','.json','.toml','.yaml','.yml','.css','.html','.sh','.sql','.go','.rs','.java','.swift','.rb','.cs','.php','.ini'}

class Address(BaseModel):
    model_config=ConfigDict(extra='forbid')
    url:str=Field(min_length=5,max_length=300)
class Import(Address):
    commit:str=Field(pattern=r'^[a-fA-F0-9]{40}$')
    paths:list[str]=Field(min_length=1,max_length=16)

def parse_address(value):
    match=re.fullmatch(r'(?:https://github\.com/|git@github\.com:)([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?',value.strip(),re.I)
    if not match or match[1] in {'.','..'} or match[2] in {'.','..'}:raise HTTPException(422,'Use a GitHub repository HTTPS URL or git@github.com:owner/repository.git address. Only public repositories are supported.')
    return match[1],match[2]

def eligible(path,size):
    p=PurePosixPath(path);parts=p.parts
    if not parts or p.is_absolute() or '..' in parts or '\\' in path or len(path)>300 or not isinstance(size,int) or size<0 or size>MAX_FILE:return False
    if any(part in {'.git','.venv','node_modules','vendor','dist','build','__pycache__'} for part in parts):return False
    if p.name.startswith('.env') and p.name!='.env.example':return False
    if p.name.lower() in {'id_rsa','id_ed25519','credentials','credentials.json'}:return False
    return p.suffix.lower() in EXTENSIONS or p.name.upper() in {'README','LICENSE','NOTICE','DOCKERFILE','MAKEFILE'}

async def github(client,path):
    # Every request is constructed locally under a fixed HTTPS host. No URL,
    # redirect, auth token or filesystem path comes from fetched content.
    try:
        async with client.stream('GET','https://api.github.com'+path,headers={'Accept':'application/vnd.github+json','User-Agent':'FOXORY-Local-Source-Inspector'}) as response:
            if response.status_code==404:raise HTTPException(404,'Public repository or revision unavailable. Private repositories need uploaded source files; FOXORY does not use your SSH credentials.')
            if response.status_code in {403,429}:raise HTTPException(429,'GitHub declined the request or its public API limit was reached. Retry later or upload the source documents.')
            if 300<=response.status_code<400:raise HTTPException(422,'Repository address redirected. Use its current canonical GitHub address.')
            response.raise_for_status();raw=bytearray()
            async for part in response.aiter_bytes():
                raw.extend(part)
                if len(raw)>2_000_000:raise HTTPException(413,'Repository API response exceeds the local size budget.')
        return json.loads(raw)
    except httpx.HTTPError:raise HTTPException(502,'GitHub could not be reached securely. Check your connection and retry.')
    except (ValueError,TypeError):raise HTTPException(502,'GitHub returned an invalid response.')

async def inventory(client,owner,name,commit=None):
    prefix='/repos/'+quote(owner,safe='')+'/'+quote(name,safe='')
    metadata=await github(client,prefix)
    revision=await github(client,prefix+'/commits/'+quote(commit or metadata.get('default_branch','HEAD'),safe=''))
    sha=revision.get('sha','')
    if not re.fullmatch('[a-f0-9]{40}',sha):raise HTTPException(502,'Invalid repository revision.')
    tree=await github(client,prefix+'/git/trees/'+sha+'?recursive=1')
    if tree.get('truncated') or len(tree.get('tree',[]))>5000:raise HTTPException(413,'This repository is too large for a complete local file listing. Upload selected source files instead.')
    files=[{'path':x['path'],'size':x['size'],'sha':x['sha']} for x in tree.get('tree',[]) if x.get('type')=='blob' and isinstance(x.get('path'),str) and eligible(x['path'],x.get('size')) and re.fullmatch('[a-f0-9]{40}',str(x.get('sha','')))]
    preferred={'readme.md':0,'architecture.md':1,'backend/pyproject.toml':2,'frontend/package.json':3,'backend/foxory/main.py':4,'backend/foxory/inference.py':5}
    files.sort(key=lambda x:(preferred.get(x['path'].lower(),10),x['path']))
    return {'owner':owner,'name':name,'url':'https://github.com/'+owner+'/'+name,'commit':sha,'branch':metadata.get('default_branch'),'description':str(metadata.get('description') or '')[:2000],'license':(metadata.get('license') or {}).get('spdx_id'),'eligible_files':files,'total_tree_entries':len(tree.get('tree',[]))}

@router.post('/preview')
async def preview(body:Address):
    owner,name=parse_address(body.url)
    async with httpx.AsyncClient(timeout=15,follow_redirects=False,trust_env=False) as client:return await inventory(client,owner,name)

@router.get('')
def snapshots():
    with Session() as s:return [r.public() for r in s.scalars(select(Record).where(Record.kind=='repository').order_by(Record.created_at.desc()))]

@router.post('/import',status_code=201)
async def import_sources(body:Import):
    owner,name=parse_address(body.url)
    if len(set(body.paths))!=len(body.paths):raise HTTPException(422,'Choose each source file once.')
    async with httpx.AsyncClient(timeout=15,follow_redirects=False,trust_env=False) as client:
        info=await inventory(client,owner,name,body.commit)
        available={f['path']:f for f in info['eligible_files']}
        if any(path not in available for path in body.paths):raise HTTPException(422,'A selected file is missing, too large or unsupported at this revision.')
        if sum(available[path]['size'] for path in body.paths)>MAX_TOTAL:raise HTTPException(413,'Selected files exceed the 600 KB import budget.')
        slots=asyncio.Semaphore(3)
        async def read(path):
            async with slots:
                meta=available[path]
                blob=await github(client,'/repos/'+quote(owner,safe='')+'/'+quote(name,safe='')+'/git/blobs/'+meta['sha'])
                try:
                    if blob.get('encoding')!='base64':raise ValueError()
                    raw=base64.b64decode(''.join(blob['content'].split()),validate=True)
                    if len(raw)>MAX_FILE or len(raw)!=meta['size'] or '\x00' in raw.decode('utf-8'):raise ValueError()
                    # Bind the saved bytes to the Git tree's immutable blob ID.
                    if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=meta['sha']:raise ValueError()
                    return path,raw,raw.decode('utf-8')
                except (ValueError,KeyError,UnicodeError):raise HTTPException(422,'Selected file is not valid bounded UTF-8 source: '+path)
        contents=await asyncio.gather(*(read(path) for path in body.paths))
    folder=DATA/'uploads';folder.mkdir(exist_ok=True,mode=0o700);created=[]
    key=hashlib.sha256((owner.lower()+'/'+name.lower()+'@'+info['commit']+':'+json.dumps(sorted(body.paths))).encode()).hexdigest()
    try:
        with Session() as s:
            docs=[];manifest=[]
            for path,raw,text in contents:
                doc_key='repo:'+hashlib.sha256((owner.lower()+'/'+name.lower()+'@'+info['commit']+':'+path).encode()).hexdigest()
                row=s.scalar(select(Record).where(Record.kind=='document',Record.dedupe_key==doc_key))
                if row is None:
                    id=uid();dest=folder/id;dest.write_bytes(raw);dest.chmod(0o600);created.append(dest)
                    source={'repository':owner+'/'+name,'commit':info['commit'],'path':path,'url':info['url']+'/blob/'+info['commit']+'/'+quote(path,safe='/'),'sha256':hashlib.sha256(raw).hexdigest()}
                    row=Record(id=id,kind='document',dedupe_key=doc_key,title=(owner+'/'+name+'/'+path+' @ '+info['commit'][:7])[:300],payload=json.dumps({'text':text,'size':len(raw),'characters':len(text),'source_repository':source}));s.add(row);s.flush();audit(s,'repository.document',id,repository=owner+'/'+name,path=path,commit=info['commit'])
                else:
                    saved=json.loads(row.payload)
                    if hashlib.sha256(saved.get('text','').encode()).hexdigest()!=hashlib.sha256(raw).hexdigest():raise HTTPException(409,'Saved source integrity check failed; restore or remove the affected imported document before re-importing.')
                    if not (folder/row.id).is_file():
                        (folder/row.id).write_bytes(raw);(folder/row.id).chmod(0o600)
                docs.append(row.id);manifest.append({'document_id':row.id,'path':path,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
            row=s.scalar(select(Record).where(Record.kind=='repository',Record.dedupe_key==key))
            payload={k:info[k] for k in ['owner','name','url','commit','branch','description','license','total_tree_entries']}
            payload.update(document_ids=docs,files=manifest,imported_at=now(),scope='Selected source files only. Commit history, contributors, other files and runtime behavior have not been inspected.')
            if row is None:row=Record(kind='repository',dedupe_key=key,title=owner+'/'+name+' @ '+info['commit'][:7],payload=json.dumps(payload));s.add(row);s.flush()
            else:row.payload=json.dumps(payload)
            audit(s,'repository.import',row.id,commit=info['commit'],files=len(docs));s.commit();return row.public()
    except Exception as error:
        for path in created:path.unlink(missing_ok=True)
        if isinstance(error,IntegrityError):raise HTTPException(409,'This snapshot changed concurrently. Retry the same import; existing source documents will be reused.')
        raise

@router.get('/{id}')
def snapshot(id:str):
    with Session() as s:
        row=get_record(s,id,'repository');value=row.public();ids=value['data']['document_ids']
        value['data']['available_document_ids']=[r.id for r in s.scalars(select(Record).where(Record.kind=='document',Record.id.in_(ids)))]
        return value

@router.get('/{id}/files/{document_id}')
def source_file(id:str,document_id:str):
    with Session() as s:
        snapshot=get_record(s,id,'repository')
        if document_id not in json.loads(snapshot.payload).get('document_ids',[]):raise HTTPException(404,'File is not in this snapshot')
        return get_record(s,document_id,'document').public()
