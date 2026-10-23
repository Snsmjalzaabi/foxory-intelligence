"""Durable single-process scheduler; UTC instants, IANA display zones, coalesced misses."""
import json
from datetime import datetime,timedelta,timezone
from sqlalchemy import select
from .db import Session,Record,Membership,Audit,audit,now
from .scope import workspace_id,actor_id,system_scope
from .agent_api import add_task,TaskBody

def tick(at=None):
    at=at or datetime.now(timezone.utc)
    with system_scope(),Session() as s:
        for memory in s.scalars(select(Record).where(Record.kind=='agent_memory')):
            if json.loads(memory.payload).get('expires_at','9999')<at.isoformat():
                # Explicit internal maintenance; ordinary APIs remain workspace-scoped.
                s.add(Audit(workspace=memory.workspace,action='agent.memory.expired',target=memory.id,detail=json.dumps({'actor_id':'scheduler','policy':'retention'})))
                s.delete(memory)
        s.commit()
        expired=[(r.id,r.workspace) for r in s.scalars(select(Record).where(Record.kind=='approval')) if json.loads(r.payload).get('expires_at','9999')<at.isoformat() and json.loads(r.payload).get('status') in {'pending','approved'}]
        ids=[(r.id,r.workspace) for r in s.scalars(select(Record).where(Record.kind=='schedule'))]
    for id,workspace in expired:
        token=workspace_id.set(workspace)
        try:
            with Session() as s:
                row=s.get(Record,id);d=json.loads(row.payload);d['status']='expired';row.payload=json.dumps(d);row.dedupe_key=None
                context=d.get('context',{});job=s.get(Record,context.get('job_id',''))
                if job:
                    j=json.loads(job.payload)
                    if j.get('approval_id')==id and j.get('status')=='awaiting_approval':j.update(status='failed',error='Approval expired');job.payload=json.dumps(j)
                audit(s,'approval.expired',id);s.commit()
        finally:workspace_id.reset(token)
    for id,workspace in ids:
        wt=workspace_id.set(workspace);ut=actor_id.set('scheduler')
        try:
            with Session() as s:
                from .agent_memory import prune
                prune(s)
                row=s.get(Record,id);d=json.loads(row.payload)
                if d.get('paused'):s.commit();continue
                creator=d['creator_id']
                if creator!='bootstrap':
                    membership=s.get(Membership,(workspace,creator))
                    if not membership or membership.role not in {'admin','editor'}:
                        d.update(enabled=False,error='Creator no longer has execution permission');row.payload=json.dumps(d);audit(s,'schedule.denied',id);s.commit();continue
                # At most one live run per schedule and eight pending jobs per workspace.
                jobs=[json.loads(r.payload) for r in s.scalars(select(Record).where(Record.kind=='job'))]
                active={'queued','running','paused','awaiting_approval'}
                if any(j.get('schedule_id')==id and j.get('status') in active for j in jobs) or sum(j.get('status') in active for j in jobs)>=8:continue
                # Bounded automatic retry of a failed scheduled job; same job, no duplicate side effects.
                if d.get('last_job_id'):
                    previous=s.get(Record,d['last_job_id']);p=json.loads(previous.payload) if previous else {}
                    if p.get('status')=='failed' and p.get('schedule_retries',0)<d['retry_limit'] and p.get('deadline_at','9999')>at.isoformat():
                        p.update(status='queued',schedule_retries=p.get('schedule_retries',0)+1);previous.payload=json.dumps(p);audit(s,'schedule.retry',previous.id);s.commit();continue
                if not d['enabled'] or datetime.fromisoformat(d['next_run_at'])>at:s.commit();continue
                due=datetime.fromisoformat(d['next_run_at']);interval=d.get('every_minutes')
                missed=(at-due).total_seconds()>60
                if not (missed and d['missed_policy']=='skip'):
                    task=add_task(s,d['agent_id'],TaskBody(objective=d['objective'],idempotency_key='schedule:'+id+':'+due.isoformat()),creator)
                    payload=json.loads(task.payload);payload['schedule_id']=id;task.payload=json.dumps(payload)
                    d['last_job_id']=task.id;d['runs']+=1;d['history']=(d['history']+[{'due_at':due.isoformat(),'job_id':task.id,'at':at.isoformat()}])[-100:]
                    audit(s,'schedule.dispatch',id,job_id=task.id)
                if not interval or d['runs']>=d['max_runs']:d['enabled']=False
                else:
                    periods=max(1,int((at-due).total_seconds()//(interval*60))+1)
                    d['next_run_at']=(due+timedelta(minutes=interval*periods)).isoformat()
                row.payload=json.dumps(d);row.updated_at=now();s.commit()
        except Exception:
            # Bad/deleted configuration disables only this schedule, never other tenants.
            with Session() as s:
                row=s.get(Record,id)
                if row:
                    d=json.loads(row.payload);d.update(enabled=False,error='Schedule configuration invalid; inspect agent permissions and membership');row.payload=json.dumps(d);audit(s,'schedule.failed',id);s.commit()
        finally:workspace_id.reset(wt);actor_id.reset(ut)
