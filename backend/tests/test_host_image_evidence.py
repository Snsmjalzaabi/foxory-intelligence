"""Synthetic report consistency tests; these do not run or scan OCI workers."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('host_image_evidence', ROOT / 'scripts/verify_host_image_evidence.py')
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)
IMAGE = 'sha256:' + 'a' * 64


def reports():
    def checks(n):
        return [{'name': 'synthetic-' + str(i), 'passed': True} for i in range(n)]
    return {
        'audit': {'status': 'passed', 'image': IMAGE, 'coverage_reported': True,
                  'blocking': [], 'unfixed_findings_ignored': False, 'sbom_components': 50,
                  'archive': {'config_digest': IMAGE, 'sha256': 'b' * 64, 'bytes': 4096}},
        'integration': {'status': 'passed', 'worker_image': IMAGE, 'checks': checks(7),
                        'cleanup_verified': True, 'owner_data_accessed': False},
        'tcp': {'status': 'passed', 'image': IMAGE, 'checks': checks(9), 'owned_container_cleanup': True},
        'unix': {'status': 'passed', 'image': IMAGE, 'checks': checks(10), 'owned_container_cleanup': True},
    }


def test_one_verified_archive_and_all_runtime_images_agree():
    result = review.verify_reports(IMAGE, **reports())
    assert result['archive_config_digest'] == result['image'] == IMAGE
    assert result['runtime_check_groups'] == {'integration': 7, 'tcp': 9, 'unix': 10}


@pytest.mark.parametrize('stage', ['audit', 'integration', 'tcp', 'unix'])
def test_no_runtime_or_scanner_image_substitution(stage):
    data = reports()
    data[stage]['worker_image' if stage == 'integration' else 'image'] = 'sha256:' + 'c' * 64
    with pytest.raises(ValueError, match='image mismatch'):
        review.verify_reports(IMAGE, **data)


@pytest.mark.parametrize('stage', ['integration', 'tcp', 'unix'])
def test_failed_cleanup_or_incomplete_groups_cannot_attest(stage):
    for mutation in ['cleanup', 'missing', 'duplicate', 'failed']:
        data = reports()
        if mutation == 'cleanup':data[stage]['cleanup_verified' if stage == 'integration' else 'owned_container_cleanup'] = False
        elif mutation == 'missing':data[stage]['checks'].pop()
        elif mutation == 'duplicate':data[stage]['checks'][1] = copy.deepcopy(data[stage]['checks'][0])
        else:data[stage]['checks'][0]['passed'] = False
        with pytest.raises(ValueError):review.verify_reports(IMAGE, **data)


@pytest.mark.parametrize('mutation', ['archive', 'config', 'hash', 'size', 'coverage', 'blocking', 'ignored', 'sbom'])
def test_unknown_or_mismatched_audit_never_attests(mutation):
    data = reports()
    if mutation == 'archive':data['audit'].pop('archive')
    elif mutation == 'config':data['audit']['archive']['config_digest'] = 'sha256:' + 'c' * 64
    elif mutation == 'hash':data['audit']['archive']['sha256'] = 'invalid'
    elif mutation == 'size':data['audit']['archive']['bytes'] = 0
    elif mutation == 'coverage':data['audit']['coverage_reported'] = False
    elif mutation == 'blocking':data['audit']['blocking'] = [{'severity': 'HIGH'}]
    elif mutation == 'ignored':data['audit']['unfixed_findings_ignored'] = True
    else:data['audit']['sbom_components'] = 0
    with pytest.raises(ValueError):review.verify_reports(IMAGE, **data)


def test_previously_separate_real_scan_and_runtime_evidence_is_rejected():
    data = reports()
    audit = json.loads((ROOT / 'docs/evidence/worker-final-ci-image-audit-2026-10-29.json').read_text())
    integration = json.loads((ROOT / 'docs/evidence/full-systemd-compose-ubuntu26-2026-10-29.json').read_text())
    assert audit['image'] != integration['worker_image']
    with pytest.raises(ValueError, match='audit worker image mismatch'):
        review.verify_reports(integration['worker_image'], audit, integration, data['tcp'], data['unix'])
