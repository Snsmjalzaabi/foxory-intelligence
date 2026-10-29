# Configuration

Keep `.env` private and out of source control. `scripts/setup.py` creates unique random values and preserves an existing file. Never paste secrets into chats, memories, documents or logs.

| Variable | Meaning |
|---|---|
| `FOXORY_TOKEN` | Bootstrap token, at least 24 characters; required at startup and retired for API access after account creation |
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

## Phase 2 accounts and intelligence

`FOXORY_TOKEN` is now the one-time bootstrap credential. It grants legacy local-only API access only while no account exists. First-run `/api/auth/setup` creates the initial administrator, preserves the Local workspace and issues an HttpOnly, SameSite=Strict session cookie. Session tokens are stored as SHA-256 digests, expire after 12 hours and are revoked on logout. Passwords use Argon2id (64 MiB, three iterations, one lane). Login/setup are limited to 12 attempts per source IP/minute and hashing has two execution slots.

Cookie-authenticated mutations require `X-CSRF-Token`, obtained from login or `/api/auth/me`. `X-Workspace-ID` selects a workspace, and membership/role are checked server-side on every request. Workspace viewers read; editors write; administrators manage membership/approve drafts. Only the initial administrator mutates installation-wide Ollama models. Membership changes apply immediately without revoking sessions belonging to unrelated workspaces.

When SEARXNG_URL is empty, search uses the documented Wikipedia MediaWiki API. Configured SearXNG remains the selected provider and failures do not switch providers silently. Public source retrieval preserves configured HTTP proxies/CA roots while pinning the validated destination IP and original TLS hostname. Private/mixed DNS answers, unsupported ports/protocols, unsafe redirects, robots restrictions and indexing prohibitions are declined.

Research defaults: four searches, six pages, 900-second wall-clock deadline (including pauses), 28,000 input characters and bounded model outputs. Dispatch attempts are reserved before external operations, including interrupted/retried attempts. Bounds are configurable per job within server limits. Character packing is not exact token accounting; truncation is disclosed in job warnings. Pages are capped at 2 MB and 60,000 readable characters; compressed responses are declined to bound decompression. Sources failing access/robots/format checks are omitted with recorded failures.

`FOXORY_ALLOW_PARALLEL_COUNCIL=1` permits the guarded parallel option only when installed model sizes are known and measured cgroup/host memory headroom exceeds conservative thresholds. At most two independent calls overlap. The inference server must separately support concurrent loading/requests. Default Compose intentionally keeps one model loaded and one request in flight. No automatic GPU capability claim is made.

Embedding indexes use explicitly selected local models via Ollama `/api/embed`; no remote inference or automatic weight download occurs. At most 200 chunks/document, batches of eight, no embedding/generation overlap by default. Changed document text invalidates its index. Rebuild indexes after replacing embedding-model weights. Search without an embedding model remains keyword-based.

The Linux parser preloads trusted libraries/codecs, then denies filesystem opens, networking, subprocesses, process inspection/control, mount/namespace operations and io_uring via seccomp. It has CPU/address-space/file-descriptor/output limits and a parent timeout. There is no unsafe fallback. Docker includes libseccomp2; other native platforms must use the Linux container.

Background research/council completions are capped at 512 generated tokens per call to remain usable within step deadlines; chat retains its existing 2048-token generation cap. Evidence context is packed separately from full saved sources. `FOXORY_INFERENCE_THREADS` sets local CPU inference threads (1–16); absent it, the backend uses a bounded cgroup/CPU estimate rather than exposing the full host thread count. The cloud integration explicitly uses two threads. Per-step timeout is clamped to the remaining wall-clock budget; expired jobs require a new budgeted job rather than unlimited retries. Page slots are shared across remaining subquestions so the first query cannot consume the entire research budget.

The optional CPU-light profile uses `FOXORY_BACKGROUND_CONTEXT=2048` and `FOXORY_BACKGROUND_OUTPUT=256`; native library defaults remain 4096/512; Compose now defaults to the tested CPU-light profile. Both are bounded, operator-configured settings and do not alter chat limits. Background input packing uses a conservative character estimate against the chosen context/output profile and discloses truncation. Small models can produce an explicitly extractive evidence fallback; passing reference-integrity checks is not proof of factual quality.

The parent parser now multiplexes/bounds stdin/stdout/stderr while the child runs, kills the process group on overflow/deadline, and permits only one active parser. Concurrent parse attempts return 429 rather than multiplying child memory use. This bounds output-flood risk even if the parser itself is compromised.

### Agent execution

`FOXORY_WORKER_CONCURRENCY` defaults to `1` and is clamped to `1–2`. It controls task workers, while local model inference remains sequential. Configure it deliberately on the supported single-process installation; multiple API replicas are unsupported. Agent-specific limits (steps, model calls, wall-clock/step timeouts, retries and retention) are configured in AI Workforce. Scheduled runs have a separate maximum-runs and retry limit; at most eight workspace jobs may be pending when schedules dispatch. Internal writes require a workspace administrator's expiring approval. No external-action tool can be enabled by changing agent settings.

Scheduling uses IANA timezones and fixed elapsed-minute recurrence; DST-ambiguous naive times require an explicit offset via API. The UI can schedule an unambiguous time or UTC. See [extension and execution contracts](docs/AGENT_EXTENSIONS.md).

### Optional Computer Mode

`FOXORY_ENABLE_SANDBOX=0` by default. Deliberate opt-in additionally needs
`FOXORY_SANDBOX_URL` and a random server-side `FOXORY_SANDBOX_KEY` shared only with
the separate manager. The manager uses `FOXORY_SANDBOX_ENABLED=1` and a private
`FOXORY_SANDBOX_DATA` directory. Native Linux is the verified topology. Compose
passes settings but does not install a manager or make host loopback reachable
from the application container. See [full setup](docs/SANDBOX_MANAGER.md).


Phase 4 now connects optional JavaScript/TypeScript and offline Playwright profiles
through the authenticated manager, approval gates and Computer Mode. They remain
disabled by default and require actual Ubuntu isolation verification; Codex tests
use a mocked OCI boundary. See [host activation and acceptance checklist](docs/SANDBOX_HOST_VERIFICATION.md)
for pinned image builds, lifecycle/ownership controls and remaining limitations.

## Bounded core verification

Installed-model listings include reported capabilities and role eligibility.
Known incompatible chat/embedding choices are filtered and checked server-side;
missing inspection metadata is explicitly unknown, never assumed verified.
Inspection is bounded/cached and does not load model weights or grant tools.

`POST /api/conversations/{id}/chat` accepts `max_output` (32–2048 tokens; existing
default 2048). This bounds requested Ollama generation, not an exact runtime or
quality guarantee. The disposable core acceptance harness uses 128 tokens for
foreground checks and context2048/output256 for background stages. It connects
only to an explicitly supplied local-model endpoint and never downloads weights.
