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

No generated-code execution, Git repository, host shell, email or browser-control tool is exposed to models. Add new tools only after threat modeling, explicit permission checks and enforceable sandbox tests. Prompt instructions alone are not permission controls. Draft review approval remains review-only; Phase 3 internal workspace writes use immutable, expiring, consumed approvals and a transactional executor. See docs/AGENT_EXTENSIONS.md before extending tools.

Phase 2 tests include accounts/CSRF/roles/tenant boundaries, real parser isolation, SSRF/TLS proxy guards, exact source quotes/hashes, local embedding fixtures and resource-aware parallel council. Linux/libseccomp2 is required for parser tests. `scripts/phase2_smoke.py` exercises real models/search/reports only against the explicit disposable verification project at loopback port 8003. `Dockerfile.verify` overlays final code on a canonically built local Phase 2 dependency base to fit this cloud VFS disk; canonical installation/CI still builds `Dockerfile`.

Phase 3 tests are in `backend/tests/test_agents.py` and the Workforce Playwright journeys. Real-model scripts `phase3_smoke.py` and `phase3_storage_smoke.py` target only the disposable loopback8003/cloud verification database, never an owner’s installation. The private test credential file is not source-controlled. Phase 3 adds no runtime dependencies or database tables.
