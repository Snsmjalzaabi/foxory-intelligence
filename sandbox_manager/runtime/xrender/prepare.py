"""Authenticate both the fixed release and the test-only vulnerable control."""
import importlib.util
import json
import os
from pathlib import Path
import tarfile


def prepare() -> None:
    spec=importlib.util.spec_from_file_location('signed_source','/opt/foxory-pcre2/prepare.py')
    source=importlib.util.module_from_spec(spec);spec.loader.exec_module(source)
    root=Path('/opt/foxory-xrender');build=Path('/build/xrender');build.mkdir(mode=0o700)
    for name,inputs in [('fixed',root),('baseline',root/'baseline')]:
        output=build/name;policy=source.fetch_verified(inputs,output,'source.tar.xz')
        prefix='libXrender-'+policy['version']
        with tarfile.open(output/'source.tar.xz','r:xz') as archive:
            members=archive.getmembers()
            if len(members)>2000 or sum(m.size for m in members)>20_000_000 or any(Path(m.name).parts[0]!=prefix for m in members):
                raise ValueError('Xrender source extraction boundary')
            archive.extractall(output,filter='data')
        text=(output/prefix/'src/Xrender.c').read_text()
        if ('(rep.numSubpixel <= rep.numScreens)' in text)!=(name=='fixed'):
            raise ValueError('Signed Xrender source does not match the reviewed fixed/control code')
        print(json.dumps({'event':'xrender_source_verified','role':name,'version':policy['version'],'sha256':policy['archive_sha256']}))


if __name__=='__main__':
    if os.environ.get('FOXORY_WORKER_IMAGE_BUILD')!='1' or os.getuid()!=1000:
        raise SystemExit('Non-root image-build-only helper')
    prepare()
