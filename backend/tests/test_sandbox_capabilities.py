from pathlib import Path
from unittest.mock import patch
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sandbox_manager.capabilities import inspect_host


def fixture(tmp_path: Path, *, controllers: str = 'cpu memory pids'):
    root = tmp_path / 'cgroup'
    scope = root / 'user.slice' / 'manager.scope'
    scope.mkdir(parents=True)
    (scope / 'cgroup.controllers').write_text(controllers)
    (scope / 'cgroup.subtree_control').write_text('')
    membership = tmp_path / 'membership'
    membership.write_text('0::/user.slice/manager.scope\n')
    return root, membership


def test_static_success_never_enables_execution(tmp_path):
    root, membership = fixture(tmp_path)
    with patch('sandbox_manager.capabilities.os.getuid', return_value=1000), patch(
        'sandbox_manager.capabilities.shutil.which', return_value='/usr/bin/tool'
    ), patch('sandbox_manager.capabilities.platform.system', return_value='Linux'):
        result = inspect_host(cgroup_root=root, membership=membership)
    assert result['static_requirements_met']
    assert not result['execution_enabled']
    assert not result['runtime_isolation_verified']
    assert result['pending_checks']


def test_missing_memory_controller_fails_closed(tmp_path):
    root, membership = fixture(tmp_path, controllers='cpu pids')
    result = inspect_host(cgroup_root=root, membership=membership)
    assert not result['static_requirements_met']
    assert any('memory' in reason for reason in result['blockers'])


def test_membership_traversal_rejected(tmp_path):
    root, membership = fixture(tmp_path)
    membership.write_text('0::/../../etc\n')
    result = inspect_host(cgroup_root=root, membership=membership)
    assert not result['static_requirements_met']
    assert any('invalid cgroup membership' in reason for reason in result['blockers'])


def test_symlink_escape_rejected(tmp_path):
    root, membership = fixture(tmp_path)
    (root / 'escape').symlink_to(tmp_path)
    membership.write_text('0::/escape\n')
    result = inspect_host(cgroup_root=root, membership=membership)
    assert any('escaped mount' in reason for reason in result['blockers'])


def test_readonly_delegation_fails_closed(tmp_path):
    root, membership = fixture(tmp_path)
    with patch('sandbox_manager.capabilities.os.access', return_value=False):
        result = inspect_host(cgroup_root=root, membership=membership)
    assert any('not writable' in reason for reason in result['blockers'])
    assert any('cannot create' in reason for reason in result['blockers'])


def test_root_and_missing_runtime_rejected(tmp_path):
    root, membership = fixture(tmp_path)
    with patch('sandbox_manager.capabilities.os.getuid', return_value=0), patch(
        'sandbox_manager.capabilities.shutil.which', return_value=None
    ):
        result = inspect_host(cgroup_root=root, membership=membership)
    assert not result['static_requirements_met']
    assert any('non-root' in reason for reason in result['blockers'])
    assert any('podman' in reason for reason in result['blockers'])


@pytest.mark.parametrize('profile', ['javascript', 'typescript', 'browser'])
def test_fixed_oci_policy_and_immutable_image(tmp_path, profile):
    from sandbox_manager.oci import command
    source = tmp_path / 'source'
    source.mkdir()
    request = tmp_path / 'request.json'
    request.write_text('{}')
    args = command(image='sha256:' + 'a'*64, task_id='b'*64, source=source, request=request, profile=profile)
    for flag in ['--network=none', '--read-only', '--cap-drop=ALL', '--memory=1073741824',
                 '--pids-limit=128', '--pull=never', '--http-proxy=false', '--user=1000:1000']:
        assert flag in args
    assert not any('docker.sock' in arg or arg == '--privileged' for arg in args)
    assert [arg for arg in args if arg.startswith('--cap-add=')] == (
        ['--cap-add=SYS_CHROOT'] if profile == 'browser' else [])
    assert [arg for arg in args if arg.startswith('--security-opt=')] == ['--security-opt=no-new-privileges']
    assert '--no-sandbox' not in args
    with pytest.raises(ValueError):
        command(image='node:latest', task_id='b'*64, source=source, request=request, profile=profile)


def test_browser_exception_preserves_every_other_oci_restriction(tmp_path):
    from sandbox_manager.oci import command
    source = tmp_path / 'source'; source.mkdir()
    request = tmp_path / 'request.json'; request.write_text('{}')
    common = dict(image='sha256:'+'a'*64, task_id='b'*64, source=source,
                  request=request, owner='c'*32)
    javascript = command(**common, profile='javascript')
    assert command(**common, profile='typescript') == javascript
    browser = command(**common, profile='browser')
    assert [arg for arg in browser if arg != '--cap-add=SYS_CHROOT'] == javascript
    for flag in ['--ipc=private', '--pid=private', '--uts=private', '--cgroupns=private',
                 '--userns=keep-id:uid=1000,gid=1000', '--memory-swap=1073741824',
                 '--cpus=1', '--timeout=45', '--ulimit=nofile=256:256', '--ulimit=core=0:0',
                 '--tmpfs=/out:rw,noexec,nosuid,nodev,size=16777216,mode=1777']:
        assert flag in browser
    # Request bytes cannot opt a code profile into the browser capability.
    request.write_text('{"profile":"browser","cap_add":["ALL"]}')
    assert command(**common, profile='javascript') == javascript
    for profile in ['python', 'browser --cap-add=ALL', '', None]:
        with pytest.raises(ValueError, match='Unsupported OCI profile'):
            command(**common, profile=profile)
    with pytest.raises(TypeError):
        command(**common)  # Callers must supply the validated dispatch profile.


def test_oci_rejects_malicious_inputs():
    import pytest
    from pydantic import ValidationError
    from sandbox_manager.oci import OCIProject, BrowserAction
    for target in ['https://example.com', '//example.com', '/%2e%2e/secret', '/a/../secret', '/a\\b']:
        with pytest.raises(ValidationError):
            BrowserAction(action='navigate', target=target)
    for name in ['../host.js', '/etc/host.js', '.env', 'a\\b.js']:
        with pytest.raises(ValidationError):
            OCIProject(profile='javascript', files={name:'0'}, entrypoint=name)
    with pytest.raises(ValidationError):
        OCIProject(profile='javascript', files={'main.py':'0'}, entrypoint='main.py')
    with pytest.raises(ValidationError):
        OCIProject(profile='browser', files={'index.html':'hi'}, actions=[])
    assert OCIProject(profile='typescript', files={'test.ts':'const x:number=1;'}, entrypoint='test.ts')


def test_ubuntu_active_probe_never_runs_on_blocked_host(monkeypatch, capsys):
    from scripts import verify_oci_runtime as verifier
    from unittest.mock import Mock
    monkeypatch.setattr(verifier, 'inspect_host', lambda: {'static_requirements_met':False, 'blockers':['no delegation']})
    monkeypatch.setattr(sys, 'argv', ['verify_oci_runtime.py','--image','sha256:'+'a'*64])
    run = Mock(side_effect=AssertionError('Must not launch a runtime on an unsafe host'))
    monkeypatch.setattr(verifier.subprocess, 'run', run)
    assert verifier.main() == 2
    assert 'blocked' in capsys.readouterr().out
    run.assert_not_called()


def test_fixed_probe_commands_preserve_profile_capability_boundaries(monkeypatch):
    """Mock only OCI process execution; exercise the actual probe command builder."""
    import json
    from types import SimpleNamespace
    from scripts import verify_oci_runtime as verifier

    commands = []
    class Process:
        returncode = 0
        def wait(self, **kwargs): return 0
        def poll(self): return 0
    def popen(args, **kwargs):
        commands.append(args)
        kwargs['stdout'].write(json.dumps({'event':'result', 'exit_code':0,
                                          'stdout':'fixture', 'artifacts':{}}).encode()+b'\n')
        return Process()
    monkeypatch.setattr(verifier.subprocess, 'Popen', popen)
    monkeypatch.setattr(verifier.subprocess, 'run', lambda args, **kwargs:
                        SimpleNamespace(returncode=1 if 'exists' in args else 0))
    projects = [verifier.OCIProject(profile=profile, files={name:verifier.PROBE}, entrypoint=name)
                for profile, name in [('javascript','probe.js'), ('typescript','probe.ts')]]
    projects.append(verifier.OCIProject(profile='browser', files={'index.html':verifier.SITE},
                                       actions=[{'action':'navigate','target':'/'}]))
    for project in projects:
        assert verifier.run_probe('sha256:'+'a'*64, project)['exit_code'] == 0
        additions = [arg for arg in commands[-1] if arg.startswith('--cap-add=')]
        assert additions == (['--cap-add=SYS_CHROOT'] if project.profile == 'browser' else [])
        assert '--security-opt=no-new-privileges' in commands[-1]


@pytest.mark.parametrize('browser_failure', [False, True])
def test_probe_reports_partial_success_without_activating_application(monkeypatch, capsys, browser_failure):
    import json
    from types import SimpleNamespace
    from scripts import verify_oci_runtime as verifier
    from scripts.oci_fixture import artifact, png

    projects = []
    def run_probe(image, project, owner):
        projects.append(project)
        if project.profile == 'browser':
            if browser_failure:
                raise RuntimeError('Fixture browser launch failure')
            return {'stdout':'FOXORY_BROWSER_OK', 'artifacts':{
                'screenshot-1.png':artifact(png()), 'result.txt':artifact(b'Controlled fixture download')}}
        assert project.files[project.entrypoint].startswith(verifier.PROBE)
        return {'stdout':'FOXORY_OCI_CONTROLS_OK'}
    monkeypatch.setattr(verifier, 'inspect_host', lambda: {'static_requirements_met':True})
    monkeypatch.setattr(verifier.subprocess, 'run', lambda *args, **kwargs: SimpleNamespace(stdout='true'))
    monkeypatch.setattr(verifier, 'run_probe', run_probe)
    monkeypatch.setattr(sys, 'argv', ['verify_oci_runtime.py','--image','sha256:'+'a'*64])
    if browser_failure:
        with pytest.raises(RuntimeError, match='Fixture browser launch failure'):
            verifier.main()
    else:
        assert verifier.main() == 0
    captured = capsys.readouterr()
    if browser_failure:
        assert captured.out == ''  # A failed browser cannot report overall success.
    else:
        report = json.loads(captured.out)
        assert report['application_execution_enabled'] is False
    assert [project.profile for project in projects] == ['javascript','typescript','browser']
    passed = projects[:2] if browser_failure else projects
    assert captured.err.splitlines() == ['FOXORY_PROBE_PASSED '+project.profile for project in passed]
