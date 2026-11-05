"""your Ubuntu computer launcher. Controls the dedicated local app, database, GPU Ollama and search services."""
import argparse
from foxory_compose import compose as compose_command
import json
import shutil
import secrets
import os
import subprocess
import urllib.request
from pathlib import Path
from setup import initialize

ROOT = Path(__file__).resolve().parents[1]


def compose(action):
    commands = {'start': ['up', '-d', '--build'], 'stop': ['stop'], 'status': ['ps']}
    if action == 'start':
        running = subprocess.run(['docker', 'ps', '-a', '--filter', 'label=com.docker.compose.project=foxory-local', '--format', '{{.Label "com.docker.compose.project.working_dir"}}'], capture_output=True, text=True)
        if running.returncode:
            print('Docker is unavailable. Start Docker before initializing FOXORY.')
            return 1
        locations = {Path(value).resolve() for value in getattr(running, 'stdout', '').splitlines() if value.strip()}
        other = sorted(str(value) for value in locations if value != ROOT.resolve())
        if other:
            print('FOXORY is already installed in: ' + other[0])
            print('Use that installation and its private .env. No settings or containers were changed.')
            return 1
        if not (ROOT / '.env').exists():
            volume = subprocess.run(['docker', 'volume', 'inspect', 'foxory-local_postgres_data'], capture_output=True)
            if volume.returncode == 0:
                print('Existing FOXORY database found. Restore its matching .env before starting; new credentials cannot unlock it.')
                return 1
        initialize(ROOT)
        settings = ROOT / 'deployment/searxng-local.yml'
        settings.parent.mkdir(parents=True, exist_ok=True)
        if not settings.exists():
            fd = os.open(settings, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w') as stream:
                stream.write('use_default_settings: true\nsearch:\n  formats: [html, json]\nserver:\n  secret_key: ' + secrets.token_hex(32) + '\n  limiter: false\n  image_proxy: false\n')
    return subprocess.run([*compose_command(), *commands[action]], cwd=ROOT).returncode


def doctor():
    ok = True
    if not shutil.which('docker'):
        print('MISSING: Docker Engine + Compose v2.'); ok = False
    else:
        for args in (['docker', 'compose', 'version'], ['docker', 'info', '--format', '{{.ServerVersion}}']):
            if subprocess.run(args, capture_output=True).returncode:
                print('CHECK: Docker Compose or daemon is unavailable.'); ok = False
    # Read only this endpoint setting, without executing or printing the .env.
    endpoint = 'http://127.0.0.1:11434'
    path = ROOT / '.env'
    if path.exists():
        for line in path.read_text().splitlines():
            key, sep, value = line.partition('=')
            if sep and key.strip() == 'FOXORY_HOST_OLLAMA_URL':
                endpoint = value.strip().strip('\"\'') or endpoint
    try:
        with urllib.request.urlopen(endpoint.rstrip('/') + '/api/tags', timeout=5) as response:
            models = json.load(response).get('models', [])
        print(f'Ollama reachable: {len(models)} installed model(s). Select a chat-capable model in Settings.')
    except Exception as error:
        print(f'CHECK: Ollama is unreachable ({type(error).__name__}). Start your local Ollama service.'); ok = False
    try:
        with urllib.request.urlopen('http://127.0.0.1:8889/', timeout=5) as response:
            print('Local research search: reachable.' if response.status == 200 else 'CHECK: local research search.')
    except Exception:
        print('CHECK: local search is unavailable. Start FOXORY to launch it.'); ok = False
    print('your computer uses localhost:3636 and a loopback database port (default 55432).')
    print('No models, services, or settings were changed by this check.')
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['doctor', 'start', 'stop', 'status','automate','evolve'])
    action = parser.parse_args().action
    try:
        if action in {'automate','evolve'}:
            locations=subprocess.check_output(['docker','ps','-a','--filter','label=com.docker.compose.project=foxory-local','--format','{{.Label "com.docker.compose.project.working_dir"}}'],text=True).splitlines()
            if any(Path(value).resolve()!=ROOT for value in locations if value):
                print('Use the active FOXORY installation folder for automation. No containers or settings were changed.');return 1
            result=subprocess.run([*compose_command(),'up','-d','--no-build','--wait','--wait-timeout','120','app'],cwd=ROOT)
            if result.returncode:return result.returncode
            subprocess.run([__import__('sys').executable,str(ROOT/'scripts/foxory_control.py'),'install'],cwd=ROOT,check=True)
            from foxory_updates import initialize,publish,write
            cfg=initialize()
            if not (ROOT/'release-channel/channel.json').exists():
                version=(ROOT/'VERSION').read_text().strip()
                if (ROOT/'releases'/('FOXORY-Local-v'+version+'.zip')).exists():publish(version)
            cfg['enabled']=True;write(ROOT/'update-policy.json',cfg)
            subprocess.run([__import__('sys').executable,str(ROOT/'scripts/foxory_control.py'),'updates_on'],cwd=ROOT,check=True)
            return subprocess.run([*compose_command(),'exec','-T','app','python','-m','foxory.evolution' if action=='evolve' else 'foxory.autonomy','start'],cwd=ROOT).returncode
        return doctor() if action == 'doctor' else compose(action)
    except OSError as error:
        print(f'Unable to launch Docker: {error}. Install/start Docker Engine and Compose v2.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
