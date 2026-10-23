# FOXORY Phase 4 continuation — restricted Python execution, incomplete milestone

Branch: development. Starting commit c039f974c357e2bd61e2fc298e696f9cdc26fba3.
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

- **106 backend tests passed in 60.84 seconds**, including the Phase 1–3 suite,
  18 advanced-file/data cases and 28 manager/Computer cases. Real Bubblewrap/
  seccomp tests exercised host-path/network/process/thread/UID/memory/file/output
  denial, invalid JSON/UTF-8/formula artifacts, auth/tenant boundaries, queue/history
  quotas, cancellation, timeout, failed preflight, restart interruption, scoped
  Computer approval, source ZIP integrity and protection against forged stdout
  artifact envelopes. Model prose alone is mocked in the backend agent test.
- **10 Chromium browser journeys passed in 1.4 minutes**, including all nine prior
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
- Local overlay image **sha256:dc11666d7a4fef17c6ee4427d62f51ae02fca9cbbfc69cfde7f01916c2c9ec82**
  passed health, default-disabled execution, authenticated memory persistence across
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

After that successful browser/Docker run, final review fixed Computer idempotency:
semantically identical resubmissions now preserve the exact running claim, and
keys belonging to non-Computer jobs cannot convert those jobs. A new regression
case passed in the 106-test rerun. The following browser rerun had nine passes and
one expected HTTP429 under the unchanged 180/minute limiter; test traffic pacing
is being verified. The earlier overlay image predates this last API fix and is
being rebuilt/rechecked before final verification is recorded.

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
