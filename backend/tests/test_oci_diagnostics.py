"""Operator errors are bounded/redacted while execution remains quarantined."""
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sandbox_manager.oci_runtime import Runtime


async def test_control_error_diagnostic_is_bounded_redacted_and_does_not_enable_profiles(tmp_path,monkeypatch,caplog):
    monkeypatch.setenv('FOXORY_SANDBOX_KEY','fictional-secret-for-redaction')
    runtime=Runtime(tmp_path)
    async def failed(*args,**kwargs):return 125,'','x'*2000+' fictional-secret-for-redaction configuration denied'
    monkeypatch.setattr(runtime,'cli',failed)
    with pytest.raises(RuntimeError):await runtime.recover()
    record=json.loads(caplog.records[-1].message)
    assert record['event']=='oci.enumeration.failed'
    assert len(record['detail'])<=1500 and '[redacted]' in record['detail']
    assert 'fictional-secret-for-redaction' not in record['detail']
    assert not runtime.capabilities()['javascript']['enabled']
