# Roadmap to v1.0

The owner’s current five-phase delivery plan supersedes the original seven-phase grouping below. Phase 1 was accepted at `3452acd`; Phase 2 acceptance is tracked in [docs/PHASE2_CHECKLIST.md](docs/PHASE2_CHECKLIST.md). The older grouping is retained for traceability; unchecked original items are not silently claimed complete. Phase 3 is not started.

Checked items identify implemented/tested slices, not completion of entire phases. PROJECT_STATUS.md contains exact evidence.

## Phase 1 — foundation (partial)
- [x] Modular source layout and original responsive React UI
- [x] Persistent chat/history/model selection and exports
- [x] Ollama HTTP adapter and SSE integration tests
- [x] Alembic SQLite migration roundtrip
- [x] Local-only Compose definition and persistent volumes
- [x] Single-owner bearer authentication and host/origin/body/rate controls
- [x] Password authentication, session lifecycle, RBAC and workspace authorization tests (OIDC remains optional/unimplemented)
- [x] Linux cloud CPU Ollama/qwen2.5:0.5b streaming and persistence smoke recorded
- [x] Local Compose startup and final-image restart/persistence smoke recorded
- [ ] Fully automated pristine installation on a clean supported Linux host
- [x] PostgreSQL revision 0002 and logical dump/restore verification (uploads separately tested with SQLite)

## Phase 2 — research (experimental slice)
- [x] Configured SearXNG search with deduplicated source metadata
- [x] Bounded durable two-search job, history, cancellation and report export
- [x] Citation IDs filtered against retrieved references
- [x] SSRF-restricted full-page retrieval, robots directives and extraction; operator remains responsible for applicable source terms
- [x] Adaptive subquestions, source-date/relevance heuristics, quoted conflict evidence and enforced research budgets
- [ ] Independent factual claim verification and measured answer-quality benchmark
- [x] Live search/page integration and saved-reference integrity checks
- [ ] Human evaluation of claim-to-citation correctness across a research benchmark

## Phase 3 — documents and memory (partial)
- [x] Bounded parsers for seven formats, storage and originals download
- [x] Keyword retrieval and evidence-context questions
- [x] Editable memory records and workspace export
- [x] Offline SQLite backup/restore utility with automated roundtrip test
- [x] Isolated Linux parser processes and adversarial upload/resource tests
- [ ] Optional malware scanner integration
- [x] Optional local embeddings and workspace-isolated semantic search
- [ ] pgvector scaling adapter (current bounded vectors are JSON-backed)
- [x] DOCX/XLSX/PDF research/document exports
- [ ] Structured calculation execution engine

## Phase 4 — agents (draft-only slice)
- [x] Persistent agent definitions with explicit zero tool permissions
- [x] Sequential council, independent results and synthesis
- [x] Durable checkpoints, idempotent job submission, pause/resume/cancel and retry ceiling
- [x] Immutable draft review snapshots, single decision and audit events
- [ ] Typed task dependencies/delegation, resource budgets and worker leases
- [ ] Permission-scoped tools with approval-bound execution and side-effect idempotency

## Phase 5 — business (partial)
- [x] Nine reusable draft-only role templates
- [x] Dashboard from real operational data, no demonstration records
- [x] Basic leads with edit/status/follow-up date, duplicate checks and CSV export
- [x] Communication drafts and explicit review
- [ ] Normalized organizations/contacts/opportunities/campaigns and atomic CRM import
- [ ] Independent timezone-aware scheduler, retries and notifications
- [ ] Least-privilege encrypted IMAP/SMTP/OAuth connectors

## Phase 6 — computer/development (unavailable)
- [ ] Restricted sandboxes without Docker socket or privileged containers
- [ ] Network allowlists, quotas, isolated sessions and explicit form submission approval
- [ ] Approved Git worktrees, test runner, patches and PR preparation
- [ ] Isolation escape, permission and destructive-action tests

## Phase 7 — stabilization (in progress)
- [x] Public-distribution documentation and Apache-2.0 source license
- [ ] Dependency/SBOM/license and security review finalized
- [ ] CI and release-preparation workflows verified in a hosted repository
- [ ] Windows/macOS compatibility and NVIDIA reference-machine measurements
- [ ] Independent security review, accessibility audit, load and recovery tests
- [ ] All definition-of-done gates satisfied before proposing v1.0 release
