"""Restricted parsing with bounded parent-side I/O and one active parser."""
import base64
import json
import os
import selectors
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from fastapi import HTTPException
WORKER=Path(__file__).with_name('parser_worker.py')
PARSER_SLOT=threading.BoundedSemaphore(1)
MAX_STDOUT=12_000_000
MAX_STDERR=128_000

def bounded_process(command:list[str],payload:bytes,timeout:float=20):
    process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,close_fds=True,start_new_session=True,cwd='/tmp',env={'LANG':'C.UTF-8','PATH':'/usr/bin:/bin'})
    output=bytearray();errors=bytearray();offset=0;deadline=time.monotonic()+timeout
    try:
        with selectors.DefaultSelector() as selector:
            for pipe,mode in [(process.stdin,selectors.EVENT_WRITE),(process.stdout,selectors.EVENT_READ),(process.stderr,selectors.EVENT_READ)]:
                os.set_blocking(pipe.fileno(),False);selector.register(pipe,mode)
            while selector.get_map():
                remaining=deadline-time.monotonic()
                if remaining<=0:raise TimeoutError('Parser deadline')
                for key,_ in selector.select(min(.2,remaining)):
                    pipe=key.fileobj
                    if pipe is process.stdin:
                        try:offset+=os.write(pipe.fileno(),payload[offset:offset+65536])
                        except BrokenPipeError:offset=len(payload)
                        except BlockingIOError:continue
                        if offset>=len(payload):selector.unregister(pipe);pipe.close()
                    else:
                        try:part=os.read(pipe.fileno(),65536)
                        except BlockingIOError:continue
                        if not part:selector.unregister(pipe);pipe.close();continue
                        buffer=output if pipe is process.stdout else errors
                        buffer.extend(part)
                        if len(buffer)>(MAX_STDOUT if pipe is process.stdout else MAX_STDERR):raise ValueError('Parser output budget')
        process.wait(timeout=max(.1,deadline-time.monotonic()))
        if process.returncode:raise ValueError('Parser exited unsuccessfully')
        return bytes(output)
    finally:
        if process.poll() is None:
            os.killpg(process.pid,signal.SIGKILL)
        process.wait(timeout=3)
        for pipe in [process.stdin,process.stdout,process.stderr]:
            if pipe and not pipe.closed:pipe.close()

def isolated_extract(name:str,raw:bytes)->str:
    if sys.platform!='linux':raise HTTPException(503,'Document parsing requires the Linux sandbox container')
    from .documents import EXTENSIONS
    if Path(name).suffix.lower() not in EXTENSIONS:raise HTTPException(415,'Unsupported document format')
    if not PARSER_SLOT.acquire(blocking=False):raise HTTPException(429,'Document parser busy; retry after the current upload')
    try:
        payload=json.dumps({'name':name,'raw':base64.b64encode(raw).decode()}).encode()
        result=bounded_process([sys.executable,'-I',str(WORKER)],payload)
        data=json.loads(result)
        if 'error' in data:raise ValueError('Document rejected')
        return data['text']
    except (ValueError,OSError,TimeoutError,subprocess.TimeoutExpired):raise HTTPException(422,'Document rejected by isolated parser or resource budget')
    finally:PARSER_SLOT.release()
