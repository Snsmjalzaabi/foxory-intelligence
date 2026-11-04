# FOXORY 8.0 — Local edition

FOXORY 8.0 is the first release of the local edition: a complete private AI workspace that
runs on your own computer with free local models. See the [README](../../README.md) to install
and the [user guide](../GUIDE.md) for each feature.

## What is new since the Phase 4 development line

- **Local install profile** (`compose.local.yaml`, `scripts/foxory.py`): one command to check,
  start, stop and automate; the app on `http://localhost:3636`; bundled Ollama and private
  SearXNG; an NVIDIA GPU used automatically when Docker can, CPU otherwise.
- **Models:** recommended catalogue with hardware fit and licenses, one-click install and
  uninstall, task-aware routing, optional CPU llama.cpp companion, and a local quality check
  that steers routing.
- **Chat:** file and image attachments, document reader and downloads, chat-driven actions,
  schedules and skills, conversational memory.
- **Voice:** local speech-to-text (whisper.cpp) and read-aloud replies.
- **Work:** project spaces, business pipeline, AI Workforce with approval gates, project
  automation, tested data-only skills and an owner-reviewed self-improvement lab.
- **Reach:** notifications (in app, desktop, optional self-hosted ntfy), installable web app
  with private phone access through Tailscale, and a read-only watched folder.
- **Control:** a matching remove for every add, profiles for names and regional defaults,
  appearance editor, backups with restore verification and signed local updates.

## Upgrading from the development branch

The original stack (`compose.yaml`, port 8000) is unchanged. The local edition uses its own
Compose project (`foxory-local`) and fresh volumes, so data from the original stack is not
migrated automatically; see [docs/DATABASE_UPGRADE.md](../DATABASE_UPGRADE.md).
