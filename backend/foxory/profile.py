"""Installation profile: names, regional defaults and starter prompts kept out of the code.

FOXORY_PROFILE selects profiles/<name>.json. Without it, profiles/personal.json is used when it
exists (an owner's private edition), otherwise profiles/default.json (the public edition).
"""
import json,os,re
from functools import lru_cache
from pathlib import Path
from typing import Literal
from fastapi import APIRouter
from pydantic import BaseModel,ConfigDict,Field

router=APIRouter(prefix='/api/profile')
FOLDER=Path(os.getenv('FOXORY_PROFILE_DIR',str(Path(__file__).resolve().parents[2]/'profiles')))

class Starter(BaseModel):
 model_config=ConfigDict(extra='forbid')
 title:str=Field(min_length=1,max_length=60)
 summary:str=Field(max_length=120)
 icon:Literal['plan','build','documents','draft']='plan'
 prompt:str=Field(default='',max_length=1000)
 action:Literal['documents']|None=None

class Profile(BaseModel):
 model_config=ConfigDict(extra='forbid')
 name:str=Field(pattern=r'^[a-z0-9_-]{1,40}$')
 machine_name:str=Field(min_length=1,max_length=40)
 edition:str=Field(min_length=1,max_length=24)
 welcome_title:str=Field(min_length=1,max_length=120)
 system_prompt:str=Field(min_length=1,max_length=4000)
 timezone:str=Field(min_length=1,max_length=64)
 currency:str=Field(pattern=r'^[A-Z]{3}$')
 currencies:list[str]=Field(min_length=1,max_length=20)
 default_model:str=Field(min_length=1,max_length=100)
 coding_model:str=Field(min_length=1,max_length=100)
 starters:list[Starter]=Field(min_length=1,max_length=6)

def selected_name():
 name=os.getenv('FOXORY_PROFILE','').strip()
 if name:return name
 return 'personal' if (FOLDER/'personal.json').is_file() else 'default'

@lru_cache(maxsize=1)
def active()->Profile:
 name=selected_name()
 if not re.fullmatch(r'[a-z0-9_-]{1,40}',name):raise RuntimeError('FOXORY_PROFILE must be a simple profile name')
 profile=Profile.model_validate(json.loads((FOLDER/f'{name}.json').read_text()))
 if profile.currency not in profile.currencies:raise RuntimeError('The profile currency must be one of its currencies')
 return profile

@router.get('')
def get_profile():return active().model_dump()
