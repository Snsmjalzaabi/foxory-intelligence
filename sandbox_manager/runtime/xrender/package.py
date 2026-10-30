"""Package the fixed library only, after actual protocol and ABI regressions."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess


def symbols(path: Path) -> set[str]:
    out=subprocess.check_output(['nm','-D','--defined-only',str(path)],text=True)
    return {line.split()[-1].split('@')[0] for line in out.splitlines()
            if line.split() and line.split()[-1].startswith(('XRender','_XRender'))}


def package() -> None:
    root=Path('/opt/foxory-xrender');build=Path('/build/xrender')
    policy=json.loads((root/'source.json').read_text())
    receipts={mode:json.loads((build/mode/'regression.json').read_text()) for mode in ['baseline-build','normal','sanitized']}
    if not receipts['baseline-build']['cases'][0].get('expected_baseline_overflow_reproduced'):
        raise ValueError('Missing genuine vulnerable control reproduction')
    for mode in ['normal','sanitized']:
        if receipts[mode]['status']!='passed' or len(receipts[mode]['cases'])!=2:
            raise ValueError('Missing fixed healthy/hostile protocol regression')
    multiarch=subprocess.check_output(['dpkg-architecture','-qDEB_HOST_MULTIARCH'],text=True).strip()
    arch=subprocess.check_output(['dpkg','--print-architecture'],text=True).strip()
    library=(build/'normal/src/.libs/libXrender.so.1').resolve(strict=True)
    old=symbols(Path('/usr/lib')/multiarch/'libXrender.so.1')
    if not old or not old<=symbols(library):raise ValueError('Xrender ABI regression')
    dynamic=subprocess.check_output(['readelf','-d',str(library)],text=True)
    if re.findall(r'\(SONAME\).*\[(.*?)\]',dynamic)!=['libXrender.so.1']:
        raise ValueError('Xrender SONAME regression')
    if set(re.findall(r'\(NEEDED\).*\[(.*?)\]',dynamic))-{'libc.so.6','libX11.so.6'}:
        raise ValueError('Unexpected Xrender dependency')
    stage=build/'package';dest=stage/'usr/lib'/multiarch;dest.mkdir(parents=True)
    shutil.copy2(library,dest/library.name);(dest/'libXrender.so.1').symlink_to(library.name)
    runtime=stage/'opt/foxory';runtime.mkdir(parents=True)
    shutil.copy2(build/'normal/probe',runtime/'xrender-verify')
    manifest={'version':policy['version'],'package_version':policy['package_version'],
        'source_sha256':policy['archive_sha256'],'fix_commit':policy['fix_commit'],'cve':policy['cve'],
        'library_path':str(Path('/usr/lib')/multiarch/library.name),
        'library_sha256':hashlib.sha256(library.read_bytes()).hexdigest(),
        'public_abi_symbols_preserved':len(old),'baseline_asan_overflow_reproduced':True,
        'normal_protocol_regressions':'passed','asan_ubsan_protocol_regressions':'passed'}
    (runtime/'xrender-runtime.json').write_text(json.dumps(manifest,indent=2)+'\n')
    docs=stage/'usr/share/doc/libxrender1';docs.mkdir(parents=True)
    shutil.copy2(root/'COPYING',docs/'copyright');shutil.copy2(root/'source.json',docs/'foxory-source.json')
    control=stage/'DEBIAN';control.mkdir()
    (control/'control').write_text(f'''Package: libxrender1
Source: libxrender ({policy['package_version']})
Version: {policy['package_version']}
Architecture: {arch}
Maintainer: FOXORY Community <noreply@localhost>
Depends: libc6 (>= 2.39), libx11-6 (>= 2:1.8.7)
Section: libs
Priority: optional
Homepage: https://gitlab.freedesktop.org/xorg/lib/libxrender
Description: libXrender {policy['version']}, verified FOXORY upstream-source build
 Fixes CVE-2026-88807 using signed upstream source. Not an Ubuntu-issued update.
''')
    (control/'triggers').write_text('activate-noawait ldconfig\n')
    subprocess.run(['dpkg-deb','--root-owner-group','--build',str(stage),'/out/libxrender1.deb'],check=True)
    print(json.dumps({'event':'xrender_build_verified',**manifest}))


if __name__=='__main__':
    if os.environ.get('FOXORY_WORKER_IMAGE_BUILD')!='1' or os.getuid()!=1000:
        raise SystemExit('Non-root image-build-only helper')
    package()
