"""Agent summaries are unverified; only explicit user writes create approved facts."""
import json
from datetime import datetime,timedelta,timezone
from sqlalchemy import select
from .db import Record,Session,now,uid,audit

def search_memory(agent_id,query):
    words=set(query.casefold().split())
    with Session() as s:
        rows=[]
        for r in s.scalars(select(Record).where(Record.kind=='agent_memory')):
            d=json.loads(r.payload)
            if d.get('expires_at','9999')<now():continue
            if d.get('agent_id')!=agent_id and not d.get('approved_fact'):continue
            score=sum(w in (r.title+' '+d.get('body','')).casefold() for w in words)
            if score:rows.append((score,dict(id=r.id,title=r.title,**d)))
        return [d for _,d in sorted(rows,key=lambda x:x[0],reverse=True)[:10]]

def retain_summary(s,job_id,data):
    days=data['agent_snapshot'].get('retention_days',30)
    if not days:return
    id=__import__('hashlib').sha256(('summary:'+job_id).encode()).hexdigest()[:36]
    if s.get(Record,id):return
    s.add(Record(id=id,kind='agent_memory',title=data['prompt'][:120],payload=json.dumps({'agent_id':data['agent_id'],'body':data.get('result','')[:20000],'approved_fact':False,'verified':False,'job_id':job_id,'expires_at':(datetime.now(timezone.utc)+timedelta(days=days)).isoformat()})))
    audit(s,'agent.memory.summary',id,job_id=job_id)

def prune(s):
    for r in s.scalars(select(Record).where(Record.kind=='agent_memory')):
        if json.loads(r.payload).get('expires_at','9999')<now():s.delete(r)
