"""Fixed optional OCI command policy. Not an execution authorization mechanism.

Only a trusted operator-selected local immutable image is accepted. Runtime
activation still requires authenticated dispatch and active isolation preflight.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .service import valid_path


class BrowserAction(BaseModel):
    model_config = ConfigDict(extra='forbid')
    action: Literal['navigate', 'inspect', 'click', 'type', 'screenshot', 'download']
    target: str = Field(default='', max_length=200)
    text: str = Field(default='', max_length=2000)

    @model_validator(mode='after')
    def check(self):
        if self.action == 'navigate' and (
            not self.target.startswith('/') or self.target.startswith('//')
            or '\\' in self.target or '..' in self.target.split('/')
            or any(ord(c) < 32 for c in self.target) or '%' in self.target
        ):
            raise ValueError('Navigation must use a literal local fixture path')
        if self.action in {'click', 'type', 'download'} and not self.target:
            raise ValueError('An explicit selector is required')
        return self


class OCIProject(BaseModel):
    model_config = ConfigDict(extra='forbid')
    profile: Literal['javascript', 'typescript', 'browser']
    files: dict[str, str] = Field(min_length=1, max_length=50)
    entrypoint: str = Field(default='', max_length=180)
    actions: list[BrowserAction] = Field(default_factory=list, max_length=12)

    @model_validator(mode='after')
    def check(self):
        if any(not valid_path(k) or '\x00' in v for k, v in self.files.items()):
            raise ValueError('Invalid source path/content')
        if sum(len(v.encode()) for v in self.files.values()) > 20000:
            raise ValueError('Source byte budget exceeded')
        if self.profile == 'browser':
            if not self.actions or self.entrypoint:
                raise ValueError('Browser requires actions and no code entrypoint')
        else:
            suffix = '.js' if self.profile == 'javascript' else '.ts'
            if self.entrypoint not in self.files or not self.entrypoint.endswith(suffix):
                raise ValueError('Entrypoint must match the selected language')
            if self.actions:
                raise ValueError('Browser actions are not code execution arguments')
        return self


def command(*, image: str, task_id: str, source: Path, request: Path) -> list[str]:
    if not re.fullmatch(r'sha256:[a-f0-9]{64}', image):
        raise ValueError('An immutable local image ID is required')
    if not re.fullmatch(r'[a-f0-9]{64}', task_id):
        raise ValueError('Invalid manager task ID')
    if any(any(c in str(p.resolve()) for c in ':,\n\r') for p in (source, request)):
        raise ValueError('Unsafe staging path')
    if not source.is_dir() or not request.is_file():
        raise ValueError('Missing manager-owned staging files')
    # No shell; users cannot supply images, runtime flags, mounts or networking.
    return [
        'podman', '--remote=false', 'run', '--pull=never', '--rm',
        '--name=foxory-task-' + task_id, '--network=none', '--read-only',
        '--ipc=private', '--pid=private', '--uts=private', '--cgroupns=private',
        '--userns=keep-id:uid=1000,gid=1000', '--user=1000:1000',
        '--cap-drop=ALL', '--security-opt=no-new-privileges',
        '--memory=1073741824', '--memory-swap=1073741824', '--cpus=1',
        '--pids-limit=128', '--ulimit=nofile=256:256', '--ulimit=core=0:0',
        '--http-proxy=false', '--env=HOME=/tmp', '--env=LANG=C.UTF-8',
        '--tmpfs=/tmp:rw,nosuid,nodev,size=134217728,mode=1777',
        '--tmpfs=/out:rw,noexec,nosuid,nodev,size=16777216,mode=1777',
        '--shm-size=64m',
        '--volume=' + str(source.resolve()) + ':/work:ro,Z',
        '--volume=' + str(request.resolve()) + ':/request.json:ro,Z',
        '--workdir=/work', '--entrypoint=node', image, '/opt/foxory/worker.mjs',
    ]
