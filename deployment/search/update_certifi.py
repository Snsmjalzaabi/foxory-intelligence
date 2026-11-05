"""Install a pinned pure-Python CA bundle without adding pip to the runtime."""
import hashlib,io,json,shutil,urllib.request,zipfile
from pathlib import Path
metadata=json.loads(Path('/tmp/certifi.json').read_text())
site=Path('/usr/local/searxng/.venv/lib/python3.14/site-packages')
assert site.is_dir(),'Search image Python layout changed; review before updating'
with urllib.request.urlopen(metadata['url'],timeout=60) as response:raw=response.read(500001)
assert len(raw)<=500000 and hashlib.sha256(raw).hexdigest()==metadata['sha256'],'Certificate bundle digest mismatch'
for old in site.glob('certifi-*.dist-info'):shutil.rmtree(old)
shutil.rmtree(site/'certifi')
with zipfile.ZipFile(io.BytesIO(raw)) as archive:
    for name in archive.namelist():
        path=Path(name)
        assert not path.is_absolute() and '..' not in path.parts
        if path.parts[0] not in {'certifi','certifi-'+metadata['version']+'.dist-info'}:continue
        target=site/path
        if name.endswith('/'):target.mkdir(parents=True,exist_ok=True)
        else:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(archive.read(name))
