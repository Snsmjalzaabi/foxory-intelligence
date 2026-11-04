"""Real-model acceptance: routing across Ollama and the CPU companion, conversational learning and skill drafts.

Run against a real local Ollama (and llama.cpp lite profile) before a release; uses a disposable database.
"""
import json,os,secrets,socket,subprocess,sys,tempfile,time
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[1]
def main():
 report={'version':'7.0.0','real_ollama':True,'owner_data_used':False,'checks':[],'routes':[]}
 with tempfile.TemporaryDirectory(prefix='foxory-v6-') as folder:
  p=Path(folder);token=secrets.token_urlsafe(40)
  with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
  env={**os.environ,'FOXORY_TOKEN':token,'FOXORY_DATA_DIR':str(p/'data'),'DATABASE_URL':'sqlite:///'+str(p/'db.sqlite'),'OLLAMA_URL':'http://127.0.0.1:11434','FOXORY_ENABLE_SANDBOX':'0'}
  env.update(FOXORY_LLAMA_URL='http://127.0.0.1:11436',FOXORY_LLAMA_API_KEY=(ROOT/'.local-ai/evaluation.env').read_text().strip().split('=',1)[1])
  with (p/'log').open('w') as log:
   subprocess.run([sys.executable,'-m','alembic','upgrade','head'],cwd=ROOT/'backend',env=env,stdout=log,stderr=log,check=True)
   process=subprocess.Popen([sys.executable,'-m','uvicorn','foxory.main:app','--host','127.0.0.1','--port',str(port),'--no-access-log'],cwd=ROOT/'backend',env=env,stdout=log,stderr=log)
   try:
    with httpx.Client(base_url=f'http://127.0.0.1:{port}/api',timeout=240,trust_env=False) as c:
     def call(method,path,**kw):r=c.request(method,path,**kw);r.raise_for_status();return None if r.status_code==204 else r.json()
     def passed(text):report['checks'].append(text);print('PASS '+text,flush=True)
     for _ in range(150):
      try:
       if c.get('/health',timeout=1).status_code==200:break
      except httpx.HTTPError:pass
      time.sleep(.1)
     auth=call('POST','/auth/setup',json={'username':'v6-evaluation-owner','password':secrets.token_urlsafe(24),'bootstrap_token':token});c.headers['X-CSRF-Token']=auth['csrf'];c.headers['X-Workspace-ID']='local'
     cases=[('Hello. Reply with one short greeting.','auto','llama.cpp/qwen2.5-1.5b-instruct-q4_k_m','chat'),('Explain a Python list comprehension in one sentence.','auto','qwen2.5-coder:7b','coding'),('Compare the tradeoffs of two ways to prioritize a small project. Keep it brief.','auto','qwen3:8b','reasoning'),('Tell a tiny fictional story in two sentences.','auto','llama.cpp/qwen2.5-1.5b-instruct-q4_k_m','writing'),('Tell a complete fictional story in two concise sentences.','auto','qwen2.5:7b','writing'),('Explain a Python dictionary briefly.','qwen2.5:7b','qwen2.5:7b','coding')]
     for prompt,requested,expected,kind in ([] if os.getenv('FOXORY_TEST_SKILL_ONLY') else cases):
      conversation=call('POST','/records/conversation',json={'title':'Disposable routing check'})
      response=c.post('/conversations/'+conversation['id']+'/chat',json={'content':prompt,'model':requested,'temperature':0,'max_output':128});response.raise_for_status()
      message=call('GET','/conversations/'+conversation['id']+'/messages')[-1];meta=message['metadata'];route=meta['model_route']
      assert meta['status'] in {'complete','truncated'} and meta['model']==expected and route['model']==expected and route['category']==kind and route['automatic']==(requested=='auto'),message
      assert meta.get('eval_count',0)>0 and message['content'];report['routes'].append({'requested':requested,'selected':meta['model'],'category':kind,'output_tokens':meta['eval_count'],'automatic':route['automatic']});passed('actual local '+kind+' inference uses '+expected+(' automatically' if requested=='auto' else ' by manual override'))
     status=call('GET','/ai/status');assert status['providers']['llama.cpp']['available'] and status['providers']['ollama']['available']
     call('PUT','/ai/policy',json={**status['policy'],'background_enabled':False})
     conv=call('POST','/records/conversation',json={'title':'Small model skill test'})
     r=call('POST','/conversations/'+conv['id']+'/command',json={'content':'Create a skill to write one short three-item checklist from saved project context','model':'llama.cpp/qwen2.5-1.5b-instruct-q4_k_m'});assert r['status']=='testing';print(json.dumps({'skill':next(x for x in call('GET','/skills') if x['id']==r['record_id'])['data']}),flush=True)
     time.sleep(2);activity=call('GET','/conversations/'+conv['id']+'/activity');assert activity[0]['status']=='queued';passed('background pause leaves the requested skill queued without stopping foreground chat')
     call('PUT','/ai/policy',json={**status['policy'],'background_enabled':True})
     end=time.monotonic()+240
     while time.monotonic()<end:
      activity=call('GET','/conversations/'+conv['id']+'/activity')
      if activity and activity[0].get('skill_status')=='active':break
      if activity and activity[0]['status']=='failed':
       print(json.dumps({'jobs':call('GET','/records/job')}),flush=True);raise AssertionError(activity)
      time.sleep(2)
     assert activity[0].get('skill_status')=='active',activity;passed('real CPU model produces a schema-valid skill, executes its test and activates after background resume')
     usage=call('GET','/ai/status')['usage'];assert usage['providers'].get('llama.cpp',0)>0 and usage['background_calls']>0;report['usage']=usage
     report['status']='passed' ;(ROOT.parent/'release-evidence/v7-real-ai.json').write_text(json.dumps(report,indent=2)+'\n')
   finally:
    process.terminate()
    try:process.wait(timeout=15)
    except subprocess.TimeoutExpired:process.kill();process.wait()
if __name__=='__main__':main()
