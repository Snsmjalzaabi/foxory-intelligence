# Actual Ubuntu26 integration and remaining distribution gates

Real workflow [40838680397](https://github.com/Snsmjalzaabi/foxory-intelligence/actions/runs/40838680397)
passed on commit `1466e6741b49b4b74470ed82942bb4b71f19c0a2`.
This was an ephemeral Ubuntu26.04.1 x86_64 VM, kernel7.0.0-1017-azure, dedicated
non-Docker/non-sudo manager account and rootless Podman. It was not Codex's
restricted OCI environment, the owner's PC, GPU execution or public deployment.

Actual immutable worker:
`sha256:9ff8be0552673bae7d3de0ad67c32d3d5ee78dd068ddf29d3a168d2fa0f25469`.
App/controller and manager ran separately; only a private authenticated Unix API
socket was mounted into the app. No application runtime socket or host shell.

## Failures diagnosed and corrected

| Failure | Correction and evidence |
| --- | --- |
| Native preflight Podman timeout; user-manager journal attempted runner HOME/XDG paths. | Dedicated user-manager startup identity, service identity and explicit child environment. Activation/notification metadata, remote-engine selectors and secrets are excluded from Podman/probe children. The full native startup now passes. This does not identify a unique kernel/AppArmor cause for the older Chromium assertion. |
| General qwen2.5:0.5b JavaScript repair still failed the real tests. | Explicit free local qwen2.5-coder:1.5b coding assignment, at most three actual-feedback attempts, distinct approvals for changed source and retained hashes. Both recorded successful full/partial runs passed on attempt1. No handwritten source fallback. |
| Agent execution error became null after failed code. | Preserve reported failed-execution errors. Terminal execution cannot be queued into an invalid done-stage retry; submit new reviewed inputs/approvals. API and UI regressions pass. |
| Controller cleanup inherited an inaccessible checkout CWD. | Change into the dedicated account home after dropping identity; no directory permissions widened. Actual final cleanup passes. |
| New app-owned recovery volume rejected copytree metadata changes. | Require an empty new target; temporarily own only that root before copy and restore UID/GID10001. No FOWNER or new worker capability. Actual coordinated restore and isolated trusted-helper smoke pass. |

The original owner-supplied Chromium fixed-probe evidence is retained separately
in [UBUNTU_OCI_RUNTIME_EVIDENCE.md](UBUNTU_OCI_RUNTIME_EVIDENCE.md).
Failed runs and partial results are retained, not renamed as passing runs.

## Actual tests

| Scope | Observed result |
| --- | --- |
| Canonical systemd/Compose/rootless application integration | Seven check groups passed; all owned cleanup verified. |
| CPU model repair and code | qwen2.5-coder:1.5b returned the saved module; actual tests checked positive, negative and fractional inputs. Separately approved source ZIP passed CRC and exact source comparison. |
| Delegation | Reviewed five-step plan across four specialists, actual JavaScript/browser/CSV/PDF/chart-source tools, qwen2.5:0.5b review/synthesis. This does not benchmark autonomous plan quality. |
| Browser | Chromium sandbox enabled; type/click actual generated module, SUM=5, screenshot and exact controlled download. Offline supplied site only. |
| Data/report | CSV groups A=30/B=5; actual PDF reopened and text checked. Model arithmetic was not used. |
| Restore | New database, app-files volume and manager directory preserve session, document bytes, artifacts, consumed-approval denial and completed request/finished_at without code replay. |
| Rootless TCP suite | Nine check groups, including actual CPU/PID/memory exhaustion, filesystem/network denial, cancellation, timeout and kill/restart/orphan ownership. |
| Rootless Unix suite | Ten check groups, additionally actual application transport adapter. Same security/recovery checks pass. |

The actual counters include CPU nr_throttled0→16, PID event max0→1/current128,
and memory oom_kill0→1 with SIGKILL. Limits remain1 CPU/1GiB/128PIDs. JS/TS
capabilities remain empty; Chromium retains only its reviewed SYS_CHROOT
exception. Rootless/non-root, no-new-privileges, read-only source/root, task-only
mounts, no network/host sockets, ownership checks and quotas were not relaxed.

Reports:

- [Canonical integration](evidence/full-systemd-compose-ubuntu26-2026-10-29.json)
- [TCP counters/recovery](evidence/rootless-tcp-ubuntu26-2026-10-29.json)
- [Unix counters/recovery](evidence/rootless-unix-ubuntu26-2026-10-29.json)
- [Real controlled-site screenshot](evidence/ubuntu26-actual-browser.png)
- [Real CSV PDF](evidence/ubuntu26-actual-report.pdf)
- [Saved model module](evidence/ubuntu26-model-attempt-1.js)
- [Coordinated recovery boundary](COORDINATED_RECOVERY.md)

The screenshot/module/PDF were retained from the earlier partial run, whose six
functional checks passed before its restore-stage failure; that exact provenance
is in [its partial report](evidence/combined-ubuntu26-partial-2026-10-29.json).
The successful full run independently checked matching outputs again.

## Regression and static security review

Verify [40838103014](https://github.com/Snsmjalzaabi/foxory-intelligence/actions/runs/40838103014)
passed all jobs at `5309912`:195 core+17 real Python-sandbox backend tests,
strict frontend builds,11 core and14 full sandbox browser journeys (overlap),
PostgreSQL0003 isolation/restart/logical restore and pristine Compose startup.
Browser/model protocol fixtures and mocked OCI UI remain explicitly separate
from the actual rootless/local-model results above.

Syft/Trivy reported no vendor HIGH/CRITICAL;26 app and633 worker lower findings
remain recorded. These exact Docker image scans are separate from the rootless
worker image ID above; they use the same reviewed worker inputs but are not
falsely described as a scan of that exact Podman image. Upstream/lower/compiled
component review remains in [SECURITY_IMAGE_REVIEW.md](SECURITY_IMAGE_REVIEW.md).

Bandit1.8.6 scanned3432 Python lines with no parse errors or nosec suppression:
zero HIGH, three MEDIUM, five LOW. Raw results are retained in
[python-static-review-2026-10-29.json](evidence/python-static-review-2026-10-29.json).
The subprocess findings cover the fixed `-I` parser worker and fixed self-test
commands without a shell; payload bytes enter after the seccomp seal. The `/tmp`
findings cover the isolated parser CWD (minimal env/closed FDs/isolated Python)
and the empty Bubblewrap namespace directory/HOME, not host temporary storage
made available to code. Existing actual parser/sandbox attack tests exercise
these boundaries. No scanner findings were removed to produce a green count.
Bandit does not establish JavaScript, async runtime, OS, browser or kernel safety.
This is engineering self-review, not an independent security assessment.

## Remaining gates

The known native startup/workflow/restore failures are fixed within this tested
configuration. Phase4 and production/distribution are still not declared complete:

- Review remaining OS/compiled-browser findings and binary license/source-delivery
  obligations. Source-only distribution and prebuilt binary distribution have
  different obligations; see [DISTRIBUTION_SCOPE.md](DISTRIBUTION_SCOPE.md).
- Validate the owner's actual installation/activation/reboot before enabling its
  profiles. Hosted Ubuntu26 evidence does not grant access to or certify that PC.
- Complete supported-scope/research-quality and release acceptance. Public browser
  navigation/submissions, runtime dependency installation, GPU, Windows/macOS and
  multi-API-process operation remain unsupported/unverified as documented.

No rootful fallback, privileged container, no-sandbox, unconfined policy, purchase,
real communications, public publication or owner-data modification occurred.
Default execution stays off. Phase5 has not started.
