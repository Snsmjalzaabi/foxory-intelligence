# Ubuntu resource-control preflight

Phase 4 remains incomplete. These commands inspect host prerequisites; they do
not authorize or activate browser/JavaScript execution. Run them from the checkout
as the dedicated **non-root** sandbox manager user on Ubuntu Linux:

```bash
python3 scripts/verify_sandbox_host.py
printf 'Preflight exit status: %s\n' "$?"
podman info --format '{{.Host.Security.Rootless}}'
cat /proc/self/cgroup
```

The JSON report is machine-readable. Exit 2 means required static capabilities
are missing. Exit 0 means static checks passed, **not** that isolation passed.
`execution_enabled` and `runtime_isolation_verified` deliberately remain false.
The existing Python profile uses its independent Bubblewrap/seccomp startup test.
Authenticated `/v1/health` includes these optional OCI diagnostics, without keys
or environment contents.

For the prospective rootless OCI profiles, operators need Podman, subordinate
UID/GID mappings (`newuidmap`/`newgidmap`), cgroup v2 and delegated `cpu`, `memory`
and `pids` controllers for the manager's account. Ubuntu packages normally include
`podman` and `uidmap`. Have the host administrator configure a dedicated systemd
user service/scope with `Delegate=cpu memory pids`; delegation is not established
by installing packages or setting an environment variable. Do not chmod the host
cgroup tree or use a privileged/rootful fallback. Ubuntu AppArmor/user-namespace
policy must also allow the intended rootless runtime and Chromium sandbox.

An optional image recipe is in `sandbox_manager/runtime/Dockerfile`. It is **not
built or verified in Codex Cloud**. On the verification host, after reviewing and
selecting a Node 22 Debian image digest, build locally:

```bash
# Replace with an actual reviewed immutable base reference, not a moving tag.
export FOXORY_NODE_BASE='node@sha256:REPLACE_WITH_REVIEWED_DIGEST'
podman build --build-arg BASE_IMAGE="$FOXORY_NODE_BASE" \
  -f sandbox_manager/runtime/Dockerfile -t localhost/foxory-worker:verification \
  sandbox_manager/runtime
podman image inspect localhost/foxory-worker:verification --format '{{.Id}}'
```

Building installs browser dependencies into the image, not into a task. Review
Node, Debian, Playwright (Apache-2.0), Chromium and bundled-library license notices
before distributing an image. No runtime dependency installation is supported.
The fixed command builder only accepts a local `sha256:` image ID and disables
pulling, network, capabilities and proxy inheritance, and requests CPU/memory/PID
limits plus read-only mounts. Those requested settings still require real tests.

## Required active verification before activation

The opt-in fixed-fixture probe is implemented, but its successful execution is
**pending an appropriate host**. After the static preflight passes and the image
has been built/reviewed, use the project virtual environment:

```bash
.venv/bin/python scripts/verify_oci_runtime.py --image sha256:REPLACE_WITH_LOCAL_IMAGE_ID
```

This checks rootless identity, effective cgroup limits, read-only paths, absent
privileged sockets, network interfaces and environment isolation with fixed JS;
then runs TS and a controlled browser click/type/screenshot/download journey.
Each container has a 45-second wall deadline and explicit force-removal/absence
check. It does not enable application profiles and is not an escape audit. Its
blocked path was tested in Codex; actual OCI probes were not run here.

Remaining engineering:

- Authenticated, approval-bound manager dispatch for the new profiles; explicit
  operator opt-in and immutable local image configuration.
- Active probes inspect effective cgroup limits inside each task and demonstrate
  memory/PID/CPU enforcement, non-root identity, filesystem/secret isolation,
  external network denial and working Chromium sandbox.
- Manager wall deadline, whole-container cancellation, orphan cleanup on restart,
  bounded output parsing and independent artifact validation.
- Controlled-site browser navigation, typing, clicking, screenshot and download;
  dependency-free JS/TS project execution and workspace/approval regression tests.
- Computer UI profile selection, screenshot display and verified result packaging.

The supplied worker and command-policy modules are implementation groundwork;
they are not exposed as working Computer Mode capabilities. Do not run generated
code by invoking `worker.mjs` on the host. Do not pass `--no-sandbox`, mount host
sockets, remove quotas or allow network merely to obtain a passing result.

In this Codex environment, the cgroup mount is not writable and rootless OCI
executables are absent. Actual isolated browser and JS/TS executions remain
unverified. Windows/macOS and GPU execution have not been verified.
