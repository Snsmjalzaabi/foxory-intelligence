# Verification record — 2026-10-23

Managed Linux x86_64 cloud environment: Python 3.12.14, Node 24.19.0, Docker 28.4.0, Compose 2.40.3. See PROJECT_STATUS.md for precise scope, failures and limitations.

- Backend: **21 pytest tests passed**, latest run 9.62 seconds.
- Frontend: strict TypeScript and Vite build passed; output JS chunks approximately 263/178/168 kB.
- Browser: **5 Playwright Chromium tests passed** (48.8 seconds) with a real API and labeled HTTP protocol fixture. An earlier rerun had a port collision; another had one timeout under build contention; final rerun passed.
- Migrations: SQLite roundtrip/preservation and safe duplicate preflight passed; Compose PostgreSQL reached **0002**.
- Backup/restore: SQLite database + original-file roundtrip passed; PostgreSQL custom-format logical restore into a disposable database preserved a test record and revision 0002.
- Compose: CPU/GPU configuration syntax validated; CPU stack ran locally with app healthy, UID/GID 10001. No GPU execution claim.
- Live model: Ollama 0.13.5 / qwen2.5:0.5b CPU chat streamed and persisted a nonempty response at context 2048; Ollama reported 3 output tokens. This is protocol/connectivity evidence, not a quality or performance benchmark. Downloaded model license text identifies Apache License 2.0.
- Dependency advisory lookup: npm and 35-package locked Python runtime had zero known advisories; pip check passed. No independent security review or full image SBOM/CVE/license clearance.
- No live SearXNG, Windows/macOS, NVIDIA or reference-machine verification. No external publication/deployment.

Final image `sha256:4713ce74119c34c8c3d60bd919353cee94cd120372c7c71d450962f2db1347b1` built successfully. The app container was replaced with that image; an existing PostgreSQL marker survived and was removed afterward. Authenticated persistence, malformed-bearer rejection, frontend HTML delivery and real CPU chat passed again. Original local artifacts and named volumes remain private and are not committed.
