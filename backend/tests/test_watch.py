import json,os,time
import pytest
from foxory import watch,parsing
from foxory.config import DATA
from foxory.db import Session,Record

@pytest.fixture
def folder(tmp_path,monkeypatch):
 root=tmp_path/'watched';root.mkdir()
 parsed=[]
 def extract(name,raw):parsed.append(name);return 'TEXT:'+raw.decode()
 monkeypatch.setattr(watch,'ROOT',root);monkeypatch.setattr(parsing,'isolated_extract',extract)
 watch.status.update(files=0,errors=[]);return root,parsed

def documents():
 with Session() as s:return {json.loads(r.payload)['path']:(r.id,json.loads(r.payload)) for r in s.query(Record).filter(Record.kind=='document',Record.dedupe_key.like('watch:%'))}

def test_sync_imports_updates_and_removes(folder,tmp_path):
 root,parsed=folder
 (root/'notes.md').write_text('hello');(root/'sub').mkdir();(root/'sub'/'plan.txt').write_text('plan')
 (root/'.secret.txt').write_text('hidden');(root/'.git').mkdir();(root/'.git'/'config.txt').write_text('hidden dir')
 (root/'photo.exe').write_text('unsupported');outside=tmp_path/'private.txt';outside.write_text('OUTSIDE');(root/'link.txt').symlink_to(outside)
 (root/'big.txt').write_bytes(b'x'*(10*1024*1024+1))
 status=watch.scan();docs=documents()
 assert set(docs)=={'notes.md','sub/plan.txt'} and docs['notes.md'][1]['text']=='TEXT:hello'
 assert status['files']==3 and any('big.txt' in e for e in status['errors'])
 assert (DATA/'uploads'/docs['notes.md'][0]).read_bytes()==b'hello'
 assert not any('OUTSIDE' in json.dumps(d) for _,d in docs.values())
 # Unchanged files are not parsed again.
 parsed.clear();watch.scan();assert parsed==[]
 # Edited files are re-imported in place; deleted files are removed with their stored copy.
 time.sleep(0.01);(root/'notes.md').write_text('hello again');os.utime(root/'notes.md',None)
 old_id=docs['notes.md'][0];(root/'sub'/'plan.txt').unlink()
 watch.scan();docs=documents()
 assert set(docs)=={'notes.md'} and docs['notes.md'][0]==old_id and docs['notes.md'][1]['text']=='TEXT:hello again'
 assert not any((DATA/'uploads').glob('missing'))

def test_long_paths_are_reported_not_fatal(folder):
 root,_=folder
 deep=root/('d'*120)/('e'*120);deep.mkdir(parents=True);(deep/(('f'*60)+'.txt')).write_text('long');(root/'ok.txt').write_text('ok')
 status=watch.scan()
 assert set(documents())=={'ok.txt'} and any('longer than 290' in e for e in status['errors'])

async def test_status_only_for_local_workspace(client,folder):
 watch.scan()
 data=(await client.get('/api/watch/status')).json()
 assert data['workspace']=='local' and 'files' in data
