"""Local overlay image/disabled-mode/persistence check; never replaces owner stack.

The --build overlay reuses the verified Phase 3 dependency image. It is not a
clean-host/canonical Dockerfile build. Only this script's container/volume are removed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import tempfile
import time
import httpx
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--build',action='store_true');parser.add_argument('--image',default='foxory-intelligence-app:phase4-python-verified');args=parser.parse_args()
def docker(*command,**kwargs):return subprocess.run(['docker','--host=unix:///var/run/docker.sock',*command],check=True,**kwargs)
if args.build:
    with tempfile.TemporaryDirectory(prefix='foxory-phase4-image-') as directory:
        context=Path(directory);filesystem=context/'rootfs'
        shutil.copytree(ROOT/'backend',filesystem/'app/backend',ignore=shutil.ignore_patterns('__pycache__','.pytest_cache','*.pyc','*.egg-info','data'))
        shutil.copytree(ROOT/'frontend/dist',filesystem/'app/frontend/dist')
        notices=filesystem/'usr/share/doc/foxory';notices.mkdir(parents=True)
        for name in ['LICENSE','NOTICE','THIRD_PARTY_NOTICES.txt']:shutil.copyfile(ROOT/name,notices/name)
        (context/'Dockerfile').write_text('FROM foxory-intelligence-app:phase3-final\nCOPY --chown=10001:10001 rootfs/ /\n')
        docker('build','--pull=false','-t',args.image,str(context))
name='foxory-phase4-smoke-'+secrets.token_hex(4);volume=name+'-data';token=secrets.token_urlsafe(40)
created=False
try:
    docker('run','-d','--name',name,'--init','--read-only','--tmpfs','/tmp:size=128m','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','128','--memory','1g',
           '-p','127.0.0.1:8006:8000','-e','FOXORY_TOKEN='+token,'-v',volume+':/data',args.image,stdout=subprocess.DEVNULL)
    created=True
    with httpx.Client(base_url='http://127.0.0.1:8006',headers={'Authorization':'Bearer '+token},timeout=5,trust_env=False) as client:
        def ready():
            for _ in range(150):
                try:
                    if client.get('/api/health').status_code==200:return
                except httpx.HTTPError:pass
                time.sleep(.1)
            raise RuntimeError('Disposable Docker application failed health check')
        ready()
        capability=client.get('/api/computer/capabilities');capability.raise_for_status();assert not capability.json()['enabled']
        assert client.get('/api/computer/overview').json()['jobs']==[]
        memory=client.post('/api/records/memory',json={'title':'Disposable Phase 4 persistence check','data':{'body':'No real user data'}});memory.raise_for_status();id=memory.json()['id']
        docker('restart',name,stdout=subprocess.DEVNULL);ready()
        assert any(row['id']==id for row in client.get('/api/records/memory').json())
        html=client.get('/').text;asset=re.search(r'src="(/assets/[^\"]+\.js)"',html).group(1)
        bundle=client.get(asset);bundle.raise_for_status();assert '/computer/tasks' in bundle.text
        assert hashlib.sha256(bundle.content).digest()==hashlib.sha256((ROOT/'frontend/dist'/asset.removeprefix('/')).read_bytes()).digest()
        for _ in range(50):
            inspector=json.loads(docker('inspect',name,capture_output=True,text=True).stdout)[0]
            if inspector['State'].get('Health',{}).get('Status')=='healthy':break
            if inspector['State'].get('Health',{}).get('Status')=='unhealthy':raise RuntimeError('Docker healthcheck failed')
            time.sleep(1)
        else:raise RuntimeError('Docker healthcheck did not become healthy')
        assert inspector['Config']['User'].split(':')[0]=='10001' and inspector['HostConfig']['ReadonlyRootfs']
        assert docker('exec',name,'id','-u',capture_output=True,text=True).stdout.strip()=='10001'
        assert inspector['HostConfig']['Init'] and inspector['HostConfig']['CapDrop']==['ALL']
        assert all('docker.sock' not in mount.get('Source','') for mount in inspector['Mounts'])
        for module in ['main.py','research.py','intelligence.py','inference.py','auth.py','computer_api.py','sandbox_client.py','agents.py','agent_tools.py','advanced_files.py','sandbox_protocol.py']:
            actual=docker('exec',name,'sha256sum','/app/backend/foxory/'+module,capture_output=True,text=True).stdout.split()[0]
            assert actual==hashlib.sha256((ROOT/'backend/foxory'/module).read_bytes()).hexdigest()
        image=docker('image','inspect',args.image,'--format','{{.Id}}',capture_output=True,text=True).stdout.strip()
        print(json.dumps({'image':image,'overlay_build':args.build,'health':True,'disabled_default':True,'restart_memory_persistence':True,'runtime_source_hashes':True,'frontend_bundle_hash':True,'nonroot_readonly_init_no_socket':True}))
except Exception:
    if created:docker('logs','--tail','50',name)
    raise
finally:
    if created:docker('rm','-f',name,stdout=subprocess.DEVNULL)
    docker('volume','rm',volume,stdout=subprocess.DEVNULL)
