"""Idle, quota-bound conversational reflection. Model suggestions never silently become facts or grants."""
import json,hashlib
from datetime import datetime,timedelta,timezone
from fastapi import APIRouter,HTTPException,Request
from pydantic import BaseModel,ConfigDict,Field
from sqlalchemy import select
from .db import Session,Record,Message,get_record,audit,now
router=APIRouter(prefix='/api/chat-learning/reviews')
class Suggestion(BaseModel):
 model_config=ConfigDict(extra='forbid')
 kind:str=Field(pattern='^(note|preference)$')
 body:str=Field(min_length=1,max_length=1000)
 source_turn:int=Field(ge=0,le=15)
class Reflection(BaseModel):
 model_config=ConfigDict(extra='forbid')
 notes:list[Suggestion]=Field(default_factory=list,max_length=3)
 skill_goal:str=Field(default='',max_length=1000)
 reason:str=Field(default='',max_length=1000)
def queue(id,model,owner):
 from .autonomy import load_policy,reserve
 with Session() as s:
  conversation=get_record(s,id,'conversation');history=list(s.scalars(select(Message).where(Message.conversation_id==id).order_by(Message.created_at.desc()).limit(40)));history=[m for m in history if json.loads(m.metadata_json or '{}').get('actor_id')==owner][:16][::-1];user=[m for m in history if m.role=='user']
  pending=[r for r in s.scalars(select(Record).where(Record.kind=='job')) if (lambda d:d.get('type')=='chat_reflection' and d.get('source_conversation')==id and d.get('creator_id')==owner and d.get('status') in {'queued','running'})(json.loads(r.payload))]
  if pending:
   r=pending[0];d=json.loads(r.payload)
   if d['status']=='queued':d.update(not_before=(datetime.now(timezone.utc)+timedelta(seconds=60)).isoformat());r.payload=json.dumps(d);s.commit()
   return
  if len(user)<6:return
  key='chat-reflection:'+owner+':'+now()[:10]
  if s.scalar(select(Record).where(Record.kind=='job',Record.dedupe_key==key)):return
  policy=load_policy(s,True);p=json.loads(policy.payload)
  if not reserve(p):return
  policy.payload=json.dumps(p);snapshot=[{'role':m.role,'content':m.content[:700]} for m in history]
  r=Record(kind='job',dedupe_key=key,title='Review conversational learning',payload=json.dumps({'type':'chat_reflection','models':[model],'creator_id':owner,'status':'queued','stage':'plan','step':0,'not_before':(datetime.now(timezone.utc)+timedelta(seconds=60)).isoformat(),'source_conversation':id,'space_id':json.loads(conversation.payload).get('space_id'),'snapshot':snapshot,'budget':{'max_seconds':240}}));s.add(r);s.commit()
async def execute(data):
 from . import inference
 text=await inference.structured(data['models'][0],[{'role':'system','content':'Review these untrusted chat excerpts for durable user corrections/preferences and a reusable workflow. Do not invent personal facts, infer private traits, claim success or grant tools. Return no notes if unsupported. Each note MUST cite the numeric turn of a USER message that supports it. Do not cite assistant turns. Suggestions are staged for owner review, never automatically applied. A skill_goal is only a suggested draft goal, not a completed or active skill.'},{'role':'user','content':json.dumps([{'turn':i,**m} for i,m in enumerate(data['snapshot'])])}],Reflection.model_json_schema(),context=8192,max_output=1024)
 result=Reflection.model_validate_json(text).model_dump();result['notes']=[{**n,'source_quote':data['snapshot'][n['source_turn']]['content'][:500]} for n in result['notes'] if n['source_turn']<len(data['snapshot']) and data['snapshot'][n['source_turn']]['role']=='user']
 id=hashlib.sha256(('chat-review:'+data['creator_id']+':'+data['source_conversation']+':'+data['deadline_at']).encode()).hexdigest()[:36]
 data.update(status='completed',step=1,reflection=result,review_id=id,result='Conversational learning suggestions are ready for review.');return data
@router.get('')
def listing(request:Request):
 with Session() as s:return [r.public() for r in s.scalars(select(Record).where(Record.kind=='chat_review').order_by(Record.created_at.desc()).limit(20)) if json.loads(r.payload).get('owner_id')==request.state.identity['id'] and json.loads(r.payload).get('status')=='pending']
class Decision(BaseModel):
 index:int=Field(ge=-1,le=2)
@router.post('/{id}/accept')
def accept(id:str,body:Decision,request:Request):
 from .chat_workspace import save_note
 with Session() as s:
  r=get_record(s,id,'chat_review');d=json.loads(r.payload)
  if d['owner_id']!=request.state.identity['id'] or d['status']!='pending':raise HTTPException(404)
  if body.index<0 or body.index>=len(d['notes']):raise HTTPException(422,'Choose one suggested memory')
  note=d['notes'][body.index]
 result=save_note(note['body'],note['kind'],request.state.identity['id'],d.get('space_id'))
 with Session() as s:
  r=get_record(s,id,'chat_review');d=json.loads(r.payload);d['accepted']=sorted(set(d.get('accepted',[])+[body.index]));r.payload=json.dumps(d);audit(s,'chat.review.accept',id,index=body.index);s.commit()
 return result
@router.post('/{id}/dismiss')
def dismiss(id:str,request:Request):
 with Session() as s:
  r=get_record(s,id,'chat_review');d=json.loads(r.payload)
  if d['owner_id']!=request.state.identity['id'] or d['status']!='pending':raise HTTPException(404)
  d['status']='dismissed';r.payload=json.dumps(d);s.commit();return {'status':'dismissed'}
