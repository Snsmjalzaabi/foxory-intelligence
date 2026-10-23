# FOXORY Phase 3 of 5 — verified development milestone

Date: 2026-10-23. Branch: development. Accepted Phase 2 baseline: 7d1cd05a0238fae6ff762df79fbb1f1e42aa113f. Phase 2 history is preserved in docs/PHASE2_STATUS.md. Phase 3 implementation increments: 674135a, 24ec0c0 and 109ccc5; the final verification commit contains this record. Use git log -1 for its exact hash.

All twelve Phase 3 acceptance checks passed within the documented bounded, single-process scope. v1.0 is not complete; production readiness is not claimed. Phase 4 has not started.

## Implemented

- Validated agent names, roles, purposes, instructions, model assignments, explicit fallback models, tools, document scopes, specialist selections, budgets and retention.
- Bundled General Coordinator, Research, Writing, Coding, Data Analysis, Document, Planning, Quality Review and Workflow templates. Coding is drafting only.
- Persisted plan/execute/review/consolidate state graph; structured Ollama output with server validation; backward-only dependencies and bounded JSON references to actual prior results; independent specialist grants and configuration snapshots.
- Explicit tool registry for public search/page retrieval, saved research references, authorized documents, workspace memory/projects, bounded arithmetic/statistics and approval-gated report/project/task creation. No arbitrary plugins, host shell, unrestricted filesystem or privileged execution.
- Coordinator and specialist limits, reserved model-call counts, deadlines, bounded retries, traceable model outputs, audit/checkpoint history, pause/resume/cancel and restart recovery. Default one worker, configurable two; local model inference remains serialized.
- Immutable approvals binding objective, job, plan/config hashes and resolved arguments. Expiration, rejection, cancellation revocation, stale reuse prevention and atomic effect/approval/checkpoint transactions. External sending, publication, purchases and privileged actions have no registered handler.
- Workspace-scoped unverified task summaries; explicit user-approved facts, search, editing/deletion and retention expiry audits.
- Durable one-time/fixed-interval schedules, IANA timezone handling, missed-run coalescing/skipping, retries, history, pause/resume, pending limits and deterministic due/job IDs. Scheduler operates independently of browser sessions.
- Connected Workforce templates/wizard/configuration, model inspection, grants, tasks/timelines/delegation, schedules, approvals, memory and downloads. One scoped overview request replaces excessive multi-request polling.
- Seven-format document support preserved. Small text formats now use a stdlib-only sealed parser profile; PDF/Office trusted imports are selected by whitelisted extension. Profile mismatches fail closed. Seccomp and size/memory/CPU/time/output restrictions remain enforced.

Key implementation files: backend/foxory/agents.py, agent_tools.py, agent_api.py, agent_memory.py, scheduler.py, jobs.py, inference.py, main.py, text_documents.py, documents.py, parsing.py and parser_worker.py; frontend/src/Workforce.tsx and main.tsx; backend/tests/test_agents.py and frontend/tests/workspace.spec.ts. Configuration, architecture/security/development docs, verification scripts and acceptance records were updated.

## Executed verification

- **60 backend tests passed in 63.19s**: original regressions plus 21 agent/parser checks. Includes accounts/tenant isolation, grants, approvals, cancellation, duplicate prevention, restart recovery, schedules, malformed plans, injection resistance, safe references, actor limits, two-worker claims, nonblocking authentication and minimal-parser sandbox/profile mismatch.
- **9 Chromium browser tests passed (1.6m)**: chat/persistence/regeneration/export, document validation/Q&A, draft approvals, Council, mobile/theme, account/workspace switching/logout, semantic research/references/exports, Workforce delegation/memory/schedules and approval-gated writes. Uses real application APIs with a labeled deterministic model protocol fixture.
- Strict TypeScript/Vite production build passed; main JS approximately 288kB. Python compile checks, pip check and CPU/GPU Compose syntax validation passed. No runtime dependencies were added; Phase 2 dependency/license inventory remains applicable, not full-image/legal clearance.
- Actual **qwen2.5:0.5b CPU** workflow: coordinator generated a validated plan, delegated 15% of 2400 to a separate analyst, actual arithmetic returned **360**, then quality review and consolidation completed in three model calls. Memory stayed unverified; four report formats downloaded. An internal project waited for approval, committed once and rejected approval reuse. A one-time task ran without a browser.
- Docker restart/restore build 637314f1 passed session, original document, paused task, resume/cancel and once-only schedule recovery; PostgreSQL logical restore preserved revision0003, accounts, memberships, agents, jobs, schedules, approvals and memory. No new schema migration was needed: existing scoped Record envelopes and unique IDs are used. Migration preservation/roundtrip tests passed.
- Final image **sha256:b547c82d6dc046d95137d8255733f152871e88ccd8b777e6c7844ed86c793106** passed real TXT/Markdown/CSV/JSON/PDF/DOCX/XLSX extraction, byte-for-byte original downloads and malformed JSON rejection. Runtime hashes for twelve modules and frontend index matched source/build artifacts; non-root10001, read-only root, init and absence of source/socket mounts verified.
- Preserved local owner stack restored and healthy at localhost8000. Authenticated persistence/delete and actual CPU chat streaming/persistence passed again (**3 output tokens**). Temporary conversations/documents removed; original database remained revision0003 with zero records/users. Owner account setup is deliberately left to the owner.
- Disposable test installation/database/volumes were removed after private backup. Owner PostgreSQL, uploads and model volumes retained. Private test credentials removed. No external deployment, public publication, paid service or business communication occurred.

## Findings and limits

Earlier contended runs had parser budget rejection and browser timing failures. Fixed excessive polling, duplicate controls, selector labels, database I/O on the API loop, approval/legacy/budget issues and expensive parser preloading. Browser assertions now wait for actual422 responses and actual status badges rather than the word “completed” in help text; CI timing allowances are explicit. No security/resource limit was relaxed. Full history is in docs/VERIFICATION.md.

The 0.5B model omitted a requested writing subtask in an earlier attempt; that run failed its assertion and is not counted as a successful three-agent demonstration. Complex objectives can be under-planned; inspect coverage/review notes and use reviewed plans or a more capable local model. Workflow completion does not establish factual correctness. Context may be truncated to local budgets.

Only one API process/replica is supported. Delegation uses bounded preplanned graphs, not recursive agent trees. UI overview/history is intended for modest workspaces. Recurrence is fixed elapsed-minute scheduling, not wall-clock cron. Parallel job claims are tested; real alternate-model fallback/GPU execution and reference hardware performance are not verified. Windows/macOS execution, live SearXNG, broad answer-quality evaluation, clean-host installation matrix, independent security audit and full-image/license clearance remain release work. Linux/libseccomp is required for uploads. Phase 2 vector-storage/proxy/credibility limitations remain documented.

## Next action

Phase 3 checklist: docs/PHASE3_CHECKLIST.md. Extension contracts: docs/AGENT_EXTENSIONS.md. Ready for the next Phase 4 engineering directive, which must introduce its own isolated execution/browser boundaries. No Phase 4 execution capability is enabled here.
