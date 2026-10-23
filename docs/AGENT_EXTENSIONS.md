# Community agent and tool extensions

Phase 3 uses the existing modular monolith and an explicit persisted state graph. `agents.py` implements `plan → execute → review → consolidate → done`; each checkpoint is one worker claim. There is no dynamic plugin loader, arbitrary Python evaluation, downloaded agent code or native model tool dispatch. Changes to registered code require ordinary source review, tests and an application rebuild.

## Agent templates

Add a named entry to `TEMPLATES` in `backend/foxory/agents.py`. Each template supplies purpose and an explicit list of registered tools. `templates()` derives the corresponding permission scopes and defaults. Users choose an installed local model and explicitly create the agent. The bundled General Coordinator is the default coordination template; it is not secretly instantiated with privileges. Coding and Writing templates have no host execution permissions.

Agent configs are validated by `AgentConfig`. Tasks snapshot the coordinator and every explicitly selected specialist. Any live configuration change, pause or deletion invalidates an existing task rather than inheriting new privileges. Delegation is bounded by the validated plan and its backward-only dependency indices. Delegates use their own grants, never the coordinator's; recursive delegation and model-generated changes to tool grants are unsupported.

## Safe tool example

`math.calculate` is a complete reference implementation:

```python
class Calculate(Input):
    expression: str = Field(min_length=1, max_length=200)

TOOLS['math.calculate'] = Tool(
    'Evaluate bounded arithmetic only; no variables, calls or code.',
    Calculate, 'calculate',
)
```

`Input` forbids unknown fields. `authorize()` checks tool allowlist, permission scope, schema and resource IDs at execution time. The handler uses a bounded AST interpreter, never `eval`. A contributor adding a tool must supply a Pydantic input model, permission, output-size bound, timeout and implementation in the explicit dispatch function. Add tests for denial, cross-workspace resource IDs, malformed input, timeout, cancellation and untrusted output. Network tools must use the existing pinned/robots-aware retrieval path; do not introduce an unrestricted HTTP client for arbitrary model URLs.

Local writes additionally require `approval=True` and an explicit handler in `commit_agent()`. The worker checks its unchanged claim, live config and immutable approval context, then commits the write, consumed approval and next checkpoint in one database transaction. A late cancellation rolls the entire transaction back. Deterministic effect IDs and immutable/consumed approval state prevent retry duplication. Do not execute side effects inside `execute()` or before the checkpoint transaction. External sending, publication, payments, shell commands, Docker/host access and privileged computer operations have no registered handler and remain denied even if a model requests them.

## Plans and local providers

Planner output is a `Plan` schema with at most 12 steps. Each step has title, optional specialist ID, optional registered tool and schema-checked arguments, or a model instruction, plus dependency indices referring only to earlier steps. User-provided reviewed plans use the same validator. Ollama structured-output format is used; a native tool-calling capability is not assumed. Output is still validated on the server. Malformed output receives only the configured bounded retry count; ungranted tools fail immediately. There is no silent pretend-success fallback.

`inference.structured(model, messages, schema)` and `inference.complete(model, messages)` are the provider boundary. New local providers must preserve locking, cancellation, deadlines, size limits and structured validation. Adding an external provider also requires explicit operator opt-in and data-sharing disclosure; no external provider is introduced here. Model capabilities can be inspected through the existing API/UI. Missing structured-output support yields a bounded visible failure. Fallback models are only those explicitly configured on the agent; model traces identify successful calls.

## Scheduling, memory and scaling

Schedule records contain normalized UTC `next_run_at`, IANA timezone, optional elapsed-minute recurrence, maximum runs, missed policy and retry limit. This is fixed-interval scheduling, not local-wall-clock cron. Ambiguous/nonexistent naive DST times are rejected; API clients may provide an explicit offset. Misses coalesce into one run or skip to the next future interval. Runs use deterministic workspace/schedule/due IDs. Dispatch and history updates commit together. Pausing a schedule does not cancel already-dispatched tasks; cancel them in Tasks. One active/paused/approval-waiting run blocks overlap. The workspace pending limit is eight; completed one-time runs can retry within the original deadline, without duplicating committed effects.

The scheduler is an independent coroutine in the API lifespan and does not depend on a browser. Default task concurrency is one. `FOXORY_WORKER_CONCURRENCY=2` permits two task workers, while model calls remain serialized to avoid simultaneous model loading. Only one API process/replica is supported. Scaling requires a database-backed lease/queue and atomic scheduler claims across processes; do not run multiple replicas with this scheduler.

Generated summaries are unverified and retained according to agent retention days (0 disables summaries). Explicit user fact writes are marked user-approved, not independently verified. Facts are shared within the workspace; generated summaries are retrieved only for the owning agent. Expired entries are filtered immediately and pruned by scheduler maintenance. Memory APIs provide editing for approved facts and deletion; execution/audit records remain retained. Never store credentials in semantic or agent memory.
