"""Shared bounded sandbox wire schemas and inert artifact validation."""
from __future__ import annotations
import base64
import binascii
import csv
import hashlib
import io
import json
import math
import re
import struct
import zlib
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

TEXT_NAMES={'result.txt','result.json','result.csv','result.md'}
PNG_NAMES={'screenshot-1.png','screenshot-2.png'}
MAX_ARTIFACT=20000
SANDBOX_TOOLS={'sandbox.python','sandbox.javascript','sandbox.typescript','sandbox.browser'}

def valid_path(name:str)->bool:
    return (0<len(name)<=180 and re.fullmatch(r'[A-Za-z0-9_./-]+',name) is not None
            and not name.startswith('/') and all(p.lower() not in ('','.','..','.git','.env') for p in name.split('/')))

class BrowserAction(BaseModel):
    model_config=ConfigDict(extra='forbid')
    action:Literal['navigate','inspect','click','type','screenshot','download']
    target:str=Field(default='',max_length=200)
    text:str=Field(default='',max_length=2000)
    @model_validator(mode='after')
    def check(self):
        if self.action=='navigate' and (not self.target.startswith('/') or self.target.startswith('//')
            or '\\' in self.target or '..' in self.target.split('/') or '%' in self.target
            or any(ord(c)<32 for c in self.target)):
            raise ValueError('Navigation must use a literal local fixture path')
        if self.action in {'click','type','download'} and not self.target:raise ValueError('Explicit selector required')
        return self

class OCIProject(BaseModel):
    model_config=ConfigDict(extra='forbid')
    profile:Literal['javascript','typescript','browser']
    files:dict[str,str]=Field(min_length=1,max_length=50)
    entrypoint:str=Field(default='',max_length=180)
    actions:list[BrowserAction]=Field(default_factory=list,max_length=12)
    @model_validator(mode='after')
    def check(self):
        if any(not valid_path(k) or '\x00' in v for k,v in self.files.items()):raise ValueError('Invalid source path/content')
        if sum(len(v.encode()) for v in self.files.values())>20000:raise ValueError('Source byte budget exceeded')
        if self.profile=='browser':
            if not self.actions or self.entrypoint:raise ValueError('Browser requires actions and no code entrypoint')
            if sum(a.action=='screenshot' for a in self.actions)>2:raise ValueError('Screenshot budget exceeded')
            if 'index.html' not in self.files:raise ValueError('Offline browser requires index.html')
        else:
            suffix='.js' if self.profile=='javascript' else '.ts'
            if self.entrypoint not in self.files or not self.entrypoint.endswith(suffix):raise ValueError('Entrypoint must match selected language')
            if self.actions:raise ValueError('Browser actions cannot be code execution arguments')
        return self

def validate_png(data:bytes)->None:
    if not data.startswith(b'\x89PNG\r\n\x1a\n'):raise ValueError('Invalid PNG signature')
    pos=8; compressed=bytearray(); dimensions=None; ended=False; seen_idat=False; idat_closed=False
    while pos<len(data):
        if pos+12>len(data):raise ValueError('Truncated PNG')
        size=struct.unpack('>I',data[pos:pos+4])[0]; tag=data[pos+4:pos+8]
        if size>MAX_ARTIFACT or pos+12+size>len(data):raise ValueError('Invalid PNG chunk length')
        content=data[pos+8:pos+8+size]; crc=struct.unpack('>I',data[pos+8+size:pos+12+size])[0]
        if binascii.crc32(tag+content)&0xffffffff!=crc:raise ValueError('PNG checksum mismatch')
        if pos==8 and tag!=b'IHDR':raise ValueError('Missing PNG header')
        if tag==b'IHDR':
            if dimensions is not None or size!=13:raise ValueError('Invalid PNG header')
            w,h,depth,color,compression,filtering,interlace=struct.unpack('>IIBBBBB',content)
            if not (0<w<=1280 and 0<h<=720 and depth==8 and color in (2,6) and compression==filtering==interlace==0):raise ValueError('Unsupported PNG profile')
            dimensions=(w,h,3 if color==2 else 4)
        elif tag==b'IDAT':
            if idat_closed:raise ValueError('Non-contiguous PNG data')
            seen_idat=True;compressed.extend(content)
        elif tag==b'IEND':
            if size or not seen_idat or pos+12!=len(data):raise ValueError('Invalid PNG end')
            ended=True
        else:
            if seen_idat:idat_closed=True
            # Only inert Chromium metadata; no unknown critical/active chunks.
            if tag not in {b'sRGB',b'gAMA',b'cHRM',b'pHYs'}:raise ValueError('Unsupported PNG chunk')
        pos+=12+size
    if not ended or dimensions is None:raise ValueError('Incomplete PNG')
    w,h,channels=dimensions; expected=h*(1+w*channels)
    inflater=zlib.decompressobj()
    try:raw=inflater.decompress(bytes(compressed),expected+1)
    except zlib.error as error:raise ValueError('Invalid PNG compression') from error
    if len(raw)!=expected or not inflater.eof or inflater.unused_data or inflater.unconsumed_tail:raise ValueError('PNG decompression bounds')
    if any(raw[row*(1+w*channels)]>4 for row in range(h)):raise ValueError('Invalid PNG filter')

def validate_artifacts(value:dict,*,allow_png:bool=False)->dict:
    if not isinstance(value,dict) or len(value)>6:raise ValueError('Artifact count exceeded')
    total=0; result={}
    for name,item in value.items():
        if name not in TEXT_NAMES|(PNG_NAMES if allow_png else set()):raise ValueError('Artifact name rejected')
        if not isinstance(item,dict) or set(item)!={'base64','size','sha256'}:raise ValueError('Invalid artifact schema')
        encoded=item['base64']
        if not isinstance(encoded,str) or len(encoded)>26668:raise ValueError('Encoded artifact budget')
        data=base64.b64decode(encoded,validate=True);total+=len(data)
        if total>MAX_ARTIFACT or type(item['size']) is not int or len(data)!=item['size']:raise ValueError('Artifact byte budget/size')
        if hashlib.sha256(data).hexdigest()!=item['sha256']:raise ValueError('Artifact integrity failure')
        if name in PNG_NAMES:validate_png(data)
        else:
            text=data.decode('utf8')
            if '\x00' in text:raise ValueError('Binary artifact rejected')
            if name.endswith('.json'):
                def reject_constant(value):raise ValueError('Non-finite JSON constant')
                json.loads(text,parse_constant=reject_constant)
            if name.endswith('.csv'):
                for row in csv.reader(io.StringIO(text)):
                    for cell in row:
                        value=cell.lstrip()
                        if value.startswith(('=','+','-','@')):
                            try:number=float(value)
                            except ValueError:raise ValueError('Active spreadsheet formula rejected')
                            if not math.isfinite(number):raise ValueError('Unsafe spreadsheet value')
        result[name]={'base64':base64.b64encode(data).decode(),'size':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    return result
