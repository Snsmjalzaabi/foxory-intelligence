"""TEST ONLY: deterministic OCI boundary. Never imported by production services.

No Node/browser/code is executed. Real schemas, lifecycle, auth, artifacts and
approval paths remain active. The result explicitly identifies the mocked engine.
"""
from __future__ import annotations
import asyncio
import base64
import hashlib
import json
from pathlib import Path
import struct
import zlib

SITE='<!doctype html><html><body><input id="name"><button id="show">Show</button><p id="result"></p><a href="/report.txt" download>Download</a></body></html>'

def png()->bytes:
    def chunk(tag,data):return struct.pack('>I',len(data))+tag+data+struct.pack('>I',zlib.crc32(tag+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b'\x00\x20\x40\x60'))+chunk(b'IEND',b'')

def artifact(data:bytes):return {'base64':base64.b64encode(data).decode(),'size':len(data),'sha256':hashlib.sha256(data).hexdigest()}

class Process:
    def __init__(self,frames:list[dict],*,hang=False,code=0):
        self.stdout=asyncio.StreamReader();self.stderr=asyncio.StreamReader();self.returncode=None
        self.done=asyncio.Event();self.code=code
        for frame in frames:self.stdout.feed_data((json.dumps(frame)+'\n').encode())
        if not hang:self.finish(code)
    def finish(self,code):
        if self.returncode is not None:return
        self.returncode=code;self.stdout.feed_eof();self.stderr.feed_eof();self.done.set()
    async def wait(self):await self.done.wait();return self.returncode
    def terminate(self):self.finish(-15)
    def kill(self):self.finish(-9)

class Engine:
    def __init__(self):
        self.containers={};self.calls=[];self.runs=0;self.hang=False;self.corrupt=False;self.cleanup_failure=False
    async def startup(self,runtime,*,authorized):
        # Replaces host verification only inside explicit test fixtures.
        runtime.opt_in=True;runtime.image='sha256:'+'a'*64
        await runtime.recover();runtime.verified=True;runtime.blockers=[]
    async def cli(self,runtime,*args,**kwargs):
        self.calls.append(args)
        if args[0]=='create':
            name=next(a.split('=',1)[1] for a in args if a.startswith('--name='))
            labels=dict(a.removeprefix('--label=').split('=',1) for a in args if a.startswith('--label='))
            request=next(a.removeprefix('--volume=').split(':/request.json:')[0] for a in args if ':/request.json:ro' in a)
            self.containers[name]={'labels':labels,'request':json.loads(Path(request).read_text())}
            return 0,'created',''
        if args[:2]==('container','inspect'):
            row=self.containers.get(args[2]);return (0,json.dumps(row['labels']),'') if row else (1,'','missing')
        if args[:2]==('container','exists'):return (0 if args[2] in self.containers else 1),'',''
        if args[0]=='rm':
            if not self.cleanup_failure:self.containers.pop(args[-1],None)
            return (1 if self.cleanup_failure else 0),'',''
        if args[0]=='ps':
            owner=next(a.split('=',2)[2] for a in args if a.startswith('label=io.foxory.manager='))
            return 0,json.dumps([{'Names':[name]} for name,row in self.containers.items() if row['labels'].get('io.foxory.manager')==owner]),''
        raise AssertionError('Unexpected OCI control invocation: '+repr(args))
    async def spawn(self,runtime,*args,**kwargs):
        assert args[:4]==('podman','--remote=false','start','--attach'),args
        self.runs+=1;project=self.containers[args[-1]]['request'];artifacts={};text='MOCK OCI boundary: no code or browser executed.\n'
        if project['profile']=='browser':
            assert project['files']['index.html']
            typed=''
            for action in project['actions']:
                if action['action']=='type':typed=action['text']
                if action['action']=='inspect':text+=typed+'\n'
                if action['action']=='screenshot':artifacts['screenshot-1.png']=artifact(png())
                if action['action']=='download':artifacts['result.txt']=artifact(project['files'].get('report.txt','Controlled download').encode())
        else:artifacts['result.json']=artifact(b'{"fixture":true,"answer":42}')
        if self.corrupt:artifacts['result.json']={'base64':'QQ==','size':1,'sha256':'bad'}
        return Process([{'event':'progress','message':'Mock worker started\n'},
                        {'event':'result','exit_code':0,'stdout':text,'artifacts':artifacts}],hang=self.hang)

    def install(self,patcher):
        from sandbox_manager.oci_runtime import Runtime
        async def startup(runtime,**kwargs):return await self.startup(runtime,**kwargs)
        async def cli(runtime,*args,**kwargs):return await self.cli(runtime,*args,**kwargs)
        async def spawn(runtime,*args,**kwargs):return await self.spawn(runtime,*args,**kwargs)
        patcher.setattr(Runtime,'startup',startup);patcher.setattr(Runtime,'cli',cli);patcher.setattr(Runtime,'spawn',spawn)
