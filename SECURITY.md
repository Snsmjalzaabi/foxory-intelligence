# Security policy

FOXORY is pre-release software for local self-hosted testing. Phase 2 implements multiple accounts and workspace roles; Phase 3 adds fixed-registry tools, bounded agents and approval-gated internal writes; this is not an independent security certification or approval for public hosting/regulated production data. Do not expose the service publicly. Use one API process/replica.

Report vulnerabilities privately to the repository owner's private reporting channel once established. No contact address is invented. Do not post secrets, personal records or exploit details publicly; until a private channel exists, do not submit sensitive reports in public issues.

## Implemented boundaries

- Argon2id password hashing; opaque server-side session digests, 12-hour expiry and logout revocation; HttpOnly/SameSite cookies, CSRF and origin checks. Initial bootstrap access is retired after the first administrator account exists. Login work is rate/concurrency limited.
- Workspace memberships/admin/editor/viewer roles checked server-side on every request. ORM record/message/audit filtering and guarded writes fail closed. Exports/downloads/bulk state transitions use the same boundary. Background jobs enter only their stored workspace and check the creator's execution membership. Workspace administration does not grant installation-wide model mutation.
- Trusted hosts, bounded request/upload bodies, random upload names, safe Markdown without raw HTML/external image fetches, draft approval snapshots and audits. Application logs minimize content; production access logs are disabled to avoid query leakage.
- Linux parsing subprocess receives only document bytes/name and a minimal environment. Trusted libraries/codecs preload before parsing; seccomp denies filesystem opens, networking, subprocesses, process inspection/control, mount/namespace operations and io_uring. CPU/address-space/descriptor/output/parent timeout limits apply. Missing policy fails closed; there is no unsafe native-platform fallback. A codec preload bug found in Docker was corrected without loosening restrictions.
- Public-source retrieval validates globally routable DNS answers, pins the address, validates redirects and TLS hostnames, preserves the configured proxy/CA path, respects robots/indexing directives and declines access challenges. No authentication/cookie forwarding to research sources or access-control bypass is implemented.
- Non-root, read-only application container with dropped capabilities and no Docker socket/host-shell access. Model outputs cannot invoke external actions. Approving a draft cannot send, publish, pay or execute.

## Unresolved limitations

No independent penetration/sandbox review, encryption at rest, administrator-proof audit trail, distributed limiter/worker lease, broad compatibility benchmark or GPU verification. Rate limits are per process/IP. JSON vectors target modest workspaces; global tenant storage quotas and larger-library indexing remain follow-up work. The pinned proxy transport uses a private httpcore 1.0.9 backend hook and must be retested on upgrades.

Research references/hashes prove saved identifier/content integrity, not truth or current source availability. Credibility and contradiction interpretation remain heuristics/model analysis; source text can be malicious or wrong. Archived reports retain snapshots if originals are later deleted; execution/review records are retained for audit. Prompt instructions are not a complete injection defense. Enforceable tool denial and parser/network controls are the current boundary.

Use encrypted disks, protect volumes/.env/exports/backups, review dependency/model terms and keep the host patched. General browser/JavaScript execution, live email and consequential external actions remain unavailable. Optional restricted Python execution requires the separate manager, explicit agent scope and immutable administrator approval; see docs/SANDBOX_MANAGER.md. Never publish local credentials, research snapshots, private documents or model weights without authorization and license review.

Agent tool grants are enforced on the server, including delegated agents’ independent permissions and explicit document IDs. Configuration snapshots invalidate queued tasks after edits. Approval context binds exact arguments, plan/config hashes, objective and job; expiration/rejection/stale reuse fails closed. Only the same transaction may consume an approval and create its internal artifact/project/task. External communications, purchases, publication and privileged execution have no tool implementation. Prompt-injection policy text is defense in depth; fixed dispatch, schema checks and server grants provide the enforcement. This does not guarantee the factual quality of model output.

Restricted Python dispatch consumes an approval into a durable one-invocation grant before contacting the authenticated manager. Manager idempotency prevents duplicate invocation across retries. The manager is disabled until its runtime isolation preflight passes. It denies networking and child processes, restricts mounts/output files and applies hard resource limits. This profile has no independent escape/security audit and cannot support a multi-process browser. The main app never executes generated code.


Phase 4 now connects optional JavaScript/TypeScript and offline Playwright profiles
through the authenticated manager, approval gates and Computer Mode. They remain
disabled by default and require actual Ubuntu isolation verification; Codex tests
use a mocked OCI boundary. See [host activation and acceptance checklist](docs/SANDBOX_HOST_VERIFICATION.md)
for pinned image builds, lifecycle/ownership controls and remaining limitations.
The browser-only OCI policy adds `SYS_CHROOT` after dropping all capabilities;
JS/TS retain zero capabilities. Rootless/non-root execution, no-new-privileges,
runtime seccomp/AppArmor, quotas and mount/network restrictions remain required.
This expands the browser container's chroot privilege and is not proof of safe
isolation. The owner supplied passing Ubuntu fixed startup probes; full host
security/recovery acceptance remains pending. See
[the security implications and host procedure](docs/CHROMIUM_SANDBOX_UBUNTU.md).
