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

## Phase 2 verification — 2026-10-23

The Phase 1 record above remains historical. Current full regression: **39 pytest tests passed (93.82s)**; strict TypeScript/Vite build passed; **7 Chromium integration tests passed (1.1m)**. Browser tests exercise the real API with deterministic, explicitly labeled inference/search fixtures. Python runtime now has 44 locked packages, with no known advisory matches in the executed pip-audit review; pip check passed. Dependency notices and inventory were refreshed.

Real CPU Ollama verification used `qwen2.5:0.5b`, `smollm2:135m` and `nomic-embed-text`. `scripts/phase2_smoke.py` passed real accounts/CSRF/isolation, restricted uploads, semantic retrieval, document research, internet search/page retrieval, pause/resume, reference integrity, PDF/DOCX/XLSX downloads, separate two-model analyses/comparison/synthesis and logout revocation. The final bounded CPU profile used context 2048/output 256/two threads; document/web reports explicitly selected `extractive_fallback` rather than claiming unsupported generated citations. Council stages generated actual outputs; no claim that agreement proves truth.

Retrieved sources in the successful internet research run:

| Actual page | SHA-256 of saved readable text |
| --- | --- |
| https://en.wikipedia.org/wiki/Retrieval-augmented_generation | `f9dfc9d39c11f61cdc9f4fb1a0540d685ab523ba7c8da48cd89baf2a6d2310b4` |
| https://en.wikipedia.org/wiki/Large_language_model | `a499bde400ea4ffe86f160422d547e1eaf401fb726af2fdc5d70dc39b18fc713` |

Digests identify snapshots, not current pages or truth. Separate public retrieval also succeeded for example.com through the managed HTTPS proxy with TLS verification enabled.

`scripts/phase2_storage_smoke.py` passed on the final parser-hardening image: actual new upload, session/file/paused-job persistence across app restart, resume/cancel, then PostgreSQL custom-format restore into a disposable database preserving revision0003/users/memberships/documents/jobs. Current tested image digest: `sha256:193b6ef2fbb320c909ce25394782b71d441732fabc34b17a317870d62b71409f`. Canonical image built; final source overlays were necessary for the cloud's 32GB VFS disk. Compose default and GPU override syntax were checked; no GPU execution was performed.

Failures found and resolved: slim-container UTF-8 BOM codec preload; unbounded parent capture of parser output; page budget monopolized by first subquestion; oversized/slow CPU background context; step deadlines; proxy tunnel TLS hostname handling; first-login loading race and browser timing under CPU contention. Earlier disk-full disposable PostgreSQL initialization, port conflicts and browser timeout runs were rerun after their causes were fixed. Final suites above passed without suppressing failures.

Limitations: no live SearXNG or Windows/macOS/GPU validation; no independent security audit/full image clearance, broad factual-answer evaluation or production readiness claim. See PROJECT_STATUS.md for operational restrictions.

The preserved original local stack was upgraded only after a private PostgreSQL backup. Revision0003, healthy localhost app, unauthenticated rejection and authenticated persistence/delete passed. Original uploads/model volumes were retained; no owner administrator account was created automatically. Disposable verification accounts/databases/volumes were removed.

Final upgraded-stack CPU chat (`FOXORY_SMOKE_MODEL=qwen2.5:0.5b python scripts/smoke.py`) passed real streaming, completion metadata and persisted nonempty response (3 output tokens); temporary conversation deleted afterward. App UID/GID10001 and read-only root filesystem confirmed. This is connectivity/regression evidence, not a quality benchmark or GPU test.
