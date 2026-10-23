# Chromium chroot failure under rootless Podman

Status: targeted policy correction implemented; **actual Ubuntu 26.04 Chromium
verification is pending**. Phase 4 remains incomplete and OCI execution remains
disabled by default. This document does not certify container isolation.

## Investigation and policy

The reported Ubuntu run builds the immutable image and reaches Chromium startup,
then fails at `sys_chroot("/proc/self/fdinfo/") == 0`. The operator reports working
rootless Podman, delegated cgroups and static checks; JS/TS appear to pass. Those
are operator observations, not new runtime results from this change.

Chromium's `ChrootToSafeEmptyDir` creates a short-lived child and chroots to its
procfs fdinfo directory to remove filesystem access. Linux requires
`CAP_SYS_CHROOT` in the caller's user namespace for `chroot(2)`. Chromium can
obtain capabilities in its own nested user namespace, but that does not override
the container's inherited seccomp filter. The upstream containers/common default
seccomp policy explicitly allows `chroot` when `CAP_SYS_CHROOT` is included and
returns `EPERM` when it is excluded. The previous unconditional `--cap-drop=ALL`
can therefore deny this call even when Chromium has created a nested namespace.
The assertion alone does not reveal errno or prove which policy denied it.

The manager now requires an explicit validated profile when building OCI commands:

| Profile | Capability policy |
| --- | --- |
| JavaScript | `--cap-drop=ALL`; no additions |
| TypeScript | `--cap-drop=ALL`; no additions |
| Browser | `--cap-drop=ALL --cap-add=SYS_CHROOT` |

The same builder is used for authenticated jobs and fixed startup probes. Clients
cannot supply capability flags or select an image. The browser tool still needs
its existing workspace/agent scope and immutable approval. All profiles retain
UID/GID 1000, rootless user namespaces, `no-new-privileges`, runtime-default
seccomp/AppArmor, read-only source/root mounts, private IPC/PID/UTS/cgroup
namespaces, no network, fixed tmpfs limits, 1 CPU, 1 GiB memory/swap ceiling, 128
PIDs and the existing timeouts, artifact checks and cleanup requirements. No
`SYS_ADMIN`, privileged mode, `--no-sandbox` or unconfined policy is introduced.

This is an intentional increase in the browser container's available privilege:
processes can use chroot when their namespace capabilities permit it. Chroot is
not itself an escape-proof security boundary. The capability is confined by the
rootless user namespace; it does not grant capability in the host's initial user
namespace, override host file ownership or expose unmounted host credentials.
`SYS_CHROOT` also participates in mount-namespace `setns` permission checks;
the additional required `SYS_ADMIN` capability is not granted, and existing
runtime syscall restrictions remain in force.
Kernel/runtime vulnerabilities remain possible. Retain the dedicated account,
minimal mounts, default LSM/seccomp policies and every other restriction. Do not
apply this exception to Python or general code execution. The Python seal is
unchanged.

References inspected during this investigation (upstream main may change; the
host's installed containers/common policy and image Chromium version govern):

- [Chromium credentials.cc](https://github.com/chromium/chromium/blob/main/sandbox/linux/services/credentials.cc):
  `ChrootToSelfFdinfo`, `ChrootToSafeEmptyDir`, `MoveToNewUserNS`.
- [containers/common default seccomp](https://github.com/containers/common/blob/main/pkg/seccomp/default_linux.go):
  `chroot` allow/deny rules conditioned on `CAP_SYS_CHROOT`.
- [Linux capabilities](https://man7.org/linux/man-pages/man7/capabilities.7.html)
  and [user namespaces](https://man7.org/linux/man-pages/man7/user_namespaces.7.html).

## Changed files

| File | Change |
| --- | --- |
| `sandbox_manager/oci.py` | Required validated profile; browser-only SYS_CHROOT. |
| `sandbox_manager/oci_runtime.py` | Dispatch the validated project profile to the builder. |
| `scripts/verify_oci_runtime.py` | Matching profile dispatch, full JS/TS controls checks, partial pass markers. |
| `backend/tests/test_sandbox_capabilities.py` | Profile invariants, negative cases, fixed-probe boundary/failure tests. |
| `backend/tests/test_oci_integration.py` | Authenticated dispatch capability assertions for all three profiles. |
| `docs/CHROMIUM_SANDBOX_UBUNTU.md` | Investigation, security review, update and host procedures. |
| `docs/SANDBOX_HOST_VERIFICATION.md` | Explicit capability exception and outstanding acceptance checks. |
| `docs/PHASE4_CHECKLIST.md` | Implemented policy versus pending actual Chromium verification. |
| `docs/SANDBOX_MANAGER.md` | Manager policy and verification scope. |
| `sandbox_manager/runtime/README.md` | Image/operator guidance for the exception. |
| `SECURITY.md` | Capability scope and remaining security verification. |
| `CHANGELOG.md` | Unreleased targeted correction. |
| `PROJECT_STATUS.md` | Actual test results, unchanged boundaries and next action. |

## Ubuntu update, rebuild and fixed runtime verification

First transfer the commit containing this change into the owner's existing
`~/Projects/foxory-intelligence` checkout. A local commit in a Codex workspace is
not automatically on GitHub; `git pull` works only after it has been pushed.
If supplied an all-history update bundle, use the following as the owner. This
fast-forward preserves existing history and refuses divergent local work:

```bash
cd "$HOME/Projects/foxory-intelligence"
test "$(git branch --show-current)" = development
test -z "$(git status --porcelain)"
git bundle verify "$HOME/Downloads/foxory-intelligence-chromium-fix.bundle"
git fetch "$HOME/Downloads/foxory-intelligence-chromium-fix.bundle" development
git merge --ff-only FETCH_HEAD
git log -1 --format='%H %s'
# Optional: upload this verified development commit to your existing PRIVATE repo:
# git push origin development
```

For the already-provisioned `foxory-sandbox` account, refresh tracked source from
the owner's checkout. Its source copy need not be a Git repository. This keeps
the existing dedicated virtualenv and private state/environment; it does not
delete directories or replace database volumes. Stop any running manager using
this source copy before updating it; leave OCI activation flags disabled.

```bash
cd "$HOME/Projects/foxory-intelligence"
set -o pipefail
git archive HEAD | sudo -u foxory-sandbox -H tar -x -C /home/foxory-sandbox/foxory-intelligence

sandbox_uid="$(id -u foxory-sandbox)"
sudo -u foxory-sandbox -H env \
  XDG_RUNTIME_DIR="/run/user/$sandbox_uid" \
  DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$sandbox_uid/bus" \
  systemd-run --user --scope --property=Delegate=yes bash -c '
    set -euo pipefail
    umask 077
    cd "$HOME/foxory-intelligence"
    logs="$HOME/foxory-verification/chromium-chroot-$(date -u +%Y%m%dT%H%M%SZ)"
    mkdir -p "$logs"
    .venv/bin/python scripts/verify_worker_supply_chain.py 2>&1 | tee "$logs/inputs.log"
    .venv/bin/python scripts/verify_worker_supply_chain.py --online 2>&1 | tee "$logs/registry.log"
    podman --remote=false build -f sandbox_manager/runtime/Dockerfile \
      -t localhost/foxory-worker:verification sandbox_manager/runtime 2>&1 | tee "$logs/build.log"
    image_id="$(podman --remote=false image inspect localhost/foxory-worker:verification --format "{{.Id}}")"
    case "$image_id" in sha256:*) ;; *) image_id="sha256:$image_id" ;; esac
    printf "%s\n" "$image_id" | tee "$logs/image-id.txt"
    .venv/bin/python scripts/verify_oci_runtime.py --image "$image_id" \
      2>&1 | tee "$logs/runtime.log"
    printf "Evidence: %s\n" "$logs"
  '
```

No image source or dependency changed in this fix, so a cached build and the same
image ID are expected. **Updating the manager/probe Python source is essential**;
rebuilding only the old image will not apply the policy correction. Do not use
`--no-cache`, delete images/volumes, reprovision the account or change quotas to
force a result.

The new verifier prints `FOXORY_PROBE_PASSED javascript`, `typescript` and
`browser` to stderr individually. Only after all succeed does stdout report
`fixed_probes_passed`. JS and TS both run the full controls fixture, checking all
five capability masks are zero, `NoNewPrivs=1`, `Seccomp=2`, effective cgroup
quotas, non-root UID, read-only paths, absent sockets/secrets and loopback-only
interfaces. TypeScript also exercises type stripping. Browser must actually
launch Chromium with its sandbox, type, click, inspect, screenshot and download
the exact controlled bytes. Container absence is checked during cleanup. These
checks remain necessary but do not replace hostile-input/recovery acceptance.

## If Chromium still fails

Keep OCI execution disabled. Capture the complete runtime traceback and retained
build/image evidence. As the owner, read kernel denial logs for that test window:

```bash
sudo journalctl -k --since '15 minutes ago' --no-pager \
  --grep='apparmor|SECCOMP|DENIED|seccomp'
```

As the dedicated account, retain `podman --remote=false info --format json` and
review its selected seccomp profile path and runtime version. An administrator
should inspect that actual policy's `chroot`, `clone`, `unshare` and `setns`
rules. Capability-aware filtering differs by installed policy/version. Seccomp
errno denials may produce no audit entry, so an empty journal does not establish
that seccomp allowed the syscall.

Ubuntu AppArmor can independently restrict user-namespace creation or chroot.
Review a denial's profile, operation and target before designing any host-local
change. This patch does not disable AppArmor, change global userns sysctls, add
`SYS_ADMIN`, relax seccomp or modify the image's Chromium sandbox. Any additional
host profile requires separate review and rerunning the full acceptance checks.
The existing `no-new-privileges` is retained; do not try to make Chromium's setuid
sandbox helper gain privilege instead.

After fixed fixtures pass, follow [the full host checklist](SANDBOX_HOST_VERIFICATION.md)
for active-manager startup, authenticated approvals, cancellation, malicious
inputs, quotas/exhaustion, orphans/restart recovery and real local-model tasks.
Record actual Ubuntu evidence before enabling application use or marking Phase 4
complete. No GPU, Windows/macOS or production-readiness claim follows from this fix.
