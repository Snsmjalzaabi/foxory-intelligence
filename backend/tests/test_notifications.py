import json
from datetime import datetime,timedelta,timezone
import httpx
from foxory import notifications
from foxory.db import Session,Record
from foxory.scope import system_scope
from tests.test_accounts import setup

def ago(**kw):return (datetime.now(timezone.utc)-timedelta(**kw)).isoformat()

def job(title,creator,status,when=None,workspace='local',**extra):
 return Record(kind='job',title=title,workspace=workspace,updated_at=when or ago(minutes=1),payload=json.dumps({'creator_id':creator,'status':status,**extra}))

async def test_feed_lists_only_my_recent_finished_tasks(client):
 me=(await setup(client))['id']
 with system_scope(),Session() as s:
  s.add_all([job('Weekly summary',me,'completed',schedule_id='s1',result='Here is the summary '*20),job('Broken run',me,'failed',error='Model unavailable'),
   job('Needs OK',me,'awaiting_approval'),job('Still running',me,'running'),job('Someone else',"other-user",'completed'),
   job('Old one',me,'completed',when=ago(days=8)),job('Other workspace',me,'completed',workspace='elsewhere')]);s.commit()
 data=(await client.get('/api/notifications')).json()
 items={i['title']:i for i in data['items']}
 assert set(items)=={'Weekly summary','Broken run','Needs OK'} and data['push'] is False
 assert items['Weekly summary']['origin']=='schedule' and len(items['Weekly summary']['summary'])==160
 assert items['Broken run']['summary']=='Model unavailable' and items['Needs OK']['summary']=='Waiting for your approval'

class FakeNtfy:
 sent=[];fail=False
 def __init__(self,*a,**kw):pass
 async def __aenter__(self):return self
 async def __aexit__(self,*a):pass
 async def post(self,url,content=None,headers=None):
  if FakeNtfy.fail:raise httpx.ConnectError('down')
  FakeNtfy.sent.append(content.decode());return httpx.Response(200,request=httpx.Request('POST',url))

async def test_push_sends_titles_once_and_retries_after_failure(client,monkeypatch,tmp_path):
 monkeypatch.setattr(notifications,'NTFY_URL','http://192.168.1.10:8080/foxory')
 monkeypatch.setattr(notifications,'STATE',tmp_path/'notify-state.json');monkeypatch.setattr(notifications.httpx,'AsyncClient',FakeNtfy);FakeNtfy.sent=[]
 with system_scope(),Session() as s:s.add(job('Old history','u','completed',when=ago(hours=1),schedule_id='s'));s.commit()
 # First run only records where to start; older history is not pushed.
 assert await notifications.push_pending()==0 and FakeNtfy.sent==[]
 with system_scope(),Session() as s:
  s.add_all([job('Daily brief','u','completed',when=ago(seconds=-5),schedule_id='s',result='PRIVATE CONTENT'),job('Chat task','u','completed',when=ago(seconds=-6)),
   job('Project draft','u','failed',when=ago(seconds=-7),automation=True)]);s.commit()
 FakeNtfy.fail=True
 assert await notifications.push_pending()==0
 FakeNtfy.fail=False
 assert await notifications.push_pending()==2
 assert FakeNtfy.sent==['Daily brief finished.','Project draft failed.'] and not any('PRIVATE' in m for m in FakeNtfy.sent)
 assert await notifications.push_pending()==0 and len(FakeNtfy.sent)==2
 assert oct((tmp_path/'notify-state.json').stat().st_mode&0o777)=='0o600'
