"""Static local-image SBOM/license inventory and HIGH/CRITICAL vulnerability gate.

Explicitly downloads pinned Apache-2.0 Syft/Trivy verification tools, never model
weights or paid services. No worker is executed and no image is published. Run on
Linux AMD64 with sufficient disk; immutable local image ID required. A scanner
pass is not full license clearance or proof of sandbox/compiled-browser safety.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile

import httpx

ROOT=Path(__file__).resolve().parents[1]
FIXES=ROOT/'deployment/required-security-fixes.json'
WORKER_PACKAGES=ROOT/'sandbox_manager/runtime/worker-packages.json'


def pcre2_version(components: list[dict]) -> dict:
    policy=json.loads((ROOT/'sandbox_manager/runtime/pcre2/source.json').read_text())
    versions={c.get('version') for c in components if c.get('name')=='libpcre2-8-0'
              and str(c.get('purl','')).startswith('pkg:deb/ubuntu/')}
    return {'status':'passed' if versions=={policy['package_version']} else 'blocked',
            'expected':policy['package_version'],'observed':sorted(versions,key=str),
            'source_sha256':policy['archive_sha256'],
            'scope':'Actual upstream source rebuild; raw distribution scanner entries remain unchanged.'}


def worker_packages(components: list[dict]) -> dict:
    raw=WORKER_PACKAGES.read_bytes();policy=json.loads(raw)
    required=policy.get('required_packages');forbidden=policy.get('forbidden_packages')
    if (policy.get('schema_version')!=1 or not isinstance(required,list) or not required
            or not isinstance(forbidden,list) or not forbidden
            or any(not isinstance(name,str) or not re.fullmatch(r'[a-z0-9][a-z0-9+.-]*',name) for name in required+forbidden)
            or len(set(required))!=len(required) or len(set(forbidden))!=len(forbidden)
            or set(required)&set(forbidden)):
        raise ValueError('Invalid worker package policy')
    debs=[c for c in components if str(c.get('purl','')).startswith('pkg:deb/ubuntu/')]
    installed={c.get('name') for c in debs}
    versions=policy.get('required_versions')
    if (not isinstance(versions,dict) or not versions or any(
            not isinstance(name,str) or not re.fullmatch(r'[a-z0-9][a-z0-9+.-]*',name)
            or not isinstance(version,str) or not re.fullmatch(r'[0-9][A-Za-z0-9.:+~_-]{0,99}',version)
            for name,version in versions.items())):
        raise ValueError('Invalid worker version policy')
    mismatches=[name for name,version in versions.items()
                if {c.get('version') for c in debs if c.get('name')==name}!={version}]
    missing=sorted(set(required)-installed);present=sorted(set(forbidden)&installed)
    return {'status':'passed' if not missing and not present and not mismatches else 'blocked',
            'sha256':hashlib.sha256(raw).hexdigest(),'required_missing':missing,
            'version_mismatches':mismatches,'required_versions':versions,
            'forbidden_present':present,'required_count':len(required),'forbidden_count':len(forbidden),
            'scope':'Merged runtime filesystem only; lower-layer binary licensing obligations are not removed.'}


def required_security_fixes() -> tuple[str, list[dict]]:
    raw=FIXES.read_bytes();policy=json.loads(raw)
    rules=policy.get('required_remediations')
    if policy.get('schema_version')!=1 or not isinstance(rules,list) or not rules:
        raise ValueError('Missing required security-remediation policy')
    pairs=set()
    for rule in rules:
        if (not isinstance(rule,dict) or not isinstance(rule.get('id'),str)
                or not re.fullmatch(r'CVE-[0-9]{4}-[0-9]{4,}',rule['id'])
                or not isinstance(rule.get('package'),str)
                or not re.fullmatch(r'[a-z0-9][a-z0-9+.-]*',rule['package'])
                or (rule['id'],rule['package']) in pairs):
            raise ValueError('Invalid or duplicate required remediation')
        pairs.add((rule['id'],rule['package']))
    return hashlib.sha256(raw).hexdigest(),rules


def archive_identity(source, image: str) -> dict:
    """Check one Docker archive's config digest without extracting any layer.

    The export must be operator-owned, stationary and trusted for scanner input;
    this is not an upload/parser service. Do not extract arbitrary image archives.
    """
    source.seek(0)
    digest=hashlib.sha256()
    while chunk:=source.read(1024*1024):digest.update(chunk)
    source.seek(0)
    with tarfile.open(fileobj=source,mode='r:') as archive:
        names=set();members={}
        for member in archive:
            if member.name in names or len(names)>=50000:raise ValueError('Ambiguous/oversized image archive')
            names.add(member.name);members[member.name]=member
        def read(name):
            if name.startswith('/') or '..' in Path(name).parts:raise ValueError('Unsafe archive metadata path')
            member=members.get(name)
            if member is None or not member.isfile() or member.size>1000000:raise ValueError('Invalid archive metadata')
            stream=archive.extractfile(member)
            if stream is None:raise ValueError('Missing archive metadata')
            with stream:return stream.read(1000001)
        manifest=json.loads(read('manifest.json'))
        if not isinstance(manifest,list) or len(manifest)!=1:raise ValueError('Exactly one exported image required')
        config=read(manifest[0]['Config'])
        if 'sha256:'+hashlib.sha256(config).hexdigest()!=image:raise ValueError('Exported image config does not match immutable image ID')
        metadata=json.loads(config)
        layers=manifest[0].get('Layers')
        rootfs=metadata.get('rootfs',{})
        diff_ids=rootfs.get('diff_ids')
        if (rootfs.get('type')!='layers' or not isinstance(layers,list) or not isinstance(diff_ids,list)
                or len(layers)!=len(diff_ids) or len(layers)>200):raise ValueError('Invalid exported layer graph')
        for name,expected in zip(layers,diff_ids,strict=True):
            if not isinstance(name,str) or name.startswith('/') or '..' in Path(name).parts:
                raise ValueError('Unsafe layer path')
            member=members.get(name)
            if member is None or not member.isfile() or member.size>8*1024**3:raise ValueError('Invalid exported layer')
            stream=archive.extractfile(member)
            if stream is None:raise ValueError('Missing exported layer')
            layer_digest=hashlib.sha256()
            with stream:
                while chunk:=stream.read(1024*1024):layer_digest.update(chunk)
            if 'sha256:'+layer_digest.hexdigest()!=expected:raise ValueError('Exported layer digest mismatch')
    source.seek(0)
    return {'sha256':digest.hexdigest(),'bytes':os.fstat(source.fileno()).st_size,'config_digest':image}


def extract_binary(archive: Path, name: str, destination: Path) -> None:
    with tarfile.open(archive,'r:gz') as source:
        member=source.getmember(name)
        if not member.isfile() or member.size>250_000_000 or member.linkname:
            raise ValueError('Invalid verification-tool binary')
        content=source.extractfile(member)
        if content is None:raise ValueError('Missing verification-tool binary')
        with content,destination.open('xb') as output:shutil.copyfileobj(content,output,1024*1024)
    destination.chmod(0o700)


def findings(report: dict) -> dict:
    policy_hash,rules=required_security_fixes()
    required={(r['id'],r['package']) for r in rules}
    entries=[v for result in report.get('Results',[]) for v in (result.get('Vulnerabilities') or [])]
    blocking=[{'id':v.get('VulnerabilityID'),'package':v.get('PkgName'),
               'installed':v.get('InstalledVersion'),'fixed':v.get('FixedVersion'),
               'severity':v.get('Severity'),
               'gate_reason':'required_remediation' if (v.get('VulnerabilityID'),v.get('PkgName')) in required else 'severity'}
              for v in entries if v.get('Severity') in {'HIGH','CRITICAL'}
              or (v.get('VulnerabilityID'),v.get('PkgName')) in required]
    os_info=report.get('Metadata',{}).get('OS',{})
    # Refuse an empty/unsupported scanner envelope instead of reporting zero CVEs.
    complete=bool(report.get('SchemaVersion') and os_info.get('Family') and report.get('Results'))
    return {'status':'passed' if complete and not blocking and not os_info.get('EOSL') else 'blocked',
            'coverage_reported':complete,'os':os_info,'blocking':blocking,
            'required_security_fixes_sha256':policy_hash,'required_remediations':rules,
            'total_findings':len(entries),'unfixed_findings_ignored':False,
            'limits':'Scanner feed coverage only; compiled browsers, sandbox isolation and license compatibility need separate review.'}


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image',required=True)
    parser.add_argument('--archive',type=Path,help='Stationary rootless Podman docker-archive export; no Docker daemon needed')
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--worker',action='store_true',help='Enforce the reviewed Chromium worker package policy')
    parser.add_argument('--pcre2',action='store_true',help='Require the reviewed PCRE2 build in an application/model image')
    args=parser.parse_args()
    if not re.fullmatch('sha256:[a-f0-9]{64}',args.image):raise ValueError('Immutable local image ID required')
    if platform.system()!='Linux' or platform.machine() not in {'x86_64','amd64'}:
        raise ValueError('Pinned verification tools currently support Linux AMD64 only')
    args.output.mkdir(parents=True,exist_ok=False,mode=0o700)
    tools=json.loads((ROOT/'deployment/security-tools.json').read_text())
    env=dict(os.environ)
    for key in ['DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH']:env.pop(key,None)
    env['DOCKER_HOST']='unix:///var/run/docker.sock'
    summary={'status':'failed','image':args.image,'tools':tools}
    exported=None
    try:
        if args.archive:
            fd=os.open(args.archive,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
            exported=os.fdopen(fd,'rb')
            info=os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_size>8*1024**3
                    or info.st_uid!=os.getuid() or info.st_mode&0o022):
                raise ValueError('Operator-owned, non-writable-by-others regular export within 8-GiB budget required')
            summary['archive']=archive_identity(exported,args.image)
            # Stable inherited descriptor, not a pathname that can be swapped.
            source='docker-archive:/proc/self/fd/'+str(fd)
            trivy_source=['--input','/proc/self/fd/'+str(fd)]
            inherited=(fd,)
        else:
            source='docker:'+args.image;trivy_source=['--image-src','docker',args.image];inherited=()
        with tempfile.TemporaryDirectory(prefix='foxory-image-tools-') as directory:
            private=Path(directory)
            for name in ['syft','trivy']:
                pin=tools[name];archive=private/(name+'.tar.gz');digest=hashlib.sha256();size=0
                with httpx.Client(timeout=60,follow_redirects=True,trust_env=True) as client:
                    with client.stream('GET',pin['url']) as response:
                        response.raise_for_status()
                        with archive.open('xb') as output:
                            for chunk in response.iter_bytes(1024*1024):
                                size+=len(chunk)
                                if size>100_000_000:raise ValueError('Verification tool download budget')
                                digest.update(chunk);output.write(chunk)
                if digest.hexdigest()!=pin['sha256']:raise ValueError('Verification tool checksum mismatch')
                extract_binary(archive,name,private/name)
            subprocess.run([str(private/'syft'),source,'--quiet','-o',
                            'cyclonedx-json='+str(args.output/'sbom.cdx.json')],env=env,check=True,timeout=600,pass_fds=inherited)
            subprocess.run([str(private/'trivy'),'image',*trivy_source,'--scanners','vuln',
                            '--format','json','--output',str(args.output/'vulnerabilities.json')],
                           env=env,check=True,timeout=600,pass_fds=inherited)
        if exported and archive_identity(exported,args.image)!=summary['archive']:
            raise ValueError('Image export changed during audit')
        summary.update(findings(json.loads((args.output/'vulnerabilities.json').read_text())))
        components=json.loads((args.output/'sbom.cdx.json').read_text()).get('components',[])
        licenses=[{'name':c.get('name'),'version':c.get('version'),'licenses':c.get('licenses',[])} for c in components]
        (args.output/'license-inventory.json').write_text(json.dumps({'review_status':'pending human compatibility/attribution review',
                                                                  'components':licenses},indent=2)+'\n')
        summary['sbom_components']=len(components)
        if not components:summary['status']='blocked'
        if args.worker:
            summary['worker_package_policy']=worker_packages(components)
            if summary['worker_package_policy']['status']!='passed':summary['status']='blocked'
        if args.worker or args.pcre2:
            summary['pcre2_version']=pcre2_version(components)
            if summary['pcre2_version']['status']!='passed':summary['status']='blocked'
    finally:
        if exported:exported.close()
        (args.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
    return 0 if summary['status']=='passed' else 1


if __name__=='__main__':raise SystemExit(main())
