---
name: foxory-release
description: This skill should be used when shipping any user-facing change to the FOXORY Intelligence repository as a new version - a fix, feature or cleanup that needs a version bump, a debloat pass, verification, release notes, the source manifest and ZIP, and a commit. Triggers include "release this", "ship it", "bump the version", "make a new version", or finishing a feature in FOXORY.
---

# FOXORY Release

Ship a FOXORY change as a verified, packaged release that follows the owner's rules in
`AGENTS.md`: every user-facing update gets a semantic version bump, every release includes
a debloat pass, and nothing private is packaged. Releases stay local; never push or
publish without the owner's explicit go-ahead.

Helper: `scripts/release_checks.py` (in this skill folder) with three subcommands:
`scan`, `verify`, `package`. Run it from anywhere inside the repository.

## Steps

### 1. Choose the version

Read `VERSION`. Pick patch (fixes, small updates), minor (features) or major
(incompatible changes). Several changes in one session can share one release.

### 2. Debloat pass (required every release)

Run `python3 .claude/skills/foxory-release/scripts/release_checks.py scan`. It lists
unused Python code (vulture), unused frontend exports/components, CSS classes referenced
nowhere, scripts nothing references, and broken Markdown links.

For each candidate, confirm it is truly unused before deleting: search imports, tests, CI
workflows (`.github/workflows`), Dockerfiles, compose files, `scripts/package_release.py`
and docs. Framework entry points (FastAPI route handlers, pydantic validators) are not dead
code. Never delete owner data, private configuration, `docs/evidence/` or anything an open
release gate in `PROJECT_STATUS.md` relies on. Remove CSS selectors surgically when they
share a rule with live selectors. Record what was removed and roughly how much in the
release notes; "nothing found" is a valid result to report. The scan exits non-zero while any
candidate remains, so never continue past it: delete the item, or wire up / document it so
it is used, then re-run until it reports 0.

### 3. Bump the version

Run `python3 scripts/release_version.py X.Y.Z`. It updates `VERSION`, backend, frontend and
package metadata together. Then update by hand: the two version headings at the top of
`README.md` and its "Current:" release-guide links.

### 4. Write the release notes

- New feature line (minor/major): create `docs/release-notes/RELEASE-VX.Y.md`.
- Patch: add a `## X.Y.Z — <summary>` section at the top of the existing `RELEASE-VX.Y.md`,
  under the title, and keep the previous sections intact with their own headings.
- Add a row to `docs/release-notes/README.md` (newest first) for a new feature line.
- Prepend a `# FOXORY Local Edition X.Y.Z — <date>` entry to `CHANGELOG.md`.

Write for the owner: what changed, how to use it, what stays private or safe, the cleanup
summary, and the upgrade command (`python3 scripts/foxory.py start`).

### 5. Verify

Run `python3 .claude/skills/foxory-release/scripts/release_checks.py verify --python <venv python>`,
where the venv has `backend/requirements.lock` and `pytest`/`pytest-asyncio` installed. It runs
backend tests (sandbox-runtime tests excluded; they need the real Ubuntu host), the strict
frontend build, the Markdown link check and compose validation. Fix every failure before
continuing. For UI changes, also exercise the change in a browser against
`scripts/e2e_server.py` (port 8001, fake Ollama); headless Chromium can hang on
screenshots and MediaRecorder here, so check DOM state and network requests instead.

### 6. Package

Run `python3 .claude/skills/foxory-release/scripts/release_checks.py package`. It regenerates
`SOURCE-MANIFEST.json` and `releases/FOXORY-Local-X.Y.Z.zip` (+ `.sha256`), removes older
release ZIPs, and fails unless the checksum matches, the manifest lists exactly the tracked
files at the new version, and no `.env`, backup, data or model weight is inside. Run it
last: any later file edit invalidates the manifest.

### 7. Commit

Commit on the working branch with a subject naming the version and a body listing the
changes, ending with the session's attribution lines. Do not push.

### 8. Report to the owner

State the new version, what changed, what was verified (and what could not be, such as
sandbox-runtime tests or screenshots), and how to apply it. The live installation runs from
a separate folder (find it with
`docker ps --format '{{.Label "com.docker.compose.project.working_dir"}}'`); upgrading it
is a separate step that needs the owner's approval and a backup first
(`scripts/foxory_backup.py`).
