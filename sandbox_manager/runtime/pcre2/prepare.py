"""Trusted image-build input verification. Never executes downloaded scripts."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import ssl
import subprocess
import tarfile
import tempfile
import urllib.request


def verify_bytes(data: bytes, expected: str) -> None:
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('PCRE2 input checksum mismatch')


def fetch_verified(root: Path, output: Path) -> dict:
    policy = json.loads((root / 'source.json').read_text())
    key = (root / 'release-key.asc').read_bytes()
    verify_bytes(key, policy['public_key_sha256'])
    context = ssl.create_default_context()
    if Path('/run/secrets/proxy_ca').is_file():
        context.load_verify_locations('/run/secrets/proxy_ca')
    output.mkdir(mode=0o700)
    for suffix, digest in [('', policy['archive_sha256']), ('.sig', policy['signature_sha256'])]:
        with urllib.request.urlopen(policy['archive_url'] + suffix, context=context, timeout=60) as response:
            data = response.read(10_000_001)
        if len(data) > 10_000_000:
            raise ValueError('PCRE2 archive byte budget')
        verify_bytes(data, digest)
        (output / ('source.tar.bz2' + suffix)).write_bytes(data)
    with tempfile.TemporaryDirectory() as home:
        subprocess.run(['gpg', '--homedir', home, '--batch', '--import', str(root / 'release-key.asc')],
                       check=True, capture_output=True, timeout=20)
        result = subprocess.run(['gpg', '--homedir', home, '--batch', '--status-fd=1', '--verify',
                                 str(output / 'source.tar.bz2.sig'), str(output / 'source.tar.bz2')],
                                check=True, capture_output=True, text=True, timeout=20)
        valid = [line.split() for line in result.stdout.splitlines() if line.startswith('[GNUPG:] VALIDSIG ')]
        if len(valid) != 1 or valid[0][2] != policy['signing_subkey_fingerprint'] or valid[0][-1] != policy['primary_key_fingerprint']:
            raise ValueError('Unexpected PCRE2 release signer')
    return policy


def prepare(root: Path, output: Path) -> None:
    policy = fetch_verified(root, output)
    # Source is authenticated before extraction. data filter still rejects unsafe entries.
    with tarfile.open(output / 'source.tar.bz2', 'r:bz2') as archive:
        members = archive.getmembers()
        if len(members) > 10000 or sum(m.size for m in members) > 200_000_000:
            raise ValueError('PCRE2 extracted source budget')
        prefix = 'pcre2-' + policy['version']
        if any(Path(m.name).parts[0] != prefix for m in members):
            raise ValueError('Unexpected PCRE2 source root')
        archive.extractall(output, filter='data')
    print(json.dumps({'status': 'pcre2_signature_verified', 'version': policy['version'],
                      'source_sha256': policy['archive_sha256'], 'signer': policy['signing_subkey_fingerprint']}))


if __name__ == '__main__':
    if os.environ.get('FOXORY_WORKER_IMAGE_BUILD') != '1':
        raise SystemExit('Image-build-only helper; not an agent tool')
    prepare(Path('/opt/foxory-pcre2'), Path('/build/pcre2'))
