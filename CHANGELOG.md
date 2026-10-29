# Changelog

## Phase 4 — incomplete, unreleased

Remove inherited optional codec/parser dependencies with guarded package changes,
Chromium preservation and literal shared-library checks. Exact-image Ubuntu26
runtime/recovery/cleanup and all regression jobs passed; findings133→71. The
remaining41 MEDIUM/30 LOW findings and binary-license review are not cleared.

Remove unused libsoup3 HTTP packages and reverse-dependent WebKit networking
packages with the same Chromium-preserving package guards and independent shared-
file tests. Exact-image Ubuntu26 scan and all actual runtime/recovery groups
passed; findings177→133. Regression suite254 passes. Existing isolation and
disabled defaults remain; no production or binary-license clearance.

Remove unused system FFmpeg libraries with guarded build-time dependency checks,
merged-filesystem validation and current-policy SBOM/provenance enforcement.
Actual exact-image Ubuntu26 runtime and regression checks passed. This removes455
package findings;177 remain. Chromium dependencies and the zlib fix are retained.
Lower-layer bytes, bundled codecs and binary licensing remain separate reviews.

Sequential verified fixes: bind actual rootless image audits and runtime reports
to one immutable image/config and the current remediation policy. Update worker
OS zlib1g to1:1.3.dfsg-3.1ubuntu2.3 for CVE-2026-85091 (USN-8954-1), with a
specific mandatory gate despite its MEDIUM vendor severity. Exact-image Ubuntu26
runtime, recovery and regression verification passed. Other findings and binary
license review remain open; default execution stays disabled.

Hosted core and actual sandbox CI now pass independently, including a pristine
canonical Compose installation and PostgreSQL migration/persistence/logical
restore. Added reported model capability roles with server-side compatibility
guards and bounded inspection, hardened SQLite backup boundaries/WAL handling,
canonical license notices and nested build-secret exclusions. Added checksum-
pinned static image SBOM/license/vulnerability gates; actual new scan findings
remain pending the candidate run. Five-phase roadmap restored, with older plans
archived. No production readiness or Phase 4 completion claim.

Core product recovery: Search/document chat now share Deep Research’s checked
reference/extractive fallback, missing document evidence skips inference, and a
bounded optional chat output limit supports CPU verification. Recovered stale
model selections, added no-model setup guidance, prioritized document navigation
and labeled Computer Mode optional. Added a real Ollama/web disposable core
acceptance harness and expanded browser/grounding regressions. No sandbox
manager is required by the core installation.

Restricted the Chromium chroot policy correction to browser containers using only
`SYS_CHROOT`; JS/TS still drop all capabilities. Strengthened both code-profile
controls probes and added separate fixture pass markers, policy/dispatch tests
and Ubuntu rebuild/denial-diagnosis instructions. The owner supplied actual Ubuntu
JS/TS/Chromium fixed-probe passes on image `sha256:248d4afc67fe3b0845b2cedd239d5b378eba4b0ad19e344891fb5fc0873ddbcb`.
Full host acceptance remains pending; OCI defaults remain disabled.

Connected offline Playwright/Node/TypeScript profiles to authenticated manager dispatch, immutable approvals and Computer Mode. Added ownership-scoped lifecycle/cancellation/recovery, strict artifact/download validation, screenshot previews, deterministic OCI-boundary tests and pinned worker-image inputs. Profiles remain disabled by default; actual Ubuntu isolation/image verification is pending. See docs/SANDBOX_HOST_VERIFICATION.md.

Bounded table filtering/grouped statistics and inert SVG chart data; approval-gated source ZIP artifacts; CSV/JSON exports and connected Workforce download controls. Computer Mode now connects optional, explicitly approved single-process Python execution through a separate rootless Bubblewrap manager. Uploaded CSV statistics, report/chart workflows and scoped artifacts are supported. General browser and JavaScript execution remain unavailable. See PROJECT_STATUS.md.

## Phase 3 — unreleased

Bounded stateful agents with schema-constrained local planning, explicit specialist delegation and result references, permission-scoped tools, approval-gated atomic internal writes, retained unverified memory, durable schedules and a connected AI Workforce interface. Small document formats now use a minimal sealed parser profile. Full verification and remaining limits are recorded in PROJECT_STATUS.md; v1.0 and production readiness remain unclaimed.

## Phase 2 — unreleased

Workspace accounts and server-side permissions; evidence-based research with real page retrieval and checkpointed recovery; independent Model Council stages; restricted Linux parsing, local semantic indexing and multi-document citations; PDF/Word/spreadsheet exports and integrated account/research interfaces. See PROJECT_STATUS.md and docs/VERIFICATION.md for executed checks and limitations. Target v1.0 remains incomplete.

## 0.1.0 — unreleased

Initial Community Edition foundation: private single-owner workspace, persistent Ollama chat, model management, document extraction and keyword Q&A, experimental search research, sequential council, bounded durable draft tasks, lead records, memory/projects, draft approval snapshots and audit dashboard. Docker/native installation and automated verification scaffolding. Target v1.0 remains incomplete; see PROJECT_STATUS.md.
