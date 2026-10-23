"""Authenticated local installation smoke. Never prints tokens or document content."""
import json
import os
import urllib.request
import urllib.error
import http.cookiejar
import time
from pathlib import Path
from uuid import uuid4

root=Path(__file__).resolve().parents[1]
config={}
if (root/'.env').exists():
    config=dict(line.split('=',1) for line in (root/'.env').read_text().splitlines() if line and not line.startswith('#') and '=' in line)
token=os.getenv('FOXORY_TOKEN',config.get('FOXORY_TOKEN',''))
base=os.getenv('FOXORY_SMOKE_URL','http://127.0.0.1:'+config.get('FOXORY_PORT','8000'))
cookie_opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
csrf=''
def request(path,method='GET',data=None,authorized=True):
    global csrf
    username=os.getenv('FOXORY_SMOKE_USERNAME')
    password=os.getenv('FOXORY_SMOKE_PASSWORD')
    if authorized and username and password and not csrf:
        login=urllib.request.Request(base+'/api/auth/login',data=json.dumps({'username':username,'password':password}).encode(),headers={'Content-Type':'application/json'},method='POST')
        with cookie_opener.open(login,timeout=30) as result:csrf=json.loads(result.read())['csrf']
    headers={'Content-Type':'application/json'}
    if authorized:
        if csrf:headers['X-CSRF-Token']=csrf
        else:headers['Authorization']='Bearer '+token
        if os.getenv('FOXORY_SMOKE_WORKSPACE'):headers['X-Workspace-ID']=os.environ['FOXORY_SMOKE_WORKSPACE']
    req=urllib.request.Request(base+'/api'+path,data=json.dumps(data).encode() if data is not None else None,headers=headers,method=method)
    opener=cookie_opener if authorized and csrf else urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req,timeout=240) as r:
        body=r.read().decode()
        if not body: return None
        return json.loads(body) if r.headers.get_content_type()=='application/json' else body

if __name__=='__main__':
    for _ in range(40):
        try:request('/health',authorized=False);break
        except (OSError,urllib.error.URLError):time.sleep(1)
    else:raise SystemExit('Local health check timed out')
    try:request('/overview',authorized=False)
    except urllib.error.HTTPError as e:assert e.code==401
    else:raise AssertionError('Unauthenticated access was accepted')
    marker='Smoke '+str(uuid4())
    r=request('/records/memory','POST',{'title':marker,'data':{'body':'Fictional installation test'}})
    assert any(x['id']==r['id'] for x in request('/records/memory'))
    request('/records/'+r['id'],'DELETE')
    print('PASS: health, unauthorized rejection, authenticated persistence and delete')
    if os.getenv('FOXORY_SMOKE_MODEL'):
        model=os.environ['FOXORY_SMOKE_MODEL']
        r=request('/records/conversation','POST',{'title':'Fictional live inference smoke'})
        result=request('/conversations/'+r['id']+'/chat','POST',{'model':model,'content':'Reply with exactly the word FOXORY.','temperature':0,'context':2048})
        assert 'event: done' in result and 'event: error' not in result,result
        messages=request('/conversations/'+r['id']+'/messages')
        assert messages[-1]['content'].strip()
        assert messages[-1]['metadata']['status']=='complete'
        print('PASS: live model streaming and persisted nonempty response; model='+model)
        print('Measured tokens: '+str(messages[-1]['metadata'].get('eval_count','unreported')))
        request('/records/'+r['id'],'DELETE')
