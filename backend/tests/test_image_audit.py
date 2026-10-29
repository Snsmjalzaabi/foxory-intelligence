"""Verifier parsing/archive boundaries, not a real image scan."""
import importlib.util
import io
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
