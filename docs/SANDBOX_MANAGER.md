# Restricted Python manager — experimental Linux execution profile

The application never executes generated code or mounts a Docker socket. This
optional service is a separate security boundary and must run under a dedicated
unprivileged OS account. Default configuration disables it. It is not a general
computer/browser sandbox and has not received an independent security audit.

## Boundary and limits

The `python-single-process-v1` profile requires Linux x86_64, Bubblewrap, util-linux
`prlimit`, system Python `/usr/bin/python3`, and libseccomp2. Trusted system runtime
libraries, one task's immutable sources and a fixed bootstrap are mounted read-only.
Host /etc, /home, /workspace, /proc, credentials, other tasks and manager state are
absent. All namespaces are unshared; capabilities are dropped; code is non-root;
no_new_privs and seccomp activate before reading/executing source. Inherited stdin
is /dev/null, descriptors close and environment is replaced. Networking, process
and thread creation, exec, namespace/mount changes, ptrace, cross-process memory,
privilege changes and selected dangerous kernel interfaces are denied.

Hard limits: 512 MiB process address space, 8 CPU seconds, 15 wall seconds, 32 FDs,
1 MiB per file, 128,000 bytes per stdout/stderr stream. Only one untrusted process
exists; no forking/threading is supported, so these process limits cannot be
multiplied by child processes. The manager and Bubblewrap helpers add their own
trusted overhead. This is not a cgroup RSS limit or a proof against kernel exploits.

The root and task source mounts are read-only, including /tmp. Only four existing
output files are writable: `/out/result.txt`, `result.json`, `result.csv`, `result.md`.
Directory creation/rename and unbounded temporary file creation are unavailable.
Artifacts are UTF-8, maximum 20,000 bytes total, separately path/type/base64/hash
validated by the manager (including JSON syntax and CSV formula rejection) and checked again when downloaded. Program logs and output
are untrusted; program exit 0 does not establish test quality or factual correctness.
The service does not execute artifacts, render active HTML/SVG, or unpack archives.

Sources: at most 50 files/20,000 UTF-8 bytes, safe relative ASCII paths and Python
entrypoint supplied in the project. No arbitrary executable, image, mount, URL,
network mode, resource increase or runtime selection is accepted from clients.

## Install and configure deliberately

Install your distribution's `bubblewrap`, `libseccomp2`, `util-linux` and full
`python3` standard library. Install the repository's locked Python dependencies
in a dedicated virtual environment. No new pip package is required beyond those
already used by the backend. Keep service source/bootstrap and runtime libraries
administrator-owned and unwritable by the service account. Give the account only
its private manager state directory. Do not grant sudo or Docker access.

Generate a random shared key of at least 32 characters outside source control.
In a mode-0600 manager environment file, set:

```
FOXORY_SANDBOX_ENABLED=1
FOXORY_SANDBOX_KEY=<your random shared key>
FOXORY_SANDBOX_DATA=/var/lib/foxory-sandbox
```

Run one service process bound to loopback:

```
.venv/bin/python -m uvicorn sandbox_manager.service:app --host 127.0.0.1 --port 8104 --workers 1
```

`deployment/foxory-sandbox.service` is a reviewable systemd example, not an
installed/tested unit. It includes service-level memory/process/CPU limits.
The startup probe must pass under your actual service hardening; do not disable
security settings to hide failures. Unprivileged user namespaces and the relevant
AppArmor/SELinux policy must permit Bubblewrap. Root execution, missing libraries,
probe failure or missing opt-in/key leaves execution disabled. Health requires
authentication and workspace scope and exposes the exact limits and blockers.

For a native backend on the same host, set:

```
FOXORY_ENABLE_SANDBOX=1
FOXORY_SANDBOX_URL=http://127.0.0.1:8104
FOXORY_SANDBOX_KEY=<the same random shared key>
```

Compose passes these variables but does not provision a manager or expose a
socket. Loopback inside the app container is not the host. Connecting containerized
app to native manager requires deliberate private routing/firewall configuration
and verification; it is not validated by the native test harness. The client
permits only explicit local hostnames/IPs, sends no proxy credentials, does not
follow redirects, and keeps manager secrets server-side. Never bind the manager
publicly. Use an authenticated private/TLS transport for cross-host deployment;
that topology is currently unsupported by the default client allowlist.

## Permissions, approvals and UI

Computer Mode can create an explicitly granted restricted Python agent or use
an agent configured with `sandbox.python`/`sandbox.execute` and `source.package`/
`documents.write`. Users submit an objective for model planning or supply reviewed
files. Every execution approval binds the job, objective, plan, agent configuration
and exact source arguments. A consumed approval creates one durable dispatch grant;
manager idempotency keys prevent re-execution across backend retries/restarts and
key rotation. Changed config, rejection, expiration and tenant mismatch fail closed.
No generated code is run from the approval database transaction.

Computer source packaging requires the most recent run to have completed with
identical source hashes. It then requires a second explicit packaging approval.
The final ZIP is inert source, not proof that the test suite was meaningful.
Model outputs cannot grant permissions or authorize other actions. No external
submission, browser, paid service, communication or privileged handler is exposed.

## Lifecycle and operations

One worker at a time, maximum eight pending manager jobs/four per workspace and
500 retained job records. A full history quota rejects new jobs; administrators
must review/archive/remove old terminal manager records while preserving active
records and their idempotency history. Never delete a record while its backend
workflow or dispatch grant can still be resumed; retain it beyond the maximum
workflow deadline before manual cleanup. The app stores bounded final results in its
normal workspace job record. Protect and back up manager state with the application.
There is no automatic history deletion or replay after lost/deleted state.

Manager results are atomic fsync/rename JSON files with scoped ownership; state
files are mode0600 and directory0700. Only one manager may hold the data-directory
lock. JSON audit events contain job/workspace/event/time, not source or keys.
Cancellation kills the namespace process tree, collects exit and removes staging.
Queued work is cancelled too. A manager restart marks prior queued/running jobs
interrupted and does not silently rerun code. The user must submit a new reviewed
run. Backend retries attach to the same existing manager job. Pausing during an
invocation cancels it; resuming the workflow does not repeat that invocation.

## Verification and unsupported capabilities

`backend/tests/test_sandbox_manager.py` launches actual Bubblewrap processes via
an ASGI HTTP transport; model prose alone is mocked in the agent integration case.
It covers the isolation probe, attack cases, limits, auth/tenant isolation,
idempotency, cancellation, restart state, failed preflight and approval-gated
Computer/source ZIP flow. `FOXORY_E2E_SANDBOX=1 npm run test:e2e` launches a separate
real manager HTTP service; Ollama remains a labeled fixture in browser tests.
`scripts/phase4_integration.py` uses an actual local Ollama model and disposable
native services/database; results must be recorded only after successful execution.

## Connected optional OCI profiles

The separate manager dispatches `javascript`, `typescript` and `browser` requests
through fixed rootless Podman commands. `FOXORY_SANDBOX_OCI_ENABLED=0` is the
default. Activation requires explicit opt-in, an immutable local image ID and
passing active startup probes for that image. No repeated host diagnostics are
performed on ordinary health requests. The `profiles` health map reports each
profile's availability, blockers and limits; legacy `enabled` denotes Python.

The manager creates the container before attaching, shares one execution slot
with Python, and labels it with manager/task ownership. Streamed untrusted logs
are bounded. Both engine and manager deadlines apply. Cancellation waits for
whole-container cleanup; startup/periodic orphan reconciliation only removes
owned containers. Failed cleanup quarantines OCI. Interrupted records are retained
without automatic replay. Parent artifact validation and application download
revalidation enforce fixed names, bytes, hashes and job/workspace ownership.

JS/TS are dependency-free and network-denied; TS uses type stripping only. Browser
sessions serve supplied offline website files with only GET/HEAD requests, no
external submissions or public browsing, and Chromium sandbox enabled. Runtime
package installation, arbitrary mounts/flags and privileged execution are blocked.
The main application never runs generated code or mounts a runtime socket.

JS/TS OCI containers drop all capabilities. Only browser containers add
`SYS_CHROOT` after dropping all capabilities, for Chromium's chroot-based
filesystem sandbox and capability-conditioned runtime seccomp policy. All other
restrictions remain unchanged. The correction is awaiting actual Ubuntu runtime
verification; see [the investigation and rebuild commands](CHROMIUM_SANDBOX_UBUNTU.md).

New OCI lifecycle/workflow tests use an explicitly mocked engine. Real isolated
OCI/browser execution remains pending the [Ubuntu checklist](SANDBOX_HOST_VERIFICATION.md).
The manager/worker/image code is connected; mocks are not isolation certification.
Windows/macOS, NVIDIA performance, live networking and independent escape/security
review remain unverified. The existing Python-only system unit is unchanged; the
new optional rootless user-unit example requires host-specific review.
