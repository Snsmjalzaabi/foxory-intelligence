"""Offline SQLite data backup. Stop the application before using this utility."""
import argparse
from contextlib import closing
import os
import shutil
import sqlite3
import stat
import tempfile
from pathlib import Path

def copy_regular(directory: int, name: str, target: Path):
    """Open one basename without following a swapped or preexisting symlink."""
    try:
        descriptor=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=directory)
        with os.fdopen(descriptor,'rb') as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):raise ValueError('Backup accepts regular files only')
            output=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            with os.fdopen(output,'wb') as destination:shutil.copyfileobj(source,destination,1024*1024)
    except OSError as error:raise ValueError('Unsafe or unavailable backup file') from error

def copy_uploads(directory: int, target: Path, depth: int = 0):
    if depth>64:raise ValueError('Backup directory depth exceeded')
    target.mkdir(mode=0o700)
    for name in os.listdir(directory):
        info=os.stat(name,dir_fd=directory,follow_symlinks=False)
        if stat.S_ISDIR(info.st_mode):
            child=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=directory)
            try:copy_uploads(child,target/name,depth+1)
            finally:os.close(child)
        elif stat.S_ISREG(info.st_mode):copy_regular(directory,name,target/name)
        else:raise ValueError('Symlinks and special files are not valid backup inputs')

def copy_data(source: Path, destination: Path):
    if not all(hasattr(os,flag) for flag in ['O_NOFOLLOW','O_DIRECTORY','O_NONBLOCK']):
        raise ValueError('Safe backup requires POSIX directory/no-follow support; run inside Linux')
    if source.is_symlink():raise ValueError('Source directory must not be a symlink')
    source=source.resolve();destination=destination.resolve()
    if destination.exists():raise ValueError('Destination already exists; refusing overwrite')
    if source==destination or source in destination.parents:raise ValueError('Destination must be outside source')
    root=os.open(source,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:destination.mkdir(parents=True,mode=0o700)
    except Exception:
        os.close(root)
        raise
    try:
        # Never let SQLite resolve an untrusted source path/symlink. Snapshot
        # regular DB/WAL bytes into a private directory first; the app MUST be
        # stopped so that these two files do not change while being copied.
        with tempfile.TemporaryDirectory(prefix='foxory-backup-input-') as temporary:
            snapshot=Path(temporary)/'foxory.db'
            copy_regular(root,'foxory.db',snapshot)
            try:os.stat('foxory.db-wal',dir_fd=root,follow_symlinks=False)
            except FileNotFoundError:pass
            else:copy_regular(root,'foxory.db-wal',snapshot.with_name('foxory.db-wal'))
            with closing(sqlite3.connect(snapshot.as_uri()+'?mode=ro',uri=True)) as src,closing(sqlite3.connect(destination/'foxory.db')) as dst:
                src.execute('PRAGMA trusted_schema=OFF');dst.execute('PRAGMA trusted_schema=OFF')
                src.backup(dst)
                if dst.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Integrity check failed')
        (destination/'foxory.db').chmod(0o600)
        try:info=os.stat('uploads',dir_fd=root,follow_symlinks=False)
        except FileNotFoundError:pass
        else:
            if not stat.S_ISDIR(info.st_mode):raise ValueError('Uploads must be a regular directory')
            uploads=os.open('uploads',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=root)
            try:copy_uploads(uploads,destination/'uploads')
            finally:os.close(uploads)
    except Exception:
        shutil.rmtree(destination)
        raise
    finally:os.close(root)
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['backup','restore']);parser.add_argument('source',type=Path);parser.add_argument('destination',type=Path)
    args=parser.parse_args();copy_data(args.source,args.destination)
    print('Copied database and uploads. Keep this directory private. Application must be stopped for consistency.')
