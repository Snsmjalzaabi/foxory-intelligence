# Phase 2 of 5 acceptance checklist

Evidence and limitations: [verification record](VERIFICATION.md), [project status](../PROJECT_STATUS.md). Checked means the stated scope was executed, not that v1.0 or production readiness is established.

- [x] Login, revocable sessions, roles and isolated workspaces: API/security tests and real container account/workspace smoke.
- [x] Research question returns real retrieved-source evidence and clickable citations: successful Wikipedia discovery/full-page research; explicit extractive fallback on the final small CPU model profile.
- [x] Deep Research plans, executes, persists, pauses/resumes and cancels: deterministic stage/budget/retry tests plus real container pause/restart/resume/cancel.
- [x] Council compares multiple local models and synthesizes traceable outputs: actual sequential Qwen 0.5B + SmolLM2 135M analyses/comparison/synthesis; parallel capacity controls tested with fixtures.
- [x] Uploaded documents analyzed in restricted parser: seven-format/security tests; real Docker parsing and nomic semantic indexing/retrieval.
- [x] Useful research/document exports: validated PDF/DOCX/XLSX, saved-reference checks and browser download/history flow.
- [x] Actual frontend/backend integration: strict TypeScript/Vite build and seven Chromium tests using the real API with labeled deterministic model fixtures.
- [x] Critical automated regressions pass: 39 backend tests, seven browser tests; tenant/approval/upload/cancellation/duplicate-prevention/migration/security checks included.
- [x] Phase 1 functionality retained: original backend tests and chat/persistence/regeneration/export/documents/approval/council/mobile browser paths pass; upgraded local stack health/persistence check passed.
- [x] PostgreSQL migration0003, session/file/job restart recovery and disposable logical restore pass; preserved original stack migrated separately after backup.
- [x] Dependency/license inventory and operational/security documentation refreshed; no known advisories in executed runtime reviews, with full-image/legal review still outstanding.
- [x] Final working changes committed in the commit containing this checklist; post-commit working-tree status checked separately (`git status --short`, `git log -1`).

No Phase 3 work begun. Unverified: GPU/parallel hardware performance, live SearXNG, Windows/macOS execution, broad source/answer-quality evaluation, independent security audit and clean-host installation matrix. Document uploads require Linux sandbox; vectors are bounded JSON-backed storage. Citations establish saved-source integrity, not claim truth. These limitations are disclosed rather than represented as completed capabilities.
