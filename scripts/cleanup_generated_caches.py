#!/usr/bin/env python3
"""Preview/remove recognized ignored FOXORY caches, never source or application data."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tomllib
from typing import Any

CACHES = ('.pytest_cache', 'backend/.pytest_cache', 'backend/foxory/__pycache__',
          'backend/tests/__pycache__', 'scripts/__pycache__', 'sandbox_manager/__pycache__')
PYTEST_FILES = {'.gitignore', 'CACHEDIR.TAG', 'README.md', 'v/cache/nodeids',
                'v/cache/lastfailed', 'v/cache/stepwise'}


def cleanup(root: Path, *, apply: bool = False) -> dict[str, Any]:
    root = root.resolve(strict=True)
    git = subprocess.check_output(['git', '-C', str(root), 'rev-parse', '--show-toplevel'], text=True).strip()
    if Path(git).resolve() != root:
        raise ValueError('Run from the FOXORY Git checkout root')
    project = tomllib.loads((root / 'backend/pyproject.toml').read_text())
    if project.get('project', {}).get('name') != 'foxory-intelligence':
        raise ValueError('Not a FOXORY checkout')
    if apply and (os.getuid() == 0 or not shutil.rmtree.avoids_symlink_attacks):
        raise ValueError('Apply requires a non-root account and safe directory deletion; do not use sudo')
    records: list[dict[str, Any]] = []
    total = 0
    for relative in CACHES:
        path = root / relative
        if not path.exists() and not path.is_symlink():
            continue
        row: dict[str, Any] = {'path': relative, 'status': 'skipped'}
        records.append(row)
        try:
            cursor = root
            for part in Path(relative).parts:
                cursor = cursor / part
                if cursor.is_symlink():raise ValueError('Symlink path retained')
            original = path.lstat()
            if not stat.S_ISDIR(original.st_mode):raise ValueError('Not a cache directory')
            if subprocess.check_output(['git', '-C', str(root), 'ls-files', '-z', '--', relative]):
                raise ValueError('Contains tracked files; retained')
            ignored = subprocess.run(['git', '-C', str(root), 'check-ignore', '--quiet', '--', relative], check=False)
            if ignored.returncode != 0:raise ValueError('Not an ignored cache; retained')
            entries = [path]
            for entry in path.rglob('*'):
                if len(entries) >= 10000:raise ValueError('Cache entry limit; retained')
                entries.append(entry)
            size = 0
            for entry in entries:
                info = entry.lstat()
                if info.st_uid != os.getuid() or stat.S_ISLNK(info.st_mode):
                    raise ValueError('Unexpected ownership or symlink; retained')
                if stat.S_ISREG(info.st_mode):
                    name = entry.relative_to(path).as_posix()
                    expected = name in PYTEST_FILES if path.name == '.pytest_cache' else entry.parent == path and entry.suffix == '.pyc'
                    if not expected:raise ValueError('Unexpected file in cache; retained')
                    size += info.st_size
                elif not stat.S_ISDIR(info.st_mode):raise ValueError('Special inode; retained')
            current = path.lstat()
            if (current.st_dev, current.st_ino) != (original.st_dev, original.st_ino):
                raise ValueError('Cache changed during inspection; retained')
            row.update(status='removed' if apply else 'would_remove', bytes=size)
            if apply:
                shutil.rmtree(path)
                total += size
        except (ValueError, OSError) as error:
            row.update(status='skipped', reason=str(error))
    return {'mode': 'apply' if apply else 'preview', 'root': str(root),
            'caches': records, 'bytes_removed': total,
            'scope': 'Recognized ignored Python/pytest caches only; no backups, credentials, models, uploads, Git history or runtime state'}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Remove recognized caches; default is preview only')
    args = parser.parse_args()
    print(json.dumps(cleanup(Path.cwd(), apply=args.apply), indent=2))


if __name__ == '__main__':
    main()
