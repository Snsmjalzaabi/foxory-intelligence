"""Verify seven sealed parser profiles against an explicitly local installation.
Uses existing smoke credentials/bootstrap; never creates an owner account.
Only its own fictional documents are created and removed.
"""
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit
import httpx
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from foxory.reports import report

def main():
    config=dict(line.split('=',1) for line in (ROOT/'.env').read_text().splitlines() if '=' in line and not line.startswith('#'))
    base=os.getenv('FOXORY_SMOKE_URL','http://127.0.0.1:'+config.get('FOXORY_PORT','8000')).rstrip('/')
    parsed=urlsplit(base)
    if parsed.hostname not in {'127.0.0.1','localhost'} or parsed.scheme not in {'http','https'}:raise ValueError('Verification is restricted to loopback')
    client=httpx.Client(base_url=base+'/api',trust_env=False,timeout=60)
    for _ in range(60):
        try:
            if client.get('/health',timeout=3).status_code==200:break
        except httpx.HTTPError:pass
        time.sleep(1)
    else:raise RuntimeError('Local API did not become healthy')
    username=os.getenv('FOXORY_SMOKE_USERNAME');password=os.getenv('FOXORY_SMOKE_PASSWORD')
    if username and password:
        login=client.post('/auth/login',json={'username':username,'password':password});login.raise_for_status();client.headers['X-CSRF-Token']=login.json()['csrf']
    else:client.headers['Authorization']='Bearer '+os.getenv('FOXORY_TOKEN',config['FOXORY_TOKEN'])
    if os.getenv('FOXORY_SMOKE_WORKSPACE'):client.headers['X-Workspace-ID']=os.environ['FOXORY_SMOKE_WORKSPACE']
    payloads={'txt':b'Profile verification 42','md':b'# Profile verification\n42','csv':b'label,value\nverification,42','json':b'{"verification":42}'}
    for format in ['pdf','docx','xlsx']:payloads[format]=report('Parser verification','Profile verification 42',[],format)[0]
    created=[]
    try:
        for extension,raw in payloads.items():
            response=client.post('/documents',files={'file':('profile-verification.'+extension,raw)});response.raise_for_status();row=response.json();created.append(row['id'])
            assert '42' in row['data']['text']
            original=client.get('/documents/'+row['id']+'/download');original.raise_for_status();assert original.content==raw
            print('PASS: sealed '+extension+' extraction and original-byte download',flush=True)
        rejected=client.post('/documents',files={'file':('invalid-profile.json',b'{')});assert rejected.status_code==422
        print('PASS: malformed JSON fails closed',flush=True)
    finally:
        for id in created:client.delete('/records/'+id).raise_for_status()
        if username:client.post('/auth/logout').raise_for_status()
    print('PASS: all verification documents removed',flush=True)
if __name__=='__main__':main()
