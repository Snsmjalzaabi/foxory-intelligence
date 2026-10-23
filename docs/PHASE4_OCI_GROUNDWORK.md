# Phase 4 final continuation — OCI groundwork, milestone still incomplete

Starting commit: `c537174d6d76af845af724f78ed8aea3eef6bd96`; branch `development`.
This increment preserves the existing Python execution profile and application
behavior. Phase 5 has not started. No production readiness is claimed.

## New implementation

- Read-only cgroup-v2/delegation and rootless-runtime diagnostics, available via
  authenticated manager health and `scripts/verify_sandbox_host.py`. Static success
  never enables execution or asserts verified isolation.
- Typed, bounded browser-action and JS/TS source schemas; fixed rootless Podman
  command policy requiring an immutable local image, non-root UID, read-only root,
  isolated namespaces, no network/proxy inheritance, CPU/memory/PID limits and
  manager-selected source/request mounts. No Docker socket or host shell added.
- Staged OCI entrypoint for dependency-free JS, Node 22 TS type stripping and an
  offline Playwright fixture site: navigation, inspection, typing, clicking,
  screenshots and selected downloads. Chromium sandbox is mandatory; external
  navigation and non-GET/HEAD requests are rejected. Runtime package installation
  is unsupported. Optional image recipe requires a reviewed immutable base.
- An opt-in fixed-fixture Ubuntu OCI integration probe for effective limits,
  JS/TS, browser interactions and cleanup; blocked-path execution tested here,
  successful host execution pending.
- Ubuntu verification instructions in `docs/SANDBOX_HOST_VERIFICATION.md` and
  explicit activation prerequisites in `sandbox_manager/runtime/README.md`.

**The new workers are not connected to dispatch and are not verified functional
product features.** Missing engineering, independently of this host: active OCI
preflight, manager timeout/whole-container cancellation and restart cleanup,
parent-side artifact validation, approval-bound dispatch, Computer Mode profile
selection/screenshots and end-to-end workflows. Existing browser/JS capability
flags remain false. Passing command/schema tests is not sandbox assurance.

## Verification in this increment

- Backend final rerun: **115 passed (40.47 seconds)**, including nine new
  capability/policy/blocked-probe tests. Existing
  real Bubblewrap tests and migration/regression tests remain included.
- Frontend production build: passed; Node worker syntax check: passed.
- Docker Compose configuration validation: passed.
- Host preflight: correctly exits **2**; cgroup delegation is read-only and
  `podman`, `newuidmap`, `newgidmap` are missing. No host policy was altered.
- Chromium UI journeys: **10 passed (2.7 minutes)** against real HTTP backend
  and real Python manager, with fixture models. These cover chat, documents,
  research, council, authentication/workspace isolation, agents, immutable approvals
  and Computer Mode Python execution; not the new OCI browser worker.
- Actual local Ollama `qwen2.5:0.5b`: failing Python project exit 1 blocked
  packaging; model-repaired project exit 0 completed after two approvals; ZIP
  integrity and persisted account/session/task restart passed. Reviewed acceptance
  tests were deterministic. This is a Python integration, not JS/browser evidence.
- Docker smoke passed against the existing Phase 4 Python image
  `sha256:09b8a43da99e13852b7d7432c82c7deaa8f01c055c97a67c7872264b0059d256`:
  health, disabled defaults, restart/memory persistence, runtime source and UI
  hashes, non-root/read-only/init/no-socket settings. No new OCI image or fresh
  canonical application image was built. Disposable smoke resources were removed;
  owner containers and persistent data were preserved.
- Actual isolated Playwright/JS/TS execution and new OCI image build: **not run**.
  No GPU or Windows/macOS verification.

## Exact next continuation

Continue on development from this increment. Preserve Python behavior. Implement
an OCI manager adapter using `sandbox_manager/oci.py`, with active effective-limit
probes and fail-closed opt-in; whole-container cancellation/cleanup/recovery;
independent bounded artifact validation; then integrate approval-bound profile
execution and Computer UI controls. Run the controlled-site and JS/TS project
workflows on an Ubuntu host that passes static and active isolation tests. Do not
activate profiles merely because the static host script exits zero. Complete the
unchecked Phase 4 acceptance criteria before Phase 5.

---

# FOXORY Phase 4 continuation — restricted Python execution, incomplete milestone

Branch: development. Starting commit c039f974c357e2bd61e2fc298e696f9cdc26fba3. Main implementation
commit cc07602; the following verification commit records the final checks and
artifact/test-fixture fixes. Use git log -1 for its exact hash.
Accepted Phase 3: ca90bcae299031a8393ba338f24f625864d5068e; full evidence in
docs/PHASE3_STATUS.md. First Phase 4 increment preserved in docs/PHASE4_INCREMENT1.md.
Phase 5 has not started; v1.0 and production readiness are not claimed.

## Implemented in this continuation

- Separate opt-in authenticated manager with rootless Bubblewrap namespaces,
  seccomp, hard single-process Python limits, network denial, immutable sources,
  fixed bounded output files, trusted-parent artifact collection/hash validation,
  output capture, cancellation/cleanup, durable scoped JSON state and startup
  recovery that never silently replays interrupted code.
- Preflight tests the real namespace/seal before enabling the service. Non-root,
  configured key, runtime dependencies and explicit opt-in are required. No host
  Docker socket or application shell execution was added. One manager process per
  private state directory, one active execution, bounded queue and history quotas.
- `sandbox.python` requires explicit agent grant, sandbox.execute permission,
  immutable administrator approval and a persisted one-invocation dispatch grant.
  Manager idempotency survives backend retries/restarts and shared-key rotation.
  Changed/rejected/stale contexts remain blocked by existing checks.
- Computer Mode connects real agent configuration/task submission/model planning,
  optional reviewed source, plans/timelines/live logs, approvals, pause/cancel,
  diagnostics, reports, output downloads and source ZIP packaging. Computer ZIP
  packaging requires the latest successful run of identical source plus its own
  approval. A zero process exit does not prove the tests are adequate.
- Authorized uploaded CSV analysis with deterministic grouping/statistics, CSV
  output and escaped SVG chart. The document must be explicitly scoped and both
  documents.read and calculate permissions are required. Approval-gated PDF report
  and chart/results ZIP workflow tested with actual parsers and file writers.
- Optional environment configuration, dedicated-user systemd example, service
  boundary/limitations documentation and distribution-runtime license inventory.

## Executed verification

- **106 backend tests passed in 36.89 seconds**, including the Phase 1–3 suite,
  18 advanced-file/data cases and 28 manager/Computer cases. Real Bubblewrap/
  seccomp tests exercised host-path/network/process/thread/UID/memory/file/output
  denial, invalid JSON/UTF-8/formula artifacts, auth/tenant boundaries, queue/history
  quotas, cancellation, timeout, failed preflight, restart interruption, scoped
  Computer approval, source ZIP integrity and protection against forged stdout
  artifact envelopes. Model prose alone is mocked in the backend agent test.
- **10 Chromium browser journeys passed in 1.8 minutes**, including all nine prior
  regression journeys and Computer Mode against a separately running real HTTP
  manager and actual Python unittest execution. Ollama is a labeled deterministic
  protocol fixture in browser tests; this does not verify a product browser agent.
- Strict TypeScript/Vite production build passed in **18.31 seconds**; main JS
  295.86 kB. Compile checks, pip check, whitespace and CPU/GPU Compose syntax passed.
  GPU syntax validation is not GPU execution. CI was updated, not remotely run.
- Real **qwen2.5:0.5b CPU** generated Python source and repaired an intentionally
  broken addition implementation using actual sandbox failure output. Reviewed
  deterministic unittest/independent acceptance checks were used because the 0.5B
  model did not reliably generate a complete test scaffold. Failed code exited1,
  consumed only its execution approval and was blocked from packaging. Corrected
  code exited0, passed tests, consumed execution plus packaging approvals, and
  produced a byte-checked/CRC-valid source ZIP. Real model review/consolidation
  completed; the authenticated session and completed task survived native app
  restart. No frontier-model capability, fully autonomous test generation or GPU
  performance is inferred. Disposable native app/manager/database were removed.
- Actual public retrieval from https://docs.python.org/3/library/unittest.html
  succeeded through the existing robots/SSRF/TLS controls. A one-page **2358-byte
  PDF** was parsed and checked for its actual retrieved citation URL. Saved content
  hash: 0d2d0e4dabaa644dbf1476e38443b18c49a31d2e9e359f17be975a9c263b6ecf.
  This is source-handler/report integration, not a new autonomous multi-agent
  research-quality benchmark or a browser demonstration.
- Local overlay image **sha256:09b8a43da99e13852b7d7432c82c7deaa8f01c055c97a67c7872264b0059d256**
  passed API and Docker engine health, default-disabled execution, authenticated memory persistence across
  restart, frontend bundle and five runtime-source hashes, actual UID10001,
  read-only/init/cap-drop and no Docker-socket mount checks. The overlay reused
  the accepted Phase 3 dependency image; no clean canonical Dockerfile build or
  container-to-native-manager topology is claimed. Disposable container/volume
  were removed; the image remains available locally.
- Owner Compose app/database remained healthy, Ollama running, application image
  stayed phase3-final and PostgreSQL remained revision0003 with zero records/users.
  No schema change was introduced. SQLite migration upgrade/downgrade/preservation
  tests and native completed-task/session restart passed. No new PostgreSQL dump/
  restore, manager process-crash escape audit or reference hardware test was run.

Final review also fixed Computer idempotency: identical resubmissions preserve
running claims byte-for-byte, and keys belonging to non-Computer jobs cannot
convert those jobs. The regression case passed in the full 106-test rerun.
Unwritten artifact slots are omitted rather than offered as empty JSON downloads.
The paced browser suite completed all ten journeys; the real production limiter
remains unchanged. Its disposable app and manager ports were confirmed closed.

## Failed attempts and corrections

Two migration tests initially failed when invoked from the repository root because
Alembic inherited the wrong working directory (**101 passed, 2 failed**). Tests now
set their backend cwd explicitly; the full final rerun passed without changing
migration behavior. The first Docker smoke run stopped on a test literal expecting
`10001` while the correctly non-root image declared `10001:10001`; the test now
checks the UID component and actual running UID. The rerun passed.

Early real-model JSON code generation returned placeholders; another plain-code
attempt returned fenced prose and omitted imports. Those failed runs were blocked
from packaging, not counted successful. The final harness extracts actual code
fences, uses reviewed deterministic tests and validates real failure/repair output.
A later fast browser run passed nine journeys and received HTTP429 at the final
approval because the shared test IP exceeded the real 180/minute limit. Test
traffic is now paced at at most 150 requests/minute, preserving the production
control. Environment restart orphaned a test manager and caused a port/auth
startup failure; only those identified fixture processes were stopped. The test
server now validates startup HTTP status and handles SIGTERM cleanup explicitly.
The final browser run passed and left neither test port listening.
No security limit was relaxed to pass tests. Earlier Phase 4 increment failures
remain in docs/PHASE4_INCREMENT1.md. Test transports/mocks and real integrations are
explicitly distinguished in docs/SANDBOX_MANAGER.md and the verification scripts.

## Remaining Phase 4 scope / blockers

The current managed account cannot write/delegate cgroups. A general multi-process
Chromium/browser/JS runtime therefore does not have verified aggregate memory/PID/
filesystem limits or constrained networking here. It remains disabled. The Python
profile is deliberately single-process: it denies network, subprocesses, threads,
package installation, temporary file creation and arbitrary output paths. It is
not a replacement for the required browser/JS/TS sandbox.

Outstanding: isolated Playwright navigation/click/type/screenshots/downloads/session
and submission policies; JavaScript/TypeScript runner; static/networked web-app
execution; full combined browser/research/coding workflows; final containerized
manager topology/recovery verification; broader independent sandbox security review.
No GPU, Windows/macOS or production readiness claims. The owner Docker stack and
its volumes remain on the accepted Phase 3 image; disposable tests use separate
native services and state. No public deployment, spending or communication.

See docs/SANDBOX_MANAGER.md and docs/PHASE4_CHECKLIST.md. Next task must preserve
this code and continue Phase 4, starting with a dedicated multi-process sandbox
host/runtime with verified aggregate resource and network enforcement. Do not
run Chromium in the main application or weaken the Python seal as a shortcut.

## Exact continuation point

Continue from development HEAD, inspect this file and docs/PHASE4_CHECKLIST.md;
preserve the accepted Phase 1–3 work and the verified restricted Python subsystem.
Next provision a dedicated Linux sandbox host/runtime with delegated aggregate
RSS/PID/disk/network enforcement. Implement isolated Playwright and JS/TS workers
behind the authenticated manager, domain/method/session/download controls and
immutable approval for consequential actions. Connect screenshots and browser
steps to Computer Mode. Demonstrate controlled-site browser tasks and a tested
web app, then combined research/data/coding/browser workflows with local models.
Run full regression, final-image, migration and recovery checks and commit evidence.
Do not weaken the single-process Python profile, expose an application Docker
socket, publish/deploy externally, or advance to Phase 5 until Phase 4 is complete.
