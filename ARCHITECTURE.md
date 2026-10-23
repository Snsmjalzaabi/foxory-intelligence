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

Adding multi-process workers requires leases and scheduling changes; it is not enabled. Consequential tools remain unavailable. Draft approval records immutable snapshots and one decision, never external execution.

## Evidence limitations

Credibility scores are transparent metadata heuristics. Conflict quotations must exist in two saved sources, but the contradiction interpretation is model analysis. Citation verification proves saved reference identifiers/content hashes, not factual correctness or current source availability. When a model omits valid citations, an explicitly extractive fallback returns saved passages instead of attaching arbitrary references to unsupported prose. Character budgets are not exact tokenizer accounting; truncation warnings are retained.

## Security/release follow-ups

Independent penetration/sandbox review; image/native dependency SBOM/license/digest review; encryption-at-rest guidance; global tenant storage quotas; larger-library vector indexing; distributed abuse limits and worker leases; accessibility/load testing; Windows/macOS Docker compatibility and actual reference GPU measurements. Public hosting, code/browser execution, live email and autonomous mutation are not enabled by this phase.
