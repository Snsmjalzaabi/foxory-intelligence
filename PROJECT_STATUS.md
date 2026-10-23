# FOXORY Intelligence — Phase 4 connected OCI profiles, host acceptance pending

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

- Backend final full run: **141 passed (47.16 seconds)**, including real Python
  sandbox tests, SQLite migrations and mocked OCI lifecycle/approval/tenant cases.
- **11 Chromium UI journeys passed (2.2 minutes)**. Existing Python execution
  uses real Bubblewrap/seccomp. The additional JS packaging/browser screenshot
  journey uses the explicit test-only mocked OCI boundary, with real HTTP manager,
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
  pending. No worker image was pulled/built here: the large base does not fit the
  available disk budget safely alongside owner data.

During development, the regression suite exposed repeated shutdown cancellation
interrupting Python process-map cleanup (128 passed, 3 teardown errors). Cleanup
is now shielded and repeated cancellation is guarded; the subsequent full 136-test
run passed. No isolation controls or tests were weakened.

## Pending final verification results

Current-source application overlay image built and verified:
`sha256:a293a9e17dec724854bae71015ebd0ddacf5bd9079fa8ded8e9ad454c57aac05`.
Health, default-disabled execution, memory persistence after restart, source/UI
hashes, actual non-root UID, read-only filesystem, init/cap-drop and absence of
runtime socket mounts passed. This reuses the accepted dependency image; it is
not a fresh canonical Dockerfile build or a worker-image isolation test. Disposable
smoke resources were removed. PostgreSQL and real local-model rerun results will
be recorded after execution. Owner containers/volumes remain untouched.

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
