# Security policy

This is pre-release software for a single trusted owner on a local machine. It has not received an independent security review. Public hosting, shared accounts and organization deployment are not supported. Do not use it for regulated or highly sensitive production workloads.

Report vulnerabilities privately to the repository owner's private reporting channel once the repository exists. No contact address is invented here. Do not post secrets, personal data or exploit details in public issues. Until a private channel exists, do not submit sensitive reports publicly.

Implemented boundaries include required random bearer authentication, no cookie/URL authentication, same-origin checks, trusted-host checks, body/rate limits, safe Markdown without raw HTML or image network fetches, random upload storage names, archive expansion checks, confirmed model deletion, bounded job steps and retries, cancellation, immutable draft snapshots and auditing. Credentials come from operator environment and are not indexed. The application has no host Docker socket, shell execution, browser control or external messaging executor. The app container runs as UID 10001, read-only root filesystem, dropped capabilities and resource limits.

Known gaps: one owner token rather than passwords/RBAC; no session expiry; token readable to JavaScript within the tab; no encryption at rest; parser execution in threads rather than isolated processes; archives and PDFs need further adversarial testing; application audit history is not tamper-proof; rate limits are per process/IP; UI and structured record validation need further hardening; no multi-tenant isolation; no CSP nonce requirement because scripts are static same-origin files. Do not enable multiple replicas or workers; restart recovery assumes one owner process.

Document, web, model and agent output are untrusted. System prompts label retrieved context, but this is not a complete prompt-injection solution. Denying models all execution and external mutation tools is the enforceable boundary in this version. Approving a draft cannot send email, make a payment, publish content or execute commands.

Use encrypted host disks, restrict data-volume and `.env` access, protect exports/backups, and keep the machine patched. Do not publish `.env`, local documents, snapshots or model weights without verifying their licenses and your authorization.
