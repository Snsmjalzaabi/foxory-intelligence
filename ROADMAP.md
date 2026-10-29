# Roadmap to v1.0 — five phases

GitHub development is canonical. Checkboxes indicate only the stated acceptance
slice; current results and limitations are in [PROJECT_STATUS.md](PROJECT_STATUS.md).
The [historical roadmap](docs/LEGACY_ROADMAP.md) is preserved for traceability and
does not introduce active Phases 6/7 or extra milestones.

## Phase 1 — Core AI Foundation (accepted)

- [x] Persistent local Ollama chat, streaming/history/exports and model selection.
- [x] Local-only Docker/Compose, authentication foundation and automated tests.
- [x] Preserve accepted milestone at `3452acd`.
- [x] Subsequent core account, model and installation repairs retain prior data.

## Phase 2 — Advanced Search and Research (accepted)

- [x] Accounts/sessions/RBAC and isolated workspace resources.
- [x] Real search/page retrieval, durable research, cancellation/resume and references.
- [x] Restricted documents, local semantic retrieval and report exports.
- [x] Model Council independent analysis/comparison/synthesis, sequential default.
- [x] Preserve accepted milestone at `7d1cd05` and [acceptance record](docs/PHASE2_CHECKLIST.md).
- [x] Shared checked-reference/extractive fallback for grounded chat and research.
- [ ] Broader search/model answer-quality evaluation; citation integrity is not factual verification.

## Phase 3 — Autonomous Agents (accepted)

- [x] Bounded plans, explicit tools/scopes, delegation, durable checkpoints and memory.
- [x] Immutable approval gates, retries/cancellation and safe fixed-interval scheduling.
- [x] Connected Workforce and actual local-model workflows.
- [x] Preserve accepted milestone at `ca90bca` and [acceptance record](docs/PHASE3_CHECKLIST.md).

## Phase 4 — Computer and Advanced Tools (in progress)

- [x] Core runs without advanced execution; all sandbox profiles default disabled.
- [x] Restricted Python execution, data tools, charts, files and source packaging.
- [x] Authenticated manager/OCI dispatch, scopes, approvals and artifact ownership.
- [x] Computer Mode state/logs/screenshots/downloads; actual Python plus mocked OCI regressions.
- [x] Owner-supplied actual Ubuntu JS/TS/Chromium fixed probes after browser-only SYS_CHROOT correction.
- [x] Hosted core and sandbox CI separation without weakening or hiding runtime tests.
- [x] Hosted canonical core Compose startup and PostgreSQL migration/restart/logical restore.
- [ ] Final worker-image SBOM, vulnerability/license review and accepted findings.
- [ ] Real Ubuntu hostile-input/network/resource-exhaustion tests with recorded results.
- [ ] Real Ubuntu cancellation, process-crash/orphan recovery and restart cleanup.
- [ ] Final app/manager topology, permissions/approvals and independent state backup/restore.
- [ ] Actual combined local-model coding/browser/research/report workflows on the accepted host.
- [ ] All remaining [Phase 4 acceptance checks](docs/PHASE4_CHECKLIST.md) pass.

## Phase 5 — Optimization and Open-Source Release Preparation (not started)

Start only after Phase 4 acceptance. No public publication/deployment is implied.

- [ ] Resolve or explicitly accept security findings; provide precise threat/compatibility limits.
- [ ] Final dependency/image SBOM and license attribution review.
- [ ] Clean supported-host install/upgrade/uninstall and tested full backup/restore.
- [ ] Performance/research-quality/accessibility evaluation with realistic local models.
- [ ] Supported OS/hardware matrix; no unmeasured NVIDIA/Windows/macOS claims.
- [ ] Final critical CI/integration/recovery tests and release artifacts verified.
- [ ] v1.0 feature/security assessment and owner approval before publication/deployment.

Optional business records remain secondary. Public browsing/submissions, email
sending, financial actions, arbitrary privileged tools and broad enterprise/CRM
integrations are not silently promoted into core release requirements or claimed
available. Larger-scale pgvector/distributed workers and unsupported model runtimes
remain explicitly disclosed future work.
