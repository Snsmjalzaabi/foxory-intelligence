"""Personal profile checks: safe routing, preserved settings, explicit grants."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import yaml
from foxory.agents import templates, AgentConfig

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('foxory_launcher', ROOT / 'scripts/foxory.py')
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


def test_host_profile_keeps_host_services_on_loopback():
    data = yaml.safe_load((ROOT / 'compose.local.yaml').read_text())
    assert set(data['services']) == {'app', 'db', 'ollama', 'search', 'llama', 'whisper'}
    voice=data['services']['whisper']
    assert voice['ports']==['127.0.0.1:11437:8080'] and voice['read_only'] and voice['profiles']==['voice']
    assert voice['cap_drop']==['ALL'] and voice['security_opt']==['no-new-privileges:true'] and 'gpus' not in voice
    assert '--convert' not in voice['command'] and voice['command'][voice['command'].index('--language')+1]=='auto'
    lite=data['services']['llama']
    assert lite['ports']==['127.0.0.1:11436:8080'] and lite['read_only'] and lite['profiles']==['lite']
    assert 'gpus' not in lite and lite['cpus']==2
    assert lite['tmpfs']==['/tmp:size=64m,mode=1777']
    assert lite['build']['args']['FOXORY_APP_IMAGE'].startswith('${FOXORY_AI_APP_IMAGE:')
    app = data['services']['app']
    assert app['network_mode'] == 'host'
    assert '--host 127.0.0.1' in app['command'][-1]
    assert app['environment']['OLLAMA_URL'].endswith('http://127.0.0.1:11434}')
    assert data['services']['db']['ports'][0].startswith('127.0.0.1:')
    assert app['environment']['FOXORY_ENABLE_SANDBOX'].endswith(':-0}')


def test_launcher_preserves_private_env_and_uses_only_personal_profile(tmp_path, monkeypatch):
    monkeypatch.setattr(launcher, 'ROOT', tmp_path)
    calls = []
    class Result:
        returncode = 0
    def fake_run(args, **kwargs):
        calls.append(args)
        result = Result()
        result.stdout = ''
        if args[:3] == ['docker', 'volume', 'inspect']: result.returncode = 1
        return result
    monkeypatch.setattr(launcher.subprocess, 'run', fake_run)
    assert launcher.compose('start') == 0
    env = tmp_path / '.env'
    original = env.read_text()
    assert os.stat(env).st_mode & 0o777 == 0o600
    assert launcher.compose('start') == 0
    assert env.read_text() == original
    launcher.compose('stop')
    assert all(c[:4] == ['docker', 'compose', '-f', 'compose.local.yaml'] for c in calls if c[:2] == ['docker', 'compose'])
    assert calls[-1][-1] == 'stop'
    assert all('-v' not in c for c in calls)


def test_personal_templates_keep_valid_explicit_grants():
    rows = templates()
    personal = [r for r in rows if r['name'].startswith('FOXORY ')]
    assert len(personal) == 5
    assert any(r['name'] == 'General Coordinator' for r in rows)
    for row in personal:
        config = AgentConfig.model_validate(row['config'])
        assert not config.model
        assert not config.document_ids
        assert all(t not in config.tools for t in ['project.create', 'task.create'])


def test_second_extraction_cannot_replace_existing_installation(tmp_path, monkeypatch):
    monkeypatch.setattr(launcher, 'ROOT', tmp_path)
    class Existing:
        returncode = 0
        stdout = '/another/foxory-installation\n'
    monkeypatch.setattr(launcher.subprocess, 'run', lambda *args, **kwargs: Existing())
    assert launcher.compose('start') == 1
    assert not (tmp_path / '.env').exists()


def test_installer_env_update_merges_profiles_and_keeps_settings(tmp_path, monkeypatch):
    import foxory_ai
    monkeypatch.setattr(foxory_ai, 'ROOT', tmp_path)
    env = tmp_path / '.env'
    env.write_text('FOXORY_TOKEN=keep-me\nCOMPOSE_PROFILES=lite\nFOXORY_WHISPER_URL=old\n')
    foxory_ai.update_env({'FOXORY_WHISPER_URL': 'http://127.0.0.1:11437'}, 'voice')
    foxory_ai.update_env({}, 'voice')
    lines = env.read_text().splitlines()
    assert 'FOXORY_TOKEN=keep-me' in lines and 'COMPOSE_PROFILES=lite,voice' in lines
    assert 'FOXORY_WHISPER_URL=http://127.0.0.1:11437' in lines and len(lines) == 3
    assert oct(env.stat().st_mode & 0o777) == '0o600' and not list(tmp_path.glob('*.ai-tmp'))


def test_pinned_download_fetches_license_from_manifest_location(tmp_path, monkeypatch):
    import hashlib, io, foxory_ai
    monkeypatch.setattr(foxory_ai, 'ROOT', tmp_path)
    body = b'model-bytes'
    requested = []
    def urlopen(url, timeout=None):
        requested.append(url)
        return io.BytesIO(b'---\nlicense: mit\n---' if url.endswith('README.md') else body)
    monkeypatch.setattr(foxory_ai.urllib.request, 'urlopen', urlopen)
    m = {'repository': 'org/repo', 'revision': 'a' * 40, 'filename': 'ggml-x.bin', 'sha256': hashlib.sha256(body).hexdigest(), 'bytes': len(body), 'license': 'MIT', 'license_file': 'README.md'}
    target = foxory_ai.download_pinned(m)
    assert target.read_bytes() == body and requested[-1].endswith('/README.md')
    assert (tmp_path / '.local-ai/models/ggml-x.bin.LICENSE').read_bytes().startswith(b'---')


def test_phone_access_uses_only_its_own_tailscale_route(tmp_path, monkeypatch):
    import json, types, foxory_ai, foxory_phone
    monkeypatch.setattr(foxory_ai, 'ROOT', tmp_path); monkeypatch.setattr(foxory_phone, 'ROOT', tmp_path)
    (tmp_path / '.env').write_text('FOXORY_TOKEN=keep\nFOXORY_ALLOWED_HOSTS=localhost,127.0.0.1,[::1]\n')
    calls = []
    def run(cmd, **kw):
        calls.append(cmd)
        out = json.dumps({'BackendState': 'Running', 'Self': {'DNSName': 'mypc.tail1234.ts.net.'}}) if cmd[:2] == ['tailscale', 'status'] else ''
        return types.SimpleNamespace(stdout=out, returncode=0)
    monkeypatch.setattr(foxory_phone.subprocess, 'run', run); monkeypatch.setattr(foxory_phone.shutil, 'which', lambda name: '/usr/bin/' + name)
    foxory_phone.enable()
    env = (tmp_path / '.env').read_text().splitlines()
    assert ['tailscale', 'serve', '--bg', 'http://127.0.0.1:3636'] in calls
    assert 'FOXORY_ALLOWED_HOSTS=localhost,127.0.0.1,[::1],mypc.tail1234.ts.net' in env and 'FOXORY_PUBLIC_ORIGINS=https://mypc.tail1234.ts.net' in env
    assert 'FOXORY_TOKEN=keep' in env and not any(l.startswith('COMPOSE_PROFILES') for l in env)
    foxory_phone.enable()
    assert (tmp_path / '.env').read_text().count('mypc.tail1234.ts.net,') == 0
    foxory_phone.disable()
    env = (tmp_path / '.env').read_text().splitlines()
    assert ['tailscale', 'serve', '--https=443', 'off'] in calls and not any('reset' in c for c in calls)
    assert 'FOXORY_ALLOWED_HOSTS=localhost,127.0.0.1,[::1]' in env and 'FOXORY_PUBLIC_ORIGINS=' in env


def test_gpu_overlay_only_when_docker_can_use_nvidia(tmp_path, monkeypatch):
    import types, foxory_compose
    data = yaml.safe_load((ROOT / 'compose.local.yaml').read_text())
    assert 'gpus' not in data['services']['ollama']
    assert yaml.safe_load((ROOT / 'compose.local.gpu.yaml').read_text())['services']['ollama']['gpus'] == 'all'
    monkeypatch.setattr(foxory_compose, 'ROOT', tmp_path)
    def scenario(env, smi=True, runtimes='{"runc":{}}', cli=False):
        (tmp_path / '.env').write_text(env)
        monkeypatch.setattr(foxory_compose.shutil, 'which', lambda n: {'nvidia-smi': smi, 'nvidia-container-cli': cli}.get(n) and '/usr/bin/' + n)
        monkeypatch.setattr(foxory_compose.subprocess, 'run', lambda cmd, **kw: types.SimpleNamespace(returncode=0, stdout=runtimes))
        foxory_compose.gpu_enabled.cache_clear()
        return foxory_compose.compose()
    base = ['docker', 'compose', '-f', 'compose.local.yaml']
    assert scenario('') == base
    assert scenario('', smi=False) == base
    assert scenario('', runtimes='{"nvidia":{},"runc":{}}') == base + ['-f', 'compose.local.gpu.yaml']
    assert scenario('', cli=True) == base + ['-f', 'compose.local.gpu.yaml']
    assert scenario('FOXORY_GPU=off\n', runtimes='{"nvidia":{}}') == base
    assert scenario('FOXORY_GPU=on\n', smi=False) == base + ['-f', 'compose.local.gpu.yaml']
    foxory_compose.gpu_enabled.cache_clear()
