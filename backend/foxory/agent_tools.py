"""Explicitly registered, schema-checked tools. No dynamic imports or executable extensions."""
import ast
import hashlib
import json
import math
import operator
from dataclasses import dataclass
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, RootModel, JsonValue, model_validator
from sqlalchemy import select
from .db import Session, Record, get_record
from .sandbox_protocol import OCIProject, BrowserAction
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
class CSVDocument(Input):
    document_id:str=Field(min_length=1,max_length=36)
    column:str=Field(min_length=1,max_length=100)
    group_by:str|None=Field(default=None,max_length=100)
    minimum:float|None=None
    maximum:float|None=None

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
class SandboxPython(SourceProject):
    entrypoint:str=Field(min_length=1,max_length=180)
    @model_validator(mode='after')
    def python_entry(self):
        if self.entrypoint not in self.files or not self.entrypoint.endswith('.py'):raise ValueError('Entrypoint must be a supplied Python file')
        return self

class SandboxJavaScript(SourceProject):
    entrypoint:str=Field(min_length=1,max_length=180)
    @model_validator(mode='after')
    def entry(self):
        OCIProject(profile='javascript',files=self.files,entrypoint=self.entrypoint);return self
class SandboxTypeScript(SandboxJavaScript):
    @model_validator(mode='after')
    def entry(self):
        OCIProject(profile='typescript',files=self.files,entrypoint=self.entrypoint);return self
class SandboxBrowser(SourceProject):
    actions:list[BrowserAction]=Field(min_length=1,max_length=12)
    @model_validator(mode='after')
    def fixture(self):
        OCIProject(profile='browser',files=self.files,actions=self.actions);return self

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
 'data.csv_document':Tool('Analyze one explicitly authorized uploaded CSV with deterministic grouped statistics and an escaped chart. Also requires calculate permission.',CSVDocument,'documents.read'),
 'data.table':Tool('Filter, group and summarize supplied table rows; returns deterministic statistics and inert SVG chart.',TableAnalysis,'calculate'),
 'sandbox.python':Tool('Run supplied Python source in the separate opt-in, network-denied, single-process manager after explicit approval. No shell, browser, subprocesses or package installs.',SandboxPython,'sandbox.execute',True,30),
 'sandbox.javascript':Tool('Run dependency-free JavaScript in a separately verified rootless OCI worker after approval. No network or runtime package installation.',SandboxJavaScript,'sandbox.execute',True,90),
 'sandbox.typescript':Tool('Run Node type-stripped TypeScript in the verified offline OCI worker after approval; no semantic type checking.',SandboxTypeScript,'sandbox.execute',True,90),
 'sandbox.browser':Tool('Navigate, inspect, click, type, screenshot and download from supplied offline fixture files only. No external browsing or form submissions. Requires approval.',SandboxBrowser,'sandbox.browser',True,90),
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
    if name=='data.csv_document':
        if 'calculate' not in config.get('permissions',[]) or parsed['document_id'] not in config.get('document_ids',[]):raise PermissionError('CSV document or calculation scope exceeded')
    if name=='documents.retrieve':
        allowed=config.get('document_ids',[])
        requested=parsed['document_ids'] or allowed
        if not requested or not set(requested)<=set(allowed):raise PermissionError('Document access scope exceeded')
        parsed['document_ids']=requested
    return parsed

async def execute(name:str,args:dict,config:dict,agent_id:str):
    args=authorize(config,name,args)
    if TOOLS[name].approval:raise PermissionError('Writes must be committed through the approval transaction')
    if name=='data.csv_document':
        import csv,io
        with Session() as session:
            document=get_record(session,args['document_id'],'document')
            if not document.title.lower().endswith('.csv'):raise ValueError('Uploaded CSV required')
            text=json.loads(document.payload)['text']
        if len(text)>20000:raise ValueError('CSV analysis text budget exceeded')
        reader=csv.DictReader(io.StringIO(text))
        fields=reader.fieldnames or []
        if not fields or len(fields)>20 or len(set(fields))!=len(fields) or any(not f for f in fields):raise ValueError('CSV header budget/uniqueness exceeded')
        rows=[]
        for row in reader:
            if len(rows)>=500 or None in row or any(v is None for v in row.values()):raise ValueError('CSV row budget or shape exceeded')
            rows.append(row)
        result=analyze_table({'rows':rows,**{k:v for k,v in args.items() if k!='document_id'}})
        result['document_id']=args['document_id'];result['source_sha256']=hashlib.sha256(text.encode()).hexdigest()
        result['report']='Grouped CSV statistics\n'+json.dumps({k:v for k,v in result.items() if k!='chart_svg'},indent=2)
        output=io.StringIO(newline='');writer=csv.writer(output)
        writer.writerow(['group','count','sum','mean','median','min','max','population_stddev'])
        for group in result['groups']:
            values=[group[k] for k in ['group','count','sum','mean','median','min','max','population_stddev']]
            writer.writerow(["'"+v if isinstance(v,str) and v.startswith(('=','+','-','@','\t','\r')) else v for v in values])
        result['csv']=output.getvalue()
        return result
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
