"""Take a coordinated private PostgreSQL/uploads/settings backup for your computer."""
import datetime
from foxory_compose import compose
import json
import hashlib
from backup_checks import COUNTS_SQL
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = compose()


def run(args, **kwargs):
    return subprocess.run(args, cwd=ROOT, check=True, **kwargs)


def main():
    locations=subprocess.check_output(['docker','ps','-a','--filter','label=com.docker.compose.project=foxory-local','--format','{{.Label "com.docker.compose.project.working_dir"}}'],text=True).splitlines()
    if any(Path(value).resolve()!=ROOT for value in locations if value):raise SystemExit('Use the active installation folder for backups; another extracted copy has different private settings.')
    os.umask(0o077)
    destination = ROOT/'backups'/datetime.datetime.now(datetime.timezone.utc).strftime('foxory-%Y%m%dT%H%M%SZ')
    destination.mkdir(parents=True, mode=0o700)
    # Prevent app writes until the database and upload snapshots are complete.
    run(COMPOSE+['stop','app'])
    try:
        counts=json.loads(subprocess.check_output(COMPOSE+['exec','-T','db','psql','-U','foxory','-d','foxory','-At','-c',COUNTS_SQL],cwd=ROOT,text=True))
        (destination/'counts.json').write_text(json.dumps(counts,indent=2)+'\n')
        with (destination/'database.dump').open('wb') as stream:
            run(COMPOSE+['exec','-T','db','pg_dump','-U','foxory','-d','foxory','-Fc'],stdout=stream)
        app_id = subprocess.check_output(COMPOSE+['ps','-a','-q','app'],cwd=ROOT,text=True).strip()
        with (destination/'app-data.tar').open('wb') as stream:
            run(['docker','run','--rm','--volumes-from',app_id+':ro','alpine:latest','tar','--exclude=./maintenance','-C','/data','-cf','-','.'],stdout=stream)
        shutil.copy2(ROOT/'.env', destination/'.env')
        (destination/'.env').chmod(0o600)
        shutil.copy2(ROOT/'compose.local.yaml',destination/'compose.local.yaml')
        shutil.copy2(ROOT/'compose.local.gpu.yaml',destination/'compose.local.gpu.yaml')
        if (ROOT/'deployment/searxng-local.yml').exists():
            shutil.copy2(ROOT/'deployment/searxng-local.yml',destination/'searxng-local.yml')
        for source,name in [(ROOT/'update-policy.json','update-policy.json'),(ROOT/'update-trust/signing-key.pem','release-signing-key.pem'),(ROOT/'update-trust/release.pub','trusted-release.pub')]:
            if source.is_file():shutil.copy2(source,destination/name);(destination/name).chmod(0o600)
        with (destination/'database-contents.txt').open('wb') as stream:
            run(COMPOSE+['exec','-T','db','pg_restore','--list'],input=(destination/'database.dump').read_bytes(),stdout=stream)
        (destination/'README.txt').write_text('Private backup: database, app uploads and .env contain sensitive data. Model weights stay in the Ollama volume and the host .local-ai/models folder; pinned CPU weights can be downloaded and hash-verified again with scripts/foxory_ai.py. To recover, restore this dump to a separate empty database with pg_restore, restore app-data.tar to its separate app volume, and use the matching private environment and Compose file. Verify before switching installations. Do not overwrite the only copy.\n')
        checksums={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir() if p.is_file()}
        (destination/'checksums.json').write_text(json.dumps(checksums,indent=2)+'\n')
        print('Backup completed:',destination)
    finally:
        run(COMPOSE+['up','-d','--wait','--wait-timeout','120','app'])


if __name__=='__main__':
    main()
