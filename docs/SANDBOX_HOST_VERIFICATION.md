# Phase 4 Ubuntu host validation — fixed probes passed, full acceptance pending

Application dispatch, lifecycle, artifact validation and Computer Mode are
implemented and tested with a mocked OCI boundary. **Actual rootless Node,
TypeScript and Chromium isolation is not verified in Codex Cloud.** Keep OCI
profiles disabled until this checklist passes. Phase 4 is not complete.

The owner has now supplied an actual Ubuntu fixed-probe pass for all three OCI
profiles and the image build. See [the evidence record](UBUNTU_OCI_RUNTIME_EVIDENCE.md).
That limited success does not check every composite security/recovery requirement
below. Do not repeat already-passing provisioning as a substitute for the remaining
active-manager, hostile-input and recovery tests.

## 1. Provision a dedicated local sandbox account

- [ ] Use Ubuntu Linux with rootless Podman, `uidmap`, cgroup v2, and subordinate
  UID/GID mappings allocated by the host administrator. Record OS, kernel,
  Podman, OCI runtime, systemd and CPU architecture versions.
- [ ] Keep the account dedicated to FOXORY execution. It must not hold owner
  credentials/repositories. Manager state must be private, owned by this account
  and mode 0700; the manager key/environment file must be mode 0600.
- [ ] Use a systemd **user** service/scope with delegated CPU, memory and PIDs.
  `deployment/foxory-sandbox-oci.service` is an unverified installation example.
  Do not reuse the Python-only system unit's TasksMax=32/ProtectHome settings for
  OCI blindly. Rootless mapping helpers may require setuid on the manager host;
  JS/TS workers drop every capability; the browser alone retains SYS_CHROOT for
  Chromium's filesystem sandbox. Privilege escalation remains denied. See the
  [Chromium chroot investigation and exact rebuild commands](CHROMIUM_SANDBOX_UBUNTU.md).
- [ ] Confirm Ubuntu AppArmor/user-namespace policy and the runtime's seccomp
  policy support Chromium's sandbox. If denied, stop and review the policy; do
  not use privileged containers, `--no-sandbox` or seccomp-unconfined.
- [ ] Verify manager loopback-only binding, authenticated API, no main-application
  runtime socket access and a trusted local API-to-manager connection. A bridge
  deployment needs deliberate local firewall/TLS configuration; not tested here.

Run from the checkout **as that non-root account**:

```bash
.venv/bin/python scripts/verify_sandbox_host.py
podman --remote=false info --format '{{.Host.Security.Rootless}}'
```

Static success is only a prerequisite. Do not chmod the host cgroup tree, use
rootful fallback or alter quotas merely to pass a probe. The Codex limitations
are already established; rerunning diagnostics here is unnecessary.

## 2. Verify and build immutable worker inputs

```bash
.venv/bin/python scripts/verify_worker_supply_chain.py
.venv/bin/python scripts/verify_worker_supply_chain.py --online
podman build -f sandbox_manager/runtime/Dockerfile \
  -t localhost/foxory-worker:verification sandbox_manager/runtime
podman image inspect localhost/foxory-worker:verification --format '{{.Id}}'
```

- [ ] Retain the reviewed base digest, npm integrity values, source/build hashes,
  builder version and build log. Base is pinned to the reviewed Playwright 1.64.1
  Ubuntu index; npm graph is locked. Record the **resulting local image ID**.
- [ ] Inspect an SBOM, image/package licenses and vulnerability scan. Preserve
  upstream notices. Online hash verification already passed in Codex, but is not
  a vulnerability audit, signed provenance or a verified image build.
- [ ] Review platform-specific manifest selection. AMD64 and ARM64 registry
  manifests exist; neither architecture's new worker execution is claimed here.

## 3. Fixed fixtures and active isolation probes

Replace the image argument with the actual reviewed local `sha256:` ID:

```bash
.venv/bin/python scripts/verify_oci_runtime.py --image sha256:REPLACE_WITH_LOCAL_IMAGE_ID
```

- [ ] Fixed JS probe passes non-root UID, memory.max=1GiB, pids.max=128, CPU quota
  ratio 1, read-only source/root paths, absent host sockets/secrets and loopback-only
  interfaces. Probe output must identify JS, TS and browser fixtures as passed.
- [ ] TypeScript stripping runs; document unsupported TS syntax/type-checking.
- [ ] Chromium sandbox enabled: navigate local site, type, click, inspect,
  screenshot and download exact controlled fixture bytes. No unsafe fallback.
- [ ] JS and TS attest empty capability masks, no-new-privileges and seccomp;
  browser uses only the reviewed SYS_CHROOT exception. Retain separate
  `FOXORY_PROBE_PASSED` markers and investigate any AppArmor/seccomp denial.
- [ ] Confirm all probe containers are absent afterward. Treat any cleanup error
  as a blocker. Probe cleanup uses only manager-created names; startup probes
  label their containers for later manager orphan detection.

The script runs only reviewed fixed fixtures. It does not enable the application.
Its successful runtime path is pending Ubuntu verification.

## 4. Activate the manager deliberately

In the private manager environment file (never source control), set:

```dotenv
FOXORY_SANDBOX_ENABLED=1
FOXORY_SANDBOX_OCI_ENABLED=1
FOXORY_SANDBOX_OCI_IMAGE=sha256:REPLACE_WITH_LOCAL_IMAGE_ID
FOXORY_SANDBOX_DATA=/PRIVATE_MANAGER_OWNED_DIRECTORY
# FOXORY_SANDBOX_KEY must contain at least 32 random characters.
```

Use the same key for the application connection, with `FOXORY_ENABLE_SANDBOX=1`
and a trusted local `FOXORY_SANDBOX_URL`. Do not share these variables with worker
containers. Start the manager with **one process**, as the dedicated account:

```bash
.venv/bin/python -m uvicorn sandbox_manager.service:app \
  --host 127.0.0.1 --port 8104 --workers 1
```

- [ ] Startup checks the exact immutable image with active probes. Disabled flags,
  failed probes, missing authentication/non-root requirements or cleanup errors
  leave OCI profiles unavailable. Python retains its independent preflight.
- [ ] Select each profile in Computer Mode, create an explicitly scoped agent,
  submit reviewed fixture sources/actions, inspect immutable approval context,
  approve and observe live logs, final states, screenshots and downloads.
- [ ] Test JS/TS project → actual tests → separate packaging approval → ZIP CRC
  and matching source. A zero exit alone does not establish test adequacy.
- [ ] Test research/documents/math → delegated browser/coding → report/PDF/source
  artifacts. Record actual source URLs and model name; label any fixture stages.

## 5. Security and recovery acceptance

- [ ] Reject wrong key, cross-workspace inspect/cancel/download, stale/rejected/
  expired/reused approval and changed config/plan. Viewer cannot submit/approve.
- [ ] Reject arbitrary image/runtime flags/mounts, paths escaping source,
  binary/macro downloads, CSV formulas, invalid JSON, corrupt/oversized PNGs,
  oversized envelopes and forged ownership/hash metadata.
- [ ] Verify denied external navigation, POST/form submission, host/metadata IPs,
  private service sockets and other task sessions. Public browsing is unsupported.
- [ ] Test infinite loops, CPU-bound jobs, aggregate memory exhaustion and PID
  exhaustion under quotas. Record effective counters/exit reasons, not just prose.
- [ ] Cancel running and queued jobs, repeat cancel and pause/resume. Require
  whole-container removal, no descendants and no source/request staging residue.
- [ ] Kill/restart the manager during create/start/run/cleanup, including with an
  intentionally orphaned **manager-owned labeled** container. Owned orphans are
  removed, foreign-owner containers untouched, interrupted records retained,
  staging cleaned and code never replayed silently. Engine failure quarantines
  execution; periodic reconciliation catches late orphans.
- [ ] Reboot and verify persisted accounts, memberships, approvals, completed jobs
  and artifacts. Back up and restore application and manager state separately.
- [ ] Confirm engine/client failures cannot report execution complete before
  cleanup, cannot activate profiles and cannot disable the existing Python seal.

## 6. Regression evidence before acceptance

```bash
.venv/bin/pytest -q backend/tests
npm --prefix frontend run build
# Browser UI with explicitly mocked OCI boundary (not isolation proof):
cd frontend
FOXORY_E2E_SANDBOX=1 FOXORY_E2E_OCI=1 npm run test:e2e
```

- [ ] Retain actual Ubuntu manager/browser/JS/TS integration logs, cancellation,
  restart, limits and security evidence separately from mocked regression results.
- [ ] Run Compose/native-manager connectivity and final-image persistence/health
  checks with disposable test data. Never replace owner volumes during validation.
- [ ] Run an actual local-model workflow and document measured limitations. No GPU,
  Windows/macOS, production readiness or Phase 4 completion claim without evidence.

This checklist is intentionally unchecked for real-host execution. The automated
Codex tests verify application control flow; they do not certify sandbox escapes
are impossible. Do not begin Phase 5 while these host-dependent criteria remain.
