"""Single worker, durable step checkpoints, bounded attempts, optimistic claims."""
import asyncio
import json
import logging
from sqlalchemy import select, update
from .scope import workspace_id, system_scope, actor_id
from .db import Session, Record, now, audit
from .inference import complete
from .research import search, evidence_prompt, validate_citations
log = logging.getLogger("foxory.worker")

async def execute_step(data):
    from .intelligence import research_step,council_step
    if data['type']=='research':return await research_step(data)
    if data['type']=='council':return await council_step(data)
    data['result']=await complete(data['models'][0],[{'role':'system','content':data.get('instructions','Draft only. No tools or external actions are available.')},{'role':'user','content':data['prompt']}])
    data.update(status='completed',step=data.get('step',0)+1)
    return data

async def run_one():
    token=workspace_id.set('__unauthorized__')
    actor_token=actor_id.set('worker')
    try:return await _run_one()
    finally:workspace_id.reset(token);actor_id.reset(actor_token)

async def _run_one():
    with system_scope(), Session() as s:
        jobs = s.scalars(select(Record).where(Record.kind=="job").order_by(Record.created_at)).all()
        for job in jobs:
            data = json.loads(job.payload)
            if data.get("status") != "queued": continue
            original = job.payload
            from datetime import datetime,timedelta,timezone
            budget=data.get('budget',{})
            data.setdefault('deadline_at',(datetime.now(timezone.utc)+timedelta(seconds=budget.get('max_seconds',900))).isoformat())
            used=data.setdefault('used',{'searches':0,'pages':0,'model_calls':0})
            stage=data.get('stage','plan')
            operation='searches' if stage=='search' and not data.get('document_only') else 'pages' if stage=='read' and data.get('pending_urls') else 'model_calls' if stage in {'plan','compare','write'} or data['type']!='research' else None
            exhausted=data['deadline_at']<now() or operation=='searches' and used.get('searches',0)>=budget.get('max_searches',4) or operation=='pages' and used.get('pages',0)>=budget.get('max_pages',6)
            # Move to synthesis rather than dispatching beyond network budgets.
            if exhausted and data['deadline_at']>=now() and data['type']=='research':
                data['stage']='compare' if stage!='compare' else 'write';operation='model_calls'
            if data['deadline_at']<now():
                data.update(status='failed',error='Research wall-clock budget exhausted')
                job.payload=json.dumps(data);s.commit();continue
            if operation:used[operation]=used.get(operation,0)+1
            data.update(status="running", started_at=now())
            claim = json.dumps(data)
            claimed = s.execute(update(Record).where(Record.id==job.id, Record.payload==original).values(payload=claim, updated_at=now())).rowcount
            s.commit()
            if not claimed: continue
            id = job.id
            workspace=job.workspace
            break
        else: return False
    workspace_id.set(workspace)
    actor_id.set(data.get('creator_id','legacy'))
    try:
        from .db import Membership
        creator=data.get('creator_id')
        if creator and creator!='bootstrap':
            with Session() as s:
                member=s.get(Membership,(workspace,creator))
                if not member or member.role not in {'admin','editor'}:raise PermissionError('Job creator no longer has execution permission')
        step_task = asyncio.create_task(asyncio.wait_for(execute_step(dict(data)), timeout=240))
        try:
            while not step_task.done():
                await asyncio.wait({step_task}, timeout=0.2)
                with Session() as s:
                    current = s.get(Record,id)
                    if current is None or current.payload != claim:
                        step_task.cancel()
                        try: await step_task
                        except asyncio.CancelledError: pass
                        return True
            result = step_task.result()
        finally:
            if not step_task.done():
                step_task.cancel()
                try: await step_task
                except asyncio.CancelledError: pass
        if result["status"] == "running": result["status"] = "queued"
        result["error"] = None
    except Exception as e:
        log.warning("Job step failed: %s", type(e).__name__)
        result = dict(data, status="failed", error=f"{type(e).__name__}: inference or search failed; check service configuration", attempts=data.get("attempts",0)+1)
    with Session() as s:
        # Cancellation/pause takes precedence over a late inference result.
        changed = s.execute(update(Record).where(Record.id==id, Record.payload==claim).values(payload=json.dumps(result), updated_at=now())).rowcount
        if changed: audit(s, "job."+result["status"], id, step=result.get("step",0))
        s.commit()
    return True

async def worker():
    # Interrupted calls are replayed from the last completed checkpoint (read-only inference only).
    with system_scope(), Session() as s:
        for job in s.scalars(select(Record).where(Record.kind=="job")):
            data = json.loads(job.payload)
            if data.get("status") == "running":
                data["status"] = "queued"
                job.payload = json.dumps(data)
        s.commit()
    while True:
        try:
            if not await run_one(): await asyncio.sleep(1)
        except asyncio.CancelledError: raise
        except Exception:
            log.exception("Worker failure")
            await asyncio.sleep(3)
