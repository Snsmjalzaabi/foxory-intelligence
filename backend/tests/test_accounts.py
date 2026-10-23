import os
import httpx
import pytest
from foxory.main import app
from foxory.db import Session, User, LoginSession

async def setup(c,name='owner'):
    c.headers.pop('authorization',None)
    r=await c.post('/api/auth/setup',json={'username':name,'password':'long-test-password-123','bootstrap_token':os.environ['FOXORY_TOKEN']})
    assert r.status_code==201,r.text
    c.headers['x-csrf-token']=r.json()['csrf']
    return (await c.get('/api/auth/me')).json()

async def test_session_login_revocation_csrf_and_bootstrap_lock(client):
    user=await setup(client)
    assert user['role']=='admin'
    assert client.cookies.get('foxory_session')
    with Session() as s:
        account=s.get(User,'initial-administrator')
        assert account.password_hash.startswith('$argon2id$')
    assert (await client.get('/api/overview',headers={'Authorization':'Bearer '+os.environ['FOXORY_TOKEN']})).status_code==401
    assert (await client.post('/api/records/memory',json={'title':'blocked'},headers={'x-csrf-token':''})).status_code==403
    assert (await client.post('/api/records/memory',json={'title':'allowed'})).status_code==201
    assert (await client.post('/api/auth/logout')).status_code==200
    assert (await client.get('/api/overview')).status_code==401
    assert (await client.post('/api/auth/login',json={'username':'owner','password':'wrong-password-123'})).status_code==401
    r=await client.post('/api/auth/login',json={'username':'owner','password':'long-test-password-123'})
    assert r.status_code==200
    assert (await client.post('/api/auth/setup',json={'username':'owner2','password':'long-test-password-123','bootstrap_token':os.environ['FOXORY_TOKEN']})).status_code==409

async def test_workspace_isolation_all_domains_and_rbac(client):
    await setup(client)
    original={}
    for kind in ['conversation','memory','agent','lead','project','draft']:
        r=await client.post('/api/records/'+kind,json={'title':'Private '+kind,'data':{}})
        assert r.status_code==201,r.text
        original[kind]=r.json()['id']
    doc=await client.post('/api/documents',files={'file':('private.txt',b'Secret workspace evidence')});assert doc.status_code==201
    original['document']=doc.json()['id']
    job=await client.post('/api/jobs',json={'type':'research','prompt':'Private question','models':['a'],'idempotency_key':'shared-key-123'})
    assert job.status_code==201
    original['job']=job.json()['id']
    approval=await client.post('/api/drafts/'+original['draft']+'/request-approval');original['approval']=approval.json()['id']
    second=(await client.post('/api/auth/workspaces',json={'name':'Second workspace'})).json()
    client.headers['x-workspace-id']=second['id']
    for kind,id in original.items():
        assert (await client.get('/api/records/'+kind)).json()==[]
        assert (await client.delete('/api/records/'+id)).status_code==404
    assert (await client.get('/api/conversations/'+original['conversation']+'/messages')).status_code==404
    assert (await client.get('/api/documents/'+original['document']+'/download')).status_code==404
    assert (await client.get('/api/documents/search?q=evidence')).json()==[]
    assert (await client.post('/api/jobs/'+original['job']+'/cancel')).status_code==404
    assert (await client.post('/api/approvals/'+original['approval']+'/approve')).status_code==404
    assert (await client.get('/api/jobs/'+original['job']+'/export')).status_code==404
    assert (await client.get('/api/workspace/export')).json()['records']==[]
    assert (await client.get('/api/audit')).json()==[]
    # Same idempotency key must not collide across workspaces.
    other=await client.post('/api/jobs',json={'type':'research','prompt':'Other question','models':['a'],'idempotency_key':'shared-key-123'})
    assert other.status_code==201 and other.json()['id']!=original['job']
    member=await client.post('/api/auth/members',json={'username':'reader','password':'reader-password-123','role':'viewer'})
    assert member.status_code==201
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://testserver') as reader:
        r=await reader.post('/api/auth/login',json={'username':'reader','password':'reader-password-123'})
        reader.headers['x-csrf-token']=r.json()['csrf']
        assert (await reader.get('/api/records/job')).status_code==200
        assert (await reader.post('/api/records/memory',json={'title':'Denied'})).status_code==403
        assert (await reader.post('/api/models/remove',json={'model':'a','confirmation':'a'})).status_code==403
        assert (await reader.get('/api/overview',headers={'x-workspace-id':'local'})).status_code==403
        assert (await reader.get('/api/auth/members')).status_code==403
        assert (await reader.post('/api/auth/logout')).status_code==200

async def test_expiry_role_revocation_and_installation_permissions(client):
    await setup(client)
    user=(await client.post('/api/auth/members',json={'username':'editor','password':'editor-password-123','role':'editor'})).json()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://testserver') as editor:
        r=await editor.post('/api/auth/login',json={'username':'editor','password':'editor-password-123'})
        editor.headers['x-csrf-token']=r.json()['csrf']
        assert (await editor.post('/api/records/memory',json={'title':'Editor can write'})).status_code==201
        assert (await editor.post('/api/models/remove',json={'model':'a','confirmation':'a'})).status_code==403
        assert (await editor.post('/api/approvals/unknown/approve')).status_code==403
        # Creating a workspace grants only workspace admin, never installation admin.
        w=(await editor.post('/api/auth/workspaces',json={'name':'Editor-owned'})).json()
        editor.headers['x-workspace-id']=w['id']
        assert (await editor.post('/api/models/remove',json={'model':'a','confirmation':'a'})).status_code==403
        editor.headers.pop('x-workspace-id')
        changed=await client.put('/api/auth/members',json={'user_id':user['id'],'role':'viewer'})
        assert changed.status_code==200
        assert (await editor.get('/api/overview')).status_code==200
        assert (await editor.post('/api/records/memory',json={'title':'Denied after downgrade'})).status_code==403
    # Expiry is checked on the server, not trusted from browser cookie metadata.
    from foxory.auth import digest
    with Session() as s:
        session=s.get(LoginSession,digest(client.cookies.get('foxory_session')))
        session.expires_at='2000-01-01T00:00:00+00:00';s.commit()
    assert (await client.get('/api/overview')).status_code==401
