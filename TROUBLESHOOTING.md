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
