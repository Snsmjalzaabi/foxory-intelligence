"""New-install safety and existing configuration preservation."""
import importlib.util
from pathlib import Path
import stat

spec=importlib.util.spec_from_file_location('setup',Path(__file__).resolve().parents[2]/'scripts/setup.py')
setup=importlib.util.module_from_spec(spec);spec.loader.exec_module(setup)


def test_new_install_private_unique_secrets_and_modern_database(tmp_path):
    first=tmp_path/'first';second=tmp_path/'second';first.mkdir();second.mkdir()
    assert setup.initialize(first) and setup.initialize(second)
    left=(first/'.env').read_text();right=(second/'.env').read_text()
    assert left!=right and 'FOXORY_DATABASE_LAYOUT=modern\n' in left
    assert stat.S_IMODE((first/'.env').stat().st_mode)==0o600


def test_existing_install_is_never_reclassified_or_overwritten(tmp_path):
    path=tmp_path/'.env';original=b'# Existing legacy installation\nFOXORY_TOKEN=fictional-existing-token\n'
    path.write_bytes(original)
    assert not setup.initialize(tmp_path)
    assert path.read_bytes()==original
