#!/usr/bin/env python3
"""Verify reviewed worker inputs; optional TLS downloads verify registry bytes.

Integrity is not a vulnerability audit or proof that upstream code is trustworthy.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import importlib.util
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]/'sandbox_manager/runtime'
FILES=('Dockerfile','.dockerignore','worker.mjs','package.json','package-lock.json','prune-media.mjs','worker-packages.json',
       'pcre2/source.json','pcre2/release-key.asc','pcre2/prepare.py','pcre2/build.sh',
       'pcre2/package.py','pcre2/probe.c','pcre2/LICENCE.md','pcre2/SLJIT-LICENSE')
BASE='mcr.microsoft.com/playwright:v1.64.1-noble@sha256:47b510dd9230bf0b9bfc9b20102241e577ea7a99334ab4c3ca19f19770e9b8ea'

def verify(online:bool=False)->dict:
    expected=json.loads((ROOT/'reviewed-inputs.json').read_text())
    actual={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in FILES}
    if actual!=expected['sha256']:raise ValueError('Worker inputs changed; review and update reviewed-inputs.json')
    if expected['base']!=BASE or 'FROM '+BASE not in (ROOT/'Dockerfile').read_text():raise ValueError('Unreviewed base image')
    lock=json.loads((ROOT/'package-lock.json').read_text())
    if set(lock['packages'])!={'','node_modules/playwright','node_modules/playwright-core'}:raise ValueError('Unexpected dependency graph')
    package=json.loads((ROOT/'package.json').read_text())
    if package['dependencies']!={'playwright':'1.64.1'}:raise ValueError('Unpinned worker dependency')
    for name in ('playwright','playwright-core'):
        dependency=lock['packages']['node_modules/'+name]
        if dependency['version']!='1.64.1' or dependency['resolved']!=f'https://registry.npmjs.org/{name}/-/{name}-1.64.1.tgz':raise ValueError('Unreviewed dependency source/version')
        if not dependency['integrity'].startswith('sha512-') or len(base64.b64decode(dependency['integrity'][7:],validate=True))!=64:raise ValueError('Missing dependency integrity')
    if online:
        spec=importlib.util.spec_from_file_location('pcre2_source',ROOT/'pcre2/prepare.py')
        verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)
        with tempfile.TemporaryDirectory(prefix='foxory-pcre-source-') as temporary:
            verifier.fetch_verified(ROOT/'pcre2',Path(temporary)/'verified')
        import httpx
        with httpx.Client(timeout=45,follow_redirects=False) as client:
            response=client.get('https://mcr.microsoft.com/v2/playwright/manifests/'+BASE.split('@')[1],headers={
                'Accept':'application/vnd.docker.distribution.manifest.list.v2+json, application/vnd.oci.image.index.v1+json'})
            response.raise_for_status()
            if 'sha256:'+hashlib.sha256(response.content).hexdigest()!=BASE.split('@')[1]:raise ValueError('Base manifest digest mismatch')
            for name in ('playwright','playwright-core'):
                dependency=lock['packages']['node_modules/'+name];digest=hashlib.sha512();size=0
                with client.stream('GET',dependency['resolved']) as response:
                    response.raise_for_status()
                    for block in response.iter_bytes():
                        size+=len(block)
                        if size>20000000:raise ValueError('Dependency archive size budget')
                        digest.update(block)
                if base64.b64encode(digest.digest()).decode()!=dependency['integrity'][7:]:raise ValueError('Dependency archive integrity mismatch')
    return {'status':'reviewed_inputs_verified','base':BASE,'sha256':actual,'registry_bytes_verified':online,
            'runtime_image_built':False,'vulnerability_audit':'pending release review'}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--online',action='store_true')
    args=parser.parse_args();print(json.dumps(verify(args.online),indent=2))
