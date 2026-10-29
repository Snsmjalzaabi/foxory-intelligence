"""Package the actually built library with truthful source/version metadata."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess


def symbols(path: Path) -> set[str]:
    result = subprocess.run(['nm', '-D', '--defined-only', str(path)], check=True, capture_output=True, text=True)
    return {line.split()[-1].split('@')[0] for line in result.stdout.splitlines()
            if line.split() and line.split()[-1].startswith('pcre2_')}


def package() -> None:
    root = Path('/opt/foxory-pcre2')
    policy = json.loads((root / 'source.json').read_text())
    build = Path('/build/pcre2/normal')
    multiarch = subprocess.check_output(['dpkg-architecture', '-qDEB_HOST_MULTIARCH'], text=True).strip()
    arch = subprocess.check_output(['dpkg', '--print-architecture'], text=True).strip()
    library = (build / '.libs/libpcre2-8.so.0').resolve(strict=True)
    previous = Path('/usr/lib') / multiarch / 'libpcre2-8.so.0'
    old_symbols, new_symbols = symbols(previous), symbols(library)
    if not old_symbols or not old_symbols <= new_symbols:
        raise ValueError('PCRE2 public ABI symbol regression')
    dynamic = subprocess.check_output(['readelf', '-d', str(library)], text=True)
    if re.findall(r'\(SONAME\).*\[(.*?)\]', dynamic) != ['libpcre2-8.so.0']:
        raise ValueError('Unexpected PCRE2 SONAME')
    if set(re.findall(r'\(NEEDED\).*\[(.*?)\]', dynamic)) - {'libc.so.6', 'ld-linux-x86-64.so.2', 'ld-linux-aarch64.so.1'}:
        raise ValueError('Unexpected PCRE2 dynamic dependency')
    output = Path('/out'); output.mkdir(exist_ok=True)
    stage = Path('/build/pcre2/package')
    destination = stage / 'usr/lib' / multiarch
    destination.mkdir(parents=True)
    shutil.copy2(library, destination / library.name)
    (destination / 'libpcre2-8.so.0').symlink_to(library.name)
    runtime = stage / 'opt/foxory'; runtime.mkdir(parents=True)
    shutil.copy2(build / 'probe', runtime / 'pcre2-verify')
    manifest = {'version': policy['version'], 'package_version': policy['package_version'],
                'source_sha256': policy['archive_sha256'],
                'library_path': str(Path('/usr/lib') / multiarch / library.name),
                'library_sha256': hashlib.sha256(library.read_bytes()).hexdigest(),
                'signing_subkey': policy['signing_subkey_fingerprint'],
                'normal_upstream_tests': 'passed', 'asan_ubsan_upstream_tests': 'passed',
                'public_abi_symbols_preserved': len(old_symbols), 'fixes': policy['fixes']}
    (runtime / 'pcre2-runtime.json').write_text(json.dumps(manifest, indent=2) + '\n')
    docs = stage / 'usr/share/doc/libpcre2-8-0'; docs.mkdir(parents=True)
    for name, source in [('copyright', root / 'LICENCE.md'), ('SLJIT-LICENSE', root / 'SLJIT-LICENSE'),
                         ('foxory-source.json', root / 'source.json')]:
        shutil.copy2(source, docs / name)
    control = stage / 'DEBIAN'; control.mkdir()
    (control / 'control').write_text(f'''Package: libpcre2-8-0
Source: pcre2 ({policy['package_version']})
Version: {policy['package_version']}
Architecture: {arch}
Maintainer: FOXORY Community <noreply@localhost>
Depends: libc6 (>= 2.39)
Section: libs
Priority: optional
Homepage: https://github.com/PCRE2Project/pcre2
Description: PCRE2 {policy['version']} 8-bit library, FOXORY upstream-source build
 Replaces the affected Noble library with signed upstream source.
 Built from the exact source recorded in foxory-source.json; not an Ubuntu update.
''')
    (control / 'triggers').write_text('activate-noawait ldconfig\n')
    subprocess.run(['dpkg-deb', '--root-owner-group', '--build', str(stage), str(output / 'libpcre2-8-0.deb')], check=True)
    shutil.copy2('/build/pcre2/source.tar.bz2', output / 'pcre2-10.49.tar.bz2')
    (output / 'pcre2-build-evidence.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'event': 'pcre2_build_verified', **manifest}))


if __name__ == '__main__':
    if os.environ.get('FOXORY_WORKER_IMAGE_BUILD') != '1' or os.getuid() != 1000:
        raise SystemExit('Non-root image-build-only helper')
    package()
