"""Real PostgreSQL migration/persistence/restore in disposable local Docker resources.

Never connects to the owner's application or database. Uses the existing local
postgres:17-bookworm image with --pull=never and removes only its own resources.
"""
from __future__ import annotations
import json
import argparse
import re
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--image',default='postgres:17-bookworm',help='Explicit reviewed local image (never pulled here)')
parser.add_argument('--restore-image',default='',help='Optional reviewed immutable target for separate logical restore; never reuse the source volume')
args=parser.parse_args()
for image in [args.image,args.restore_image]:
    if image and image!='postgres:17-bookworm' and not re.fullmatch(r'sha256:[a-f0-9]{64}',image):
        raise ValueError('Reviewed immutable image ID required')
name='foxory-phase4-pg-'+secrets.token_hex(5)
volume=name+'-data';password=secrets.token_urlsafe(30)
restore_name=name+'-restore';restore_volume=restore_name+'-data';restore_created=False
guard_name=name+'-guard';guard_verified=False
env={**os.environ,'POSTGRES_PASSWORD':password,'PGPASSWORD':password}

def docker(*args,**kwargs):
    kwargs.setdefault('check',True)
    return subprocess.run(['docker','--host=unix:///var/run/docker.sock',*args],env=env,timeout=30,**kwargs)

def ready(container=name):
    deadline=time.monotonic()+90
    while time.monotonic()<deadline:
        state=docker('inspect',container,'--format','{{.State.Status}}',capture_output=True,text=True).stdout.strip()
        if state in {'exited','dead'}:raise RuntimeError('Disposable PostgreSQL exited during startup')
        # initdb's temporary server accepts socket connections before createdb.
        # Require the final TCP listener AND an actual query in the requested DB.
        check=subprocess.run(['docker','--host=unix:///var/run/docker.sock','exec','-e','PGPASSWORD',container,
                             'psql','-h','127.0.0.1','-U','foxory','-d','foxory','-At','-v','ON_ERROR_STOP=1','-c','SELECT 1'],
                             env=env,capture_output=True,text=True,timeout=10)
        if check.returncode==0 and check.stdout.strip()=='1':return
        time.sleep(.5)
    raise RuntimeError('Disposable PostgreSQL did not become ready')

created=False
try:
    docker('run','-d','--pull=never','--name',name,'-e','POSTGRES_USER=foxory','-e','POSTGRES_DB=foxory',
           '-e','POSTGRES_PASSWORD','-p','127.0.0.1::5432','--memory=512m','--pids-limit=128',
           '--security-opt=no-new-privileges','-v',volume+':/var/lib/postgresql/data',args.image,stdout=subprocess.DEVNULL)
    created=True;ready()
    version=int(docker('exec',name,'psql','-U','foxory','-d','foxory','-At','-c','SHOW server_version_num',capture_output=True,text=True).stdout.strip())
    assert 170000<=version<180000,'Only PostgreSQL major 17 is supported by this smoke'
    inspection=json.loads(docker('inspect',name,capture_output=True,text=True).stdout)[0]
    port=inspection['NetworkSettings']['Ports']['5432/tcp'][0]['HostPort']
    with tempfile.TemporaryDirectory(prefix='foxory-pg-smoke-') as directory:
        testenv={**os.environ,'DATABASE_URL':f'postgresql+psycopg://foxory:{password}@127.0.0.1:{port}/foxory',
                 'FOXORY_DATA_DIR':directory,'FOXORY_TOKEN':secrets.token_urlsafe(30)}
        subprocess.run([sys.executable,'-m','alembic','upgrade','head'],cwd=ROOT/'backend',env=testenv,check=True,stdout=subprocess.DEVNULL)
        # Test tenancy uniqueness and application-independent persistence using
        # the actual ORM and workspace guards, never owner records.
        code='''import json
from sqlalchemy.exc import IntegrityError
from foxory.db import Session,Record,get_record,User,Membership,LoginSession
from foxory.auth import passwords
from foxory.scope import workspace_id
workspace_id.set('local')
with Session() as s:
 user=User(username='migration-fixture',password_hash=passwords.hash('fictional migration password'))
 s.add(user);s.flush();s.add(Membership(workspace_id='local',user_id=user.id,role='admin'))
 s.add(LoginSession(token_hash='a'*64,user_id=user.id,expires_at='2099-01-01T00:00:00+00:00',csrf='fixture-csrf'))
 s.add(Record(kind='approval',title='Fictional consumed approval',payload=json.dumps({'status':'consumed','context_hash':'fictional-immutable-hash'}),dedupe_key='migration-approval'))
 r=Record(kind='memory',title='Disposable PostgreSQL evidence',payload=json.dumps({'body':'fictional smoke data'}),dedupe_key='pg-smoke')
 s.add(r);s.commit();id=r.id
 try:
  s.add(Record(kind='memory',title='Duplicate',payload='{}',dedupe_key='pg-smoke'));s.commit()
 except IntegrityError:s.rollback()
 else:raise AssertionError('Duplicate constraint missing')
 workspace_id.set('unrelated-workspace')
 try:get_record(s,id,'memory')
 except Exception as e:assert getattr(e,'status_code',None)==404
 else:raise AssertionError('Tenant boundary missing')
print(id)
'''
        id=subprocess.run([sys.executable,'-c',code],cwd=ROOT/'backend',env=testenv,check=True,capture_output=True,text=True).stdout.strip()
        docker('restart',name,stdout=subprocess.DEVNULL);ready()
        count=docker('exec',name,'psql','-U','foxory','-d','foxory','-At','-v','ON_ERROR_STOP=1','-c',
                     "SELECT count(*) FROM records WHERE dedupe_key='pg-smoke'",capture_output=True,text=True).stdout.strip()
        assert count=='1','PostgreSQL restart lost fictional record'
        dump=Path(directory)/'database.dump'
        with dump.open('wb') as output:docker('exec',name,'pg_dump','-U','foxory','-d','foxory','-Fc',stdout=output)
        dump.chmod(0o600)
        target=name
        if args.restore_image:
            # The new entrypoint must refuse physical reuse BEFORE chmod/chown
            # or recovery can alter even this fictional legacy cluster.
            uid=docker('exec',name,'id','-u','postgres',capture_output=True,text=True).stdout.strip()
            gid=docker('exec',name,'id','-g','postgres',capture_output=True,text=True).stdout.strip()
            docker('stop',name,stdout=subprocess.DEVNULL)
            def snapshot():
                return docker('run','--rm','--pull=never','--user='+uid+':'+gid,
                    '--read-only','--network=none','--cap-drop=ALL','--security-opt=no-new-privileges',
                    '--memory=128m','--pids-limit=32','--entrypoint=sh','-v',volume+':/snapshot:ro',args.image,
                    '-c','cd /snapshot && find . -type f -exec sha256sum {} + && find . -exec stat -c "%n|%u|%g|%a|%s|%Y" {} +',
                    capture_output=True,text=True).stdout.splitlines()
            before=sorted(snapshot())
            rejected=docker('run','--rm','--pull=never','--name',guard_name,'--network=none',
                '--memory=512m','--pids-limit=128','--security-opt=no-new-privileges',
                '-v',volume+':/var/lib/postgresql/data',args.restore_image,check=False,capture_output=True,text=True)
            assert rejected.returncode==78 and 'FOXORY_DATABASE_LAYOUT_MISMATCH' in rejected.stderr,rejected.stderr
            assert sorted(snapshot())==before,'Legacy cluster bytes/ownership/modes changed'
            guard_verified=True
            docker('run','-d','--pull=never','--name',restore_name,'-e','POSTGRES_USER=foxory','-e','POSTGRES_DB=foxory',
                '-e','POSTGRES_PASSWORD','-p','127.0.0.1::5432','--memory=512m','--pids-limit=128','--security-opt=no-new-privileges',
                '-v',restore_volume+':/var/lib/postgresql/data',args.restore_image,stdout=subprocess.DEVNULL)
            restore_created=True;ready(restore_name);target=restore_name
        docker('exec',target,'createdb','-U','foxory','restored')
        with dump.open('rb') as source:docker('exec','-i',target,'pg_restore','-U','foxory','-d','restored',stdin=source)
        result=docker('exec',target,'psql','-U','foxory','-d','restored','-At','-v','ON_ERROR_STOP=1','-c',
                     "SELECT count(*) FROM records WHERE dedupe_key='pg-smoke'; SELECT version_num FROM alembic_version",capture_output=True,text=True).stdout.strip().splitlines()
        assert result==['1','0003'],result
        restored_port=json.loads(docker('inspect',target,capture_output=True,text=True).stdout)[0]['NetworkSettings']['Ports']['5432/tcp'][0]['HostPort']
        restored_env={**testenv,'DATABASE_URL':f'postgresql+psycopg://foxory:{password}@127.0.0.1:{restored_port}/restored'}
        verify='''import json
from sqlalchemy import select
from foxory.auth import passwords
from foxory.db import Session,User,Membership,LoginSession,Record,get_record
from foxory.scope import workspace_id
workspace_id.set('local')
with Session() as s:
 user=s.scalar(select(User).where(User.username=='migration-fixture'))
 assert passwords.verify(user.password_hash,'fictional migration password')
 assert s.get(Membership,('local',user.id)).role=='admin'
 assert s.get(LoginSession,'a'*64).csrf=='fixture-csrf'
 approval=s.scalar(select(Record).where(Record.dedupe_key=='migration-approval'))
 assert json.loads(approval.payload)=={'status':'consumed','context_hash':'fictional-immutable-hash'}
 workspace_id.set('unrelated-workspace')
 try:get_record(s,approval.id,'approval')
 except Exception as e:assert getattr(e,'status_code',None)==404
 else:raise AssertionError('Restored tenant boundary missing')
'''
        subprocess.run([sys.executable,'-c',verify],cwd=ROOT/'backend',env=restored_env,check=True)
    print(json.dumps({'postgresql':'17','image':args.image,'migration':'0003','workspace_isolation':True,'duplicate_constraint':True,
                      'restart_persistence':True,'dump_restore':True,'restore_image':args.restore_image or args.image,
                      'separate_restore_volume':bool(args.restore_image),'legacy_physical_reuse_denied_unchanged':guard_verified,
                      'account_membership_session_approval_restored':True,'owner_database_accessed':False}))
except Exception:
    if created:
        # Inspect only state, never Config.Env (which holds the disposable secret).
        subprocess.run(['docker','--host=unix:///var/run/docker.sock','inspect',name,
                        '--format','{{json .State}}'],check=False)
        subprocess.run(['docker','--host=unix:///var/run/docker.sock','logs','--tail','60',name],check=False)
    raise
finally:
    subprocess.run(['docker','--host=unix:///var/run/docker.sock','rm','-f',guard_name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    if restore_created:docker('rm','-f',restore_name,stdout=subprocess.DEVNULL)
    if created:docker('rm','-f',name,stdout=subprocess.DEVNULL)
    # The volume has a unique per-invocation prefix, never an owner volume.
    subprocess.run(['docker','--host=unix:///var/run/docker.sock','volume','rm',volume],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    if args.restore_image:subprocess.run(['docker','--host=unix:///var/run/docker.sock','volume','rm',restore_volume],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
