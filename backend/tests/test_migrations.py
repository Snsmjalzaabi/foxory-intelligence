import os
import subprocess
import sys
import sqlite3
from pathlib import Path
BACKEND=Path(__file__).resolve().parents[1]

def test_migration_roundtrip(tmp_path):
    db=tmp_path/'migrate.db'
    env={**os.environ,'DATABASE_URL':'sqlite:///'+str(db)}
    def run(*args):subprocess.run([sys.executable,'-m','alembic',*args],env=env,cwd=BACKEND,check=True,capture_output=True)
    run('upgrade','head')
    with sqlite3.connect(db) as c:
        c.execute("INSERT INTO records (id,kind,workspace,title,payload,created_at,updated_at) VALUES ('id','memory','local','Preserved','{}','now','now')")
    run('upgrade','head')
    with sqlite3.connect(db) as c:assert c.execute('SELECT title FROM records').fetchone()[0]=='Preserved'
    run('downgrade','base')
    run('upgrade','head')
    with sqlite3.connect(db) as c:assert c.execute('SELECT count(*) FROM records').fetchone()[0]==0

def test_duplicate_preflight_leaves_schema_unchanged(tmp_path):
    db=tmp_path/'duplicates.db';env={**os.environ,'DATABASE_URL':'sqlite:///'+str(db)}
    def run(*args,check=True):return subprocess.run([sys.executable,'-m','alembic',*args],env=env,cwd=BACKEND,check=check,capture_output=True)
    run('upgrade','0001')
    with sqlite3.connect(db) as c:
        for id in ['a','b']:c.execute('INSERT INTO records (id,kind,workspace,title,payload,created_at,updated_at) VALUES (?,?,?,?,?,?,?)',(id,'lead','local','Duplicate','{}','now','now'))
    failed=run('upgrade','head',check=False)
    assert failed.returncode!=0
    with sqlite3.connect(db) as c:
        assert 'dedupe_key' not in [r[1] for r in c.execute('PRAGMA table_info(records)')]
        assert c.execute('SELECT count(*) FROM records').fetchone()[0]==2
        c.execute("DELETE FROM records WHERE id='b'")
    run('upgrade','head')
    with sqlite3.connect(db) as c:assert c.execute('SELECT dedupe_key FROM records').fetchone()[0]
