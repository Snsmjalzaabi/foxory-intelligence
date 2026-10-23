# FOXORY Intelligence · Community Edition

A local-first AI workspace for conversations, document questions, research and draft-only business assistants. Your infrastructure, your data, your models. No paid AI API is required or enabled.

**Pre-release v0.1.0. Target v1.0 is not complete. Single owner only; do not expose publicly or use for shared organization access.** See [PROJECT_STATUS.md](PROJECT_STATUS.md) for executed checks and [ROADMAP.md](ROADMAP.md) for release gates.

## Start locally

Requires Docker Engine and Compose v2, Python 3.11+ for setup, available disk space, and internet access to download dependencies and model weights.

```sh
python scripts/setup.py
docker compose up -d --build
```

Open <http://localhost:8000>. Enter `FOXORY_TOKEN` from your private `.env` file. Go to Settings, test Ollama connectivity, and explicitly download a model after reviewing its license. Model weights are not included. CPU is the default. See [INSTALLATION.md](INSTALLATION.md) for NVIDIA, native development, backups, and uninstall.

The setup step generates unique credentials; startup intentionally refuses missing secrets. The application port binds only to `127.0.0.1`; database and Ollama have no published ports. Persistent named volumes survive `docker compose down`.

## Included

- Ollama chat streaming, stop, regenerate, history, rename, delete, search and Markdown export.
- Safe Markdown rendering, code highlighting, themes and responsive navigation.
- Model inventory, metadata/capabilities, explicit download and confirmed removal.
- Upload/extract PDF, DOCX, XLSX, CSV, TXT, Markdown and JSON; bounded keyword retrieval and document Q&A.
- Experimental search-snippet research with retrieved reference lists and resumable bounded jobs.
- Sequential Model Council with independent analyses and synthesis. Consensus is not verification.
- Nine reusable draft-only agent templates, persistent job checkpoints, cancellation, pause/resume and bounded manual retries.
- Editable memories and projects, basic lead CRM with duplicate detection and CSV export.
- Business drafts, immutable review snapshots, explicit approval/rejection and audit trail. Approval does **not** send or execute anything.
- Command Center using actual backend data; workspace JSON export.

## Explicit limitations

Research requires your own SearXNG instance with JSON output enabled; it currently reads search snippets, not full pages. Citation identifiers are checked against retrieved results; this does not verify claims, quotations, dates, or source reliability. There is no semantic/vector retrieval, OCR, spreadsheet formula calculation, scheduler, tool execution, browser control, Git workflow, live email integration, organizational RBAC or multi-workspace support. The owner token grants access to the entire one-owner workspace. Computer and outbound communication are unavailable.

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md), [ARCHITECTURE.md](ARCHITECTURE.md), [SECURITY.md](SECURITY.md), and [CONFIGURATION.md](CONFIGURATION.md). No repository URL is claimed; nothing has been published.

Source is licensed under Apache-2.0. Dependency and model terms remain separate; see [docs/DEPENDENCIES.md](docs/DEPENDENCIES.md). No third-party artwork is bundled.
