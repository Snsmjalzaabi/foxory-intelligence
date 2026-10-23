# Development

Python 3.11+ (tested with 3.12), Node 22+ (local checks also on Node 24), npm lockfile. Backend runtime dependencies are frozen in `backend/requirements.lock`; install it first for reproducible environments, then `pip install --no-deps -e 'backend[test]'` after installing test tools. CI runs actual tests and builds; fixture tests must never be described as real model quality verification.

```sh
cd backend
../.venv/bin/pytest -q
cd ../frontend
npm ci
npm run build
npx playwright install chromium
npm run test:e2e
```

Browser tests start a real FastAPI server against a temporary migrated SQLite database and a clearly labeled local Ollama HTTP protocol fixture. The fixture contains no model weights and provides no inference quality evidence. It is never enabled by production code. Browser testing port 8001 and fixture port 11435 must be free.

Migration tests exercise upgrade, repeated upgrade with preserved data, downgrade and re-upgrade on temporary SQLite. PostgreSQL verification is reported separately. Create migration revisions for schema changes; do not call `create_all` at startup. Back up before production-data migrations.

No code, Git repository, shell, email or browser tool is exposed to models. Add new tools only after threat modeling, explicit permission checks and enforceable sandbox tests. Prompt instructions alone are not permission controls. Draft review approval is currently an audit workflow with no executor.

Phase 2 tests include accounts/CSRF/roles/tenant boundaries, real parser isolation, SSRF/TLS proxy guards, exact source quotes/hashes, local embedding fixtures and resource-aware parallel council. Linux/libseccomp2 is required for parser tests. `scripts/phase2_smoke.py` exercises real models/search/reports only against the explicit disposable verification project at loopback port 8003. `Dockerfile.verify` overlays final code on a canonically built local Phase 2 dependency base to fit this cloud VFS disk; canonical installation/CI still builds `Dockerfile`.
