> Historical verification snapshots are preserved below. For the latest recovery
> results, real-model/web evidence, feature matrix and remaining limitations, use
> [PROJECT_STATUS.md](../PROJECT_STATUS.md) and [CORE_PRODUCT_RECOVERY.md](CORE_PRODUCT_RECOVERY.md).

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

## Phase 3 verification — 2026-10-23

Accepted Phase 2 baseline: 7d1cd05a0238fae6ff762df79fbb1f1e42aa113f. Implementation increments: 674135a and 24ec0c0. A serial pre-optimization run passed 59 backend tests in 151.27s. The final optimized run passed **60 tests in 63.19s**, including 21 agent-specific/parser-boundary checks and all existing regressions. Strict TypeScript/Vite production build passed; latest main JS approximately 288kB. The final complete Chromium browser suite passed **9 tests (1.6m)**. It uses the real API and an explicitly labeled deterministic model protocol fixture; actual Ollama CPU execution was verified separately below.

Real Ollama CPU demonstration used **qwen2.5:0.5b**, two threads, context2048/output256. A General Coordinator generated a validated plan and delegated a 15%-of-2400 contingency calculation to a separately configured analyst. The actual arithmetic tool returned **360**; coordinator quality review and consolidation completed in three model calls. Generated memory remained unverified. Markdown/PDF/DOCX/XLSX downloads passed. A second internal-project workflow waited for approval, committed one project, consumed its immutable approval and rejected reuse. A one-time schedule dispatched and completed without a browser. The harness resumed a persisted job after a transient polling failure rather than resubmitting it.

An earlier 0.5B-model attempt omitted a requested writing subtask despite valid JSON. That assertion failed and is not counted as a successful three-agent demonstration. A larger background profile reached a step timeout under CPU contention. Complex-goal coverage and factual quality remain unverified; use a more capable local model or an explicit reviewed plan. No GPU or reference-machine performance claim.

Final code overlay image: sha256:637314f1ddec45a689fe13d9b90f109ee5e636f8c17daed3bfc0b3d816ff55bb. Runtime hashes for eight implementation modules matched source. Non-root UID/GID10001, read-only root, init process, no source/Docker-socket mounts and IANA Europe/Paris timezone data were checked. The dependency base was built with the canonical Dockerfile in Phase 2; Phase 3 adds no runtime dependencies. Cloud VFS limits required source overlays and cleanup of rebuildable caches/superseded images; owner data/model volumes and Git history were preserved.

scripts/phase3_storage_smoke.py passed on this exact image: restricted TXT upload, original bytes/session/paused-task persistence over restart, resume/cancel, once-only overdue schedule dispatch after restart, then PostgreSQL custom-format restore preserving revision0003, accounts, memberships, agents, jobs, schedules, approvals and memory. Phase 3 uses existing workspace-scoped Record envelopes; no schema migration was necessary. Existing migration roundtrip/preservation tests passed.

Failures corrected: duplicate legacy agent-create UI; six-request polling exceeding API limits (now one scoped overview and no overlapping refreshes); selector labeling; malformed/ungranted plans; specialist limits; legacy zero-tool definitions; database I/O blocking the API loop; stale approval revocation; and missing startup health wait in the integration harness. Early disposable testing filled the cloud disk; cleanup preserved owner volumes.

A contended full run reported 57 passed/one valid TXT rejected by the unchanged 20-second parser budget; the final serial run passed all59. Earlier browser runs recorded CPU/startup timeouts, a five-second pre-response upload assertion and a false-positive completion match against help text. Checks now wait for the actual422 response and actual status badge, with explicit CI timing allowances. No parser limit, execution budget, permission or approval enforcement was relaxed.

Remaining release work includes independent security review, full-image/dependency legal clearance, clean-host installation matrix and broader model-quality/performance evaluation. Phase 4 execution tools remain absent.

Trusted parser preload now depends only on a whitelisted extension. TXT/Markdown/CSV/JSON use a shared stdlib-only parser. Payload bytes are read after seccomp activation, profile/name mismatches are rejected, and host file/network/process self-tests pass for the minimal profile. All seven format tests pass; memory/CPU/time/output restrictions remain unchanged. Final image after this improvement: sha256:b547c82d6dc046d95137d8255733f152871e88ccd8b777e6c7844ed86c793106. The earlier image digest above identifies the separately tested restart/restore build.

Final Chromium rerun after the parser optimization: **9 passed (1.6m)**. Final image b547c82d passed all seven actual container format profiles and malformed JSON rejection via scripts/verify_document_profiles.py; original downloads matched input bytes and all created documents were deleted. Runtime/source hashes for twelve modules and frontend index matched. The preserved owner stack is healthy, still revision0003, with zero records/users after cleanup. Actual qwen2.5:0.5b CPU chat streamed/persisted again (3 output tokens), then the temporary conversation was deleted. No owner account was created. Original volumes and private backup retained; disposable test volumes/database/credentials removed.
