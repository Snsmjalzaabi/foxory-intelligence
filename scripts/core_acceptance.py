"""Opt-in real core-product acceptance, with Computer Mode explicitly disabled.

Uses fresh private SQLite/data, actual Ollama models and public Wikipedia search.
Never contacts the owner's application, imports model fixtures, downloads models,
executes generated code or starts a sandbox manager. Uses existing dependencies.
Run: .venv/bin/python scripts/core_acceptance.py --ollama-url http://LOCAL:11434
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import secrets
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import zipfile

import httpx

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ollama-url', required=True)
    parser.add_argument('--model', default='qwen2.5:0.5b')
    parser.add_argument('--council-model', default='smollm2:135m')
    parser.add_argument('--embedding-model', default='nomic-embed-text:latest')
    parser.add_argument('--evidence', type=Path)
    args = parser.parse_args()
    evidence: dict = {'real_ollama': True, 'real_web': True, 'fixtures': False,
                      'sandbox_enabled': False, 'checks': [], 'models': [args.model, args.council_model]}
    def passed(name, **detail):
        evidence['checks'].append({'name': name, **detail})
        print('PASS: '+name, flush=True)

    # Read-only discovery: never automatically pull weights or mutate endpoints.
    with httpx.Client(base_url=args.ollama_url.rstrip('/'), trust_env=False, timeout=10) as ollama:
        result = ollama.get('/api/tags'); result.raise_for_status()
        installed = {m['name'] for m in result.json()['models']}
    required = {args.model, args.council_model, args.embedding_model}
    if missing := required-installed:
        raise RuntimeError('Install/review the requested models explicitly first: '+', '.join(sorted(missing)))
    if args.model == args.council_model:
        raise ValueError('Council acceptance requires two distinct installed models')

    with tempfile.TemporaryDirectory(prefix='foxory-core-acceptance-') as directory:
        private = Path(directory); private.chmod(0o700)
        database = private/'core.db'; token = secrets.token_urlsafe(40)
        with socket.socket() as reservation:
            reservation.bind(('127.0.0.1', 0)); port = reservation.getsockname()[1]
        env = {**os.environ, 'FOXORY_DATA_DIR':str(private/'data'),
               'DATABASE_URL':'sqlite:///'+str(database), 'FOXORY_TOKEN':token,
               'OLLAMA_URL':args.ollama_url.rstrip('/'), 'SEARXNG_URL':'',
               'FOXORY_ENABLE_SANDBOX':'0', 'FOXORY_SANDBOX_URL':'', 'FOXORY_SANDBOX_KEY':'',
               'FOXORY_BACKGROUND_CONTEXT':'2048', 'FOXORY_BACKGROUND_OUTPUT':'256',
               'FOXORY_INFERENCE_THREADS':'2', 'FOXORY_WORKER_CONCURRENCY':'1',
               'FOXORY_ALLOW_PARALLEL_COUNCIL':'0'}
        log = (private/'app.log').open('w')
        process = None
        client = httpx.Client(base_url=f'http://127.0.0.1:{port}/api', trust_env=False, timeout=180)
        def call(method, path, **kwargs):
            response = client.request(method, path, **kwargs); response.raise_for_status()
            return response.json() if 'application/json' in response.headers.get('content-type','') else response
        def start():
            nonlocal process
            process = subprocess.Popen([sys.executable,'-m','uvicorn','foxory.main:app',
                                        '--host','127.0.0.1','--port',str(port),'--no-access-log'],
                                       env=env, cwd=ROOT/'backend', stdout=log, stderr=log)
            for _ in range(150):
                if process.poll() is not None: raise RuntimeError('Disposable core exited during startup')
                try:
                    if client.get('/health', timeout=2).status_code == 200: return
                except httpx.HTTPError: pass
                time.sleep(.1)
            raise RuntimeError('Disposable core did not become healthy')
        def stop():
            if process is not None and process.poll() is None:
                process.terminate()
                try: process.wait(timeout=15)
                except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)
        def finish(id):
            deadline = time.monotonic()+900
            while time.monotonic() < deadline:
                value = next(r['data'] for r in call('GET','/records/job') if r['id']==id)
                if value['status'] in {'completed','failed','cancelled','awaiting_approval'}:
                    if value['status'] != 'completed':
                        raise AssertionError({k:value.get(k) for k in ['status','stage','error','error_detail']})
                    return value
                time.sleep(1)
            raise TimeoutError('Bounded core acceptance task did not finish')
        def chat(id, text, mode='chat'):
            response = call('POST',f'/conversations/{id}/chat',json={
                'content':text, 'model':args.model, 'context':2048, 'max_output':128, 'temperature':0, 'mode':mode})
            frames = []
            for block in response.text.split('\n\n'):
                event = next((s[7:] for s in block.splitlines() if s.startswith('event: ')), '')
                data = next((s[6:] for s in block.splitlines() if s.startswith('data: ')), '')
                if data: frames.append((event,json.loads(data)))
            assert frames and not any(event=='error' for event, _ in frames), frames[-1:]
            answer = ''.join(data for event,data in frames if event=='delta')
            assert answer.strip()
            return answer, next(data for event,data in frames if event=='done')
        try:
            subprocess.run([sys.executable,'-m','alembic','upgrade','head'],env=env,
                           cwd=ROOT/'backend',check=True,stdout=log,stderr=log)
            start()
            credentials = {'username':'core-verification-owner','password':secrets.token_urlsafe(30)}
            setup = call('POST','/auth/setup',json={**credentials,'bootstrap_token':token})
            client.headers['X-CSRF-Token'] = setup['csrf']
            identity = call('GET','/auth/me'); original = identity['workspace_id']
            client.headers['X-Workspace-ID'] = original
            assert call('GET','/models')['available']
            assert not call('GET','/computer/capabilities')['enabled']
            passed('fresh account, model discovery and core startup without sandbox manager')

            conversation = call('POST','/records/conversation',json={'title':'Disposable real core conversation'})
            answer, metadata = chat(conversation['id'],'Reply with exactly the word LOCAL.')
            messages = call('GET',f'/conversations/{conversation["id"]}/messages')
            assert len(messages)==2 and messages[-1]['content']==answer
            assert call('GET',f'/conversations/{conversation["id"]}/export').content
            passed('real streaming local chat, saved history and conversation export', model=args.model)

            doc = call('POST','/documents',files={'file':('core-evidence.txt',
                b'This fictional evaluation dataset records 123 units of revenue in June. It is test data, not a real business record.','text/plain')})
            rejected = client.post('/documents',files={'file':('invalid.json',b'{','application/json')})
            assert rejected.status_code==422
            call('POST',f'/documents/{doc["id"]}/index',json={'model':args.embedding_model})
            retrieved = call('GET','/documents/retrieve',params={'q':'What was revenue in June?','model':args.embedding_model})
            assert retrieved and retrieved[0]['document_id']==doc['id']
            qa = call('POST','/records/conversation',json={'title':'Disposable document question'})
            _, grounded = chat(qa['id'],'What was revenue in June? Answer briefly with a [1] source citation.','documents')
            assert grounded['sources'] and grounded['sources'][0]['document_id']==doc['id']
            assert grounded['citation_verification']['valid'], 'Document Q&A returned unsupported prose'
            passed('isolated upload parsing, invalid-file rejection, real embeddings and document Q&A',
                   embedding_model=args.embedding_model, citation_verification=grounded.get('citation_verification'))

            research = call('POST','/records/conversation',json={'title':'Disposable real internet search'})
            _, web = chat(research['id'],'What is retrieval augmented generation?','research')
            assert web['sources'] and all(s['evidence_type']=='retrieved_page' for s in web['sources'])
            assert web['citation_verification']['valid'], 'Search chat returned unsupported prose'
            evidence['web_sources'] = [{'url':s['url'],'content_hash':s['content_hash']} for s in web['sources']]
            passed('real default internet search and public-page retrieval', citation_verification=web.get('citation_verification'))

            research_request = {'type':'research','prompt':'retrieval augmented generation',
                'models':[args.model],'idempotency_key':secrets.token_hex(16),
                'budget':{'max_searches':2,'max_pages':2,'max_seconds':900,'max_input_chars':8000}}
            job = call('POST','/jobs',json=research_request)
            assert call('POST','/jobs',json=research_request)['id'] == job['id']
            call('POST',f'/jobs/{job["id"]}/pause')
            call('POST',f'/jobs/{job["id"]}/resume')
            deep = finish(job['id']); assert deep['sources'] and deep['citation_verification']['valid']
            assert call('GET',f'/jobs/{job["id"]}/citations')['valid']
            for source in deep['sources']:
                assert source['content_hash']==hashlib.sha256(source['text'].encode()).hexdigest()
            for format in ['pdf','docx','xlsx']:
                result = call('GET',f'/jobs/{job["id"]}/export?format={format}').content
                if format=='pdf': assert result.startswith(b'%PDF')
                else:
                    with zipfile.ZipFile(io.BytesIO(result)) as archive: assert archive.testzip() is None
            passed('real Deep Research, pause/resume, saved citation verification and PDF/Word/XLSX export',
                   evidence_mode=deep.get('evidence_mode','model_synthesis'), used=deep['used'])
            cancelled = call('POST','/jobs',json={**research_request,'idempotency_key':secrets.token_hex(16)})
            call('POST',f'/jobs/{cancelled["id"]}/cancel')
            assert next(r['data'] for r in call('GET','/records/job') if r['id']==cancelled['id'])['status']=='cancelled'
            passed('real research duplicate prevention and durable cancellation')

            council = call('POST','/jobs',json={'type':'council','prompt':'Briefly explain one benefit and limitation of local data ownership.',
                'models':[args.model,args.council_model],'idempotency_key':secrets.token_hex(16)})
            result = finish(council['id'])
            assert len(result['analyses'])==2 and result['comparison_output'] and result['result']
            passed('real two-model sequential council, independent analyses, comparison and synthesis')

            agent = call('POST','/agents',json={'name':'Core arithmetic research helper','config':{
                'role':'Research assistant','model':args.model,'tools':['math.calculate','web.search'],'permissions':['calculate','web.read'],
                'max_steps':3,'max_model_calls':8,'step_timeout':240,'max_seconds':900}})
            task = call('POST',f'/agents/{agent["id"]}/tasks',json={
                'objective':'Use math.calculate to calculate 6*7. Return one tool step, then review the tool result.',
                'idempotency_key':secrets.token_hex(16)})
            result = finish(task['id'])
            assert any(o['result'].get('value')==42 for o in result['outputs'])
            passed('real local-model agent planning, safe tool execution and final result without computer tools')
            web_task = call('POST',f'/agents/{agent["id"]}/tasks',json={
                'objective':'Find discovery sources for retrieval augmented generation; do not treat search snippets as verified claims.',
                'plan':[{'title':'Search public discovery metadata','tool':'web.search',
                         'args':{'query':'retrieval augmented generation'}}], 'idempotency_key':secrets.token_hex(16)})
            result = finish(web_task['id'])
            assert result['outputs'][0]['result']['results']
            passed('safe research agent executes actual web search and local-model review',
                   plan_basis='explicit reviewed plan; autonomous planning checked separately with math')

            other = call('POST','/auth/workspaces',json={'name':'Disposable isolated core workspace'})
            client.headers['X-Workspace-ID'] = other['id']
            assert call('GET','/records/conversation')==[]
            assert client.get(f'/conversations/{conversation["id"]}/messages').status_code==404
            client.headers['X-Workspace-ID'] = original
            passed('workspace isolation for saved conversations and protected resources')

            # SQLite's online backup API gives a consistent database snapshot.
            backup = private/'restored.db'
            with sqlite3.connect(database) as source, sqlite3.connect(backup) as target:
                source.backup(target)
            stop(); start()
            assert call('GET','/auth/me')['id']==identity['id']
            assert len(call('GET',f'/conversations/{conversation["id"]}/messages'))==2
            assert any(r['id']==job['id'] for r in call('GET','/records/job'))
            passed('account/session, conversations and completed research survive process restart')
            stop(); env['DATABASE_URL']='sqlite:///'+str(backup); start()
            assert call('GET','/auth/me')['id']==identity['id']
            assert len(call('GET',f'/conversations/{conversation["id"]}/messages'))==2
            passed('restore consistent disposable SQLite snapshot and reopen saved account/history')
            call('POST','/auth/logout')
            assert client.get('/overview').status_code==401
            passed('server-side logout revocation')
            logged_in = call('POST','/auth/login',json=credentials)
            client.headers['X-CSRF-Token'] = logged_in['csrf']
            assert call('GET','/auth/me')['id']==identity['id']
            passed('existing account signs back in after restore and logout')
            evidence['status']='passed'
        except Exception as error:
            evidence.update(status='failed', error=type(error).__name__+': '+str(error)[:800])
            log.flush()
            print((private/'app.log').read_text()[-3000:],file=sys.stderr)
            raise
        finally:
            stop(); client.close(); log.close()
            payload=json.dumps(evidence,indent=2)
            if args.evidence: args.evidence.write_text(payload+'\n')
            print(payload,flush=True)


if __name__=='__main__': main()
