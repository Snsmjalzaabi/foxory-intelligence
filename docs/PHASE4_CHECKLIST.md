# Phase 4 acceptance — host-dependent criteria pending

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
- [x] Backend (193), browser journeys (14), frontend build, migration/security and Compose regressions; real core acceptance separately records 14 checks. Counts refer to their stated individual run scopes; canceled CI is not a pass.
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
- [ ] Final application/manager topology and persistence/backup restore checks.
- [x] Actual native application adapter → private Unix manager → rootless JS
  execution; TCP/Unix fixture recovery and quotas pass on Ubuntu 24.04.
- [ ] Final systemd activation/Compose socket GID mapping and owner Ubuntu 26.04.
- [x] Safe default infrastructure upgrade with actual model compatibility and
  separate-volume logical database migration; no automatic owner-volume change.
- [ ] Combined local-model workflows produce real browser/code/report artifacts.
- [ ] Final real-host critical tests pass before Phase 4 acceptance or Phase 5.

Existing Python and real local-model verification is retained in PROJECT_STATUS.md
and docs/PHASE4_OCI_GROUNDWORK.md. Source ZIPs/zero exits do not establish test
adequacy. No privileged fallback, public deployment or GPU verification is claimed.
The actual Ubuntu fixture scope and image ID are recorded in
[UBUNTU_OCI_RUNTIME_EVIDENCE.md](UBUNTU_OCI_RUNTIME_EVIDENCE.md).
