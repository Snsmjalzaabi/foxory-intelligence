"""Fail-closed PCRE2 version/source/runtime evidence. No native PoC runs on host."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess

import pytest

ROOT=Path(__file__).resolve().parents[2]


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


audit=module('pcre_audit','scripts/image_audit.py')
review=module('pcre_review','scripts/verify_host_image_evidence.py')
source=module('pcre_source','sandbox_manager/runtime/pcre2/prepare.py')
POLICY=json.loads((ROOT/'sandbox_manager/runtime/worker-packages.json').read_text())
SOURCE=json.loads((ROOT/'sandbox_manager/runtime/pcre2/source.json').read_text())
IMAGE='sha256:'+'a'*64


@pytest.mark.parametrize('version',[None,'10.42-4ubuntu2.1','10.48-0foxory1','10.49-0foxory1'])
def test_missing_old_or_unfixed_package_cannot_pass_worker_gate(version):
    components=[{'name':n,'purl':'pkg:deb/ubuntu/'+n+'@fixture'} for n in POLICY['required_packages']]
    if version:
        components.append({'name':'libpcre2-8-0','version':version,'purl':'pkg:deb/ubuntu/libpcre2-8-0@'+version})
    result=audit.worker_packages(components)
    assert (result['status']=='passed')==(version==SOURCE['package_version'])
    if version!=SOURCE['package_version']:assert result['version_mismatches']==['libpcre2-8-0']


def test_changed_source_bytes_are_rejected():
    with pytest.raises(ValueError,match='checksum'):source.verify_bytes(b'changed archive','a'*64)


@pytest.mark.parametrize('variant',['missing','old','new','ambiguous'])
def test_application_and_model_gate_reject_absent_old_or_ambiguous_versions(variant):
    components=[]
    if variant!='missing':components=[{'name':'libpcre2-8-0','version':SOURCE['package_version'] if variant!='old' else '10.42-4ubuntu2.1','purl':'pkg:deb/ubuntu/libpcre2-8-0@fixture'}]
    if variant=='ambiguous':components.append({**components[0],'version':'10.42-4ubuntu2.1'})
    assert (audit.pcre2_version(components)['status']=='passed')==(variant=='new')


def fixture():
    p={'version':'10.49 fixture','source_sha256':SOURCE['archive_sha256'],'library_sha256':'b'*64,
       'jit':True,'unicode':True,'dfa_error':-63,'jit_stack_error':-46,
       'normal_upstream_tests':'passed','asan_ubsan_upstream_tests':'passed'}
    return {'status':'fixed_probes_passed','image':IMAGE,'evidence':[
        {'profile':n,'fixture_passed':True,**({'pcre2':copy.deepcopy(p)} if n!='browser' else {})}
        for n in ['javascript','typescript','browser']]}


def test_matching_native_evidence_passes_only_the_scoped_consistency_check():
    assert review.verify_pcre2_probe(IMAGE,fixture())['dfa_error']==-63


@pytest.mark.parametrize('mutation',['old','source','library','jit','sanitizers','image','missing','mismatch','dfa'])
def test_version_metadata_alone_cannot_attest_native_fix(mutation):
    data=fixture()
    for row in data['evidence'][:2]:
        p=row['pcre2']
        if mutation=='old':p['version']='10.42 vulnerable'
        elif mutation=='source':p['source_sha256']='a'*64
        elif mutation=='library':p['library_sha256']='not-a-hash'
        elif mutation=='jit':p['jit']=False
        elif mutation=='sanitizers':p.pop('asan_ubsan_upstream_tests')
        elif mutation=='dfa':p['dfa_error']=0
    if mutation=='image':data['image']='sha256:'+'c'*64
    elif mutation=='missing':data['evidence'].pop()
    elif mutation=='mismatch':data['evidence'][0]['pcre2']['library_sha256']='c'*64
    with pytest.raises(ValueError):review.verify_pcre2_probe(IMAGE,data)


def test_native_package_builder_cannot_be_invoked_as_host_installer():
    result=subprocess.run(['python3',str(ROOT/'sandbox_manager/runtime/pcre2/package.py')],capture_output=True,text=True,timeout=5)
    assert result.returncode!=0 and 'image-build-only' in result.stderr
