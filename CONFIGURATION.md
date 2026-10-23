# Configuration

Keep `.env` private and out of source control. `scripts/setup.py` creates unique random values and preserves an existing file. Never paste secrets into chats, memories, documents or logs.

| Variable | Meaning |
|---|---|
| `FOXORY_TOKEN` | Owner bearer token, at least 24 characters; required at startup |
| `POSTGRES_PASSWORD` | Random database secret for Compose; generated hex to avoid URL escaping issues |
| `FOXORY_PORT` | Local published port; default 8000 |
| `SEARXNG_URL` | Optional private search service base URL with JSON enabled |
| `OLLAMA_URL` | Native backend endpoint; default `http://127.0.0.1:11434`; Compose uses `http://ollama:11434` |
| `DATABASE_URL` | SQLAlchemy URL; Compose uses `postgresql+psycopg`; native default SQLite in data directory |
| `FOXORY_DATA_DIR` | Native data directory; default `./data`, Compose `/data` |
| `FOXORY_ALLOWED_HOSTS` | Comma separated trusted hostnames, without ports; default localhost/127.0.0.1/IPv6 loopback/testserver |

Changing an endpoint requires restarting the backend. External LLM providers are unsupported. Ollama and SearXNG use local-network HTTP clients with environment proxies disabled; configure trusted private endpoints rather than public gateways. Search requests leave the workspace through your SearXNG configuration. Review its upstream providers' terms.

Default inference limits: 4096 context, 2048 generated tokens, 180-second HTTP inactivity timeout, one inference at a time. UI allows a context setting up to 32768; support depends on the model. History packing is conservative character budgeting, not exact tokenization. Ollama-reported prompt and output counts are preserved. No hard total token accounting claim is made.

Rate limit: 180 API requests per source IP per minute in process memory. This is a local guard, not a distributed internet abuse defense. Request bodies are capped at 10 MiB plus multipart allowance; uploads at 10 MiB; extracted text at 2 million characters. Spreadsheet import reads cached values, never executes formulas. Images in generated Markdown are suppressed to avoid external tracking fetches.
