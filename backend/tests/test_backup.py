import importlib.util
from pathlib import Path
import sqlite3
import pytest

def test_offline_backup_restore(tmp_path):
    spec=importlib.util.spec_from_file_location('backup',Path(__file__).resolve().parents[2]/'scripts/backup.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    source=tmp_path/'data';source.mkdir();(source/'uploads').mkdir();(source/'uploads'/'random-id').write_bytes(b'Original private document')
    with sqlite3.connect(source/'foxory.db') as c:c.execute('CREATE TABLE facts(value TEXT)');c.execute("INSERT INTO facts VALUES ('preserved')")
    module.copy_data(source,tmp_path/'backup');module.copy_data(tmp_path/'backup',tmp_path/'restored')
    with sqlite3.connect(tmp_path/'restored'/'foxory.db') as c:assert c.execute('SELECT value FROM facts').fetchone()[0]=='preserved'
    assert (tmp_path/'restored'/'uploads'/'random-id').read_bytes()==b'Original private document'
    with pytest.raises(ValueError):module.copy_data(source,tmp_path/'restored')


@pytest.mark.parametrize('kind',['file','directory','database'])
def test_backup_rejects_symlinks_without_copying_unrelated_files(tmp_path,kind):
    spec=importlib.util.spec_from_file_location('backup',Path(__file__).resolve().parents[2]/'scripts/backup.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    source=tmp_path/'data';source.mkdir();(source/'uploads').mkdir()
    with sqlite3.connect(source/'foxory.db') as connection:connection.execute('CREATE TABLE facts(value TEXT)')
    outside=tmp_path/'unrelated';outside.mkdir();(outside/'private').write_text('Must not enter a backup')
    if kind=='database':
        (source/'foxory.db').rename(outside/'other.db');(source/'foxory.db').symlink_to(outside/'other.db')
    else:(source/'uploads'/'escape').symlink_to(outside if kind=='directory' else outside/'private',target_is_directory=kind=='directory')
    with pytest.raises(ValueError):module.copy_data(source,tmp_path/'backup')
    assert not (tmp_path/'backup').exists()
    assert (outside/'private').read_text()=='Must not enter a backup'


def test_backup_preserves_committed_wal_and_handles_uri_characters(tmp_path):
    spec=importlib.util.spec_from_file_location('backup',Path(__file__).resolve().parents[2]/'scripts/backup.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    source=tmp_path/'data ? #';source.mkdir()
    with sqlite3.connect(source/'foxory.db') as connection:
        connection.execute('PRAGMA journal_mode=WAL')
        connection.execute('CREATE TABLE facts(value TEXT)');connection.execute("INSERT INTO facts VALUES ('committed WAL')");connection.commit()
        assert (source/'foxory.db-wal').exists()
        module.copy_data(source,tmp_path/'backup ? #')
    with sqlite3.connect(tmp_path/'backup ? #/foxory.db') as restored:
        assert restored.execute('SELECT value FROM facts').fetchone()[0]=='committed WAL'
    assert (tmp_path/'backup ? #/foxory.db').stat().st_mode & 0o777 == 0o600


def test_backup_rejects_fifo_without_waiting_for_a_writer(tmp_path):
    import os
    spec=importlib.util.spec_from_file_location('backup',Path(__file__).resolve().parents[2]/'scripts/backup.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    source=tmp_path/'data';source.mkdir();(source/'uploads').mkdir()
    with sqlite3.connect(source/'foxory.db') as connection:connection.execute('CREATE TABLE facts(value TEXT)')
    os.mkfifo(source/'uploads'/'pipe')
    with pytest.raises(ValueError):module.copy_data(source,tmp_path/'backup')
    assert not (tmp_path/'backup').exists()
