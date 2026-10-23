"""Inventory installed Python runtime and npm dependencies; preserve bundled license notices."""
import importlib.metadata as md
import json
from pathlib import Path
import re
root=Path(__file__).resolve().parents[1]
norm=lambda n:re.sub(r'[-_.]+','-',n).lower()
names={norm(x.split('==')[0]) for x in (root/'backend/requirements.lock').read_text().splitlines() if '==' in x}
python=[];notices=[]
for d in md.distributions():
    name=d.metadata['Name']
    if norm(name) not in names:continue
    python.append({'name':name,'version':d.version,'license':d.metadata.get('License-Expression') or d.metadata.get('License') or 'See bundled license notices','homepage':d.metadata.get('Home-page') or d.metadata.get('Project-URL')})
    for f in d.files or []:
        if re.search(r'(^|/)(licen[cs]e|copying|notice)([./_-]|$)',str(f),re.I):
            p=d.locate_file(f)
            if p.is_file():
                notices.append(f'\n===== Python {name} {d.version}: {f} =====\n'+p.read_text(errors='replace'))
npm=[]
for p in sorted((root/'frontend/node_modules').glob('**/package.json')):
    try:d=json.loads(p.read_text())
    except Exception:continue
    if not d.get('name') or not d.get('version'):continue
    npm.append({'name':d['name'],'version':d['version'],'license':d.get('license','Unknown'),'repository':d.get('repository')})
    for f in p.parent.iterdir():
        if f.is_file() and re.match(r'^(licen[cs]e|copying|notice)([._-]|$)',f.name,re.I):
            notices.append(f'\n===== npm {d["name"]} {d["version"]}: {f.name} =====\n'+f.read_text(errors='replace'))
(root/'docs/dependency-inventory.json').write_text(json.dumps({'python_runtime':python,'npm_installed_including_dev':npm},indent=2)+'\n')
(root/'THIRD_PARTY_NOTICES.txt').write_text('Installed dependency license notices. These packages retain their own licenses.\n'+''.join(notices))
print(f'Inventoried {len(python)} Python runtime packages and {len(npm)} npm package manifests.')
