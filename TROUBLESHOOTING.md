# Troubleshooting

- Startup reports missing FOXORY_TOKEN: run `python scripts/setup.py`; native development needs the variable explicitly exported. Token must be at least 24 characters.
- Unauthorized: use FOXORY_TOKEN from the current private `.env`, not the database password. Lock and unlock after rotation.
- Ollama offline: inspect `docker compose logs ollama`; native backend defaults to localhost:11434. No installed model is an empty state, not a service error.
- Chat or job failure: inspect app/Ollama logs; reduce model size or context. The API deliberately returns sanitized provider errors. Research also needs SearXNG JSON enabled.
- Model downloads consume storage; check disk capacity and model license. Download is an explicit operation. No automatic purchases or paid API fallback occur.
- Search fails: check your configured SearXNG endpoint and its `/search?q=test&format=json` access. No public fallback is configured.
- Research source URLs exist but evidence is weak: this release uses search snippets only. Inspect the source yourself; generated interpretations are not verified facts.
- Upload rejected: only listed formats are accepted, max 10 MiB. UTF-8 required for text; macros, encrypted PDFs, malformed JSON and oversized archives are rejected. Scanned PDFs need OCR, which is unsupported.
- Rate limit: wait a minute, reduce polling or separate unrelated clients. Shared proxies use one source-IP quota.
- `Invalid host header`: access localhost/127.0.0.1. Deliberately changing FOXORY_ALLOWED_HOSTS does not make public deployment supported.
- Migration failure: preserve volumes, inspect logs, restore a verified backup rather than deleting data. Do not run several migrating app instances.
- Docker cloud TLS error: pass the environment CA as a build secret as documented. Never disable certificate verification.
- Draft approval did not send: expected; there is no external executor in this release.

- In managed cloud containers with an HTTP proxy, Ollama's CLI may try to use its bind address `0.0.0.0` through the proxy. Use `docker compose exec -T -e OLLAMA_HOST=http://127.0.0.1:11434 ollama ollama list` (or `pull MODEL`) to address the local server explicitly. Keep the HTTPS proxy for registry traffic and trust the environment CA; do not disable TLS verification. This does not change the application endpoint, which uses the private service name.
- Cloud Docker VFS storage can duplicate large image layers during builds/recreation. A 32 GB task filesystem exhausted space during this verification. Remove only task-owned unused build artifacts; never prune persistent data/model volumes as a troubleshooting shortcut.

### Computer Mode reports disabled

Check authenticated `/api/computer/capabilities` and the separate manager's logs.
Both sides need deliberate opt-in and the same private key; the manager must pass
its actual namespace/seccomp preflight under a non-root account. A failed probe
keeps execution disabled. The application container's loopback is not host
loopback. Use the [documented topology](docs/SANDBOX_MANAGER.md), not a Docker socket
mount, root execution or an unsealed subprocess fallback. Browser/JS execution
is currently unavailable and cannot be enabled by setting the Python flags.


Phase 4 now connects optional JavaScript/TypeScript and offline Playwright profiles
through the authenticated manager, approval gates and Computer Mode. They remain
disabled by default and require actual Ubuntu isolation verification; Codex tests
use a mocked OCI boundary. See [host activation and acceptance checklist](docs/SANDBOX_HOST_VERIFICATION.md)
for pinned image builds, lifecycle/ownership controls and remaining limitations.
