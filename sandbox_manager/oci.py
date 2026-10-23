"""Fixed optional OCI command policy. Not an execution authorization mechanism.

Only a trusted operator-selected local immutable image is accepted. Runtime
activation still requires authenticated dispatch and active isolation preflight.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from foxory.sandbox_protocol import OCIProject, BrowserAction


def command(*, image: str, task_id: str, source: Path, request: Path,
            profile: Literal['javascript', 'typescript', 'browser'], owner: str = "") -> list[str]:
    # Explicit validated dispatch profile, never a flag/image supplied by a user
    # or inferred by reading the mutable request file during command construction.
    if profile not in {'javascript', 'typescript', 'browser'}:
        raise ValueError('Unsupported OCI profile')
    if not re.fullmatch(r'sha256:[a-f0-9]{64}', image):
        raise ValueError('An immutable local image ID is required')
    if not re.fullmatch(r'[a-f0-9]{64}', task_id):
        raise ValueError('Invalid manager task ID')
    if any(any(c in str(p.resolve()) for c in ':,\n\r') for p in (source, request)):
        raise ValueError('Unsafe staging path')
    if not source.is_dir() or not request.is_file():
        raise ValueError('Missing manager-owned staging files')
    if owner and not re.fullmatch(r'[a-f0-9]{32}',owner):raise ValueError('Invalid manager owner')
    # No shell; users cannot supply images, runtime flags, mounts or networking.
    return [
        'podman', '--remote=false', 'run', '--pull=never', '--rm',
        *(['--label=io.foxory.manager='+owner,'--label=io.foxory.task='+task_id] if owner else []),
        '--name=foxory-task-' + task_id, '--network=none', '--read-only',
        '--ipc=private', '--pid=private', '--uts=private', '--cgroupns=private',
        '--userns=keep-id:uid=1000,gid=1000', '--user=1000:1000',
        '--cap-drop=ALL',
        # Chromium chroots inside its user-namespace sandbox. The containers/common
        # default seccomp policy gates chroot on this capability even for nested
        # user namespaces. Keep default seccomp/AppArmor and every other cap dropped.
        *(['--cap-add=SYS_CHROOT'] if profile == 'browser' else []),
        '--security-opt=no-new-privileges',
        '--memory=1073741824', '--memory-swap=1073741824', '--cpus=1',
        '--pids-limit=128', '--timeout=45', '--ulimit=nofile=256:256', '--ulimit=core=0:0',
        '--http-proxy=false', '--env=HOME=/tmp', '--env=LANG=C.UTF-8',
        '--tmpfs=/tmp:rw,nosuid,nodev,size=134217728,mode=1777',
        '--tmpfs=/out:rw,noexec,nosuid,nodev,size=16777216,mode=1777',
        '--shm-size=64m',
        '--volume=' + str(source.resolve()) + ':/work:ro,Z',
        '--volume=' + str(request.resolve()) + ':/request.json:ro,Z',
        '--workdir=/work', '--entrypoint=node', image, '/opt/foxory/worker.mjs',
    ]
