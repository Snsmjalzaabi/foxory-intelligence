# FOXORY Intelligence — core product recovery; Phase 4 acceptance still pending

## Latest continuation: independent core and sandbox CI gates

On 29 October 2026, Cloud and GitHub development both matched `4b57d90` before
edits. Actual GitHub workflow `40038556044` was reviewed through its job logs:
**139 passed, 17 real sandbox fixture setup errors**. The namespace isolation
preflight failed on the hosted runner, and all frontend/build/install checks were
consequently skipped. Prior local success was not a hosted-CI success.

CI now has separate core (Ubuntu 24.04) and sandbox (Ubuntu 22.04) jobs. Both
contribute to overall workflow status; repository branch-protection settings are
unchanged. The default pytest command still runs all tests. A registered
`sandbox_runtime` marker selects the 17 tests requiring actual Bubblewrap; no
test is silently mocked/skipped or security policy weakened. Core includes the
remaining 139 tests, parser/authorization/default-disabled guards, manager-free
browser journeys, real PostgreSQL migration/restore and a new pristine Compose
installation harness. Sandbox still requires actual preflight/attack/cancel/
approval tests plus real Python and explicitly mocked OCI UI journeys.

`scripts/compose_smoke.py` creates a generated project name, independent secrets,
loopback port and fresh app/database/model volumes, uses the canonical Dockerfile
with `--build`, and removes only its own resources. It checks account creation,
Ollama availability without downloading weights, disabled execution, restricted
documents/invalid uploads, tenant download isolation and account/session/records/
originals across restart. It never reads the owner's .env or connects to the
owner installation. An explicit reviewed `--image` supports noncanonical checks.

Local verification of this CI change: **156 tests passed (45.60s)**; selection
identifies all 17 real-runtime tests separately. Compose harness syntax/CLI and
whitespace checks passed. Actual hosted jobs/pristine Compose execution are
pending the push; no fresh successful installation claim is made from script
existence. Existing Cloud disk limits are not worked around by deleting owner
data. Phase 4 remains incomplete; Phase 5 has not started.

## Current recovery increment

Branch: `development`. Before edits, the clean Cloud checkout, configured private
GitHub origin and actual remote development ref all matched
`aab7884e6a598f4cde1d9f06d4342cc20fb0be08`. The owner's supplied Ubuntu pull reached
that same commit; the pasted master directive's older Git-discrepancy assumption
was superseded by these checks. No history rewrite, reset, branch deletion or
unrelated repository modification was needed. GitHub remains canonical/private.

The owner subsequently supplied actual Ubuntu fixed runtime passes for JavaScript,
TypeScript and sandboxed Chromium on image
`sha256:248d4afc67fe3b0845b2cedd239d5b378eba4b0ad19e344891fb5fc0873ddbcb`.
See [the scope of that host evidence](docs/UBUNTU_OCI_RUNTIME_EVIDENCE.md).
Application execution stayed disabled. Full host security/recovery acceptance
remains pending; **Phase 4 is incomplete and Phase 5 has not started**.

### Core usability and feature matrix

Core chat/research/documents/accounts/Council/safe agents run independently of
Computer Mode. Default Compose has only app, PostgreSQL and Ollama, with loopback
web binding and persistent volumes. No execution OS account, Podman, sandbox
manager or delegated cgroups are needed for ordinary core installation.

| Capability | Status and evidence | Remaining limit |
| --- | --- | --- |
| Account setup, login/logout, workspace isolation | Implemented and verified: real disposable HTTP workflow plus API/browser authorization tests. | Local single-process deployment; not independently security-reviewed public hosting. |
| Ollama chat, model selection/history/export | Implemented and verified: actual qwen2.5:0.5b, persisted stream/history, Markdown download; stale-model/no-model UI repaired. | Selector still includes embedding-only models: inspect capabilities and select a completion model. Other runtime protocols not verified. |
| Web search and cited answers | Implemented and verified with actual Wikipedia API/public-page retrieval, saved source hashes and IDs. Uncited model prose now falls back to labeled source excerpts. | Default discovery is encyclopedia-scoped; citation validity is not claim truth. Live SearXNG is implemented but unverified in this increment. |
| Deep Research/history/reports | Implemented and verified: actual model planning, two searches/two pages/three model calls, pause/resume, duplicates/cancel, checked citations and PDF/Word/XLSX. | Tiny-model synthesis used extractive fallback. General research usefulness needs broader evidence/model evaluation. |
| Document intelligence | Implemented and verified: real isolated TXT parsing, JSON rejection, local nomic embeddings/Q&A; seven-format parsing/security regressions. | Linux sealed parser; OCR/macros/formula execution missing or intentionally unsupported. No unrestricted document execution. |
| Model Council | Implemented and verified: actual qwen2.5:0.5b + smollm2:135m independent analysis/comparison/synthesis, sequential. | Consensus is not factual verification; GPU/parallel performance unverified. |
| Safe agents and workspace memory | Implemented and verified: actual model arithmetic plan/tool result; actual web-search tool and model review with an explicit research plan. | Complex autonomous task quality remains experimental; model errors are bounded and visible. |
| Safe scheduling | Implemented: current unit/browser schedule controls and prior accepted real Phase 3 execution evidence. | Fixed intervals, one API process; real timed dispatch not rerun in this increment. |
| Persistence/recovery | Implemented and verified: real session/history/research process restart and consistent disposable SQLite snapshot restore. | Full final Ubuntu application/manager backup/restore acceptance remains pending. |
| Core Docker installation | Implemented, partially verified: Compose syntax and disposable source-overlay container health/persistence/hardening. | Fresh canonical Dockerfile + full new Ubuntu installation not rerun; overlay is not a canonical build. |
| Optional Computer Mode | Experimental and disabled by default. Real Ubuntu fixed JS/TS/browser probes supplied by owner; real Python + mocked OCI UI/lifecycle regressions in Cloud. | Live-manager tenant/approval, exhaustion, cancellation/orphans/recovery and combined model workflows still pending on Ubuntu. |
| Business modules | Existing optional secondary records/drafts preserved; no business-specific expansion. | No email sending, purchases or publication implementation. |
| Public browsing/submissions and production release | Disabled/unsupported; v1.0 and Phase 4 completion not claimed. | Security review, image SBOM/CVE/license review, broader compatibility and host acceptance remain outstanding. |

### Repairs and current evidence

The live audit exposed Search chat displaying inaccurate, uncited small-model
prose despite retrieved pages. Search/document chat now share Deep Research's
reference check and extractive fallback; empty document evidence skips inference.
Numeric citation examples reduce literal `[N]` output. This guards reference
integrity, not every claim's factual correctness. New unit/API regressions cover
uncited/forged evidence, release/persistence and bounded output requests.

Model refresh now recovers removed selections and prunes unavailable Council
choices. A connected empty installation has a visible model-setup action. Login
explains the private bootstrap token, Documents precedes Computer, Computer is
labeled optional, and Settings states that core tools work independently. A real
response-budget control reaches the validated local inference request. No new
runtime dependency, service, schema or paid provider was introduced.

The strict real acceptance harness, `scripts/core_acceptance.py`, passed **14
checks** with actual local qwen2.5:0.5b, smollm2:135m and nomic-embed-text:latest;
no model/web fixture and no sandbox manager. Evidence with actual public source
URLs/hashes is saved in [core-acceptance.json](docs/evidence/core-acceptance.json).
It uses private disposable SQLite/files, an ephemeral loopback API and already
installed models. The owner application/database/credentials are not accessed; the explicitly
supplied existing Ollama endpoint serves local inference.

The initial exploratory harness did not assert citation validity; its successful
exit is not full core acceptance. Its uncited result prompted the stricter checks
and fix. A targeted browser regression also failed before stale-model recovery was
fixed. These failures are retained in [the recovery report](docs/CORE_PRODUCT_RECOVERY.md),
along with eight inspected UI screenshots, architecture findings and limits.

Final checks executed for this increment:

| Check | Result and scope |
| --- | --- |
| `.venv/bin/pytest -q backend/tests` | **156 passed (71.72s)**: API, grounding, auth/tenant, approvals, jobs, migration and parser/security regressions. |
| `FOXORY_E2E_SANDBOX=1 FOXORY_E2E_OCI=1 npm run test:e2e` in frontend | **13 passed (2.3m)**: actual HTTP UI, fixture Ollama, real restricted Python and explicitly mocked OCI. Intermediate response-budget selector failure was corrected; no timeout/security relaxation. After the final mobile copy-layout fix, the focused mobile journey passed again (13.5s). |
| Core-only browser run | **10 passed, 3 optional tests skipped (2.1m)** without manager; prior to the final response-budget UI addition. Final core independence is also checked by the real native harness. |
| `npm --prefix frontend run build` | Strict TypeScript/Vite passed (7.35s), final main JS 299.98kB. |
| `scripts/core_acceptance.py --ollama-url OPERATOR_LOCAL_OLLAMA` | **14 actual local-model/public-web checks passed**, no model/web/OCI fixture, sandbox disabled. SQLite restart/restore and logout/login included. |
| `scripts/phase4_docker_smoke.py --build --image foxory-intelligence-app:core-recovery` | Passed backend-current overlay image `sha256:e3ddcd099ef22077a043eab8af34df878e452b26f345e46d1609490421d4f13b`: health, disabled sandbox, persisted memory, core/agent source and frontend hashes, UID10001/read-only/init/cap-drop/no socket. Disposable container/volume removed. This is not a fresh canonical build; its frontend snapshot predates the final mobile paragraph-layout adjustment, checked separately. |
| `scripts/phase4_postgres_smoke.py` | **Blocked, not passed**: first readiness failure; diagnostic retry exited with `initdb` ENOSPC creating pg_wal, before migrations. Both disposable containers/volumes removed. Existing accepted PostgreSQL evidence below is historical only. Rerun on sufficient container storage; do not remove owner volumes. |
| Other checks | CPU/GPU Compose syntax, pip dependency consistency, offline worker input integrity, Node syntax, Python compilation, documentation shell syntax and whitespace passed. No GPU runtime or fresh dependency/image security audit. |

Structured evidence: [real core](docs/evidence/core-acceptance.json),
[Docker overlay](docs/evidence/core-docker-check.json),
[PostgreSQL blocker](docs/evidence/postgres-recovery-check.json).
No owner application/database records were accessed by these disposable harnesses.
The authorized local Ollama endpoint was used for actual inference. Prior
increment evidence below remains historical, not rerun claims.

### Continuation and Phase 4 boundaries

Use normal GitHub fast-forwards, not bundles when authenticated push is available.
On Ubuntu, pull development and install/upgrade the core through the documented
Compose workflow with sandbox enablement off. Review larger local completion
models and broader search quality when resources permit. Do not redo already
passing rootless provisioning/Chromium diagnostics. Continue the remaining
host-only checklist for security, cancellation, orphan/restart handling and actual
integrated Computer Mode workflows, keeping optional execution disabled until
accepted. No Phase 5/public release/production readiness claim is justified.

## Historical Chromium correction increment (before owner runtime evidence)

### Original browser-only chroot implementation record

Branch: `development`. Baseline: `d5503e8f785571a146444666b873f13789c60517`.
Phase 4 remains **incomplete**; Phase 5 has not started. The operator reports
rootless Podman/delegation/static checks and an immutable image build on Ubuntu
26.04, with JS/TS apparently passing before Chromium fails at
`sys_chroot("/proc/self/fdinfo/") == 0`. This is supplied host evidence, not a
successful rerun of the correction.

Upstream Chromium uses that chroot to remove filesystem access. Upstream
containers/common seccomp conditions chroot allow/deny on `CAP_SYS_CHROOT`;
dropping every capability can therefore deny the syscall even inside Chromium's
nested user namespace. AppArmor or a different installed seccomp policy may
still deny it. The assertion alone does not establish the actual errno/cause.

Implemented a required validated profile in the shared OCI command builder:
only browser adds `--cap-add=SYS_CHROOT` after `--cap-drop=ALL`. Authenticated
manager dispatch and fixed probes both pass that profile. JS/TS command policies
remain identical to each other and retain every previous restriction. No
privileged mode, SYS_ADMIN, no-sandbox, unconfined policy or resource relaxation.
The Python profile, image inputs, dependencies, approvals and data are unchanged.

Both code-profile fixtures now check all five capability masks are zero,
NoNewPrivs=1 and Seccomp=2, plus existing effective quota/filesystem/network
checks. The verifier emits separate stderr pass markers without corrupting its
machine-readable stdout; browser failure cannot report overall success or enable
execution. No automatic activation was introduced.

Verification executed for this increment in Codex Cloud:

- `.venv/bin/pytest -q backend/tests`: **148 passed in 57.86 seconds**, including
  policy equality/negative cases, authenticated dispatch, probe command building,
  partial failure reporting and existing migration/security/recovery regressions.
  OCI execution is explicitly mocked in these tests; it is not isolation proof.
- `npm --prefix frontend run build`: passed strict TypeScript and Vite build
  (14.50 seconds). No frontend source changed. The previous 12 UI journeys below
  are historical evidence, not rerun results for this increment.
- Offline worker supply-chain verification: passed, pinned inputs unchanged.
  Node worker and fixed JS probe syntax, Python compilation, documentation bash
  syntax and `git diff --check`: passed. Bash procedures were parsed, not run.
- Actual rootless Chromium/JS/TS, image rebuild, Docker integration and local-model
  workflows were **not rerun** for this correction. Known Codex host limitations
  were not re-probed. No Ubuntu runtime success or production readiness is claimed.

Security implications, exact changed-file manifest, source references, update
transfer and dedicated-account Ubuntu rebuild/reverification commands are in
[CHROMIUM_SANDBOX_UBUNTU.md](docs/CHROMIUM_SANDBOX_UBUNTU.md). Keep OCI disabled
until fixed probes and the full remaining host acceptance checks pass. If the
browser still fails, retain logs and inspect installed seccomp/AppArmor denials;
do not weaken isolation. Next action: transfer this commit to the Ubuntu owner's
checkout, refresh the dedicated account's tracked source without replacing its
virtualenv/state, rebuild and run the fixed verifier in the delegated scope.

## Preserved evidence from the prior connected-OCI increment

Branch: `development`. Starting commit:
`09b707da144b72e481117ce7b0dd19cfef96bb73`.
Phases 1–3 remain accepted; Phase 5 has not started. Phase 4 is **not complete**
and production readiness is not claimed. Prior evidence is preserved in
[the previous increment](docs/PHASE4_OCI_GROUNDWORK.md) and
[Phase 3 status](docs/PHASE3_STATUS.md).

## Implemented in this continuation

- Authenticated manager dispatch for JavaScript, Node type-stripped TypeScript
  and offline Playwright, sharing the existing single execution slot with Python.
  New profiles require explicit operator opt-in, an immutable local worker image
  and active startup probes; defaults remain disabled. No host-code fallback.
- Rootless OCI create/attach lifecycle with source-only read-only mounts, network
  denial, fixed CPU/memory/PID/tmpfs quotas, engine and manager wall deadlines,
  bounded streamed logs, status persistence and whole-container cancellation.
- Ownership labels restrict removal to this manager/task. Cleanup must establish
  absence before reporting completion. Failures quarantine OCI execution. Startup
  and periodic reconciliation detect owned orphans; interrupted records remain
  auditable without silent code replay. Foreign containers are not removed.
- Shared artifact validation: fixed names, exact metadata, base64/size/SHA-256,
  UTF-8, strict JSON, safe CSV cells, bounded PNG structure/CRC/decompression.
  Download APIs revalidate bytes and owning workspace/job/approval-derived manager
  ID, prevent cross-workspace access, audit downloads and set no-store/nosniff.
- Explicit agent tool scopes and immutable expiring approval gates for all new
  profiles. Failed/interrupted execution stops the workflow and prevents source
  packaging. JS/TS packaging requires successful execution of identical sources.
- Computer Mode profile configuration, availability/limits, reviewed source and
  browser actions, plans/timelines/live logs, approvals, pause/cancel, failures,
  newly approved retry, authenticated screenshot previews and artifact downloads.
- Pinned upstream worker image index, locked Playwright dependency graph, reviewed
  source/build hashes and online registry-byte checks. Optional image recipe has
  no runtime dependency install. Complete Ubuntu setup/security acceptance
  checklist and a separate rootless systemd user-unit example are supplied.

## Verified in Codex Cloud

- Backend final full run: **142 passed (47.58 seconds)**, including real Python
  sandbox tests, SQLite migrations and mocked OCI lifecycle/approval/tenant cases.
- **12 Chromium UI journeys passed (2.4 minutes)**. Existing Python execution
  uses real Bubblewrap/seccomp. The additional JS packaging/browser screenshot
  and failure/retry/pause/cancel journeys use the explicit test-only mocked OCI
  boundary, with real HTTP manager,
  backend, scopes, approval persistence and artifact downloads. Ollama is a fixture
  in browser journeys. These results do not prove actual OCI/browser isolation.
- Combined multi-agent workflow test passed: web/model/OCI fixtures, real durable
  delegation and four approval gates, deterministic calculation, actual PDF
  generation/parsing and source ZIP integrity. No live web/browser task is claimed.
- Frontend strict TypeScript/Vite production build passed; Node worker syntax,
  pip dependency check, CPU and GPU Compose syntax passed. GPU syntax is not GPU
  execution. CI now includes mocked OCI UI journeys and worker input checks;
  remote CI has not been run.
- Worker supply-chain checks passed offline and online: pinned upstream manifest
  digest plus exact Playwright/playwright-core archive SHA-512 integrity. Worker
  image build/runtime, SBOM/vulnerability audit and real-host isolation remain
  pending. The npm bulk advisory query returned no advisories for the two pinned
  packages; this excludes OS/Chromium vulnerabilities. No worker image was pulled/built here: the large base does not fit the
  available disk budget safely alongside owner data.

During development, the regression suite exposed repeated shutdown cancellation
interrupting Python process-map cleanup (128 passed, 3 teardown errors). Cleanup
is now shielded and repeated cancellation is guarded; the subsequent full 136-test
run passed. Final compatibility review also retained downloads of accepted Python artifact
records that predate the explicit workspace field, while checking their scoped
record, consumed approval and workspace-derived manager ID. Rejected approvals
still prevent downloads. No isolation controls or tests were weakened.

## Docker, database and actual local-model verification

Current-source application overlay image built and verified:
`sha256:4c40f0258785d9a7d3fd7192a0914a2264111367064f99c2205a9b32a5fd09aa`.
Health, default-disabled execution, memory persistence after restart, source/UI
hashes, actual non-root UID, read-only filesystem, init/cap-drop and absence of
runtime socket mounts passed. This reuses the accepted dependency image; it is
not a fresh canonical Dockerfile build or a worker-image isolation test. Disposable
smoke resources were removed. A separate PostgreSQL 17 container passed revision
0003 migrations, workspace isolation, duplicate constraints, restart persistence
and custom-format dump/restore; its container/volume were removed. Owner database
and application were not accessed by that harness. Real local-model rerun results
passed with actual `qwen2.5:0.5b`: intentionally failing Python source exited 1
and was blocked from packaging; model-repaired source exited 0 after real tests,
consumed separate execution/packaging approvals and produced a matching CRC-valid
ZIP. Account/session/completed task survived restart. Acceptance tests were
reviewed deterministic tests, not autonomously generated tests. This verifies
Python, not the new OCI worker or GPU performance. Owner containers/volumes remain
untouched.

## Remaining Phase 4 acceptance

Application wiring and deterministic tests are complete. Actual Ubuntu-host
acceptance remains **unchecked** in [PHASE4_CHECKLIST.md](docs/PHASE4_CHECKLIST.md)
and [SANDBOX_HOST_VERIFICATION.md](docs/SANDBOX_HOST_VERIFICATION.md):

1. Build/review the pinned worker image and run actual rootless JS/TS/Chromium
   fixtures; verify effective aggregate controls, Chromium sandbox and artifact
   validity. A static host capability result is never sufficient.
2. Demonstrate real cancellation, deadlines, descendants/staging cleanup,
   manager process-crash/orphan recovery and restart persistence on that host.
3. Exercise malicious inputs, cross-workspace/approval boundaries, network/host
   denial, PID/memory exhaustion and the final manager/container topology.
4. Run actual local-model combined workflows and retain real screenshots,
   calculations, tests, reports and source packages with evidence of each stage.
5. Complete final-image regression, image vulnerability/license review and the
   independent security review appropriate before a proposed public release.

Public network browsing, external form submission, runtime package installation,
privileged tools and remote communications remain unsupported/blocked. The
browser profile is deliberately an offline supplied-site environment. No GPU,
Windows/macOS or production compatibility verification is claimed.

## Prior continuation (superseded by current recovery notes)

Continue on development HEAD. Do not rebuild the architecture or repeat the known
Codex cgroup diagnostics. The next work is the Ubuntu checklist against the pinned
image and connected manager; investigate failures while keeping quotas, namespace
isolation and Chromium sandbox intact. Record actual host evidence before marking
Phase 4 complete. Do not begin Phase 5 or publish/deploy publicly.

## Verification commands executed

```bash
.venv/bin/pytest -q backend/tests
npm --prefix frontend run build
# Run from frontend/:
FOXORY_E2E_SANDBOX=1 FOXORY_E2E_OCI=1 npm run test:e2e
# Run from repository root:
.venv/bin/python scripts/verify_worker_supply_chain.py --online
.venv/bin/python scripts/phase4_postgres_smoke.py
.venv/bin/python scripts/phase4_docker_smoke.py --build --image foxory-intelligence-app:phase4-oci-connected
# The Ollama URL is a discovered local disposable-test connection, supplied by the operator:
.venv/bin/python scripts/phase4_integration.py --ollama-url http://LOCAL_OLLAMA:11434
```

`pip check`, Node worker syntax, Compose CPU/GPU syntax and whitespace checks
also passed. Worker source was reviewed to make output-budget violations fail
explicitly, then syntax/input-integrity checks were rerun. Its runtime path still
requires Ubuntu verification. The optional user-service example is not installed.
No public publishing, production deployment, real communications or purchases.
