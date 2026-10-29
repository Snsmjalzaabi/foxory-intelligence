"""Destructive-command boundaries in disposable filesystem/Git fixtures only."""
import importlib.util
from pathlib import Path
import subprocess

import pytest

spec = importlib.util.spec_from_file_location('cache_cleanup', Path(__file__).resolve().parents[2] / 'scripts/cleanup_generated_caches.py')
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


@pytest.fixture
def checkout(tmp_path):
    subprocess.run(['git', 'init', '--quiet', str(tmp_path)], check=True)
    (tmp_path / 'backend').mkdir()
    (tmp_path / 'backend/pyproject.toml').write_text('[project]\nname="foxory-intelligence"\n')
    (tmp_path / '.gitignore').write_text('__pycache__/\n.pytest_cache/\n')
    (tmp_path / '.env').write_text('PRIVATE_FIXTURE=not-a-real-secret\n')
    return tmp_path


def cache(root):
    path = root / 'scripts/__pycache__'
    path.mkdir(parents=True)
    (path / 'fixture.pyc').write_bytes(b'disposable bytecode')
    return path


def test_preview_then_apply_preserves_source_and_credentials(checkout):
    path = cache(checkout)
    result = review.cleanup(checkout)
    assert result['caches'][0]['status'] == 'would_remove' and path.exists()
    result = review.cleanup(checkout, apply=True)
    assert result['caches'][0]['status'] == 'removed' and not path.exists()
    assert (checkout / '.env').read_text() == 'PRIVATE_FIXTURE=not-a-real-secret\n'
    assert (checkout / 'backend/pyproject.toml').exists() and (checkout / '.git').is_dir()


def test_escaping_symlink_cache_is_retained(checkout, tmp_path_factory):
    outside = tmp_path_factory.mktemp('outside-cache')
    (outside / 'keep.pyc').write_bytes(b'keep')
    (checkout / 'scripts').mkdir()
    (checkout / 'scripts/__pycache__').symlink_to(outside, target_is_directory=True)
    result = review.cleanup(checkout, apply=True)
    assert result['caches'][0]['status'] == 'skipped' and (outside / 'keep.pyc').exists()


def test_unexpected_cache_file_is_not_deleted(checkout):
    path = cache(checkout)
    (path / 'owner-notes.txt').write_text('retain')
    result = review.cleanup(checkout, apply=True)
    assert result['caches'][0]['status'] == 'skipped' and (path / 'owner-notes.txt').read_text() == 'retain'


def test_force_tracked_cache_is_not_deleted(checkout):
    path = cache(checkout)
    subprocess.run(['git', '-C', str(checkout), 'add', '--force', 'scripts/__pycache__/fixture.pyc'], check=True)
    result = review.cleanup(checkout, apply=True)
    assert result['caches'][0]['status'] == 'skipped' and (path / 'fixture.pyc').exists()


def test_unrelated_repository_is_refused(checkout):
    path = cache(checkout)
    (checkout / 'backend/pyproject.toml').write_text('[project]\nname="unrelated"\n')
    with pytest.raises(ValueError, match='Not a FOXORY'):review.cleanup(checkout, apply=True)
    assert path.exists()
