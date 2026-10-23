"""Read-only host diagnostics. Passing diagnostics never authorizes execution."""
from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path
from typing import Any


def inspect_host(*, cgroup_root: Path = Path('/sys/fs/cgroup'),
                 membership: Path = Path('/proc/self/cgroup')) -> dict[str, Any]:
    blockers: list[str] = []
    if platform.system() != 'Linux':
        blockers.append('Linux is required')
    if os.getuid() == 0:
        blockers.append('A dedicated non-root manager account is required')
    delegated: Path | None = None
    try:
        entries = membership.read_text().splitlines()
        unified = [line[3:] for line in entries if line.startswith('0::')]
        if len(unified) != 1:
            raise ValueError('unified cgroup membership missing')
        relative = unified[0]
        if not relative.startswith('/') or '..' in Path(relative).parts:
            raise ValueError('invalid cgroup membership')
        root = cgroup_root.resolve(strict=True)
        delegated = (root / relative.lstrip('/')).resolve(strict=True)
        if not delegated.is_relative_to(root):
            raise ValueError('cgroup path escaped mount')
        available = set((delegated / 'cgroup.controllers').read_text().split())
        missing = {'cpu', 'memory', 'pids'} - available
        if missing:
            blockers.append('Missing delegated controllers: ' + ', '.join(sorted(missing)))
        if not os.access(delegated / 'cgroup.subtree_control', os.W_OK):
            blockers.append('Current cgroup subtree_control is not writable')
        if not os.access(delegated, os.W_OK):
            blockers.append('Current cgroup cannot create child cgroups')
    except (OSError, ValueError) as exc:
        blockers.append('Cannot establish cgroup v2 delegation: ' + str(exc))
    for executable in ('podman', 'newuidmap', 'newgidmap'):
        if not shutil.which(executable):
            blockers.append(executable + ' is required for the optional rootless OCI profiles')
    return {
        'schema_version': 1,
        'static_requirements_met': not blockers,
        'execution_enabled': False,
        'runtime_isolation_verified': False,
        'cgroup_path': str(delegated) if delegated else None,
        'blockers': blockers,
        'pending_checks': [
            'Rootless runtime identity and subordinate UID/GID mappings',
            'Active CPU, memory and process-limit enforcement inside a disposable task',
            'Read-only root, task-only mounts, network denial and secret isolation',
            'Chromium sandbox, cancellation, cleanup and artifact integrity',
        ],
    }
