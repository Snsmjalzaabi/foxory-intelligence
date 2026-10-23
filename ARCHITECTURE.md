# Architecture

FOXORY is a modular monolith: React/TypeScript built with Vite, served from FastAPI, with SQLAlchemy persistence and explicit Alembic migrations. Vite is used instead of Next.js because this local workspace needs no server-rendering service. Compose uses PostgreSQL 17; native development and automated tests use SQLite WAL. PostgreSQL and SQLite share migration 0001. There is no Redis or pgvector dependency yet.

`frontend/src/api.ts` handles authenticated JSON, downloads and SSE. `main.tsx` provides the UI; component extraction is a follow-up maintainability task. `backend/foxory/main.py` owns the HTTP interface, validation and owner authentication. `db.py` owns records, messages and audit events. Documents use established parsers in `documents.py`. `inference.py` speaks the documented Ollama API. `research.py` integrates an administrator-configured SearXNG endpoint. `jobs.py` implements bounded state transitions and optimistic job claims.

The job worker runs as an independent asyncio task inside the single API process, irrespective of browser sessions. **Run exactly one application process/replica.** Restart recovery requeues interrupted read-only inference from the last completed step. Optimistic payload comparison prevents a late result from overwriting cancellation or pause. Each step has a 240-second timeout. Manual retries stop after three failed attempts. Research performs at most two searches; council uses at most four models plus one synthesis. There are no autonomous unbounded agent loops. A shared semaphore serializes chat and background inference, and Compose limits Ollama to one loaded model and one parallel request.

Jobs use deterministic IDs from idempotency keys and a unique primary key. No workflow side effects exist. Approval records contain a full immutable draft snapshot; approval decisions do not activate external actions. A future executor must independently bind permission, exact action parameters, recipient, approval expiry, and idempotency before adding consequential tools.

## Trust boundaries

1. Browser → bearer-authenticated same-origin API. Token lives in tab session storage, never URLs or ordinary memory records.
2. API → private database, uploads and configured Ollama/SearXNG. Endpoints come only from operator environment, not user-supplied URLs.
3. Retrieved text → untrusted context. No model output can invoke a tool or host shell.
4. Uploads → bounded parsing without macro execution. Extraction currently occurs in a thread, not an isolated parser process; hostile parser resource exhaustion remains a release blocker.

One owner token represents one local workspace. This is not organizational isolation, password authentication, session expiry or RBAC. No multi-user claim is made. Audit records are durable but not tamper-proof against an infrastructure administrator. Generated output is untrusted. Source lists use only retrieved metadata, but snippet evidence is not factual verification.

## Planned evolution

Replace generic JSON records with typed domain tables and normalized lead keys; isolate document parsers; add user/password/OIDC authentication and workspace-scoped authorization before multi-user operation; split durable workers with leases before replication; add verified content retrieval under SSRF/robots/network policy; introduce embeddings only with model capabilities and measured hardware tests. Sandboxes must not mount the host Docker socket.
