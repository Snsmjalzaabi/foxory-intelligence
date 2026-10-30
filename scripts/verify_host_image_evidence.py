#!/usr/bin/env python3
"""Bind a trusted fixture's actual runtime reports to its audited worker image.

This is consistency verification, not signed attestation or license clearance.
It never activates profiles, runs task code or accepts application uploads.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any

ROOT=Path(__file__).resolve().parents[1]


def required_policy_digest() -> str:
    return hashlib.sha256((ROOT/'deployment/required-security-fixes.json').read_bytes()).hexdigest()


def worker_policy_digest() -> str:
    return hashlib.sha256((ROOT/'sandbox_manager/runtime/worker-packages.json').read_bytes()).hexdigest()


def verify_reports(image: str, audit: dict[str, Any], integration: dict[str, Any],
                   tcp: dict[str, Any], unix: dict[str, Any]) -> dict[str, Any]:
    if not re.fullmatch(r'sha256:[a-f0-9]{64}', image):
        raise ValueError('An immutable image ID is required')
    reports = {'audit': audit, 'integration': integration, 'tcp': tcp, 'unix': unix}
    for name, report in reports.items():
        identity = report.get('worker_image') if name == 'integration' else report.get('image')
        if identity != image:
            raise ValueError(name + ' worker image mismatch')
        if report.get('status') != 'passed':
            raise ValueError(name + ' did not pass')
    archive = audit.get('archive', {})
    if (archive.get('config_digest') != image
            or not isinstance(archive.get('sha256'), str)
            or not re.fullmatch(r'[a-f0-9]{64}', archive['sha256'])
            or type(archive.get('bytes')) is not int
            or not 0 < archive['bytes'] <= 8 * 1024**3):
        raise ValueError('Missing verified source archive identity')
    if (audit.get('coverage_reported') is not True or audit.get('blocking') != []
            or audit.get('unfixed_findings_ignored') is not False
            or type(audit.get('sbom_components')) is not int or audit['sbom_components'] <= 0):
        raise ValueError('Incomplete or blocking image audit')
    if audit.get('required_security_fixes_sha256') != required_policy_digest():
        raise ValueError('Audit security-remediation policy mismatch')
    packages=audit.get('worker_package_policy',{})
    if (packages.get('status')!='passed' or packages.get('sha256')!=worker_policy_digest()
            or packages.get('required_missing')!=[] or packages.get('forbidden_present')!=[]
            or packages.get('version_mismatches')!=[]):
        raise ValueError('Worker package-removal policy mismatch/incomplete')
    if integration.get('owner_data_accessed') is not False:
        raise ValueError('Disposable fixture boundary was not established')
    groups: dict[str, int] = {}
    for name, report, minimum, cleanup in [
        ('integration', integration, 7, 'cleanup_verified'),
        ('tcp', tcp, 9, 'owned_container_cleanup'),
        ('unix', unix, 10, 'owned_container_cleanup'),
    ]:
        checks = report.get('checks')
        if (report.get(cleanup) is not True or not isinstance(checks, list)
                or len(checks) < minimum or not all(
                    isinstance(check, dict) and check.get('passed') is True
                    and isinstance(check.get('name'), str) and check['name'] for check in checks)):
            raise ValueError(name + ' acceptance/cleanup is incomplete')
        if len({check['name'] for check in checks}) != len(checks):
            raise ValueError(name + ' has duplicate check groups')
        groups[name] = len(checks)
    return {
        'status': 'passed', 'image': image,
        'archive_sha256': archive['sha256'], 'archive_bytes': archive['bytes'],
        'archive_config_digest': archive['config_digest'],
        'runtime_check_groups': groups,
        'sbom_components': audit['sbom_components'],
        'required_security_fixes_sha256': audit['required_security_fixes_sha256'],
        'worker_package_policy_sha256':packages['sha256'],
        'total_findings': audit.get('total_findings'),
        'limits': 'Trusted fixture consistency only. Lower findings, compiled-browser '
                  'coverage and binary license/source-delivery review remain separate. '
                  'No owner-PC, GPU, production or universal sandbox assurance.',
    }


def load_report(path: Path) -> dict[str, Any]:
    with path.open('rb') as source:
        value = source.read(1_000_001)
    if len(value) > 1_000_000:
        raise ValueError('Summary byte budget exceeded')
    report = json.loads(value)
    if not isinstance(report, dict):
        raise ValueError('Expected a summary object')
    return report


def verify_pcre2_probe(image: str, probe: dict[str, Any]) -> dict[str, Any]:
    policy=json.loads((ROOT/'sandbox_manager/runtime/pcre2/source.json').read_text())
    rows=probe.get('evidence',[])
    if (probe.get('image')!=image or probe.get('status')!='fixed_probes_passed'
            or len(rows)!=3 or {r.get('profile') for r in rows}!={'javascript','typescript','browser'}
            or not all(r.get('fixture_passed') is True for r in rows)):
        raise ValueError('Missing exact-image native PCRE2 probe')
    native=[r.get('pcre2',{}) for r in rows if r['profile']!='browser']
    if native[0]!=native[1]:raise ValueError('PCRE2 JS/TS evidence mismatch')
    p=native[0]
    if (not str(p.get('version','')).startswith(policy['version']+' ')
            or p.get('source_sha256')!=policy['archive_sha256']
            or not re.fullmatch('[a-f0-9]{64}',str(p.get('library_sha256','')))
            or p.get('jit') is not True or p.get('unicode') is not True
            or p.get('normal_upstream_tests')!='passed' or p.get('asan_ubsan_upstream_tests')!='passed'
            or p.get('dfa_error')!=-63 or p.get('jit_stack_error')!=-46):
        raise ValueError('Invalid installed PCRE2 security evidence')
    return p


def verify_xrender_probe(image: str, probe: dict[str, Any]) -> dict[str, Any]:
    policy=json.loads((ROOT/'sandbox_manager/runtime/xrender/source.json').read_text())
    rows=probe.get('evidence',[])
    if (probe.get('image')!=image or probe.get('status')!='fixed_probes_passed'
            or len(rows)!=3 or {r.get('profile') for r in rows}!={'javascript','typescript','browser'}
            or not all(r.get('fixture_passed') is True for r in rows)):
        raise ValueError('Missing exact-image Xrender probe')
    native=[r.get('xrender',{}) for r in rows if r['profile']!='browser']
    if native[0]!=native[1]:raise ValueError('Xrender JS/TS evidence mismatch')
    p=native[0]
    if (p.get('version')!=policy['version'] or p.get('source_sha256')!=policy['archive_sha256']
            or not re.fullmatch('[a-f0-9]{64}',str(p.get('library_sha256','')))
            or p.get('loaded_path')!=p.get('library_path') or not str(p.get('loaded_path','')).startswith('/usr/lib/')
            or p.get('symbol')!='XRenderQueryFormats' or p.get('baseline_asan_overflow_reproduced') is not True
            or p.get('normal_protocol_regressions')!='passed' or p.get('asan_ubsan_protocol_regressions')!='passed'):
        raise ValueError('Invalid installed Xrender security evidence')
    return p


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    root = args.evidence
    info = root.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('A private operator-owned fixture directory is required')
    report = verify_reports(args.image,
        load_report(root / 'image-audit/summary.json'), load_report(root / 'summary.json'),
        load_report(root / 'security/tcp/summary.json'), load_report(root / 'security/unix/summary.json'))
    report['pcre2_runtime']=verify_pcre2_probe(args.image,load_report(root/'pcre2-runtime-probe.json'))
    report['xrender_runtime']=verify_xrender_probe(args.image,load_report(root/'pcre2-runtime-probe.json'))
    report['source_commit'] = os.getenv('GITHUB_SHA', '')
    descriptor = os.open(root / 'verified-image-provenance.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w') as output:
        json.dump(report, output, indent=2)
        output.write('\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
