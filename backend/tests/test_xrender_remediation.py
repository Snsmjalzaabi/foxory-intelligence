"""Synthetic protocol/evidence guards only; native overflow tests stay in builders."""
import copy
import importlib.util
import json
from pathlib import Path
import struct

import pytest

ROOT=Path(__file__).resolve().parents[2]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


relay=load('xrender_relay','sandbox_manager/runtime/xrender/regression.py')
review=load('xrender_review','scripts/verify_host_image_evidence.py')
audit=load('xrender_audit','scripts/image_audit.py')
signed=load('signed_source','sandbox_manager/runtime/pcre2/prepare.py')
POLICY=json.loads((ROOT/'sandbox_manager/runtime/worker-packages.json').read_text())
SOURCE=json.loads((ROOT/'sandbox_manager/runtime/xrender/source.json').read_text())
IMAGE='sha256:'+'a'*64


@pytest.mark.parametrize('endian',['<','>'])
def test_protocol_fixture_preserves_screen_count_and_adds_one_excess_subpixel(endian):
    packet=bytearray(36);packet[0]=1
    for offset,value in [(4,1),(12,1),(24,1)]:struct.pack_into(endian+'I',packet,offset,value)
    result=relay.malicious_reply(bytes(packet),endian)
    assert len(result)==40 and result[:4]==packet[:4]
    assert struct.unpack_from(endian+'I',result,12)[0]==1
    assert struct.unpack_from(endian+'I',result,24)[0]==2
    assert struct.unpack_from(endian+'I',result,4)[0]==2


def test_bad_fixture_cannot_masquerade_as_reproduced_vulnerability():
    for data in [b'',bytes(32),b'\x01'+bytes(31)]:
        with pytest.raises(ValueError):relay.malicious_reply(data,'<')


@pytest.mark.parametrize('name',['../escape','/absolute','nested/name','', 'x'*100])
def test_shared_release_helper_rejects_archive_path_escape_before_io(tmp_path,name):
    with pytest.raises(ValueError,match='filename'):signed.fetch_verified(tmp_path,tmp_path/'output',name)
    assert not (tmp_path/'output').exists()


@pytest.mark.parametrize('version',['1:0.9.10-1.1build1','1:0.9.12-0foxory1','1:0.9.13-0foxory1'])
def test_old_or_unfixed_xrender_cannot_pass_version_gate(version):
    components=[{'name':n,'purl':'pkg:deb/ubuntu/'+n+'@fixture'} for n in POLICY['required_packages']]
    components += [{'name':n,'version':version if n=='libxrender1' else v,'purl':'pkg:deb/ubuntu/'+n+'@fixture'}
                   for n,v in POLICY['required_versions'].items()]
    result=audit.worker_packages(components)
    assert (result['status']=='passed')==(version==SOURCE['package_version'])


def fixture():
    native={'version':SOURCE['version'],'source_sha256':SOURCE['archive_sha256'],'library_sha256':'b'*64,
        'library_path':'/usr/lib/x86_64-linux-gnu/libXrender.so.1.3.0',
        'loaded_path':'/usr/lib/x86_64-linux-gnu/libXrender.so.1.3.0','symbol':'XRenderQueryFormats',
        'baseline_asan_overflow_reproduced':True,'normal_protocol_regressions':'passed',
        'asan_ubsan_protocol_regressions':'passed'}
    return {'image':IMAGE,'status':'fixed_probes_passed','evidence':[
        {'profile':p,'fixture_passed':True,**({'xrender':copy.deepcopy(native)} if p!='browser' else {})}
        for p in ['javascript','typescript','browser']]}


def test_matching_loaded_library_and_security_control_evidence():
    assert review.verify_xrender_probe(IMAGE,fixture())['source_sha256']==SOURCE['archive_sha256']


@pytest.mark.parametrize('mutation',['version','source','hash','path','symbol','baseline','sanitizer','image','missing','mismatch'])
def test_missing_stale_or_mismatched_native_evidence_cannot_attest(mutation):
    data=fixture()
    for row in data['evidence'][:2]:
        n=row['xrender']
        if mutation=='version':n['version']='0.9.12'
        elif mutation=='source':n['source_sha256']='c'*64
        elif mutation=='hash':n['library_sha256']='invalid'
        elif mutation=='path':n['loaded_path']='/tmp/forged.so'
        elif mutation=='symbol':n['symbol']='unrelated'
        elif mutation=='baseline':n['baseline_asan_overflow_reproduced']=False
        elif mutation=='sanitizer':n['asan_ubsan_protocol_regressions']='skipped'
    if mutation=='image':data['image']='sha256:'+'c'*64
    elif mutation=='missing':data['evidence'].pop()
    elif mutation=='mismatch':data['evidence'][0]['xrender']['library_sha256']='c'*64
    with pytest.raises(ValueError):review.verify_xrender_probe(IMAGE,data)
