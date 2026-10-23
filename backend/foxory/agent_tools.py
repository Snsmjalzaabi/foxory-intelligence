"""Explicitly registered, schema-checked tools. No dynamic imports or executable extensions."""
import ast
import hashlib
import json
import math
import operator
from dataclasses import dataclass
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, RootModel, JsonValue
from sqlalchemy import select
from .db import Session, Record, get_record
from .advanced_files import SourceProject, TableAnalysis, analyze_table

class ToolOutput(RootModel[dict[str,JsonValue]]):
    """JSON-only output envelope; tool fields are documented in the catalogue."""

class Input(BaseModel):
    model_config=ConfigDict(extra='forbid')
class Query(Input):
    query:str=Field(min_length=1,max_length=1000)
class Page(Input):
    url:str=Field(min_length=8,max_length=2000)
class Documents(Query):
    document_ids:list[str]=Field(default_factory=list,max_length=20)
class CitationInput(Input):
    job_id:str=Field(min_length=1,max_length=36)
class Calculate(Input):
    expression:str=Field(min_length=1,max_length=200)
class DataInput(Input):
    values:list[float]=Field(min_length=1,max_length=1000)
    operation:Literal['sum','mean','min','max','count']='mean'
class Generate(Input):
    title:str=Field(min_length=1,max_length=200)
    content:str=Field(min_length=1,max_length=20000)
class TaskInput(Generate):
    project_id:str=Field(min_length=1,max_length=36)
class MemoryQuery(Query):
    pass
@dataclass(frozen=True)
class Tool:
    description:str
    schema:type[Input]
    scope:str
    approval:bool=False
    timeout:int=30
TOOLS={
 'web.search':Tool('Search public sources; results are untrusted discovery data.',Query,'web.read'),
 'web.retrieve':Tool('Read one permitted public page, respecting robots and SSRF restrictions.',Page,'web.read'),
 'research.references':Tool('Read saved research references; integrity is not factual verification.',CitationInput,'research.read'),
 'documents.retrieve':Tool('Retrieve excerpts from explicitly authorized workspace documents.',Documents,'documents.read'),
 'math.calculate':Tool('Evaluate bounded arithmetic only; no variables, calls or code.',Calculate,'calculate'),
 'data.table':Tool('Filter, group and summarize supplied table rows; returns deterministic statistics and inert SVG chart.',TableAnalysis,'calculate'),
 'source.package':Tool('Save inert source files for ZIP download after approval. Does not run code or modify repositories.',SourceProject,'documents.write',True),
 'data.analyze':Tool('Compute finite-number summary statistics.',DataInput,'calculate'),
 'projects.list':Tool('Read workspace projects and tasks.',Input,'projects.read'),
 'memory.search':Tool('Search this agent\'s history and user-approved shared facts.',MemoryQuery,'memory.read'),
 'document.generate':Tool('Create an internal downloadable report artifact after approval.',Generate,'documents.write',True),
 'project.create':Tool('Create an internal workspace project after approval.',Generate,'projects.write',True),
 'task.create':Tool('Create an internal task on an existing workspace project after approval.',TaskInput,'projects.write',True),
}

def catalogue():
    return {name:{'description':t.description,'input_schema':t.schema.model_json_schema(),'output_schema':ToolOutput.model_json_schema(),'output_limit_chars':60000,'permission':t.scope,'approval_required':t.approval,'timeout_seconds':t.timeout} for name,t in TOOLS.items()}

def arithmetic(expression:str):
    tree=ast.parse(expression,mode='eval')
    if sum(1 for _ in ast.walk(tree))>40:raise ValueError('Arithmetic complexity limit')
    binary={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv,ast.Mod:operator.mod,ast.Pow:operator.pow}
    def evaluate(node):
        if isinstance(node,ast.Constant) and type(node.value) in (int,float):value=node.value
        elif isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.USub,ast.UAdd)):value=(-1 if isinstance(node.op,ast.USub) else 1)*evaluate(node.operand)
        elif isinstance(node,ast.BinOp) and type(node.op) in binary:
            a,b=evaluate(node.left),evaluate(node.right)
            if isinstance(node.op,ast.Pow) and (abs(b)>10 or abs(a)>1e6):raise ValueError('Power budget')
            value=binary[type(node.op)](a,b)
        else:raise ValueError('Only bounded arithmetic is permitted')
        if isinstance(value,complex) or not math.isfinite(value) or abs(value)>1e15:raise ValueError('Numeric budget')
        return value
    return evaluate(tree.body)

def authorize(config:dict,name:str,args:dict):
    if name not in TOOLS or name not in config.get('tools',[]):raise PermissionError('Tool not granted to this agent')
    tool=TOOLS[name]
    if tool.scope not in config.get('permissions',[]):raise PermissionError('Missing tool permission scope')
    parsed=tool.schema.model_validate(args).model_dump()
    if name=='documents.retrieve':
        allowed=config.get('document_ids',[])
        requested=parsed['document_ids'] or allowed
        if not requested or not set(requested)<=set(allowed):raise PermissionError('Document access scope exceeded')
        parsed['document_ids']=requested
    return parsed

async def execute(name:str,args:dict,config:dict,agent_id:str):
    args=authorize(config,name,args)
    if TOOLS[name].approval:raise PermissionError('Writes must be committed through the approval transaction')
    if name=='data.table':return analyze_table(args)
    if name=='math.calculate':return {'value':arithmetic(args['expression'])}
    if name=='data.analyze':
        values=args['values']
        if not all(math.isfinite(x) and abs(x)<=1e15 for x in values):raise ValueError('Numeric budget')
        op=args['operation'];return {'operation':op,'value':{'sum':sum,'mean':lambda v:sum(v)/len(v),'min':min,'max':max,'count':len}[op](values)}
    if name=='web.search':
        from .research import search
        return {'results':await search(args['query'],limit=4),'warning':'Discovery only; retrieve pages before citing claims.'}
    if name=='web.retrieve':
        from .web import retrieve_page
        return await retrieve_page(args['url'])
    if name=='documents.retrieve':
        from .knowledge import document_evidence
        return {'sources':await document_evidence(args['query'],ids=args['document_ids'])}
    if name=='research.references':
        from .research import citation_manifest
        with Session() as s:
            row=get_record(s,args['job_id'],'job');d=json.loads(row.payload)
            return {'sources':d.get('sources',[]),'verification':citation_manifest(d.get('result',''),d.get('sources',[]))}
    if name=='projects.list':
        with Session() as s:return {'projects':[r.public() for r in s.scalars(select(Record).where(Record.kind.in_(['project','task']))).all()][:100]}
    if name=='memory.search':
        from .agent_memory import search_memory
        return {'memories':search_memory(agent_id,args['query'])}
    raise PermissionError('Unregistered tool')
