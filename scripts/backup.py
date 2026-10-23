"""Offline SQLite data backup. Stop the application before using this utility."""
import argparse
import shutil
import sqlite3
from pathlib import Path

def copy_data(source: Path, destination: Path):
    source=source.resolve();destination=destination.resolve()
    if not (source/'foxory.db').is_file():raise ValueError('Source must contain foxory.db')
    if destination.exists():raise ValueError('Destination already exists; refusing overwrite')
    if source==destination or source in destination.parents:raise ValueError('Destination must be outside source')
    destination.mkdir(parents=True,mode=0o700)
    try:
        with sqlite3.connect(f'file:{source / "foxory.db"}?mode=ro',uri=True) as src,sqlite3.connect(destination/'foxory.db') as dst:
            src.backup(dst)
            if dst.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Integrity check failed')
        (destination/'foxory.db').chmod(0o600)
        if (source/'uploads').exists():shutil.copytree(source/'uploads',destination/'uploads')
    except Exception:
        shutil.rmtree(destination)
        raise
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['backup','restore']);parser.add_argument('source',type=Path);parser.add_argument('destination',type=Path)
    args=parser.parse_args();copy_data(args.source,args.destination)
    print('Copied database and uploads. Keep this directory private. Application must be stopped for consistency.')
