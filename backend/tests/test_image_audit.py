"""Verifier parsing/archive boundaries, not a real image scan."""
import importlib.util
import io
import hashlib
import json
from pathlib import Path
import tarfile

import pytest

spec=importlib.util.spec_from_file_location('image_audit',Path(__file__).resolve().parents[2]/'scripts/image_audit.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)


def test_unfixed_high_findings_and_unknown_coverage_are_blockers():
    report={'SchemaVersion':2,'Metadata':{'OS':{'Family':'ubuntu'}},'Results':[{'Vulnerabilities':[
        {'VulnerabilityID':'CVE-FIXTURE','Severity':'HIGH','PkgName':'fictional','FixedVersion':''}]}]}
    result=audit.findings(report)
    assert result['status']=='blocked' and result['blocking'][0]['id']=='CVE-FIXTURE'
    report['Results'][0]['Vulnerabilities']=[]
    assert audit.findings(report)['status']=='passed'
    assert audit.findings({})['status']=='blocked'
    report['Metadata']['OS']['EOSL']=True
    assert audit.findings(report)['status']=='blocked'


def test_required_zlib_remediation_blocks_medium_severity_without_relabeling():
    vulnerability={'VulnerabilityID':'CVE-2026-85091','PkgName':'zlib1g',
                   'InstalledVersion':'1:1.3.dfsg-3.1ubuntu2.2',
                   'FixedVersion':'1:1.3.dfsg-3.1ubuntu2.3','Severity':'MEDIUM'}
    report={'SchemaVersion':2,'Metadata':{'OS':{'Family':'ubuntu','Name':'24.04'}},
            'Results':[{'Vulnerabilities':[vulnerability]}]}
    result=audit.findings(report)
    assert result['status']=='blocked' and result['blocking'][0]['severity']=='MEDIUM'
    assert result['blocking'][0]['gate_reason']=='required_remediation'
    assert result['required_security_fixes_sha256']==hashlib.sha256(audit.FIXES.read_bytes()).hexdigest()
    report['Results'][0]['Vulnerabilities']=[]
    assert audit.findings(report)['status']=='passed'


@pytest.mark.parametrize('rules',[[],[{'id':'invalid','package':'zlib1g'}]])
def test_invalid_or_missing_remediation_policy_does_not_silently_pass(tmp_path,monkeypatch,rules):
    policy=tmp_path/'policy.json'
    policy.write_text(json.dumps({'schema_version':1,'required_remediations':rules}))
    monkeypatch.setattr(audit,'FIXES',policy)
    with pytest.raises(ValueError):audit.findings({})


@pytest.mark.parametrize('unsafe',[True,False])
def test_tool_archive_extracts_only_expected_regular_binary(tmp_path,unsafe):
    archive=tmp_path/'tool.tar.gz'
    with tarfile.open(archive,'w:gz') as output:
        member=tarfile.TarInfo('syft')
        if unsafe:member.type=tarfile.SYMTYPE;member.linkname='/etc/passwd';output.addfile(member)
        else:member.size=4;output.addfile(member,io.BytesIO(b'tool'))
        other=tarfile.TarInfo('../escape');other.size=3;output.addfile(other,io.BytesIO(b'bad'))
    if unsafe:
        with pytest.raises(ValueError):audit.extract_binary(archive,'syft',tmp_path/'syft')
    else:
        audit.extract_binary(archive,'syft',tmp_path/'syft')
        assert (tmp_path/'syft').read_bytes()==b'tool'
    assert not (tmp_path.parent/'escape').exists()


@pytest.mark.parametrize('variant',['valid','wrong-id','duplicate','symlink','multi-image','changed-layer'])
def test_rootless_export_identity_and_ambiguous_metadata_denial(tmp_path,variant):
    layer=b'reviewed fixture layer'
    config=json.dumps({'architecture':'amd64','os':'linux','rootfs':{
        'type':'layers','diff_ids':['sha256:'+hashlib.sha256(layer).hexdigest()]}}).encode()
    image='sha256:'+hashlib.sha256(config).hexdigest()
    manifest=[{'Config':'config.json','Layers':['layer.tar']}]
    if variant=='multi-image':manifest*=2
    path=tmp_path/'image.tar'
    with tarfile.open(path,'w') as output:
        for name,data in [('manifest.json',json.dumps(manifest).encode()),('config.json',config),
                          ('layer.tar',b'changed' if variant=='changed-layer' else layer)]:
            member=tarfile.TarInfo(name);member.size=len(data)
            if variant=='symlink' and name=='config.json':
                member.type=tarfile.SYMTYPE;member.linkname='/etc/passwd';member.size=0;output.addfile(member)
            else:output.addfile(member,io.BytesIO(data))
            if variant=='duplicate':output.addfile(member,io.BytesIO(data))
    with path.open('rb') as source:
        if variant=='valid':
            result=audit.archive_identity(source,image)
            assert result['sha256']==hashlib.sha256(path.read_bytes()).hexdigest()
            assert result['config_digest']==image
        else:
            with pytest.raises(ValueError):audit.archive_identity(source,'sha256:'+'a'*64 if variant=='wrong-id' else image)
