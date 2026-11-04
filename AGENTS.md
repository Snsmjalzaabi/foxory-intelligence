# Guidance for AI coding agents

## Releases

For every user-facing change, increment the version before building or packaging: patch for
fixes, minor for features, major for incompatible changes. Run
`python3 scripts/release_version.py X.Y.Z` to update `VERSION`, backend, frontend and package
metadata together; the version badge and `/api/health` must agree. The `foxory-release`
skill in `.claude/skills/` walks through the whole release.

## Debloat every release

Before each version bump, remove what is no longer needed: unreferenced modules, functions,
components and scripts, unused dependencies, superseded docs and duplicate assets. Confirm
nothing imports, tests, packages, documents or runs a file (CI workflows included) before
deleting it, then run the backend tests and frontend build. List what was removed in the
release notes. Never delete user data, private configuration or evidence that open release
gates in `PROJECT_STATUS.md` rely on.

## Privacy

Keep FOXORY local-first: no paid or cloud inference, nothing sent off the computer without the
user asking for it. Never commit `.env`, backups, model weights or anything under `data/`,
`backups/` or `.local-ai/`, and never bundle them in release archives. User-specific names and
defaults belong in `profiles/`, not in code.
