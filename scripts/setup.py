"""Generate local secrets; never overwrite an existing installation."""
from pathlib import Path
import secrets
import os
import subprocess

root = Path(__file__).resolve().parents[1]
path = root / '.env'
if path.exists():
    print('.env already exists; preserved. Rotate tokens manually if needed.')
else:
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd,'w') as f:
        f.write(f'FOXORY_TOKEN={secrets.token_urlsafe(36)}\nPOSTGRES_PASSWORD={secrets.token_hex(24)}\nFOXORY_PORT=8000\nSEARXNG_URL=\n')
    print('Created .env with random secrets. Keep this file private.')
print('Next: docker compose up -d --build')
print('Open http://localhost:8000 and enter FOXORY_TOKEN from .env.')
print('In Settings, explicitly download a model after reviewing its license.')
try:
    subprocess.run(['docker','compose','version'],check=True,cwd=root)
except (OSError,subprocess.CalledProcessError):
    print('Docker Compose is not available. Install Docker Engine + Compose v2 first.')
