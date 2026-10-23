# Architecture

FOXORY remains a modular monolith: React/strict TypeScript/Vite served by FastAPI; SQLAlchemy/Alembic; PostgreSQL in Compose, SQLite WAL for local development/tests. No paid inference provider, host shell, Docker socket, external messaging executor or browser tool is exposed to models.

## Modules and boundaries

- `auth.py`, `scope.py`, `db.py`: Argon2id accounts, opaque revocable session digests, membership/roles, scoped ORM criteria and guarded writes. Default scope is unauthorized. Public bootstrap works only before the first account. Existing data remains in `local` under migration 0003. Messages are constrained through their owning conversation; exports, audit and optimistic updates use the same tenant boundary.
- `main.py`: bounded API requests, trusted hosts/origins, CSRF checks, installation vs workspace administration, SSE and endpoint wiring.
- `inference.py`, `resources.py`: documented Ollama protocol, serialized generation/embedding by default, explicit conservative memory guard for opt-in parallel council. No GPU inference is assumed from model metadata.
- `research.py`, `web.py`, `pinned_transport.py`: SearXNG or default documented Wikipedia search; validated/pinned public HTTP retrieval and TLS proxy handling, robots/pacing, bounded content, metadata credibility and reference hashes. Every source is untrusted data. Proxy routes and certificate verification are preserved; no unpinned fallback exists.
- `intelligence.py`, `jobs.py`: research planning/search/read/comparison/write stages, one external operation per durable step, manual bounded retries and cancellation. Follow-up queries are bounded. Reserved dispatch counts survive interrupted/failed calls. A wall-clock deadline includes pauses. Council stores independent results, separate comparison and synthesis. Evidence/claim checks are explicitly distinguished.
- `parser_worker.py`, `parsing.py`, `documents.py`: preload trusted libraries/codecs, activate Linux seccomp/resource limits, then parse only supplied bytes in a minimal-environment subprocess. Filesystem/network/process access is denied. The parent enforces timeout/output bounds; unavailable policy fails closed.
- `knowledge.py`: scoped chunk retrieval; optional installed Ollama embedding model, stored vectors and text hashes, cosine similarity. No embedding model is automatically downloaded. Indexing is limited to 200 chunks/document and serialized with generation. Intended for modest libraries; pgvector is a future scaling option.
- `reports.py`: plain-data PDF, Word and XLSX writers. No generated macros/code; spreadsheet formula prefixes are neutralized.
- Frontend `Accounts.tsx` and `IntelligenceUI.tsx` provide login/workspaces, source inspection, budgets, exports, indexing and saved-reference checks. Existing workspace features remain in `main.tsx`.

## Durability and topology

Run exactly one API process/replica. The worker runs independently of browser sessions inside that process. Restart recovery requeues interrupted read-only calls from saved checkpoints. Compare-and-swap prevents cancelled/paused jobs from being overwritten by late results; active coroutines are cancelled. Jobs execute within their stored workspace and validate the creator's current membership. New workspace administrators do not inherit global model-management privileges. Generic record endpoints cannot forge jobs/approvals/documents.

Adding multi-process workers requires leases and scheduling changes; it is not enabled. Phase 3 tools are a fixed registry with explicit schemas/grants. Local writes require immutable expiring approval, live configuration checks and a transaction committing the deterministic effect, approval consumption and checkpoint together. External actions remain unavailable. Draft approval remains a review-only snapshot.

## Evidence limitations

Credibility scores are transparent metadata heuristics. Conflict quotations must exist in two saved sources, but the contradiction interpretation is model analysis. Citation verification proves saved reference identifiers/content hashes, not factual correctness or current source availability. When a model omits valid citations, an explicitly extractive fallback returns saved passages instead of attaching arbitrary references to unsupported prose. Character budgets are not exact tokenizer accounting; truncation warnings are retained.

## Security/release follow-ups

Independent penetration/sandbox review; image/native dependency SBOM/license/digest review; encryption-at-rest guidance; global tenant storage quotas; larger-library vector indexing; distributed abuse limits and worker leases; accessibility/load testing; Windows/macOS Docker compatibility and actual reference GPU measurements. Public hosting, code/browser execution, live email and autonomous mutation are not enabled by this phase.

## Bounded autonomous agents

`agents.py`, `agent_tools.py`, `agent_api.py`, `agent_memory.py` and `scheduler.py` extend the existing job/Record envelopes. No schema migration is required beyond revision0003; existing unique record IDs provide schedule/task/effect idempotency. The graph plans validated steps, executes each under its assigned agent’s snapshot and current grants, checks quality and consolidates actual outputs. User-reviewed plans use the same validator. Malformed model JSON is retried within configured limits; unavailable tools fail closed. Tool results are untrusted evidence, not commands.

The API lifespan runs a scheduler coroutine and 1–2 configured task loops. Local inference remains serialized. Scheduler dispatch/history and local effects/checkpoints use atomic transactions; interrupted read-only model/tool calls may replay. One API process/replica remains required. Agent facts are user-approved but not independently verified; generated summaries are explicitly unverified and expire under retention settings. See docs/AGENT_EXTENSIONS.md for schemas, extension examples, scheduling semantics and boundaries.

## Optional Phase 4 execution boundary

`computer_api` and `sandbox_client` connect existing scoped jobs/approval state to
a separately deployed native Linux manager. The app performs no local execution.
`commit_agent` atomically consumes a sandbox approval into a durable dispatch grant;
a later worker step uses the manager's idempotent protocol. The manager has its
own private state/lock, startup isolation preflight and bounded single-process
Python profile. Computer Mode observes the real state and artifacts. Browser and
JavaScript remain disabled. See [manager design](docs/SANDBOX_MANAGER.md).


Phase 4 now connects optional JavaScript/TypeScript and offline Playwright profiles
through the authenticated manager, approval gates and Computer Mode. They remain
disabled by default and require actual Ubuntu isolation verification; Codex tests
use a mocked OCI boundary. See [host activation and acceptance checklist](docs/SANDBOX_HOST_VERIFICATION.md)
for pinned image builds, lifecycle/ownership controls and remaining limitations.
