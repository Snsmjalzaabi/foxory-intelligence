import asyncio
from .version import __version__
import contextlib
import csv
import io
import json
import logging
import re
import secrets
import hashlib
import os
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import StreamingResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import select, func, delete, update, text
from sqlalchemy.exc import IntegrityError
import httpx
from . import inference
from .config import TOKEN, DATA, MAX_UPLOAD
from .auth import router as auth_router, identity
from .scope import workspace_id, actor_id
from .db import Session, Record, Message, Audit, audit, get_record, now, uid
from .documents import extract, retrieve
from .parsing import isolated_extract
from .knowledge import document_evidence, index_document
from .jobs import worker
from .research import search, gather, evidence_prompt, citation_manifest, grounded_answer
from .reports import report

from .logging_config import configure_logging
configure_logging()

@asynccontextmanager
async def lifespan(app):
    if len(TOKEN) < 24: raise RuntimeError("Set FOXORY_TOKEN to a random secret of at least 24 characters")
    # Migrations are an explicit startup prerequisite, never implicit create_all.
    with Session() as s: s.execute(select(Record).limit(1))
    from .profile import active
    active()  # An invalid profile stops startup with a clear error instead of failing later.
    task = asyncio.create_task(worker())
    yield
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError): await task

active_chats: set[str] = set()
requests_by_client: dict[str, deque] = defaultdict(deque)
# HTTPS addresses a trusted local proxy serves this app on (e.g. Tailscale); set only in the private .env.
PUBLIC_ORIGINS = {o.strip().rstrip('/') for o in os.getenv('FOXORY_PUBLIC_ORIGINS','').split(',') if o.strip().startswith('https://')}

app = FastAPI(title="FOXORY Intelligence", version=__version__, lifespan=lifespan)

app.include_router(auth_router)
from .agent_api import router as agent_router
app.include_router(agent_router)
from .computer_api import router as computer_router
app.include_router(computer_router)
from .business import router as business_router
from .local_runtime import router as runtime_router
app.include_router(business_router)
app.include_router(runtime_router)
from .starter_team import router as starter_router
app.include_router(starter_router)
from .model_catalog import router as model_catalog_router
from .images import router as images_router
app.include_router(images_router)
from .voice import router as voice_router
app.include_router(voice_router)
from .notifications import router as notifications_router
app.include_router(notifications_router)
from .watch import router as watch_router
app.include_router(watch_router)
from .model_eval import router as quality_router
app.include_router(quality_router)
from .profile import router as profile_router
app.include_router(profile_router)
app.include_router(model_catalog_router)
from .repositories import router as repository_router
app.include_router(repository_router)
from .project_spaces import router as spaces_router
app.include_router(spaces_router)
from .maintenance import router as maintenance_router
app.include_router(maintenance_router)
from .skills import router as skills_router
from .autonomy import router as autonomy_router
app.include_router(skills_router)
app.include_router(autonomy_router)

from starlette.middleware.trustedhost import TrustedHostMiddleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=[host.strip() for host in os.getenv("FOXORY_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1],testserver").split(",") if host.strip()])

@app.middleware("http")
async def security(request: Request, call_next):
    path = request.url.path
    if path.startswith("/api/"):
        key = request.client.host if request.client else "unknown"
        times = requests_by_client[key]
        tick = time.monotonic()
        while times and tick-times[0] > 60: times.popleft()
        if len(times) >= 180: return Response("Rate limit exceeded", 429, headers={"Retry-After":"60"})
        times.append(tick)
        if len(requests_by_client) > 1024:
            for stale in [k for k,v in requests_by_client.items() if not v or tick-v[-1] > 60]: del requests_by_client[stale]
        if path in {'/api/auth/login','/api/auth/setup'}:
            attempts=requests_by_client['auth:'+key]
            while attempts and tick-attempts[0]>60:attempts.popleft()
            if len(attempts)>=12:return Response('Login attempt limit exceeded',429,headers={'Retry-After':'60'})
            attempts.append(tick)
        if request.method in {"POST", "PUT", "PATCH"}:
            # Read in bounded chunks, including requests without Content-Length.
            chunks, size = [], 0
            async for chunk in request.stream():
                size += len(chunk)
                if size > MAX_UPLOAD + 100_000: return Response("Request too large", 413)
                chunks.append(chunk)
            request._body = b"".join(chunks)

    scope_token=None
    actor_token=None
    public={"/api/health","/api/ready","/api/auth/status","/api/auth/setup","/api/auth/login"}
    if path.startswith("/api/"):
        origin=request.headers.get('origin')
        if origin and origin.rstrip('/')!=str(request.base_url).rstrip('/') and origin.rstrip('/') not in PUBLIC_ORIGINS:
            return Response('Cross-origin access denied',403)
        if path not in public:
            try:actor=await asyncio.to_thread(identity,request)
            except HTTPException as e:return Response(e.detail,e.status_code)
            request.state.identity=actor
            if request.method not in {'GET','HEAD','OPTIONS'} and actor['role']=='viewer' and path!='/api/auth/logout':
                return Response('Read-only workspace membership',403)
            if request.method not in {'GET','HEAD','OPTIONS'} and (path.startswith('/api/models/') or path.startswith('/api/approvals/')) and (actor['role']!='admin' or path.startswith('/api/models/') and actor['id'] not in {'bootstrap','initial-administrator'}):
                return Response('Workspace or installation administrator required',403)
    if hasattr(request.state,'identity'):
        scope_token=workspace_id.set(request.state.identity['workspace_id'])
        actor_token=actor_id.set(request.state.identity['id'])
    try: response = await call_next(request)
    finally:
        if scope_token is not None: workspace_id.reset(scope_token)
        if actor_token is not None: actor_id.reset(actor_token)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    if path.startswith("/api/"): response.headers["Cache-Control"] = "no-store"
    return response

class Create(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    data: dict = Field(default_factory=dict)

KINDS = {"conversation", "memory", "lead", "project", "agent", "draft"}

def validate_record(kind, body):
    if len(json.dumps(body.data)) > 100_000: raise HTTPException(413, "Record too large")
    if kind == "lead":
        body.data = {k:v for k,v in body.data.items() if k in {"organization","email","website","status","score","notes","follow_up"}}
        if any(not isinstance(v,str) for v in body.data.values()): raise HTTPException(422,"Lead fields must be strings")
        email = body.data.get("email", "")
        if email and (not isinstance(email,str) or len(email)>254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+",email)): raise HTTPException(422,"Invalid email")
        if body.data.get("status", "new") not in {"new","qualified","contacted","won","lost"}: raise HTTPException(422,"Invalid lead status")
    if kind == "agent":
        from .agents import AgentConfig
        from .agent_api import validate_resources
        try:config=AgentConfig.model_validate(body.data)
        except ValueError as e:raise HTTPException(422,str(e))
        with Session() as s:validate_resources(s,config)
        body.data=config.model_dump()
    return body

@app.get("/api/health")
def health(): return {"status":"ok", "version":__version__, "edition":"Community"}

@app.get("/api/ready")
def ready():
    # Liveness stays independent of dependencies. Readiness checks the migrated
    # schema, including accounts, without exposing connection details or data.
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from .db import User
    try:
        root = Path(__file__).resolve().parents[1]
        cfg = Config(str(root / "alembic.ini"))
        cfg.set_main_option("script_location", str(root / "migrations"))
        heads = set(ScriptDirectory.from_config(cfg).get_heads())
        with Session() as s:
            revisions = set(s.execute(text("SELECT version_num FROM alembic_version")).scalars())
            if revisions != heads:
                return Response('{"status":"not_ready"}', 503, media_type="application/json")
            s.execute(select(Record.id).limit(1))
            s.execute(select(User.id).limit(1))
    except Exception:
        return Response('{"status":"not_ready"}', 503, media_type="application/json")
    return {"status": "ready"}

@app.get("/api/overview")
def overview():
    with Session() as s:
        records = s.scalars(select(Record)).all()
        counts = {kind:sum(r.kind==kind for r in records) for kind in ["conversation","document","agent","lead","project","memory"]}
        jobs = [json.loads(r.payload) for r in records if r.kind=="job"]
        counts.update({status:sum(j.get("status")==status for j in jobs) for status in ["queued","running","completed","failed"]})
        counts["pending_approvals"] = sum(r.kind=="approval" and json.loads(r.payload).get("status")=="pending" for r in records)
        return {"counts":counts,"computer_mode":False,"outbound_email":False,"workspace":workspace_id.get()}

@app.get("/api/records/{kind}")
def records(kind: str, q: str = ""):
    if kind not in KINDS | {"document", "job", "approval", "schedule", "agent_memory", "task", "artifact"}: raise HTTPException(404)
    with Session() as s:
        rows = s.scalars(select(Record).where(Record.kind==kind).order_by(Record.updated_at.desc())).all()
        return [r.public() for r in rows if q.lower() in (r.title+" "+r.payload).lower()]

@app.post("/api/records/{kind}", status_code=201)
def create(kind: str, body: Create):
    if kind not in KINDS: raise HTTPException(422, "Unsupported record type")
    body = validate_record(kind, body)
    with Session() as s:
        if kind=="lead":
            key = str(body.data.get("email") or body.title).strip().casefold()
            for old in s.scalars(select(Record).where(Record.kind=="lead")):
                d = json.loads(old.payload)
                if str(d.get("email") or old.title).strip().casefold()==key: raise HTTPException(409,"Duplicate lead")
        r = Record(kind=kind, title=body.title, payload=json.dumps(body.data))
        if kind=="lead": r.dedupe_key=hashlib.sha256(key.encode()).hexdigest()
        s.add(r)
        try:
            s.flush(); audit(s, kind+".create",r.id); s.commit()
        except IntegrityError:
            s.rollback(); raise HTTPException(409,"Duplicate record")
        return r.public()

@app.put("/api/records/{id}")
def edit(id: str, body: Create):
    with Session() as s:
        r = get_record(s,id)
        if r.kind not in KINDS: raise HTTPException(403,"Use dedicated action endpoint")
        body = validate_record(r.kind,body)
        if r.kind=="lead":
            key = str(body.data.get("email") or body.title).strip().casefold()
            for other in s.scalars(select(Record).where(Record.kind=="lead", Record.id!=id)):
                if str(json.loads(other.payload).get("email") or other.title).strip().casefold()==key:
                    raise HTTPException(409,"Duplicate lead")
        if r.kind=="lead": r.dedupe_key=hashlib.sha256(key.encode()).hexdigest()
        r.title, r.payload, r.updated_at = body.title,json.dumps(body.data),now()
        audit(s,r.kind+".update",id)
        try: s.commit()
        except IntegrityError:
            s.rollback(); raise HTTPException(409,"Duplicate record")
        return r.public()

@app.delete("/api/records/{id}", status_code=204)
def remove(id: str, request: Request):
    with Session() as s:
        r = get_record(s,id)
        if r.kind in {"approval", "job", "task", "artifact"}: raise HTTPException(403,"Execution records retained for audit")
        if r.kind=="skill":
            from .skills import delete_skill
            if request.state.identity["role"]!="admin":raise HTTPException(403,"Workspace administrator required")
            delete_skill(s,r);s.commit();return
        if r.kind=="space":
            from .project_spaces import delete_space
            delete_space(s,r);s.commit();return
        if r.kind in {"document","image"}: (DATA / "uploads" / id).unlink(missing_ok=True)
        s.delete(r); audit(s,r.kind+".delete",id); s.commit()

@app.get("/api/conversations/{id}/messages")
def messages(id: str):
    with Session() as s:
        get_record(s,id,"conversation")
        return [m.public() for m in s.scalars(select(Message).where(Message.conversation_id==id).order_by(Message.created_at))]

@app.get('/api/context/preview')
def preview_workspace_context(q:str=''):
    if len(q)>1000:raise HTTPException(422,'Use a context query of at most 1000 characters')
    from .workspace_context import retrieve_context
    return retrieve_context(q)

class Chat(BaseModel):
    content: str = Field(min_length=1, max_length=30000)
    model: str = Field(default="auto",min_length=1,max_length=100)
    mode: Literal["chat","research","documents"] = "chat"
    system: str = Field(default="You are FOXORY, a helpful local AI assistant. Be honest about uncertainty.",max_length=10000)
    temperature: float = Field(default=0.7,ge=0,le=2)
    context: int = Field(default=4096,ge=1024,le=32768)
    max_output: int = Field(default=2048,ge=32,le=2048)
    document_ids: list[str] = Field(default_factory=list,max_length=8)
    image_ids: list[str] = Field(default_factory=list,max_length=4)
    use_workspace_context: bool = True
    regenerate: bool = False
    embedding_model:str|None=Field(default=None,max_length=100)

@app.post("/api/conversations/{id}/chat")
async def chat(id: str, body: Chat, request: Request):
    if id in active_chats: raise HTTPException(409,"Conversation already generating")
    active_chats.add(id)
    try:
        with Session() as s:
            conversation_record=get_record(s,id,"conversation")
            project_id=json.loads(conversation_record.payload).get("space_id")
            if project_id:get_record(s,project_id,"space")
            history = list(s.scalars(select(Message).where(Message.conversation_id==id).order_by(Message.created_at)))
            from .model_routing import choose
            project_data=json.loads(get_record(s,project_id,'space').payload) if project_id else {}
            project_kind=project_data.get('kind')
            if body.regenerate and not body.document_ids:
                previous_user=next((m for m in reversed(history) if m.role=='user'),None)
                if previous_user:
                    previous=json.loads(previous_user.metadata_json)
                    body=body.model_copy(update={'document_ids':[f['id'] for f in previous.get('attachments',[])],'image_ids':body.image_ids or [f['id'] for f in previous.get('images',[])]})
            from .chat_files import attachments
            attached=attachments(s,body.document_ids,project_id,max(200,min(5000,(body.context-min(body.max_output,body.context//2)-256)*2//3)))
            from .images import for_message
            image_info,image_data=for_message(s,body.image_ids)
            if image_info and body.mode!='chat':raise HTTPException(422,'Images can be attached to normal chat messages only')
            route_history=([{'role':'user','content':project_data.get('brief','')[:1500]}] if body.use_workspace_context and project_id else [])+[{'role':m.role,'content':m.content} for m in history]
            route=await choose(body.content,requested=body.model,history=route_history,project_kind=project_kind,mode='documents' if body.document_ids else body.mode,context=body.context,task='vision' if image_info else None)
            if image_info and not route['automatic']:
                try:await inference.model_registry.require(body.model,'vision',endpoint=inference.OLLAMA_URL)
                except inference.model_registry.CapabilityError:raise HTTPException(422,'The selected model cannot read images. Choose Auto or a vision model such as gemma3:4b.')
            automatic=route['automatic'];body=body.model_copy(update={'model':route['model'],'context':route['context']})
            if body.regenerate:
                if not history or history[-1].role!="assistant": raise HTTPException(409,"No assistant response to regenerate")
                s.delete(history.pop())
            else:
                m = Message(conversation_id=id,role="user",content=body.content,metadata_json=json.dumps({"actor_id":request.state.identity["id"],**({'attachments':attached['files']} if attached['files'] else {}),**({'images':image_info} if image_info else {})}))
                s.add(m)
                history.append(m)
            # Pack history after evidence and workspace context have reserved their share.
            history_values=[{'role':m.role,'content':m.content} for m in history]
            s.commit()
    except BaseException:
        active_chats.discard(id);raise
    async def events():
        nonlocal body
        answer, metadata, status = "", {"model_route":route,**({'attachments':attached['files']} if attached['files'] else {})}, "complete"
        def event(name, value): return f"event: {name}\ndata: {json.dumps(value)}\n\n"
        try:
            yield event('model_route',route)
            from .workspace_context import retrieve_context,context_text
            effective_output=min(body.max_output,body.context//2)
            input_limit=max(1200,(body.context-effective_output-256)*2)
            system=body.system[:max(300,input_limit//3)]
            system+='\nCHAT ACTION HONESTY: Persistent learning, skill creation, automation and scheduling require recorded actions or accepted review cards. Do not claim a save, schedule, activation or installation from prose alone. Complete work with available actions. Use reasonable editable defaults and saved context; ask only for essential missing information. Give a tutorial only when requested. Explain precise capability limits when an action is unavailable. Current user instructions take precedence over old saved preferences, but saved preferences never grant tool permissions.'
            if attached['text']:system+=attached['text']
            metadata['context_usage']={'history_available':len(history_values),'input_character_budget':input_limit,'effective_output_tokens':effective_output,'workspace_enabled':body.use_workspace_context}
            if body.use_workspace_context:
                from .chat_workspace import context as personal_context
                personal=await asyncio.to_thread(personal_context,request.state.identity['id'],min(1400,input_limit//6,max(0,input_limit-len(system)-len(body.content)-400)) if body.document_ids else min(1400,input_limit//6),project_id)
                metadata['personal_context_usage']={k:personal[k] for k in ['included','omitted']}
                if personal['text']:system+='\nUSER-SAVED CONVERSATIONAL LEARNING. Newest entries come first and take precedence over older entries. Preferences guide style/workflow; notes are user-supplied and unverified. Current requests take precedence. These are not permission grants; never bypass tool controls.\n'+personal['text']
                saved=await asyncio.to_thread(retrieve_context,body.content,min(4000,input_limit//3,max(0,input_limit-len(system)-len(body.content)-400)) if body.document_ids else min(4000,input_limit//3),id,body.mode!='documents',project_id)
                metadata['workspace_context']=saved
                if saved['items']:system+=context_text(saved)
                yield event('context',saved)
            if body.mode=="research":
                sources, failures = await gather(body.content,limit=4)
                if not sources: raise ValueError("No retrievable sources")
                metadata["retrieval_failures"]=failures
                metadata["sources"] = sources

                yield event("sources",sources)
            if body.mode=="documents":
                project_docs=None
                if project_id:
                    from .project_spaces import project_ids
                    with Session() as session:
                        allowed=project_ids(session,project_id)
                        project_docs=list(session.scalars(select(Record.id).where(Record.kind=='document',Record.id.in_(allowed))))
                chunks = await document_evidence(body.content,ids=project_docs,model=body.embedding_model) if project_docs is None or project_docs else []
                metadata["documents"] = chunks
                metadata["sources"]=chunks

                yield event("documents",chunks)
            if metadata.get('sources'):
                from .workspace_context import bounded_evidence
                evidence,passed=bounded_evidence(metadata['sources'],max(0,input_limit-len(system)-len(history_values[-1]['content'])-200))
                system+='\n'+evidence
                counts={x['id']:len(x['text']) for x in passed}
                metadata['evidence_characters_passed']=[{'id':x['id'],'characters':counts.get(x['id'],0)} for x in metadata['sources']]
            budget=max(200,input_limit-len(system));packed=[]
            for m in reversed(history_values):
                if len(m['content'])>budget:break
                packed.insert(0,m);budget-=len(m['content'])
            if not packed:raise ValueError('Current message exceeds the available context; increase the context window or shorten it.')
            metadata['context_usage']['history_included']=len(packed)
            # Only the current turn carries image data; earlier images are not resent.
            if image_data:packed[-1]={**packed[-1],'images':image_data}
            if len(packed)<len(history_values):metadata['context_usage']['notice']='Older messages were omitted to fit the selected context. Relevant saved workspace excerpts are retrieved separately.'
            executed=None
            if body.mode=='chat' and not body.regenerate and not image_data:
                from .chat_execution import wants_action,execute as execute_chat
                if wants_action(body.content):
                    yield event('delta','Working on it…\n\n')
                    executed=await execute_chat(id,body.content,body.model,request,system,body.use_workspace_context or bool(body.document_ids),auto_model=automatic)
                    if executed:
                        metadata['execution_results']=executed['results']
                        answer=executed['answer']
                        yield event('replace',answer)
                    else:yield event('replace','')
            if not executed and (body.mode=="chat" or metadata.get('sources')):
                async for data in inference.chat_stream(body.model,[{"role":"system","content":system}]+packed,
                                                  body.temperature,body.context,max_output=effective_output,route=route):
                    if data.get('_foxory_fallback_model'):
                        body=body.model_copy(update={'model':data['_foxory_fallback_model']})
                        from .providers import backend
                        route.update(fallback_from=route['model'],provider=backend(body.model),model=body.model,reason=route['reason']+' The first backend failed before output; selected an available fallback.')
                        metadata['model_route']=route;yield event('model_route',route);continue
                    if await request.is_disconnected(): status="stopped"; break
                    delta = data.get("message",{}).get("content","")
                    answer += delta
                    # Grounded modes release prose only after reference checks.
                    if body.mode=="chat": yield event("delta",delta)
                    if data.get("done"):
                        metadata.update({k:data[k] for k in ["prompt_eval_count","eval_count","total_duration","done_reason"] if k in data})
                        if data.get("done_reason")=="length":
                            status="truncated";metadata["warning"]="Reply reached the response budget and may be incomplete. Increase the budget or ask a narrower question."
            if body.mode!="chat":
                answer,verification,mode=grounded_answer(answer,metadata.get('sources',[]),body.content)
                metadata.update(citation_verification=verification,evidence_mode=mode)
                yield event("delta",answer)
        except inference.model_registry.CapabilityError as error:
            status="error"
            yield event("error",str(error))
        except asyncio.CancelledError:
            status="stopped"
            raise
        except Exception as e:
            status="error"
            yield event("error",f"{type(e).__name__}: local inference or search unavailable. Check Settings and service logs.")
        finally:
            active_chats.discard(id)
            metadata.update(status=status,model=body.model,mode=body.mode,actor_id=request.state.identity["id"])
            with Session() as s:
                if s.get(Record,id):
                    s.add(Message(conversation_id=id,role="assistant",content=answer,metadata_json=json.dumps(metadata)))
                    r = s.get(Record,id); r.updated_at=now()
                    s.commit()
        if status=='complete' and body.use_workspace_context:
            try:
                from .chat_reflection import queue as queue_reflection
                await asyncio.to_thread(queue_reflection,id,body.model,request.state.identity['id'])
            except Exception:logging.getLogger('foxory.chat').warning('Learning review could not be queued')
        yield event("done",metadata)
    return StreamingResponse(events(),media_type="text/event-stream")

@app.get("/api/conversations/{id}/export")
def export_chat(id: str):
    with Session() as s:
        r = get_record(s,id,"conversation")
        rows = s.scalars(select(Message).where(Message.conversation_id==id).order_by(Message.created_at)).all()
        content = "# "+r.title+"\n\n"+"\n\n".join("## "+m.role+"\n\n"+m.content for m in rows)
        return Response(content,media_type="text/markdown",headers={"Content-Disposition":'attachment; filename="conversation.md"'})

@app.get("/api/models")
async def list_models():
    from .model_registry import catalog
    try: return {"available":True,"models":await catalog(await inference.models(),endpoint=inference.OLLAMA_URL)}
    except Exception: return {"available":False,"models":[],"error":"Local AI backends unavailable. Check Ollama or the optional llama.cpp runtime."}

@app.get("/api/models/capabilities")
async def capabilities(model: str):
    from .model_registry import inspect
    if not model or len(model)>100:raise HTTPException(422,'Invalid model name')
    return {'model':model,**await inspect(model,endpoint=inference.OLLAMA_URL,refresh=True)}

class ModelAction(BaseModel):
    model: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._:/-]{0,99}$")
    confirmation: str

@app.post("/api/models/pull")
async def pull(body: ModelAction):
    from .providers import PREFIX
    if body.model.startswith(PREFIX):raise HTTPException(422,'The CPU companion uses its pinned host installer, not Ollama downloads')
    if body.confirmation!=body.model: raise HTTPException(422,"Confirm model name; download may use substantial bandwidth and storage")
    async def events():
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(1800,connect=5),trust_env=False) as c:
                async with c.stream("POST",inference.OLLAMA_URL+"/api/pull",json={"name":body.model}) as r:
                    r.raise_for_status()
                    async for line in r.aiter_lines():
                        if line: yield line+"\n"
        except Exception: yield json.dumps({"error":"Model download failed; inspect Ollama logs"})+"\n"
    return StreamingResponse(events(),media_type="application/x-ndjson")

@app.post("/api/models/remove")
async def remove_model(body: ModelAction):
    from .providers import PREFIX
    if body.model.startswith(PREFIX):raise HTTPException(422,'The managed CPU companion is outside Ollama; disable its host service to remove it')
    if body.confirmation!=body.model: raise HTTPException(422,"Type exact model name to confirm deletion")
    async with httpx.AsyncClient(timeout=30,trust_env=False) as c:
        try:
            r = await c.request("DELETE",inference.OLLAMA_URL+"/api/delete",json={"name":body.model});r.raise_for_status()
        except Exception: raise HTTPException(502,"Model removal failed")
    with Session() as s: audit(s,"model.remove",body.model);s.commit()
    return {"removed":body.model}

@app.post("/api/documents",status_code=201)
async def upload(file: UploadFile = File(...)):
    raw = await file.read(MAX_UPLOAD+1)
    if len(raw)>MAX_UPLOAD: raise HTTPException(413,"Upload limit is 10 MiB")
    name = Path(file.filename or "upload.txt").name[:250]
    text = await asyncio.to_thread(isolated_extract,name,raw)
    id = uid(); folder=DATA/"uploads";folder.mkdir(exist_ok=True,mode=0o700)
    dest=folder/id
    dest.write_bytes(raw); dest.chmod(0o600)
    try:
        with Session() as s:
            r = Record(id=id,kind="document",title=name,payload=json.dumps({"text":text,"size":len(raw),"characters":len(text)}))
            s.add(r);audit(s,"document.upload",id);s.commit();return r.public()
    except Exception:
        dest.unlink(missing_ok=True);raise

@app.get("/api/documents/{id}/download")
def download(id: str):
    with Session() as s:
        r=get_record(s,id,"document")
        return FileResponse(DATA/"uploads"/id,filename=r.title,media_type="application/octet-stream")

@app.get("/api/documents/search")
def document_search(q: str):
    with Session() as s: return retrieve(s.scalars(select(Record).where(Record.kind=="document")),q)

class ResearchBudget(BaseModel):
    max_searches:int=Field(default=4,ge=1,le=8)
    max_pages:int=Field(default=6,ge=1,le=12)
    max_seconds:int=Field(default=900,ge=30,le=1800)
    max_input_chars:int=Field(default=28000,ge=4000,le=60000)

class JobCreate(BaseModel):
    type: Literal["research","council","agent"]
    prompt: str = Field(min_length=1,max_length=20000)
    models: list[str] = Field(min_length=1,max_length=4)
    agent_id: str | None = None
    budget:ResearchBudget=Field(default_factory=ResearchBudget)
    document_ids:list[str]=Field(default_factory=list,max_length=20)
    document_only:bool=False
    embedding_model:str|None=Field(default=None,max_length=100)
    parallel:bool=False
    idempotency_key: str = Field(min_length=8,max_length=100)

@app.post("/api/jobs", status_code=201)
async def create_job(body: JobCreate,request:Request):
    from .evidence_policy import repository_review, REPOSITORY_SOURCE_REQUIRED
    if body.type=="council" and repository_review(body.prompt) and not body.document_ids:
        raise HTTPException(422,REPOSITORY_SOURCE_REQUIRED)
    if body.document_only and not body.document_ids:raise HTTPException(422,'Select documents for document-only research')
    if any(not m or len(m)>100 for m in body.models): raise HTTPException(422,"Invalid model name")
    if body.type=="council" and len(set(body.models))<2: raise HTTPException(422,"Council needs at least two distinct models")
    if body.parallel:
        from .resources import parallel_capacity
        capacity=await parallel_capacity(body.models)
        if body.type!='council' or not capacity['parallel_allowed']:raise HTTPException(422,capacity['reason'])
    with Session() as s:
        # Deterministic primary key makes concurrent duplicate submissions impossible.
        import hashlib
        id = hashlib.sha256((workspace_id.get()+":"+body.idempotency_key).encode()).hexdigest()[:36]
        old = s.get(Record,id)
        if old: return old.public()
        for document_id in body.document_ids:get_record(s,document_id,'document')
        data = body.model_dump(); data.update(status="queued",step=0,attempts=0,creator_id=request.state.identity["id"])
        if body.type=="agent":
            from .agent_api import task_data
            data=task_data(s,body.agent_id,body.prompt,request.state.identity['id'])
        r=Record(id=id,kind="job",title=body.prompt[:120],payload=json.dumps(data))
        s.add(r);audit(s,"job.create",id)
        try: s.commit()
        except __import__('sqlalchemy').exc.IntegrityError:
            s.rollback(); return get_record(s,id,"job").public()
        return r.public()

@app.post("/api/jobs/{id}/{action}")
def control_job(id: str,action: Literal["cancel","pause","resume","retry"]):
    with Session() as s:
        r=get_record(s,id,"job");original=r.payload;d=json.loads(original);status=d["status"]
        allowed={"cancel":{"queued","running","paused","failed","awaiting_approval"},"pause":{"queued","running"},"resume":{"paused"},"retry":{"failed"}}
        if status not in allowed[action]: raise HTTPException(409,"Invalid state transition")
        if action=='retry' and d.get('type')=='agent' and d.get('stage')=='done':
            raise HTTPException(409,'Execution ended; create a new task with reviewed inputs and fresh approvals')
        if action=="retry" and d.get("deadline_at",now())<now():raise HTTPException(409,"Wall-clock budget expired; create a new bounded job")
        if action=="retry" and d.get("attempts",0)>=3: raise HTTPException(409,"Retry budget exhausted")
        d["status"]={"cancel":"cancelled","pause":"paused","resume":"queued","retry":"queued"}[action]
        changed=s.execute(update(Record).where(Record.id==id,Record.payload==original).values(payload=json.dumps(d),updated_at=now())).rowcount
        if not changed: raise HTTPException(409,"Task changed; refresh and retry")
        if action=='cancel' and d.get('approval_id'):
            approval=s.get(Record,d['approval_id'])
            if approval:
                a=json.loads(approval.payload)
                if a.get('status') in {'pending','approved'}:
                    a.update(status='revoked',reason='Task cancelled',decided_at=now());approval.payload=json.dumps(a);audit(s,'approval.revoked',approval.id,job_id=id)
        audit(s,"job."+action,id);s.commit();s.refresh(r);return r.public()

@app.get("/api/jobs/{id}/export")
def export_job(id: str,format:Literal["md","pdf","docx","xlsx"]="md"):
    with Session() as s:
        r=get_record(s,id,"job");d=json.loads(r.payload)
        from .evidence_policy import council_export_text
        result=council_export_text(d)
        if d.get('warnings'):result='Report notes:\n'+'\n'.join('- '+str(x) for x in d['warnings'])+'\n\n'+result
        if d.get('model_source_coverage'):result+='\n\nModel source coverage (bounded excerpts):\n'+'\n'.join(str(x['id'])+': '+x.get('title','')+' — '+str(x['characters_in_prompt'])+' characters' for x in d['model_source_coverage'])
        if format!='md':
            content,mime=report(r.title,result,d.get('sources',[]),format)
            return Response(content,media_type=mime,headers={'Content-Disposition':f'attachment; filename="report.{format}"'})
        text="# "+r.title+"\n\n"+result+"\n\n## Retrieved sources\n"+("\n".join(f"[{x['id']}] {x['title']} — {x['url']}" for x in d.get("sources",[])) or "No source material supplied.")
        return Response(text,media_type="text/markdown",headers={"Content-Disposition":'attachment; filename="report.md"'})

@app.post("/api/drafts/{id}/request-approval")
def request_approval(id: str):
    with Session() as s:
        draft=get_record(s,id,"draft")
        existing=s.scalars(select(Record).where(Record.kind=="approval")).all()
        for r in existing:
            d=json.loads(r.payload)
            if d.get("draft_id")==id and d.get("status")=="pending": return r.public()
        r=Record(kind="approval",dedupe_key=id,title=draft.title,payload=json.dumps({"draft_id":id,"snapshot":draft.public(),"status":"pending","action":"review_draft","external_execution":False,"expires_at":(__import__('datetime').datetime.now(__import__('datetime').timezone.utc)+__import__('datetime').timedelta(minutes=15)).isoformat()}))
        s.add(r)
        try: s.flush();audit(s,"approval.request",r.id);s.commit()
        except IntegrityError:
            s.rollback()
            return s.scalar(select(Record).where(Record.kind=="approval",Record.dedupe_key==id)).public()
        return r.public()

@app.post("/api/approvals/{id}/{decision}")
def decide(id: str,decision: Literal["approve","reject"]):
    with Session() as s:
        r=get_record(s,id,"approval");original=r.payload;d=json.loads(original)
        if d["status"]!="pending": raise HTTPException(409,"Already decided")
        if d.get('expires_at','9999')<now():raise HTTPException(409,'Approval expired')
        if d.get('action')=='agent_tool':
            from .agents import fingerprint,config_for
            context=d['context'];job=get_record(s,context['job_id'],'job');j=json.loads(job.payload)
            if j.get('status')!='awaiting_approval' or j.get('approval_id')!=id:raise HTTPException(409,'Task no longer awaits this approval')
            try:cfg=config_for(j,context['effect']['agent_id'])
            except PermissionError:raise HTTPException(409,'Agent configuration changed')
            if fingerprint(context)!=d['context_hash'] or fingerprint(cfg)!=context['agent_config_hash'] or fingerprint(j['plan'])!=context['plan_hash']:raise HTTPException(409,'Stale approval context')
            j.update(status='queued' if decision=='approve' else 'failed',error=None if decision=='approve' else 'User rejected tool action')
            claimed=s.execute(update(Record).where(Record.id==job.id,Record.payload==job.payload).values(payload=json.dumps(j),updated_at=now())).rowcount
            if not claimed:raise HTTPException(409,'Task state changed')
        d.update(status="approved" if decision=="approve" else "rejected",decided_at=now())
        changed=s.execute(update(Record).where(Record.id==id,Record.payload==original).values(payload=json.dumps(d),dedupe_key=None,updated_at=now())).rowcount
        if not changed: raise HTTPException(409,"Approval already changed")
        audit(s,"approval."+decision,id);s.commit();s.refresh(r);return r.public()

@app.get("/api/audit")
def audit_history():
    with Session() as s: return [{"id":r.id,"action":r.action,"target":r.target,"created_at":r.created_at,"detail":json.loads(r.detail)} for r in s.scalars(select(Audit).order_by(Audit.created_at.desc()).limit(200))]

@app.get("/api/leads/export")
def leads_export():
    with Session() as s:
        out=io.StringIO();w=csv.writer(out);w.writerow(["name","organization","email","status","notes"])
        for r in s.scalars(select(Record).where(Record.kind=="lead")):
            d=json.loads(r.payload)
            cells=[r.title]+[str(d.get(k,"")) for k in ["organization","email","status","notes"]]
            w.writerow(["'"+x if x.startswith(("=","+","-","@","\t","\r")) else x for x in cells])
        return Response(out.getvalue(),media_type="text/csv",headers={"Content-Disposition":'attachment; filename="leads.csv"'})

@app.get("/api/workspace/export")
def workspace_export():
    with Session() as s:
        return {"version":1,"exported_at":now(),"records":[r.public() for r in s.scalars(select(Record))],"messages":[dict(conversation_id=m.conversation_id,**m.public()) for m in s.scalars(select(Message))]}

class IndexRequest(BaseModel):
    model:str=Field(min_length=1,max_length=100)

@app.post('/api/documents/{id}/index')
async def build_index(id:str,body:IndexRequest):
    with Session() as s:
        r=get_record(s,id,'document')
        try:data=await index_document(r,body.model)
        except Exception:raise HTTPException(422,'Embedding index failed; select an installed embedding-capable model and check the chunk budget')
        r.payload=json.dumps(data);s.commit()
        return {'document_id':id,'model':body.model,'chunks':len(data['embedding_index']['chunks'])}

@app.get('/api/documents/retrieve')
async def semantic_search(q:str,model:str|None=None):
    return await document_evidence(q,model=model)

@app.get('/api/documents/{id}/export')
def export_document(id:str,format:Literal['pdf','docx','xlsx']):
    with Session() as s:
        r=get_record(s,id,'document');d=json.loads(r.payload)
        content,mime=report(r.title,d['text'],[],format)
        return Response(content,media_type=mime,headers={'Content-Disposition':f'attachment; filename="document.{format}"'})

@app.get('/api/jobs/{id}/citations')
def verify_saved_citations(id:str):
    with Session() as s:
        r=get_record(s,id,'job');d=json.loads(r.payload)
        return citation_manifest(d.get('result',''),d.get('sources',[]))

@app.get('/api/council/resources')
async def council_resources(models:str=''):
    from .resources import parallel_capacity
    return await parallel_capacity([x for x in models.split(',') if x])

from .chat_reflection import router as chat_reflection_router
app.include_router(chat_reflection_router)

from .chat_workspace import router as chat_workspace_router
app.include_router(chat_workspace_router)
from .chat_execution import router as chat_execution_router
app.include_router(chat_execution_router)
from .ai_runtime import router as ai_runtime_router
app.include_router(ai_runtime_router)
from .chat_files import router as chat_files_router
app.include_router(chat_files_router)

from .evolution import router as evolution_router
app.include_router(evolution_router)

from .performance import router as performance_router
app.include_router(performance_router)

from .operations import router as operations_router
app.include_router(operations_router)

static = Path(__file__).resolve().parents[2]/"frontend"/"dist"
if static.exists():
    app.mount("/",StaticFiles(directory=static,html=True),name="frontend")

