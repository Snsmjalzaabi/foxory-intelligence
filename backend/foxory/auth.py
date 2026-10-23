"""Password authentication and server-side, revocable, opaque sessions."""
import hashlib
import secrets
import threading
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from .config import TOKEN
from .db import Session, User, Workspace, Membership, LoginSession, uid, now
from .scope import workspace_id
router=APIRouter(prefix='/api/auth')
hash_slots=threading.BoundedSemaphore(2)
class BoundedHasher(PasswordHasher):
    def hash(self,*args,**kwargs):
        with hash_slots:return super().hash(*args,**kwargs)
    def verify(self,*args,**kwargs):
        with hash_slots:return super().verify(*args,**kwargs)
passwords=BoundedHasher(time_cost=3,memory_cost=65536,parallelism=1)
DUMMY=passwords.hash('not-an-account-'+secrets.token_hex(16))

def digest(token:str)->str:return hashlib.sha256(token.encode()).hexdigest()

def identity(request:Request):
    authorization=request.headers.get('authorization','')
    has_bearer=authorization.startswith('Bearer ') and len(authorization)>7
    if authorization and not has_bearer:raise HTTPException(401,'Invalid authorization header')
    raw=authorization.removeprefix('Bearer ') if has_bearer else request.cookies.get('foxory_session','')
    with Session() as s:
        login=s.get(LoginSession,digest(raw)) if raw else None
        if login and login.expires_at>now():
            user=s.get(User,login.user_id)
            memberships=s.execute(select(Membership,Workspace).join(Workspace,Membership.workspace_id==Workspace.id).where(Membership.user_id==user.id)).all()
            selected=request.headers.get('x-workspace-id') or (memberships[0][1].id if memberships else '')
            match=next(((m,w) for m,w in memberships if w.id==selected),None)
            if not match:raise HTTPException(403,'Workspace membership required')
            if not has_bearer and request.method not in {'GET','HEAD','OPTIONS'}:
                if not secrets.compare_digest(request.headers.get('x-csrf-token','').encode(),login.csrf.encode()):raise HTTPException(403,'CSRF token required')
            m,w=match
            return {'id':user.id,'username':user.username,'role':m.role,'workspace_id':w.id,'workspace_name':w.name,'csrf':login.csrf,'workspaces':[{'id':w.id,'name':w.name,'role':m.role} for m,w in memberships]}
        # Legacy API compatibility is limited to the pre-account local installation.
        if not s.scalar(select(func.count()).select_from(User)) and TOKEN and secrets.compare_digest(authorization.encode(),('Bearer '+TOKEN).encode()):
            return {'id':'bootstrap','username':'Bootstrap owner','role':'admin','workspace_id':'local','workspace_name':'Local workspace','csrf':'','workspaces':[{'id':'local','name':'Local workspace','role':'admin'}]}
    raise HTTPException(401,'Login required')

class Credentials(BaseModel):
    username:str=Field(pattern=r'^[a-zA-Z0-9_.@-]{3,100}$')
    password:str=Field(min_length=12,max_length=256)
class Setup(Credentials):
    bootstrap_token:str=Field(max_length=256)

@router.get('/status')
def status():
    with Session() as s:return {'setup_required':not bool(s.scalar(select(func.count()).select_from(User)))}

def issue(user_id:str,request:Request,response:Response):
    token=secrets.token_urlsafe(40);csrf=secrets.token_urlsafe(32)
    with Session() as s:
        s.add(LoginSession(token_hash=digest(token),user_id=user_id,expires_at=(datetime.now(timezone.utc)+timedelta(hours=12)).isoformat(),csrf=csrf));s.commit()
    response.set_cookie('foxory_session',token,httponly=True,samesite='strict',secure=request.url.scheme=='https',max_age=43200,path='/')
    return {'authenticated':True,'csrf':csrf}

@router.post('/setup',status_code=201)
def setup(body:Setup,request:Request,response:Response):
    if not TOKEN or not secrets.compare_digest(body.bootstrap_token.encode(),TOKEN.encode()):raise HTTPException(403,'Invalid bootstrap token')
    with Session() as s:
        if s.scalar(select(func.count()).select_from(User)):raise HTTPException(409,'Setup already completed')
        # Fixed initial ID makes concurrent bootstrap requests atomic.
        user=User(id='initial-administrator',username=body.username.casefold(),password_hash=passwords.hash(body.password))
        s.add(user)
        try:
            s.flush();s.add(Membership(workspace_id='local',user_id=user.id,role='admin'));s.commit()
        except IntegrityError:s.rollback();raise HTTPException(409,'Setup already completed')
    return issue(user.id,request,response)

@router.post('/login')
def login(body:Credentials,request:Request,response:Response):
    with Session() as s:
        user=s.scalar(select(User).where(User.username==body.username.casefold()))
        try:passwords.verify(user.password_hash if user else DUMMY,body.password)
        except (VerificationError,InvalidHashError):raise HTTPException(401,'Invalid credentials')
        if not user:raise HTTPException(401,'Invalid credentials')
        if passwords.check_needs_rehash(user.password_hash):user.password_hash=passwords.hash(body.password);s.commit()
        return issue(user.id,request,response)

@router.get('/me')
def me(request:Request):return request.state.identity

@router.post('/logout')
def logout(request:Request,response:Response):
    raw=request.cookies.get('foxory_session','')
    with Session() as s:
        login=s.get(LoginSession,digest(raw))
        if login:s.delete(login);s.commit()
    response.delete_cookie('foxory_session',path='/')
    return {'logged_out':True}

class NewWorkspace(BaseModel):
    name:str=Field(min_length=1,max_length=100)
@router.post('/workspaces',status_code=201)
def workspace(body:NewWorkspace,request:Request):
    actor=request.state.identity
    if actor['id']=='bootstrap':raise HTTPException(403,'Create an account first')
    with Session() as s:
        w=Workspace(name=body.name);s.add(w);s.flush();s.add(Membership(workspace_id=w.id,user_id=actor['id'],role='admin'));s.commit()
        return {'id':w.id,'name':w.name,'role':'admin'}

class Member(Credentials):
    role:str=Field(pattern=r'^(admin|editor|viewer)$')
@router.post('/members',status_code=201)
def member(body:Member,request:Request):
    actor=request.state.identity
    if actor['role']!='admin' or actor['id']=='bootstrap':raise HTTPException(403,'Workspace administrator required')
    with Session() as s:
        user=s.scalar(select(User).where(User.username==body.username.casefold()))
        if user:raise HTTPException(409,'Username exists; add existing membership by ID instead')
        user=User(username=body.username.casefold(),password_hash=passwords.hash(body.password));s.add(user);s.flush()
        s.add(Membership(workspace_id=workspace_id.get(),user_id=user.id,role=body.role));s.commit()
        return {'id':user.id,'username':user.username,'role':body.role}

class ExistingMember(BaseModel):
    user_id:str
    role:str=Field(pattern=r'^(admin|editor|viewer)$')
@router.put('/members')
def existing_member(body:ExistingMember,request:Request):
    if request.state.identity['role']!='admin':raise HTTPException(403,'Administrator required')
    with Session() as s:
        if not s.get(User,body.user_id):raise HTTPException(404,'User not found')
        membership=s.get(Membership,(workspace_id.get(),body.user_id))
        if membership:
            if membership.user_id==request.state.identity['id'] and body.role!='admin':raise HTTPException(409,'Cannot demote yourself')
            membership.role=body.role
        else:s.add(Membership(workspace_id=workspace_id.get(),user_id=body.user_id,role=body.role))
        # Membership is re-evaluated on every request. A workspace administrator
        # must not revoke the user's sessions in unrelated workspaces.
        s.commit();return {'updated':True}

@router.get('/members')
def members(request:Request):
    if request.state.identity['role']!='admin':raise HTTPException(403,'Administrator required')
    with Session() as s:return [{'id':u.id,'username':u.username,'role':m.role} for m,u in s.execute(select(Membership,User).join(User,Membership.user_id==User.id).where(Membership.workspace_id==workspace_id.get()))]
