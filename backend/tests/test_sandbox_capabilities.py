from pathlib import Path
from unittest.mock import patch
import sys
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


def test_fixed_oci_policy_and_immutable_image(tmp_path):
    from sandbox_manager.oci import command
    source = tmp_path / 'source'
    source.mkdir()
    request = tmp_path / 'request.json'
    request.write_text('{}')
    args = command(image='sha256:' + 'a'*64, task_id='b'*64, source=source, request=request)
    for flag in ['--network=none', '--read-only', '--cap-drop=ALL', '--memory=1073741824',
                 '--pids-limit=128', '--pull=never', '--http-proxy=false', '--user=1000:1000']:
        assert flag in args
    assert not any('docker.sock' in arg or arg == '--privileged' for arg in args)
    import pytest
    with pytest.raises(ValueError):
        command(image='node:latest', task_id='b'*64, source=source, request=request)


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
