# FOXORY Phase 2 of 5 — in progress

Baseline accepted by owner: development / 3452acd. Phase 1 history is preserved in docs/PHASE1_STATUS.md. No Phase 3 work, external publication, paid service or external business action is authorized or enabled.

## Implemented increment

- Argon2id passwords, HttpOnly/SameSite session cookies, hashed/revocable server-side sessions, CSRF protection, initial administrator setup and bootstrap-token retirement.
- Workspace creation/membership and admin/editor/viewer authorization, fail-closed ORM tenant filters across records/messages/audit, scoped worker execution and workspace-specific idempotency keys. Installation model mutation is restricted to the initial administrator.
- Real SearXNG adapter and free default documented Wikipedia/MediaWiki search API. Full public-page retrieval with DNS pinning, TLS hostname preservation through the configured proxy, public-IP-only validation, redirect validation, robots enforcement, pacing and response-size restrictions.
- Model-generated bounded research plans, per-operation checkpoints, follow-up evidence, relevance/metadata credibility heuristics, content/URL deduplication, source-date extraction, exact-quotation conflict evidence, saved hashes and reference validation. Claim truth is not implied by integrity validation.
- Separate council analysis/comparison/synthesis outputs; sequential default, optional operator/memory-guarded parallel execution.
- Linux document subprocess with resource limits, seccomp denial of filesystem/network/process access, fail-closed behavior; seven existing formats preserved. Optional Ollama embedding index and multi-document evidence; PDF/DOCX/XLSX exports.
- Integrated accounts/workspaces, research controls/budgets, source previews, saved-reference checks, exports and semantic-index controls in React UI.

## Executed verification so far

- 28 backend tests passed after workflow fixture updates (61.26 seconds).
- 6 Playwright browser tests passed (48.2 seconds), including existing chat/documents/approvals/council/mobile and new login/workspace-switch/logout behavior. Model HTTP fixture explicitly labeled; not inference-quality evidence.
- Strict TypeScript/Vite production builds passed. Newer UI changes require final rebuild.
- Sandbox self-test denied host file read, socket creation and process execution; actual isolated PDF/DOCX/XLSX/JSON parsing passed.
- Real public retrieval succeeded through the managed HTTPS proxy for example.com (171 readable characters) and Wikipedia RAG page (22,882 characters), with saved SHA-256 hashes and TLS validation enabled.
- Real Wikipedia search API returned three actual page URLs for retrieval augmented generation.

## Still required before declaring Phase 2 complete

Final full tests after all changes; stronger SSRF/TLS proxy/rebinding/robots/budget/citation/security tests; session expiry/revocation and editor/parallel guards; real model research/embedding/council integration; current Docker image with libseccomp and PostgreSQL migration/restart/restore smoke; dependency/license refresh; complete installation/security documentation and acceptance checklist. Existing local Compose container is still Phase 1 until deliberately replaced with the Phase 2 build.

## Known boundaries

One API process/replica remains required. SQLite is a local development option; Compose uses PostgreSQL. Parallel execution is disabled unless explicitly configured and conservative memory headroom is measured; no GPU claim. Credential encryption at rest/host hardening and independent security review are outside these implementation checks. Source credibility and contradiction interpretation are heuristics/model analysis, not factual verification. Default Wikipedia search has encyclopedia-only breadth; configure SearXNG for broader discovery. Unavailable or restricted sources are declined; no paywall/access-control bypass. Linux sandbox is required for uploads; no unsafe native Windows/macOS fallback. Computer control, code execution and outbound business communication remain unavailable.
