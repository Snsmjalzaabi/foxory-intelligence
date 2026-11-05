#!/usr/bin/env python3
"""FOXORY release checks: debloat scan, verification and packaging.

Usage (from anywhere inside the repository):
  release_checks.py scan                      list debloat candidates (read-only)
  release_checks.py verify [--python PATH]    backend tests, frontend build, links, compose
  release_checks.py package                   rebuild manifest + ZIP, verify checksum and coverage
"""
import argparse,hashlib,json,pathlib,re,shutil,subprocess,sys,zipfile

ROOT=pathlib.Path(subprocess.run(['git','rev-parse','--show-toplevel'],capture_output=True,text=True,check=True).stdout.strip())
# Imported only for their side effects before a security lockdown; never remove.
INTENTIONAL_IMPORTS={('backend/foxory/parser_worker.py','encodings'),('sandbox_manager/bootstrap.py','unittest')}
# distribution/ holds public-edition templates whose links resolve only in the generated tree.
SKIP_PARTS={'node_modules','.git','dist','.venv','__pycache__','distribution'}

def tracked():
    """Committed files plus new files not yet committed, minus anything .gitignore excludes."""
    return subprocess.run(['git','ls-files','--cached','--others','--exclude-standard'],cwd=ROOT,capture_output=True,text=True,check=True).stdout.split()

def broken_links():
    bad=[]
    for md in ROOT.rglob('*.md'):
        if SKIP_PARTS & set(md.relative_to(ROOT).parts):continue
        for m in re.finditer(r'\]\(([^)\s]+)\)',md.read_text(errors='ignore')):
            link=m.group(1).split('#')[0]
            if link and not re.match(r'[a-z]+:',link) and not (md.parent/link).exists():bad.append(f'{md.relative_to(ROOT)}: {link}')
    return bad

def scan(_):
    issues=0
    print('== Python dead code (vulture >=80%)')
    if shutil.which('vulture') or subprocess.run([sys.executable,'-m','vulture','--version'],capture_output=True).returncode==0:
        out=subprocess.run([sys.executable,'-m','vulture','backend/foxory','sandbox_manager','--min-confidence','80'],cwd=ROOT,capture_output=True,text=True).stdout
        for line in out.splitlines():
            m=re.match(r"(\S+):\d+: unused import '(\w+)'",line)
            if m and (m[1],m[2]) in INTENTIONAL_IMPORTS:continue
            print('  '+line);issues+=1
    else:print('  vulture not installed: pip install vulture')
    src={p:p.read_text() for p in (ROOT/'frontend/src').glob('*.ts*')}
    print('== Frontend exports and components never used elsewhere')
    for p,t in src.items():
        for name in re.findall(r'export (?:async )?(?:function|const|type) (\w+)',t):
            if not any(re.search(r'\b'+name+r'\b',o) for q,o in src.items() if q!=p) and len(re.findall(r'\b'+name+r'\b',t))<2:print(f'  {p.name}: {name}');issues+=1
        if p.suffix=='.tsx' and p.stem!='main' and not any(f"from './{p.stem}'" in o for o in src.values()):print(f'  unimported component: {p.name}');issues+=1
    print('== CSS classes never referenced')
    css=(ROOT/'frontend/src/style.css').read_text();code=' '.join(src.values())+(ROOT/'frontend/index.html').read_text()
    for c in sorted(set(re.findall(r'\.([a-zA-Z][\w-]*)',re.sub(r'url\([^)]*\)','',css)))):
        if not re.search(r'(?<![\w-])'+re.escape(c)+r'(?![\w-])',code):print('  .'+c);issues+=1
    print('== Scripts referenced nowhere (CI, tests, docs, other scripts)')
    files=tracked()
    for f in sorted(x for x in files if x.startswith('scripts/') and x.endswith('.py')):
        name=pathlib.Path(f).stem
        users=subprocess.run(['git','grep','-lIE',rf'{name}(\.py)?\b','--','.',':!'+f,':!SOURCE-MANIFEST.json'],cwd=ROOT,capture_output=True,text=True).stdout.split()
        if not users:print('  '+f);issues+=1
    print('== Broken Markdown links')
    for b in broken_links():print('  '+b);issues+=1
    print(f'\n{issues} candidate(s). Confirm each is unused (imports, tests, CI, packaging, docs) before deleting.')
    # A non-zero exit stops chained release commands until every candidate is resolved.
    if issues:sys.exit(1)

def run(cmd,cwd,label):
    print('== '+label,flush=True)
    r=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True)
    tail='\n'.join((r.stdout+r.stderr).strip().splitlines()[-3:])
    print('  '+tail.replace('\n','\n  '))
    if r.returncode:sys.exit(f'FAILED: {label}')

def verify(args):
    python=args.python or next((str(p) for p in [ROOT/'backend/.venv/bin/python',ROOT/'.venv/bin/python'] if p.exists()),sys.executable)
    run([python,'-m','pytest','-q','-m','not sandbox_runtime','-p','no:cacheprovider'],ROOT/'backend','Backend tests')
    run(['npm','run','build'],ROOT/'frontend','Frontend type check and build')
    shutil.rmtree(ROOT/'frontend/dist',ignore_errors=True);(ROOT/'frontend/tsconfig.tsbuildinfo').unlink(missing_ok=True)
    bad=broken_links()
    print('== Markdown links\n  '+(f'{len(bad)} broken: '+'; '.join(bad) if bad else 'all resolve'))
    if bad:sys.exit('FAILED: broken links')
    env={'FOXORY_TOKEN':'x','POSTGRES_PASSWORD':'x','FOXORY_DATABASE_LAYOUT':'modern','PATH':'/usr/bin:/bin:/usr/local/bin'}
    if shutil.which('docker'):
        r=subprocess.run(['docker','compose','--env-file','/dev/null','-f','compose.local.yaml','--profile','lite','--profile','voice','config','--quiet'],cwd=ROOT,env=env,capture_output=True,text=True)
        print('== Compose config\n  '+('valid' if not r.returncode else r.stderr.strip()[-300:]))
        if r.returncode:sys.exit('FAILED: compose config')
    print('\nVerification passed.')

def package(_):
    version=(ROOT/'VERSION').read_text().strip()
    shutil.rmtree(ROOT/'frontend/dist',ignore_errors=True)
    for old in (ROOT/'releases').glob('FOXORY-Local-*'):
        if not old.name.startswith(f'FOXORY-Local-{version}.'):old.unlink()
    out=ROOT/f'releases/FOXORY-Local-{version}.zip'
    subprocess.run([sys.executable,'scripts/package_release.py','--output',str(out)],cwd=ROOT,check=True)
    expected=(ROOT/f'releases/FOXORY-Local-{version}.sha256').read_text().split()[0]
    assert hashlib.sha256(out.read_bytes()).hexdigest()==expected,'ZIP checksum mismatch'
    manifest=json.loads((ROOT/'SOURCE-MANIFEST.json').read_text())
    listed={f['path'] for f in manifest['files']};files=set(tracked())-{'SOURCE-MANIFEST.json'}
    extra,missing=sorted(listed-files),sorted(files-listed)
    with zipfile.ZipFile(out) as z:leaked=[n for n in z.namelist() if re.search(r'/\.env$|/backups/|/data/|/\.local-ai/|\.gguf$',n)]
    print(f'== Package {out.name}\n  checksum OK, manifest version {manifest["version"]}, {len(listed)} files')
    problems=[f'manifest version {manifest["version"]} != {version}']*(manifest['version']!=version)
    problems+=[f'packaged but not in the repository: {extra[:5]}']*bool(extra)+[f'in the repository but not packaged: {missing[:5]}']*bool(missing)+[f'private files in ZIP: {leaked[:5]}']*bool(leaked)
    if problems:sys.exit('FAILED: '+'; '.join(problems))
    print('  manifest matches tracked files; no private files in the ZIP')

def main():
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('scan');v=sub.add_parser('verify');v.add_argument('--python',help='Python with backend test dependencies');sub.add_parser('package')
    args=p.parse_args();{'scan':scan,'verify':verify,'package':package}[args.command](args)

if __name__=='__main__':main()
