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
