#!/usr/bin/env python3
"""Check locked source dependency inventory and retained license notices.

Not legal clearance for compiled OS/browser/GPU images or model redistribution.
Uses package metadata only; never imports dependency code or dynamic plugins.
"""
from __future__ import annotations
import argparse
import importlib.metadata
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]


def normalize(name:str)->str:return re.sub(r'[-_.]+','-',name).lower()


def notice_coverage(python:list[dict],frontend:list[dict],notices:str)->list[dict]:
    headers={(kind,normalize(name),version) for kind,name,version in
             re.findall(r'^===== (Python|npm) (\S+) (\S+): ',notices,re.M)}
    return [{'kind':kind,'name':row['name'],'version':row['version']}
            for kind,rows in [('Python',python),('npm',frontend)] for row in rows
            if (kind,normalize(row['name']),row['version']) not in headers]


def inventory()->dict:
    python=[]
    for line in (ROOT/'backend/requirements.lock').read_text().splitlines():
        if not line or line.startswith('#'):continue
        name,version=line.split('==');distribution=importlib.metadata.distribution(name)
        if distribution.version!=version:raise ValueError('Installed dependency does not match lock: '+name)
        metadata=distribution.metadata
        license=metadata.get('License-Expression') or metadata.get('License') or ' | '.join(
            value for value in metadata.get_all('Classifier',[]) if value.startswith('License ::'))
        python.append({'name':name,'version':version,'license_metadata':license or 'UNKNOWN'})
    lock=json.loads((ROOT/'frontend/package-lock.json').read_text())
    frontend=[{'name':path.rsplit('node_modules/',1)[-1],'version':metadata['version'],
               'license_metadata':metadata.get('license','UNKNOWN')}
              for path,metadata in lock['packages'].items() if path and not metadata.get('dev')]
    missing=notice_coverage(python,frontend,(ROOT/'THIRD_PARTY_NOTICES.txt').read_text())
    unknown=[row['name'] for row in python+frontend if row['license_metadata']=='UNKNOWN']
    return {'status':'inventory_verified' if not missing and not unknown else 'review_required',
            'application_license':'Apache-2.0','python_runtime_count':len(python),'frontend_runtime_count':len(frontend),
            'missing_notices':missing,'unknown_metadata':unknown,'python':python,'frontend':frontend,
            'conditional_obligations':['psycopg/psycopg-binary LGPL-3.0-only: preserve library licenses, replacement/relinking rights and corresponding-source obligations for binary distribution.',
                'certifi MPL-2.0: preserve file-level notices and corresponding source when distributing covered files.',
                'OS/browser/GPU images and model weights require independent version-specific distribution review.'],
            'distribution_scope':'Repository/source archive inventory and retained notices only; no blanket image/model or legal clearance.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path)
    args=parser.parse_args();result=inventory()
    if args.output:
        with args.output.open('x') as output:json.dump(result,output,indent=2);output.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in {'python','frontend'}},indent=2))
    if result['status']!='inventory_verified':raise SystemExit(1)


if __name__=='__main__':main()
