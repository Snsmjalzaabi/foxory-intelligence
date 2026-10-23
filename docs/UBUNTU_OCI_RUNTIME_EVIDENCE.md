# Ubuntu operator evidence: fixed OCI runtime probes

The owner supplied terminal output from Ubuntu 26.04 after pulling development
commit `aab7884e6a598f4cde1d9f06d4342cc20fb0be08`. This is operator-provided
real-host evidence, not an independently observed Codex run or a mocked test.

The source was refreshed in the existing dedicated `foxory-sandbox` account,
then built and tested inside a systemd user scope with `Delegate=yes`. No
activation flag or isolation bypass was added. The scope reported
`run-p27174-i4662.scope`, invocation `ec435d37cee4414abfcc148c204a7edf`.

Reviewed base:
`mcr.microsoft.com/playwright:v1.64.1-noble@sha256:47b510dd9230bf0b9bfc9b20102241e577ea7a99334ab4c3ca19f19770e9b8ea`.

Actual built local image:
`sha256:248d4afc67fe3b0845b2cedd239d5b378eba4b0ad19e344891fb5fc0873ddbcb`.

The offline input check returned `reviewed_inputs_verified`. All cached image
build stages succeeded. The final verifier output was:

```text
FOXORY_PROBE_PASSED javascript
FOXORY_PROBE_PASSED typescript
FOXORY_PROBE_PASSED browser
```

```json
{
  "status": "fixed_probes_passed",
  "evidence": [
    {"profile": "javascript", "fixture_passed": true},
    {"profile": "typescript", "fixture_passed": true},
    {"profile": "browser", "fixture_passed": true}
  ],
  "application_execution_enabled": false,
  "warning": "Not comprehensive sandbox security assurance; complete the Ubuntu host acceptance checklist."
}
```

## What this establishes

- JavaScript and type-stripped TypeScript ran actual fixed code under the reviewed
  rootless/non-root command policy. Both fixtures checked empty capability masks,
  NoNewPrivs=1, Seccomp=2, effective memory/PID/CPU cgroup values, denied writes to
  fixed root/source paths, absent host sockets/key and loopback-only interfaces.
- Chromium launched with Playwright's `chromiumSandbox:true` and the browser-only
  SYS_CHROOT exception. The former chroot startup assertion no longer blocked
  this configuration. The controlled fixture exercised navigation, typing,
  clicking, text inspection, screenshot output and exact download bytes.
- Fixed artifact byte counts/hashes, PNG signature and controlled download bytes
  met the verifier's checks. Each probe's cleanup checked container absence.
- The verifier did not enable application execution.

The supplied output does not identify the exact earlier denial mechanism. Success
supports the targeted capability/seccomp correction on this configuration; it
does not establish that every AppArmor/seccomp version will behave the same way.

## Still pending

No full host-acceptance or Phase 4 completion claim follows. Remaining evidence:
image SBOM/CVE/license review; authenticated live-manager/application approvals
and tenant isolation; actual cancellation during running/queued work; CPU/PID/
memory exhaustion and timeout counters; crash/orphan recovery and manager restart;
final deployment connectivity and backup/restore; actual combined local-model
browser/coding/report workflows. Public browsing/submissions remain unsupported.
No GPU, Windows/macOS, general escape resistance or production-readiness claim.

Retain the original private build/runtime logs on Ubuntu. Follow
[the remaining host checklist](SANDBOX_HOST_VERIFICATION.md), rather than repeating
the already-passing provisioning/probe steps or weakening the execution policy.
