#!/usr/bin/env python3
"""Non-mutating Ubuntu host preflight; exit 2 means requirements are missing.

This script does not enable execution, install software, change cgroups or run
untrusted code. Run it as the intended dedicated sandbox-manager account.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sandbox_manager.capabilities import inspect_host

if __name__ == '__main__':
    report = inspect_host()
    print(json.dumps(report, indent=2))
    sys.exit(0 if report['static_requirements_met'] else 2)
