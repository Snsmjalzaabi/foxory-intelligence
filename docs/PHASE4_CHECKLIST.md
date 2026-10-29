# Phase 4 acceptance — hosted runtime passed; distribution/owner acceptance pending

Latest exact-image evidence:
[Issue5 Ubuntu26 runtime](evidence/issue5-codec-removal-verified-2026-10-29.json)
at `0edf13b`:7 canonical/9 TCP/10 Unix check groups and all owned cleanup passed.
Current worker scan71 lower findings; compiled coverage/licenses remain open.
Local backend272 and hosted Verify40868917095 passed; OCI UI remains mocked.
Earlier evidence: [Ubuntu26 integration](UBUNTU26_INTEGRATION_EVIDENCE.md).
Run `40838680397` passed actual hosted Ubuntu26 systemd/Compose/OCI workflows,
coordinated restore and TCP/Unix attack/recovery suites. This does not check the
owner's installation, GPU, public browsing or universal sandbox security.

## Implemented and verified in Codex Cloud

- [x] Preserve Phases 1–3 and restricted Python execution.
- [x] Authenticated JS/TS/offline-browser manager dispatch with disabled defaults.
- [x] Explicit agent tools, scopes, immutable approvals and duplicate prevention.
- [x] OCI lifecycle: bounded create/attach, wall deadlines, cancellation, cleanup,
  ownership labels, quarantine and startup/periodic orphan recovery (mocked OCI).
- [x] Artifact integrity/content validation and scoped authorized downloads.
- [x] Computer Mode profiles, states, logs, approvals, retry, screenshots/downloads
  through actual HTTP UI/backend and an explicitly mocked OCI boundary.
- [x] Multi-agent research/data/coding/browser/report/source workflow with fixtures;
  actual deterministic calculations, PDF parsing and source ZIP validation.
- [x] Worker base digest, locked dependencies, input hashes and registry-byte checks.
- [x] Ubuntu installation, image build and security/recovery validation checklist.
- [x] Backend212, core browser11/full sandbox14 (overlapping suites), frontend
  build, migration/security and Compose regressions at `5309912`. OCI UI is
  explicitly mocked; actual hosted runtime evidence is separate. Canceled CI is not a pass.
- [x] Current-source application image health/persistence and separate PostgreSQL 17
  migrations, tenant/duplicate guards, restart and dump/restore smoke tests.
- [x] Actual local qwen2.5:0.5b Python repair/test/package/restart regression.
- [x] Browser-only SYS_CHROOT command policy; JS/TS retain zero capabilities.
  Authenticated dispatch/probe-builder regression tests use mocked OCI execution;
  the owner subsequently supplied passing actual Ubuntu fixed runtime probes.

## Required real-host evidence — do not infer from mocks

- [x] Actual Ubuntu immutable image build (operator supplied output).
- [ ] Review image SBOM and vulnerability/license findings.
- [x] Actual canonical application and worker scans have zero HIGH/CRITICAL
  findings after remediation; lower findings/licenses/compiled binaries still
  require review. Reports retained separately from fixture scanner tests.
- [x] Actual rootless Node/TypeScript fixed execution with effective CPU/memory/PID quota checks.
- [x] Actual sandboxed Chromium controlled-site navigation, interaction, screenshot and download.
- [x] Actual Ubuntu 24.04/Podman 4.9.3 CPU throttling, PID denial, cgroup OOM kill,
  JS/TS filesystem/network denial, Chromium controlled-site/screenshot/download.
- [x] Ubuntu 24.04 whole-container running/queued/repeat cancellation, bounded
  timeout, actual manager kill/restart, owned orphan cleanup/foreign preservation.
- [ ] Repeat relevant final-image/topology acceptance on the owner's Ubuntu
  26.04; hostile-input coverage is representative, not escape certification.
- [x] Final hosted application/manager topology, systemd activation, Compose
  GID/socket mapping and coordinated DB/app-files/manager restore.
- [x] Actual native application adapter → private Unix manager → rootless JS
  execution; TCP/Unix fixture recovery and quotas pass on Ubuntu 24.04.
- [x] Ubuntu26 hosted TCP/Unix quotas, network/filesystem denial, actual kill/
  restart, orphan ownership, cancellation/timeout and cleanup with counters.
- [ ] Owner Ubuntu26 activation/reboot acceptance (separate from hosted proof).
- [x] Safe default infrastructure upgrade with actual model compatibility and
  separate-volume logical database migration; no automatic owner-volume change.
- [x] Combined local-model workflows produce real browser/code/CSV/PDF/ZIP artifacts.
- [x] Current hosted real-runtime critical tests pass within the stated boundary.
- [ ] Remaining distribution/security findings and supported-scope acceptance
  resolved before declaring Phase4 complete or beginning Phase5.

Existing Python and real local-model verification is retained in PROJECT_STATUS.md
and docs/PHASE4_OCI_GROUNDWORK.md. Source ZIPs/zero exits do not establish test
adequacy. No privileged fallback, public deployment or GPU verification is claimed.
The actual Ubuntu fixture scope and image ID are recorded in
[UBUNTU_OCI_RUNTIME_EVIDENCE.md](UBUNTU_OCI_RUNTIME_EVIDENCE.md).
