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
    if data['type']=='agent':
        from .agents import agent_step
        return await agent_step(data)
    data['result']=await complete(data['models'][0],[{'role':'system','content':data.get('instructions','Draft only. No tools or external actions are available.')},{'role':'user','content':data['prompt']}])
    data.update(status='completed',step=data.get('step',0)+1)
    return data

def unchanged_claim(id,claim):
    with Session() as s:
        current=s.get(Record,id)
        return current is not None and current.payload==claim

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
            if data['type']=='agent':
                if 'agent_snapshot' not in data:
                    data.update(status='failed',error='Legacy draft agent task: submit a new task with explicit agent grants');job.payload=json.dumps(data);s.commit();continue
                cfg=data['agent_snapshot']
                target=(data['plan'][data['cursor']].get('agent_id') or data['agent_id']) if stage=='execute' else data['agent_id']
                acting=cfg if target==data['agent_id'] else data['delegates'][target]
                data['active_agent_id']=target
                actor_usage=data.setdefault('agent_usage',{}).setdefault(target,{'model_calls':0,'deadline_at':(datetime.now(timezone.utc)+timedelta(seconds=acting['max_seconds'])).isoformat()})
                if actor_usage['deadline_at']<now():
                    data.update(status='failed',error='Assigned agent wall-clock budget exhausted');job.payload=json.dumps(data);s.commit();continue
                needs_model=stage in {'plan','review','consolidate'} or stage=='execute' and not data['plan'][data['cursor']].get('tool')
                if needs_model:
                    if data.get('agent_model_calls',0)>=cfg['max_model_calls'] or actor_usage['model_calls']>=acting['max_model_calls']:
                        data.update(status='failed',error='Agent model-call budget exhausted');job.payload=json.dumps(data);s.commit();continue
                    data['agent_model_calls']=data.get('agent_model_calls',0)+1
                    actor_usage['model_calls']+=1
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
    working=json.loads(json.dumps(data))
    try:
        from .db import Membership
        creator=data.get('creator_id')
        if creator and creator!='bootstrap':
            with Session() as s:
                member=s.get(Membership,(workspace,creator))
                if not member or member.role not in {'admin','editor'}:raise PermissionError('Job creator no longer has execution permission')
        step_timeout=240
        if data['type']=='agent':
            target=data['active_agent_id'];cfg=data['agent_snapshot'] if target==data['agent_id'] else data['delegates'][target]
            step_timeout=min(cfg['step_timeout'],(datetime.fromisoformat(data['agent_usage'][target]['deadline_at'])-datetime.now(timezone.utc)).total_seconds())
        step_task = asyncio.create_task(asyncio.wait_for(execute_step(working), timeout=max(.1,min(step_timeout,data.get('agent_snapshot',{}).get('step_timeout',240),(datetime.fromisoformat(data["deadline_at"])-datetime.now(timezone.utc)).total_seconds()))))
        try:
            while not step_task.done():
                await asyncio.wait({step_task}, timeout=0.2)
                if not await asyncio.to_thread(unchanged_claim,id,claim):
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
        if data['type']=='agent':result['step_failures']=0
    except Exception as e:
        log.warning("Job step failed: %s", type(e).__name__)
        result = dict(working, status="failed", error=f"{type(e).__name__}: inference, tool or permission validation failed; inspect configuration and task limits", attempts=data.get("attempts",0)+1)
        result.pop('_approval_effect',None)
        if data['type']=='agent':
            if isinstance(e,(PermissionError,ValueError)):result['error_detail']=str(e)[:500]
            result['step_failures']=data.get('step_failures',0)+1
            target=data.get('active_agent_id',data['agent_id']);acting=data['agent_snapshot'] if target==data['agent_id'] else data['delegates'][target]
            if not isinstance(e,PermissionError) and result['step_failures']<=min(data['agent_snapshot']['max_retries'],acting['max_retries']):
                result['status']='queued'
            result.setdefault('timeline',[]).append({'event':'step_error','stage':data.get('stage'),'error_type':type(e).__name__,'at':now()})
    with Session() as s:
        # Cancellation/pause takes precedence over a late inference result.
        if data['type']=='agent':
            current=s.get(Record,id)
            if not current or current.payload!=claim:return True
            try:
                from .agents import commit_agent
                commit_agent(s,id,result)
                s.flush()
            except Exception as e:
                s.rollback()
                result=dict(data,status='failed',error=f'{type(e).__name__}: approval or tool commit rejected')
        changed = s.execute(update(Record).where(Record.id==id, Record.payload==claim).values(payload=json.dumps(result), updated_at=now())).rowcount
        if not changed:
            s.rollback();return True
        if changed:
            audit(s, "job."+result["status"], id, step=result.get("step",0))
            if data['type']=='agent':audit(s,'agent.checkpoint',id,stage=result.get('stage'),cursor=result.get('cursor'),status=result['status'])
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
    import os
    concurrency=max(1,min(2,int(os.getenv('FOXORY_WORKER_CONCURRENCY','1'))))
    async with asyncio.TaskGroup() as group:
        group.create_task(schedule_loop())
        for _ in range(concurrency):group.create_task(worker_loop())

async def schedule_loop():
    from .scheduler import tick
    while True:
        pending=asyncio.create_task(asyncio.to_thread(tick))
        try:await asyncio.shield(pending)
        except asyncio.CancelledError:
            await pending
            raise
        except Exception:log.exception('Scheduler tick failed')
        await asyncio.sleep(1)

async def worker_loop():
    while True:
        try:
            if not await run_one(): await asyncio.sleep(1)
        except asyncio.CancelledError: raise
        except Exception:
            log.exception('Worker failure')
            await asyncio.sleep(3)
