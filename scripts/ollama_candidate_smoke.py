#!/usr/bin/env python3
"""Explicit disposable CPU Ollama compatibility with free Apache-2.0 models.

Downloads qwen2.5:0.5b and nomic-embed-text into bounded temporary model storage.
No owner model directory/app/database, generated-code execution or GPU access.
The exact reviewed local immutable image must already be present. No deployment.
"""
from __future__ import annotations
import argparse
import json
import math
import os
from pathlib import Path
import re
import secrets
import subprocess
import time
import httpx


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image',required=True)
    parser.add_argument('--evidence',required=True,type=Path)
    args=parser.parse_args()
    if not re.fullmatch(r'sha256:[a-f0-9]{64}',args.image):raise ValueError('Immutable local image required')
    os.umask(0o077)
    output=args.evidence.open('x')
    nonce=secrets.token_hex(10);name='foxory-model-review-'+nonce;created=False
    report={'status':'failed','image':args.image,'models':[], 'checks':[],
            'gpu_verified':False,'owner_data_accessed':False,'model_persistence_tested':False}
    def docker(*values,**kwargs):
        kwargs.setdefault('check',True)
        return subprocess.run(['docker','--host=unix:///var/run/docker.sock',*values],timeout=30,**kwargs)
    try:
        docker('create','--pull=never','--name',name,'--label','io.foxory.smoke='+nonce,
               '--user=10001:10001','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges',
               '--memory=3g','--pids-limit=256','--cpus=2','-p','127.0.0.1::11434',
               '--tmpfs=/tmp:rw,nosuid,nodev,size=134217728,mode=1777',
               '--tmpfs=/models:rw,noexec,nosuid,nodev,size=1073741824,uid=10001,gid=10001,mode=0700',
               '-e','HOME=/tmp','-e','OLLAMA_MODELS=/models','-e','OLLAMA_HOST=0.0.0.0:11434',
               '-e','OLLAMA_MAX_LOADED_MODELS=1','-e','OLLAMA_NUM_PARALLEL=1','-e','OLLAMA_MAX_QUEUE=2',
               args.image,stdout=subprocess.DEVNULL)
        created=True;docker('start',name,stdout=subprocess.DEVNULL)
        inspection=json.loads(docker('inspect',name,capture_output=True,text=True).stdout)[0]
        port=inspection['NetworkSettings']['Ports']['11434/tcp'][0]['HostPort']
        with httpx.Client(base_url='http://127.0.0.1:'+port,trust_env=False,timeout=180) as client:
            deadline=time.monotonic()+90
            while time.monotonic()<deadline:
                try:
                    response=client.get('/api/version',timeout=2)
                    if response.status_code==200:report['version']=response.json()['version'];break
                except httpx.HTTPError:pass
                time.sleep(.2)
            else:raise TimeoutError('Disposable Ollama startup')
            def post(path,body):
                response=client.post(path,json=body);response.raise_for_status();return response.json()
            for model in ['qwen2.5:0.5b','nomic-embed-text']:
                post('/api/pull',{'model':model,'stream':False})
                info=post('/api/show',{'model':model})
                if 'apache' not in info.get('license','').lower():raise ValueError('Expected Apache model license not reported')
                report['models'].append({'name':model,'capabilities':info.get('capabilities',[]),'license_reported':'Apache (full license review remains required)'})
            response=client.get('/api/tags');response.raise_for_status()
            report['installed']=response.json()['models']
            start=time.monotonic()
            answer=post('/api/chat',{'model':'qwen2.5:0.5b','stream':False,'keep_alive':0,
                'messages':[{'role':'user','content':'Reply with exactly FOXORY_CANDIDATE_OK and nothing else.'}],
                'options':{'temperature':0,'num_ctx':512,'num_predict':64,'num_thread':2}})
            text=answer['message']['content']
            assert 'FOXORY_CANDIDATE_OK' in text,text
            report['checks'].append({'name':'actual-local-completion','passed':True,'seconds':time.monotonic()-start,
                                     'response':text,'eval_count':answer.get('eval_count')})
            embedding=post('/api/embed',{'model':'nomic-embed-text','input':'Public fictional fox research fixture','keep_alive':0})['embeddings'][0]
            assert len(embedding)==768 and all(isinstance(x,(int,float)) and math.isfinite(x) for x in embedding)
            report['checks'].append({'name':'actual-local-embedding','passed':True,'dimensions':len(embedding)})
            report['status']='passed'
    finally:
        try:
            if created:
                owner=docker('inspect',name,'--format','{{index .Config.Labels "io.foxory.smoke"}}',capture_output=True,text=True).stdout.strip()
                if owner!=nonce:raise PermissionError('Disposable container ownership mismatch')
                if report['status']!='passed':docker('logs','--tail','60',name,check=False)
                docker('rm','--force',name,stdout=subprocess.DEVNULL)
                report['cleanup_verified']=not docker('ps','--all','--filter','name=^/'+name+'$',
                    '--format','{{.ID}}',capture_output=True,text=True).stdout.strip()
                if not report['cleanup_verified']:raise RuntimeError('Model container cleanup not established')
        except Exception as error:
            report.update(status='failed',cleanup_verified=False,cleanup_error=type(error).__name__)
        finally:
            json.dump(report,output,indent=2);output.write('\n');output.close()
    if report['status']!='passed':raise RuntimeError('Candidate model compatibility failed')


if __name__=='__main__':main()
