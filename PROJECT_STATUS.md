# FOXORY Intelligence — Phase 4 Chromium policy correction, Ubuntu acceptance pending

## Current increment: browser-only chroot capability

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

## Exact continuation

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
