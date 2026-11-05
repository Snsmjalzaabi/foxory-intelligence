"""Project knowledge, explicit fact approval, writing and launch deliverables."""
import hashlib,io,json,re,zipfile
from typing import Literal
from datetime import date
from fastapi import APIRouter,HTTPException,Request
from fastapi.responses import Response
from pydantic import BaseModel,Field,ConfigDict
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from .db import Session,Record,get_record,audit,now
from .profile import active
router=APIRouter(prefix='/api/spaces')
ITEMS={'fact','chapter','lore','action','decision','deliverable','experiment'}
LINKABLE={'document','conversation','project','opportunity','lead','draft','repository','artifact','job','memory'}
class Strict(BaseModel):model_config=ConfigDict(extra='forbid')
class Space(Strict):
 title:str=Field(min_length=1,max_length=200)
 kind:Literal['business','writing','general']='general'
 brief:str=Field(default='',max_length=12000)
 stage:Literal['idea','validation','offer','prototype','launch','planning','drafting','revision','ready']='idea'
 audience:str=Field(default='',max_length=2000)
 problem:str=Field(default='',max_length=3000)
 offer:str=Field(default='',max_length=3000)
 assumptions:str=Field(default='',max_length=4000)
 evidence:str=Field(default='',max_length=8000)
 budget:float=Field(default=0,ge=0,le=1e9,allow_inf_nan=False)
 currency:str=Field(default_factory=lambda:active().currency,pattern=r'^[A-Z]{3}$')
 next_action:str=Field(default='',max_length=1000)
 revision:int=Field(default=0,ge=0)
class Item(Strict):
 kind:Literal['fact','chapter','lore','action','decision','deliverable','experiment']
 title:str=Field(min_length=1,max_length=200)
 body:str=Field(default='',max_length=30000)
 status:Literal['draft','pending','approved','done','superseded','validated']='draft'
 source:str=Field(default='',max_length=3000)
 fact_key:str=Field(default='',max_length=200)
 order:int=Field(default=0,ge=0,le=10000)
 due_date:date|None=None
 cost:float=Field(default=0,ge=0,le=1e9,allow_inf_nan=False)
 review:list[str]=Field(default_factory=list,max_length=12)
 review_done:list[str]=Field(default_factory=list,max_length=12)
 revision:int=Field(default=0,ge=0)
 supersedes:list[str]=Field(default_factory=list,max_length=20)
class Link(Strict):record_id:str=Field(min_length=1,max_length=36)
class Layout(Strict):
 name:str=Field(default='My workspace',min_length=1,max_length=80)
 widgets:list[Literal['Brief','Actions','Knowledge','Manuscript','Launch','Deliverables']]=Field(min_length=1,max_length=6)
 columns:int=Field(default=2,ge=1,le=3)
 sizes:dict[str,int]=Field(default_factory=dict,max_length=6)
 heights:dict[str,int]=Field(default_factory=dict,max_length=6)

def payload(row):return json.loads(row.payload)
def lock_space(s,id):
 row=s.scalar(select(Record).where(Record.id==id,Record.kind=='space').with_for_update().execution_options(populate_existing=True))
 if row is None:raise HTTPException(404,'Project not found')
 return row
def all_items(s,id):return list(s.scalars(select(Record).where(Record.kind.in_({'space_item','space_link'}),Record.dedupe_key.like(id+':%')).order_by(Record.created_at)))
def project_ids(s,id):
 get_record(s,id,'space');ids={id}
 for row in all_items(s,id):
  if row.kind=='space_item':ids.add(row.id)
  else:ids.add(payload(row)['record_id'])
 return ids

def public_item(row):
 v=row.public();v['data'].pop('revisions',None);return v

def snapshot(row,data,actor):
 old=payload(row);rev=old.get('revision',0)
 if data.get('revision',0)!=rev:raise HTTPException(409,'This item changed in another window. Reload before saving.')
 history=old.get('revisions',[])+[{'title':row.title,'data':{k:v for k,v in old.items() if k!='revisions'},'at':now(),'changed_by':actor}]
 data.update(revision=rev+1,revisions=history[-12:]);row.updated_at=now();return data

@router.get('')
def spaces():
 with Session() as s:return [r.public() for r in s.scalars(select(Record).where(Record.kind=='space').order_by(Record.updated_at.desc()))]
@router.post('',status_code=201)
def create(body:Space):
 with Session() as s:
  d=body.model_dump(mode='json');title=d.pop('title');row=Record(kind='space',title=title,payload=json.dumps(d));s.add(row);s.flush();audit(s,'space.create',row.id);s.commit();return row.public()
@router.get('/{id}')
def detail(id:str):
 with Session() as s:
  row=get_record(s,id,'space');items=all_items(s,id);links=[]
  for link in items:
   if link.kind!='space_link':continue
   try:target=get_record(s,payload(link)['record_id']);links.append({'link_id':link.id,**public_item(target)})
   except HTTPException:continue
  facts=[x for x in items if x.kind=='space_item' and payload(x).get('kind')=='fact' and payload(x).get('status')!='superseded']
  conflicts=[]
  for i,a in enumerate(facts):
   da=payload(a);key=da.get('fact_key','').strip().casefold()
   if not key:continue
   for b in facts[i+1:]:
    db=payload(b)
    if db.get('fact_key','').strip().casefold()==key and da['body'].strip()!=db['body'].strip():conflicts.append({'key':key,'item_ids':[a.id,b.id],'titles':[a.title,b.title],'resolution':'Review and explicitly supersede the outdated fact.'})
  return {'space':row.public(),'items':[public_item(x) for x in items if x.kind=='space_item'],'links':links,'conflicts':conflicts}
@router.put('/{id}')
def update(id:str,body:Space,request:Request):
 with Session() as s:
  row=lock_space(s,id);d=body.model_dump(mode='json');title=d.pop('title')
  if d['kind']=='business' and d['stage']=='launch':
   items=[payload(x) for x in all_items(s,id) if x.kind=='space_item']
   if not d['evidence'].strip() or not any(x['kind']=='deliverable' and x['status']=='approved' for x in items):raise HTTPException(409,'Before marking a launch ready, record validation evidence and approve at least one deliverable. Draft packages can be exported at any stage.')
  old=payload(row);d=snapshot(row,d,request.state.identity['id']);d['layout']=old.get('layout',{});d['layouts']=old.get('layouts',{});row.title=title;row.payload=json.dumps(d);audit(s,'space.update',id);s.commit();return row.public()
@router.post('/{id}/items',status_code=201)
def create_item(id:str,body:Item,request:Request):return save_item(id,None,body,request)
@router.put('/{id}/items/{item_id}')
def edit_item(id:str,item_id:str,body:Item,request:Request):return save_item(id,item_id,body,request)
def save_item(id,item_id,body,request):
 try:return _save_item(id,item_id,body,request)
 except IntegrityError:raise HTTPException(409,'Another edit approved this fact. Reload the project before reviewing the conflict.')
def _save_item(id,item_id,body,request):
 with Session() as s:
  lock_space(s,id);d=body.model_dump(mode='json');title=d.pop('title');d['space_id']=id
  if body.kind=='deliverable' and body.status=='approved' and (not body.review or not set(body.review)<=set(body.review_done)):raise HTTPException(409,'Complete every deliverable review check before approval.')
  if body.kind=='fact' and body.status=='approved':
   if not body.source.strip() or not body.fact_key.strip():raise HTTPException(422,'Approved facts require a source and a stable fact key.')
   for other in all_items(s,id):
    if other.kind!='space_item' or other.id==item_id:continue
    old=payload(other)
    if old.get('kind')=='fact' and old.get('status')=='approved' and old.get('fact_key','').casefold().strip()==body.fact_key.casefold().strip() and old.get('body','').strip()!=body.body.strip() and other.id not in body.supersedes:raise HTTPException(409,'A conflicting approved fact exists. Explicitly select it for superseding.')
  for previous_id in body.supersedes:
   previous=get_record(s,previous_id,'space_item');old=payload(previous)
   if body.kind!='fact' or body.status!='approved' or old.get('space_id')!=id or old.get('kind')!='fact' or old.get('fact_key','').casefold().strip()!=body.fact_key.casefold().strip() or previous_id==item_id:raise HTTPException(422,'Only facts with the same key in this project can be superseded.')
   old=snapshot(previous,old,request.state.identity['id']);old['status']='superseded';previous.dedupe_key=id+':'+__import__('uuid').uuid4().hex;previous.payload=json.dumps(old);audit(s,'fact.supersede',previous.id)
  if item_id:
   row=get_record(s,item_id,'space_item')
   if payload(row).get('space_id')!=id:raise HTTPException(404,'Item not in this project')
   if payload(row)['kind']!=body.kind:raise HTTPException(422,'Item type cannot be changed')
   original=payload(row)
   d=snapshot(row,d,request.state.identity['id'])
   for key in ['origin_job_id','original_sha256']: 
    if key in original:d[key]=original[key]
   row.title=title;row.payload=json.dumps(d)
   if body.kind=='fact':row.dedupe_key=id+(':approved:'+hashlib.sha256(body.fact_key.casefold().strip().encode()).hexdigest() if body.status=='approved' else ':'+__import__('uuid').uuid4().hex)
  else:
   row=Record(kind='space_item',title=title,dedupe_key=id+(':approved:'+hashlib.sha256(body.fact_key.casefold().strip().encode()).hexdigest() if body.kind=='fact' and body.status=='approved' else ':'+__import__('uuid').uuid4().hex),payload=json.dumps(d));s.add(row);s.flush()
  audit(s,'space.item.save',row.id,space_id=id,status=body.status);s.commit();return row.public()
@router.get('/{id}/items/{item_id}')
def item_detail(id:str,item_id:str):
 with Session() as s:
  get_record(s,id,'space');row=get_record(s,item_id,'space_item')
  if payload(row).get('space_id')!=id:raise HTTPException(404,'Item not in this project')
  return row.public()
@router.post('/{id}/links',status_code=201)
def link(id:str,body:Link):
 with Session() as s:
  get_record(s,id,'space');r=get_record(s,body.record_id)
  if r.kind not in LINKABLE:raise HTTPException(422,'This record cannot be linked to project knowledge')
  key=id+':'+body.record_id;existing=s.scalar(select(Record).where(Record.kind=='space_link',Record.dedupe_key==key))
  if existing:return existing.public()
  row=Record(kind='space_link',title=r.title,dedupe_key=key,payload=json.dumps({'space_id':id,'record_id':r.id}));s.add(row);s.flush();audit(s,'space.link',id,record_id=r.id);s.commit();return row.public()
@router.delete('/{id}/links/{link_id}',status_code=204)
def unlink(id:str,link_id:str):
 with Session() as s:
  get_record(s,id,'space');row=get_record(s,link_id,'space_link')
  if payload(row).get('space_id')!=id:raise HTTPException(404,'Link not in this project')
  s.delete(row);audit(s,'space.unlink',id);s.commit()
@router.put('/{id}/layout')
def layout(id:str,body:Layout):
 if len(set(body.widgets))!=len(body.widgets):raise HTTPException(422,'Choose each widget once')
 if any(k not in body.widgets or v not in {1,2,3} for k,v in body.sizes.items()) or any(k not in body.widgets or not 180<=v<=900 for k,v in body.heights.items()):raise HTTPException(422,'Invalid widget size')
 with Session() as s:
  row=lock_space(s,id);d=payload(row);d['layout']=body.model_dump();saved=d.setdefault('layouts',{});saved[body.name]=body.model_dump();d['layouts']=dict(list(saved.items())[-8:]);row.payload=json.dumps(d);audit(s,'space.layout',id);s.commit();return d['layout']
@router.post('/{id}/conversation',status_code=201)
def conversation(id:str):
 with Session() as s:
  space=get_record(s,id,'space');row=Record(kind='conversation',title=space.title+' · project chat',payload=json.dumps({'space_id':id}));s.add(row);s.flush();s.add(Record(kind='space_link',title=row.title,dedupe_key=id+':'+row.id,payload=json.dumps({'space_id':id,'record_id':row.id})));audit(s,'space.conversation',id);s.commit();return row.public()
class Capture(Strict):job_id:str=Field(min_length=1,max_length=36)
@router.post('/{id}/capture',status_code=201)
def capture(id:str,body:Capture):
 with Session() as s:
  get_record(s,id,'space');job=get_record(s,body.job_id,'job');d=payload(job)
  if d.get('status')!='completed' or not d.get('result'):raise HTTPException(409,'Only a completed task with a result can become a deliverable.')
  key=id+':job:'+job.id;old=s.scalar(select(Record).where(Record.kind=='space_item',Record.dedupe_key==key))
  if old:return old.public()
  item=Record(kind='space_item',dedupe_key=key,title=job.title[:200],payload=json.dumps({'space_id':id,'kind':'deliverable','body':d['result'][:30000],'status':'draft','source':'Agent task '+job.id,'origin_job_id':job.id,'original_sha256':hashlib.sha256(d['result'].encode()).hexdigest(),'review':['Check supplied evidence','Remove unsupported claims','Verify usable output'],'revision':0}));s.add(item);s.flush();audit(s,'deliverable.capture',item.id,job_id=job.id);s.commit();return item.public()
@router.get('/{id}/export')
def export(id:str,format:Literal['md','zip','json']='zip'):
 with Session() as s:
  detail_value=detail(id);space=detail_value['space'];items=sorted(detail_value['items'],key=lambda x:(x['data'].get('order',0),x['created_at']))
  text='# '+space['title']+'\n\n'+space['data'].get('brief','')+'\n\n'
  text+='Stage: '+space['data'].get('stage','')+'\n\n'
  if space['data']['kind']=='business':
   text+='## Launch brief\n\n'+'\n\n'.join(k.replace('_',' ').title()+': '+str(space['data'].get(k,'')) for k in ['audience','problem','offer','assumptions','evidence','budget','currency','next_action'])+'\n\n'
   text+='Costs recorded: '+str(round(sum(x['data'].get('cost',0) for x in items),2))+' '+space['data'].get('currency',active().currency)+'\n\n'
  for item in items:
   d=item['data'];text+='## '+item['title']+'\n\n'+d.get('body','')+'\n\nStatus: '+d.get('status','draft')+'\nSource: '+d.get('source','')+'\n\n'
  text+='\nThis package contains saved user material and AI drafts. Approval is a human review status, not independent factual verification. No sending, publishing or code execution occurred.\n'
  if format=='md':return Response(text,media_type='text/markdown',headers={'Content-Disposition':'attachment; filename="foxory-project.md"'})
  if format=='json':return Response(json.dumps(detail_value,indent=2),media_type='application/json',headers={'Content-Disposition':'attachment; filename="foxory-project.json"'})
  out=io.BytesIO()
  with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
   z.writestr('project.md',text);z.writestr('project.json',json.dumps(detail_value,indent=2))
   if space['data']['kind']=='writing':z.writestr('manuscript.md','# '+space['title']+'\n\n'+'\n\n'.join('## '+x['title']+'\n\n'+x['data']['body'] for x in items if x['data']['kind']=='chapter'))
  return Response(out.getvalue(),media_type='application/zip',headers={'Content-Disposition':'attachment; filename="foxory-project.zip"'})
class ProjectTask(Strict):
 model:str|None=Field(default=None,min_length=1,max_length=100)
 profile:Literal['quick','balanced','thorough']='balanced'
 agent_id:str=Field(min_length=1,max_length=36)
 objective:str=Field(min_length=1,max_length=6000)
 purpose:Literal['general','continuity','launch']='general'
 item_ids:list[str]=Field(default_factory=list,max_length=12)
 idempotency_key:str=Field(min_length=8,max_length=100)
@router.post('/{id}/tasks',status_code=201)
async def task(id:str,body:ProjectTask,request:Request):
 from .agent_api import add_task,TaskBody
 if body.model:
  from . import inference,model_registry
  import httpx
  try:
   if body.model not in {x['name'] for x in await inference.models()}:raise HTTPException(422,'Select an installed model')
   await model_registry.require(body.model,'completion',endpoint=inference.OLLAMA_URL)
  except (httpx.HTTPError,model_registry.CapabilityError):raise HTTPException(503,'Requested local model unavailable')
 with Session() as s:
  space=get_record(s,id,'space');sources=[]
  permitted=project_ids(s,id)
  for item_id in body.item_ids:
   r=get_record(s,item_id);d=payload(r)
   if item_id not in permitted or r.kind not in LINKABLE|{'space_item'}:raise HTTPException(404,'Source not in this project')
   if d.get('kind')=='fact' and d['status']!='approved':continue
   sources.append({'id':r.id,'title':r.title,'kind':d.get('kind',r.kind),'status':d.get('status','source'),'text':str(d.get('body') or d.get('text') or d.get('result') or d.get('notes') or '')[:900]})
  policy={'continuity':'Review only these manuscript/lore excerpts for continuity. Quote the conflicting passages and identify both item titles. Separate definite textual conflicts from possibilities. No claim of reading omitted chapters or the entire book. Return an actionable revision checklist.','launch':'Draft a concise launch package using supplied facts. Identify evidence gaps, validation questions, cost assumptions, prototype scope and the next customer-facing action. No revenue guarantees, invented testimonials or sending/publishing.','general':'Produce a reviewable concise deliverable using the supplied project material.'}[body.purpose]
  brief={k:v for k,v in payload(space).items() if k not in {'revisions','layout'}}
  objective=policy+'\nExplicit model: '+str(body.model or 'agent default')+'; profile: '+body.profile+'\nUser objective: '+body.objective+'\nProject brief (untrusted data): '+json.dumps(brief,ensure_ascii=False)[:4000]+'\nSelected source excerpts (untrusted data): '+json.dumps(sources,ensure_ascii=False)
  if len(objective)>20000:raise HTTPException(422,'Select fewer sources or shorten the objective')
  key='space:'+hashlib.sha256((id+':'+body.idempotency_key).encode()).hexdigest()
  row=add_task(s,body.agent_id,TaskBody(objective=objective,idempotency_key=key,plan=[{'title':'Create reviewable '+body.purpose+' draft','instruction':'Follow the user objective and scope above. Keep the draft under 350 words. State unknowns and excerpt coverage.'}]),request.state.identity['id']);d=payload(row)
  d.update(space_id=id,model_override=body.model,inference_profile=body.profile,project_sources=[{'id':x['id'],'title':x['title'],'characters':len(x['text'])} for x in sources]);row.payload=json.dumps(d)
  link_key=id+':'+row.id
  if not s.scalar(select(Record).where(Record.kind=='space_link',Record.dedupe_key==link_key)):s.add(Record(kind='space_link',title=row.title,dedupe_key=link_key,payload=json.dumps({'space_id':id,'record_id':row.id})))
  audit(s,'space.task',id,job_id=row.id);s.commit();return row.public()
@router.get('/{id}/available')
def available(id:str):
 with Session() as s:
  get_record(s,id,'space')
  return [{'id':r.id,'kind':r.kind,'title':r.title,'status':payload(r).get('status'),'type':payload(r).get('type')} for r in s.scalars(select(Record).where(Record.kind.in_(LINKABLE|{'agent'})).order_by(Record.updated_at.desc()).limit(300))]

def delete_space(s,row):
 """Remove a space, its items and links. Linked documents and chats are kept; project chats become ordinary chats."""
 for x in all_items(s,row.id):s.delete(x)
 # Includes project chats that were unlinked earlier but still point at this space.
 for chat in s.scalars(select(Record).where(Record.kind=='conversation',Record.payload.contains(row.id,autoescape=True))):
  d=json.loads(chat.payload)
  if d.get('space_id')==row.id:d.pop('space_id');chat.payload=json.dumps(d)
 s.delete(row);audit(s,'space.delete',row.id)
@router.delete('/{id}',status_code=204)
def remove_space(id:str):
 with Session() as s:get_record(s,id,'space');delete_space(s,lock_space(s,id));s.commit()
@router.delete('/{id}/items/{item_id}',status_code=204)
def remove_item(id:str,item_id:str):
 with Session() as s:
  lock_space(s,id);row=get_record(s,item_id,'space_item')
  if not (row.dedupe_key or '').startswith(id+':'):raise HTTPException(404,'Item not in this project')
  s.delete(row);audit(s,'space.item.delete',id,item_id=item_id);s.commit()
