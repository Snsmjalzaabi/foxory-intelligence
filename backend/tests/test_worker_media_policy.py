"""Pure package-plan/SBOM guards. Never runs apt or generated programs on the host."""
import importlib.util
import json
from pathlib import Path
import subprocess

import pytest

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('media_audit',ROOT/'scripts/image_audit.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
POLICY=json.loads((ROOT/'sandbox_manager/runtime/worker-packages.json').read_text())


def test_sbom_keeps_chromium_and_rejects_removed_or_missing_packages():
    components=[{'name':name,'purl':'pkg:deb/ubuntu/'+name+'@fixture'} for name in POLICY['required_packages']]
    components += [{'name':name,'version':version,'purl':'pkg:deb/ubuntu/'+name+'@'+version}
                   for name,version in POLICY['required_versions'].items()]
    assert audit.worker_packages(components)['status']=='passed'
    assert audit.worker_packages(components[1:])['required_missing']==[POLICY['required_packages'][0]]
    for name in POLICY['forbidden_packages']:
        result=audit.worker_packages(components+[{'name':name,'purl':'pkg:deb/ubuntu/'+name+'@fixture'}])
        assert result['status']=='blocked' and result['forbidden_present']==[name]


@pytest.mark.parametrize('variant',['allowed','chromium','incomplete','conflict','install'])
def test_trusted_node_build_helper_validates_only_fixture_plan(variant):
    # Importing the module never invokes package-management operations.
    driver='''import {validatePlan} from %s;
import fs from 'node:fs';
const data=JSON.parse(fs.readFileSync(0,'utf8'));
console.log(JSON.stringify([...validatePlan(data.policy,data.plan)]));'''
    driver=driver%json.dumps((ROOT/'sandbox_manager/runtime/prune-media.mjs').as_uri())
    policy=json.loads(json.dumps(POLICY));lines=['Purg '+name+' [fixture]' for name in policy['forbidden_packages']]
    if variant=='chromium':lines.append('Remv libnss3:amd64 [fixture]')
    if variant=='incomplete':lines.pop()
    if variant=='conflict':policy['forbidden_packages'].append(policy['required_packages'][0])
    if variant=='install':lines.append('Inst replacement-library (fixture)')
    # Put this reviewed test driver in -e; only JSON fixture data goes on stdin.
    result=subprocess.run(['node','--input-type=module','-e',driver],input=json.dumps({'policy':policy,'plan':'\n'.join(lines)}),text=True,capture_output=True,timeout=10)
    if variant=='allowed':assert result.returncode==0 and set(json.loads(result.stdout))==set(POLICY['forbidden_packages'])
    else:assert result.returncode!=0 and 'Error:' in result.stderr


def test_build_helper_refuses_direct_host_invocation():
    result=subprocess.run(['node',str(ROOT/'sandbox_manager/runtime/prune-media.mjs')],text=True,capture_output=True,timeout=10)
    assert result.returncode!=0 and 'Build-only helper' in result.stderr


@pytest.mark.parametrize('filename',['libsoup-3.0.so','libsoup-3.0.so.0','libsoup-3.0.so.0.7.3','libavcodec.so.60',
    'libcjson.so.1','libmbedcrypto.so.7','libOpenEXR-3_1.so.30','libOpenEXRCore-3_1.so.30','libOpenEXRUtil-3_1.so.30','libmfx.so.1',
    'libzvbi.so.0','libsndfile.so.1','libopenjp2.so.7','libvpl.so.2','libfluidsynth.so.3',
    'libsrt-gnutls.so.1.5','libass.so.9','libduktape.so.207','libopenh264.so.7',
    'libvo-amrwbenc.so.0','libwavpack.so.1','libx264.so.164'])
def test_removed_library_files_rejected_even_without_package_metadata(filename):
    driver='''import {validateSharedLibraryNames} from %s;
import fs from 'node:fs';
validateSharedLibraryNames(JSON.parse(fs.readFileSync(0,'utf8')));'''
    driver=driver%json.dumps((ROOT/'sandbox_manager/runtime/prune-media.mjs').as_uri())
    result=subprocess.run(['node','--input-type=module','-e',driver],input=json.dumps([filename]),text=True,capture_output=True,timeout=10)
    assert result.returncode!=0 and 'Excluded media/HTTP library' in result.stderr
    # Reviewed Chromium dependencies/bundled codec names are not this policy's targets.
    result=subprocess.run(['node','--input-type=module','-e',driver],input=json.dumps(['libnss3.so','libffmpeg.so','libsoup-fixture.txt']),text=True,capture_output=True,timeout=10)
    assert result.returncode==0
