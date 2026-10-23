import os
import subprocess
import sys
import sqlite3

def test_migration_roundtrip(tmp_path):
    db=tmp_path/'migrate.db'
    env={**os.environ,'DATABASE_URL':'sqlite:///'+str(db)}
    def run(*args):subprocess.run([sys.executable,'-m','alembic',*args],env=env,check=True,capture_output=True)
    run('upgrade','head')
    with sqlite3.connect(db) as c:
        c.execute("INSERT INTO records (id,kind,workspace,title,payload,created_at,updated_at) VALUES ('id','memory','local','Preserved','{}','now','now')")
    run('upgrade','head')
    with sqlite3.connect(db) as c:assert c.execute('SELECT title FROM records').fetchone()[0]=='Preserved'
    run('downgrade','base')
    run('upgrade','head')
    with sqlite3.connect(db) as c:assert c.execute('SELECT count(*) FROM records').fetchone()[0]==0
