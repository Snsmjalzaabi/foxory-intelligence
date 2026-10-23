# FOXORY Intelligence · Community Edition

A local-first AI workspace for conversations, web research, document intelligence and permission-scoped local agents. Your infrastructure, your data, your models. No paid AI API is required or enabled.

**Pre-release.** Phase 1 was accepted at `3452acd`; Phase 2 adds accounts/workspaces and advanced research; Phase 3 adds bounded agents and scheduling (see its acceptance record). v1.0 production readiness is not claimed. See [PROJECT_STATUS.md](PROJECT_STATUS.md), [Phase 2 acceptance](docs/PHASE2_CHECKLIST.md) and [ROADMAP.md](ROADMAP.md).

## Start locally

Requires Docker Engine + Compose v2 and Python 3.11+ for local secret generation.

```sh
python scripts/setup.py
docker compose up -d --build
```

Open <http://localhost:8000>. On first run, enter `FOXORY_TOKEN` from your private `.env` and create an administrator username/password. Existing Phase 1 data stays in the Local workspace. **The bootstrap token stops granting API access once an account exists.** Subsequent login uses a revocable, HttpOnly session. Do not publish `.env`.

In Settings, explicitly download a completion model (for example a small Qwen model) after reviewing its license. Select an installed model for Chat. Download an embedding-capable model separately if semantic indexing is wanted. No model weights are bundled or downloaded automatically. Model families/variants have different terms and capabilities.

The app binds to `127.0.0.1`; PostgreSQL/Ollama have no published ports. Named volumes survive `docker compose down`. Run **one API process/replica**. Linux containers are required for restricted parsing; native Windows/macOS parsing fails closed. Docker Desktop compatibility/GPU performance remain unverified.

## Working capabilities

- Streaming local Ollama chat, stop/regenerate, searchable persistent history and Markdown export.
- Account login/logout, 12-hour server sessions, Argon2id password hashes, CSRF protection, workspaces, memberships and admin/editor/viewer access. The initial administrator controls installation-wide model mutation; workspace administration does not grant that permission.
- Real search through configured SearXNG, or the free documented Wikipedia MediaWiki API by default. Wikipedia discovery has encyclopedia-only breadth; use SearXNG for wider web discovery. There is no silent fallback if configured SearXNG fails.
- Real public HTML/text retrieval: public-address DNS pinning, verified TLS through configured proxies, validated redirects, robots/indexing directives, pacing, limits, source snapshots/hashes, relevance ranking and date metadata.
- Durable Deep Research: model planning, subquestions, multiple queries, per-operation checkpoints, follow-up searches, comparison, exact-quotation conflict evidence and report synthesis. Pause/resume/cancel, retries and explicit network/time/input budgets.
- Traceable Model Council: independent local-model analyses, disagreement/evidence comparison and synthesis. Sequential default; parallel analysis needs operator opt-in and measured conservative memory headroom.
- Restricted PDF/DOCX/XLSX/CSV/TXT/Markdown/JSON parsing. Workspace document retrieval, optional local Ollama embeddings/cosine search, multi-document research and grounded source references.
- Saved-reference checks and Markdown/PDF/Word/XLSX reports. Citation integrity checks validate IDs and saved hashes, **not claim truth**. When model synthesis lacks valid references, the report is explicitly labeled extractive source evidence rather than unsupported prose.
- AI Workforce: bundled local templates, configuration wizard, explicit tool/document/specialist grants, durable tasks and timelines, model traces, memory, schedules and approval center. Local writes require an administrator’s approval of exact immutable arguments; external actions remain unavailable.
- Existing projects/memory, basic CRM, business drafts, audit history and dashboard remain available. Draft reviews remain review-only.
- Community extension contracts and examples: [AGENT_EXTENSIONS.md](docs/AGENT_EXTENSIONS.md).

## Limits

This is not independently security-reviewed or approved for public hosting. Live email, browser/code execution, unapproved workspace writes, parallel GPU verification, OCR and spreadsheet formula execution remain unavailable. Scheduling is fixed-interval and single-process; agent planning/delegation is bounded and can fail visibly on small models. Parser isolation requires Linux/libseccomp and fails closed. Vectors are stored with document records and scanned locally; indexing is bounded to 200 chunks/document and is intended for modest workspaces, not a large-scale vector database.

Source credibility is a transparent metadata heuristic. Contradiction interpretation is model analysis; matching quotations only proves that the text was present in saved evidence. Reports can remain incomplete or incorrect. Restricted sources are declined; there is no CAPTCHA, authentication or paywall bypass. Deleting an original document does not purge previously saved research snapshots/audit records.

See [INSTALLATION.md](INSTALLATION.md), [CONFIGURATION.md](CONFIGURATION.md), [SECURITY.md](SECURITY.md), [DEVELOPMENT.md](DEVELOPMENT.md) and [ARCHITECTURE.md](ARCHITECTURE.md). Apache-2.0 covers original source; dependency/image/model terms remain separate in [docs/DEPENDENCIES.md](docs/DEPENDENCIES.md). Nothing has been published externally.
