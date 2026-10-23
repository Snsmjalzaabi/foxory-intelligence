"""No document bytes enter a parser before the restricted child seals itself."""
import base64
import json
import os
import subprocess
import sys
from pathlib import Path
from fastapi import HTTPException
WORKER=Path(__file__).with_name('parser_worker.py')

def isolated_extract(name:str,raw:bytes)->str:
    if sys.platform!='linux':raise HTTPException(503,'Document parsing requires the Linux sandbox container')
    from .documents import EXTENSIONS
    if Path(name).suffix.lower() not in EXTENSIONS:raise HTTPException(415,'Unsupported document format')
    payload=json.dumps({'name':name,'raw':base64.b64encode(raw).decode()})
    try:
        result=subprocess.run([sys.executable,'-I',str(WORKER)],input=payload,capture_output=True,text=True,timeout=20,close_fds=True,cwd='/tmp',env={'LANG':'C.UTF-8','PATH':'/usr/bin:/bin'})
        if result.returncode or len(result.stdout)>12_000_000:raise ValueError('Sandbox failed or resource limit reached')
        data=json.loads(result.stdout)
        if 'error' in data:raise ValueError('Document rejected')
        return data['text']
    except (ValueError,OSError,subprocess.TimeoutExpired):raise HTTPException(422,'Document rejected by isolated parser or resource budget')
