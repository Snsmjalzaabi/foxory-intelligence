# Verification record

2026-10-23 execution in managed Linux x86_64 environment, Python 3.12.14, Node 24.19.0, Docker 28.4.0, Compose 2.40.3.

- Backend pytest: 18 tests passed after atomic deduplication/recovery changes; newer adapter tests are pending execution.
- Frontend strict TypeScript + Vite build: passed. Split output chunks are below 500 kB (approximately 263/178/168 kB JavaScript).
- Playwright Chromium: first five-test integration suite passed. Tests use a real API and local protocol fixture, not real model inference.
- SQLite migrations: upgrade/downgrade/re-upgrade with preservation test passed.
- SQLite backup/restore and original-upload roundtrip: passed in pytest.
- Compose CPU/GPU YAML configuration: validated; GPU execution not performed.
- Docker image: built successfully with a trusted CA build secret. Later ownership/lock changes are rebuilding and require runtime smoke.
- PostgreSQL 17.11 container: healthy, no public database port. Schema/restore smoke pending.
- npm audit: zero known advisories. pip-audit: zero known advisories in 35 pinned runtime packages.

See PROJECT_STATUS.md for final results. No v1.0, production-readiness, NVIDIA, Windows/macOS or independent security-review claim is made.
