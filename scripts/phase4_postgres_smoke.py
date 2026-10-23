"""Real PostgreSQL migration/persistence/restore in disposable local Docker resources.

Never connects to the owner's application or database. Uses the existing local
postgres:17-bookworm image with --pull=never and removes only its own resources.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
name='foxory-phase4-pg-'+secrets.token_hex(5)
volume=name+'-data';password=secrets.token_urlsafe(30)
env={**os.environ,'POSTGRES_PASSWORD':password}

def docker(*args,**kwargs):
    return subprocess.run(['docker','--host=unix:///var/run/docker.sock',*args],check=True,env=env,**kwargs)

def ready():
    deadline=time.monotonic()+90
    while time.monotonic()<deadline:
        state=docker('inspect',name,'--format','{{.State.Status}}',capture_output=True,text=True).stdout.strip()
        if state in {'exited','dead'}:raise RuntimeError('Disposable PostgreSQL exited during startup')
        check=subprocess.run(['docker','--host=unix:///var/run/docker.sock','exec',name,'pg_isready','-U','foxory','-d','foxory'],
                             stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10)
        if check.returncode==0:return
        time.sleep(.5)
    raise RuntimeError('Disposable PostgreSQL did not become ready')

created=False
try:
    docker('run','-d','--pull=never','--name',name,'-e','POSTGRES_USER=foxory','-e','POSTGRES_DB=foxory',
           '-e','POSTGRES_PASSWORD','-p','127.0.0.1::5432','--memory=512m','--pids-limit=128',
           '--security-opt=no-new-privileges','-v',volume+':/var/lib/postgresql/data','postgres:17-bookworm',stdout=subprocess.DEVNULL)
    created=True;ready()
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
from foxory.db import Session,Record,get_record
from foxory.scope import workspace_id
workspace_id.set('local')
with Session() as s:
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
        docker('exec',name,'createdb','-U','foxory','restored')
        with dump.open('rb') as source:docker('exec','-i',name,'pg_restore','-U','foxory','-d','restored',stdin=source)
        result=docker('exec',name,'psql','-U','foxory','-d','restored','-At','-v','ON_ERROR_STOP=1','-c',
                     "SELECT count(*) FROM records WHERE dedupe_key='pg-smoke'; SELECT version_num FROM alembic_version",capture_output=True,text=True).stdout.strip().splitlines()
        assert result==['1','0003'],result
    print(json.dumps({'postgresql':'17','migration':'0003','workspace_isolation':True,'duplicate_constraint':True,
                      'restart_persistence':True,'dump_restore':True,'owner_database_accessed':False}))
except Exception:
    if created:
        # Inspect only state, never Config.Env (which holds the disposable secret).
        subprocess.run(['docker','--host=unix:///var/run/docker.sock','inspect',name,
                        '--format','{{json .State}}'],check=False)
        subprocess.run(['docker','--host=unix:///var/run/docker.sock','logs','--tail','60',name],check=False)
    raise
finally:
    if created:docker('rm','-f',name,stdout=subprocess.DEVNULL)
    # The volume has a unique per-invocation prefix, never an owner volume.
    subprocess.run(['docker','--host=unix:///var/run/docker.sock','volume','rm',volume],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
