# Project status — 2026-10-23

**Community Edition 0.1.0 pre-release. Target v1.0 is incomplete.** A functioning foundation increment is implemented; no entire master-directive phase is marked complete. The application is for one trusted local owner, not organizational or public deployment. Nothing was published or deployed externally.

Branch: `development`. Initial preserved checkpoint: `101f114`. Final verification/status commit is reported in the execution response and Git history (a commit cannot contain its own final hash).

## Implemented features

- React + strict TypeScript frontend connected to FastAPI: safe Markdown, code highlighting, dark/light themes, responsive navigation and original interface.
- Ollama availability/model selection, inventory, metadata/capabilities, explicit model download and confirmed deletion. No paid provider or external inference fallback.
- Streaming chat, stop, regeneration, persistent/searchable history, rename/delete, system instructions, context setting, Ollama token metadata and Markdown export.
- PostgreSQL Compose persistence and SQLite native development, Alembic 0001/0002 migrations, real operational dashboard and JSON workspace export.
- PDF/DOCX/XLSX/CSV/TXT/Markdown/JSON upload extraction, bounded validation, isolated random storage names, original downloads, keyword retrieval and evidence-context questions.
- Experimental two-search SearXNG research with deduplicated retrieved reference metadata, checkpointed progress, report export and citation-identifier filtering. Search snippets are not full-page or factual verification.
- Sequential Model Council: independent analyses followed by comparison/synthesis; no consensus-as-truth claim.
- Nine configurable draft-only agent templates with no execution tools. Durable read-only inference jobs, idempotent submission, pause/resume/cancel, step timeouts, restart recovery and bounded manual retries.
- Editable project/memory records, basic leads/status/follow-up dates, database-enforced duplicate prevention and CSV export with formula protection.
- Business drafts, immutable approval snapshots, one-time approve/reject decisions, audit events. Approval records review only and cannot send, publish, purchase or execute anything.
- Local-only Compose binding, non-root/read-only app container, persistent volumes, generated private secrets, required owner token, host/origin/body/rate controls and content-minimizing structured application logs.
- Installation/configuration/development/security/contribution documentation, Apache-2.0 original source license, dependency inventory/notices, CI and owner-invoked review-artifact workflow. Hosted workflows have not run.

## Verification actually executed

| Check | Result and scope |
|---|---|
| Backend | **21 passed**, latest run 9.62 seconds, including malformed bearer token handling, host/origin/auth rejection, persistence, SSE/error/regeneration, deletion, upload validation/parsers, CSV formula protection, concurrent duplicate jobs/leads, approval snapshot enforcement, cancellation of active research coroutine, retries, checkpoint recovery, serialized Ollama protocol and SearXNG metadata adapter |
| Migrations | SQLite upgrade/repeated upgrade/data preservation/downgrade/re-upgrade passed; duplicate preflight leaves schema/data unchanged and allows later successful upgrade. PostgreSQL startup reached revision **0002** |
| Frontend | Strict TypeScript/Vite production builds passed; JavaScript split into approximately 263/178/168 kB chunks |
| Browser integration | **5 Playwright Chromium tests passed** in final rerun (48.8 seconds): streaming/persistence/regeneration/export, document upload/Q&A/rejection, draft approval, sequential council and mobile navigation/layout. Uses a labeled local Ollama HTTP fixture, not model quality evidence |
| Docker | Multi-stage image built with trusted CA mounted as a build secret. Compose CPU/GPU configurations validated. App + PostgreSQL + Ollama ran locally; app healthy under UID/GID **10001**, read-only root filesystem and dropped capabilities. Final rebuilt image **4713ce74119c** started successfully; PostgreSQL record survived container replacement, frontend HTML delivery and malformed-bearer rejection passed, and live CPU chat passed again |
| Local installation smoke | Health, unauthenticated rejection, authenticated create/read/delete passed against Compose/PostgreSQL |
| PostgreSQL restore | Custom-format pg_dump restored into a disposable database; original test record and revision 0002 verified; disposable database removed |
| SQLite backup/restore | Database and original uploaded-file roundtrip passed in automated tests |
| Real inference | **Passed CPU smoke** using Ollama **0.13.5**, **qwen2.5:0.5b**, context 2048: streamed and persisted a nonempty response; Ollama reported **3 output tokens**. No accuracy, throughput, NVIDIA or reference-machine benchmark claim. Model license text contained Apache License Version 2.0 |
| Advisory/consistency checks | npm audit: zero known advisories; pip-audit: zero known advisories for 35 pinned runtime packages; pip check: no broken requirements. Dated checks, not proof of security |
| Secret handling | Generated .env, virtualenv, data, node_modules and build output excluded from Git. No real private credentials committed |

## Failures discovered and corrected

- Dependency installation was initially blocked by sandbox network permissions; succeeded after the environment policy changed.
- Fixed setuptools discovering migrations as a package, malformed JSX, nullable metadata, stale draft list and mixed document/chat UI state.
- Cancellation originally discarded a late result but left inference running; now cancels the active coroutine and protects state with optimistic writes.
- Replaced non-atomic duplicate checks with database uniqueness; approval decisions use compare-and-swap.
- Added migration duplicate preflight before DDL to avoid a partially changed SQLite schema.
- Fixed container source ownership so non-root startup can read source/migrations/config.
- First cloud Docker build failed without its trusted CA; subsequent builds retained TLS verification and mounted the CA only during build.
- Repeat browser testing encountered a port conflict and one login-hook timeout under concurrent build load. Moved the test server to 8001, stopped superseded builds, and the complete five-test rerun passed.
- Cloud BuildKit also encountered an inactive-session timeout during overlapping superseded builds; a single retry built successfully.
- Cloud Docker VFS filled the 32 GB filesystem while duplicating the Ollama image. Removed unused task build cache/superseded failed app artifacts; preserved all persistent volumes and source. Avoid recreating the large Ollama container unnecessarily in this environment.
- Fixed the smoke script interpreting a successful empty 204 response as JSON.
- Ollama CLI initially used bind address 0.0.0.0 through the cloud HTTP proxy; explicitly addressed 127.0.0.1 for the local CLI, retained HTTPS proxy for downloads and trusted the cloud CA in this disposable test container. Model pull and CPU inference then passed.

## Security and release limitations

Single-owner bearer token only: **no password accounts, session expiry, RBAC, multi-user or workspace isolation**. One API process/replica only; recovery assumes that topology. Parser execution uses threads, not resource-isolated subprocesses. No encryption at rest. Audit logs are not administrator-tamper-proof. Rate limits are per-process/IP. Python strict typing/domain normalization remain incomplete. Image/system/native-library license review, SBOM, digest pinning, independent security review, load/accessibility/adversarial tests and hosted CI remain open.

No live SearXNG service was verified; protocol behavior is tested with fixtures. No full-page retrieval, robots handling, fact/quotation verification, semantic embeddings/pgvector, OCR, calculated spreadsheets, generated office documents, CRM import/relations, recurring scheduler, task-dependency graph, tool-enabled delegation, email connectors, financial execution, browser/computer sandboxes, Git/code execution or PR automation. These capabilities are unavailable rather than represented by fake functional controls. Computer control and outbound email remain disabled/unavailable.

Linux cloud CPU smoke is the only measured inference configuration. Windows, macOS, NVIDIA/RTX 3060, the stated i5 reference machine, larger model quality/performance and parallel council execution are unverified. Apache-2.0 applies to original source, not every dependency/model/image; LGPL/MPL and bundled native/OS terms require final distribution review.

Final local image: `sha256:4713ce74119c34c8c3d60bd919353cee94cd120372c7c71d450962f2db1347b1`. PostgreSQL and Ollama named volumes were preserved through final app replacement. App, database and Ollama remain local only; no ports other than the loopback app port are published.

## Next development action / continuation prompt

Continue in `foxory-intelligence` on `development`, preserving existing commits. Read this status, ROADMAP.md and SECURITY.md first. The final Docker restart result is recorded in docs/VERIFICATION.md. Close Phase 1 security gates before adding autonomous tools: implement typed user/session/workspace/RBAC models with migrations, password hashing or local OIDC, session revocation, per-workspace repository/service scoping and cross-user authorization tests. Retain local-only defaults and zero external side effects. Then isolate parsers and complete SSRF-safe, robots-aware full-page research with a real local SearXNG integration test. Do not enable public deployment, paid APIs, email sending, privileged containers or Docker socket access. Update status with executed checks and commit each reviewable increment.
