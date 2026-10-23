"""Verify local Compose PostgreSQL logical restore into a disposable database."""
import os
from pathlib import Path
import subprocess
import tempfile
from uuid import uuid4, UUID
from smoke import request, root

def compose(*args,**kwargs):
    return subprocess.run(['docker','compose','exec','-T','db',*args],cwd=root,check=True,**kwargs)

if __name__=='__main__':
    record=request('/records/memory','POST',{'title':'Fictional restore verification','data':{'body':'Disposable test record'}})
    id=str(UUID(record['id']))
    database='foxory_verify_'+uuid4().hex[:12]
    created=False
    try:
        compose('createdb','-U','foxory',database);created=True
        with tempfile.TemporaryDirectory(prefix='foxory-pg-verify-') as folder:
            dump=Path(folder)/'workspace.dump'
            with dump.open('wb') as f:compose('pg_dump','-U','foxory','-d','foxory','-Fc',stdout=f)
            dump.chmod(0o600)
            with dump.open('rb') as f:compose('pg_restore','-U','foxory','-d',database,stdin=f)
            result=compose('psql','-U','foxory','-d',database,'-At','-c',f"SELECT count(*) FROM records WHERE id='{id}'",capture_output=True,text=True)
            assert result.stdout.strip()=='1','Restored record was not found'
            version=compose('psql','-U','foxory','-d',database,'-At','-c','SELECT version_num FROM alembic_version',capture_output=True,text=True)
            assert version.stdout.strip()=='0002'
        print('PASS: PostgreSQL custom-format dump/restore, record preservation and migration revision 0002')
    finally:
        if created:compose('dropdb','-U','foxory',database)
        request('/records/'+id,'DELETE')
