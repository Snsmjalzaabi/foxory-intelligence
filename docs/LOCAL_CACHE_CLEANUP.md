# Reviewed FoxPC cache cleanup

Run as your normal Ubuntu account, without sudo. These commands update the
existing development checkout, check Git objects and remove only recognized
ignored Python/pytest caches. They do not reset source, delete Git history,
bundles, credentials, uploads, models, database volumes or manager state.

```bash
bash <<'BASH'
set -euo pipefail
cd "$HOME/Projects/foxory-intelligence"
git fsck --full
git switch development
git pull --ff-only origin development
python3 scripts/cleanup_generated_caches.py
python3 scripts/cleanup_generated_caches.py --apply
git status --short
BASH
```

Python3.11+ and Git are required; no dependency installation is needed. The first
Python command previews candidates; the second applies the same guarded policy.
Unexpected files, symlinks, other owners, tracked files and unrecognized caches
are retained and reported. A safe directory-deletion implementation is required.
Some harmless caches can be recreated by later Python/test commands.

If Git integrity checking fails, the block stops before cleanup. Dangling Git
objects alone are not corruption; do not prune/reset to remove that message.
Share the terminal output for review. These commands do not establish that every
file on the PC is healthy or disposable, and they do not remove chat attachments.
No PC cleanup is claimed until the owner executes and reports the result.
