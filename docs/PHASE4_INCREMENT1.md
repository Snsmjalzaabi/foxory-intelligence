# FOXORY Phase 4 of 5 — first implementation increment, incomplete

Date: 2026-10-23. Branch: development. Accepted Phase 3 baseline:
`ca90bcae299031a8393ba338f24f625864d5068e`. Its complete verification record is
preserved in docs/PHASE3_STATUS.md. This increment does not complete Phase 4 or v1.0.

## Implemented

- Registered `data.table`: bounded supplied-row filtering, grouping, compensated
  totals, mean/median/min/max/population standard deviation, invalid-row counts
  and escaped self-contained SVG chart output. No generated code is executed.
- Registered `source.package`: validated relative-path UTF-8 source maps, bounded
  files/bytes and approval-gated, atomic, workspace-scoped artifact creation.
  ZIP packaging never executes code or writes a repository. Generated projects
  have not been tested merely because they can be downloaded.
- Artifact JSON/CSV exports alongside existing Markdown/PDF/DOCX/XLSX; CSV formula
  prefixes are escaped. Authenticated source ZIP download and real Workforce
  download controls. Overview exposes availability, not private source bodies.
- Existing server-side agent grants, configuration snapshots, immutable approvals,
  audit/checkpoint transactions and tenant authorization remain in the dispatch
  path. Data Analysis template includes the new deterministic tool.
- No dependencies, database schema changes, network permissions, paid services,
  Docker socket mounts or external deployment introduced.

Files: backend/foxory/advanced_files.py, agent_tools.py, agents.py, agent_api.py;
backend/tests/test_advanced_files.py; frontend/src/Workforce.tsx; status, checklist,
roadmap/changelog and docs/ADVANCED_FILES.md.

## Verification

- Final serialized backend run: **76 passed in 67.49 seconds**, including migration,
  accounts/workspace isolation, Phase 1–3 regressions and 16 new cases for table
  calculations/budgets/escaping, archive paths/integrity, permissions, approval,
  tenant isolation and export API behavior.
- First overlapping backend/build/browser run: **73 passed, one failed** because
  the full-profile parser self-test printed successful denial checks but exceeded
  its 25-second exit timeout. This failure is retained here. The serialized rerun
  passed without changing parser code, security restrictions or time limits.
- **9 Chromium browser journeys passed in 2.3 minutes** against the real backend
  and explicitly labeled deterministic Ollama protocol fixture. Existing chat,
  research, document, account, Council, Workforce and approval journeys passed.
  No new isolated-product-browser or source-ZIP UI journey is claimed.
- Strict TypeScript/Vite build passed (44.69 seconds; main JS 288.41 kB).
- Python compile, pip dependency consistency, git whitespace checks and Docker
  Compose configuration validation passed. No dependency installation was needed;
  no newly introduced dependency licenses require review in this increment.
- Existing Compose app and PostgreSQL reported healthy; Ollama was running.
  No Phase 4 image build, Docker sandbox integration, fresh backup/restore or
  real-model Phase 4 workflow was executed. Earlier Phase 3 results are preserved
  in docs/PHASE3_STATUS.md. All approval/source tests used deterministic fixtures.

## Security and limitations

The managed daemon reports seccomp/cgroup namespaces but no rootless security
option. A rootless Bubblewrap 0.12.0 namespace probe succeeded (restricted mount
tree, network connection returned unreachable). This offers a possible Linux
implementation path, but is not an authenticated manager or a security test suite.
It has not established the isolation required for untrusted code/browser
execution. Disk inspection found 2.3 GB free; a browser runtime was not installed
or provisioned for the product. Neither issue justifies weakening isolation.
The application still has no host-shell or Docker-socket execution capability.
Sandbox manager, isolated coding/test execution, isolated browser sessions,
Computer Mode, presentation export and combined Phase 4 workflows remain absent.
Uploaded table-to-analysis mapping and richer chart/report previews remain work.
Charts are returned as escaped SVG tool data; existing task inspectors show their
serialized output. No new real-model or GPU benchmark is claimed.

The running owner Compose stack was preserved on its accepted Phase 3 image;
new source changes are not installed there. Existing app/database health and
Compose syntax were inspected. Phase 4 image, restart and persistence tests have
not run; earlier Phase 3 evidence remains historical, not Phase 4 verification.
No production readiness, sandbox assurance, Windows/macOS testing or independent
security audit is claimed. Phase 5 is not ready to begin.

## Exact continuation

Continue on development at the latest commit, read this file and
`docs/PHASE4_CHECKLIST.md`, preserve Phases 1–3 and this increment. First implement
an opt-in separately authenticated sandbox manager with fixed execution profiles,
rootless runtime verification, quotas, network-deny defaults, cancellation,
artifact boundaries and malicious-code integration tests. Keep unsupported
execution disabled. Then add isolated Playwright sessions and Python/JS/TS coding
workspaces, connect authorized tools and Computer Mode, verify realistic combined
workflows with local Ollama, perform final image/migration/recovery and regression
tests, update acceptance evidence and commit. Do not begin Phase 5 or publish.
