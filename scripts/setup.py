"""Generate local secrets; never overwrite an existing installation."""
from pathlib import Path
import secrets
import os
import subprocess

def initialize(root:Path)->bool:
    path=root/'.env'
    if path.exists():
        print('.env already exists; preserved. Read docs/DATABASE_UPGRADE.md before selecting a database layout or rebuilding.')
        return False
    fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,'w') as f:
        f.write(f'FOXORY_TOKEN={secrets.token_urlsafe(36)}\nPOSTGRES_PASSWORD={secrets.token_hex(24)}\nFOXORY_PORT=8000\nSEARXNG_URL=\nFOXORY_DATABASE_LAYOUT=modern\n')
    print('Created private .env with random secrets and the new-install modern database layout.')
    return True


def main():
    root=Path(__file__).resolve().parents[1]
    fresh=initialize(root)
    if fresh:print('Next: docker compose up -d --build')
    else:print('Existing data is not converted. Select the documented legacy maintenance or new-volume migration path first.')
    print('Open http://localhost:8000 and enter FOXORY_TOKEN from your private .env.')
    print('In Settings, explicitly download a model after reviewing its license.')
    try:subprocess.run(['docker','compose','version'],check=True,cwd=root)
    except (OSError,subprocess.CalledProcessError):print('Docker Compose is not available. Install Docker Engine + Compose v2 first.')


if __name__=='__main__':main()
