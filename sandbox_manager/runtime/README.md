# Optional isolated worker image

The manager connects this entrypoint to approval-bound `sandbox.javascript`,
`sandbox.typescript` and `sandbox.browser` tools. All profiles remain disabled by
default. Explicit opt-in, an immutable local image ID and passing startup probes
are required. Mocked-boundary tests do not satisfy the host acceptance checklist.

`Dockerfile` pins the upstream Playwright/Ubuntu/Chromium/Node base by OCI index
digest. `npm ci --ignore-scripts` installs only the exact Playwright dependency
graph, checked using npm SHA-512 integrity. `reviewed-inputs.json` records the
reviewed source/build-file hashes. There are no runtime package installs or paid
services. This provides reproducible inputs, not a promise of byte-identical
image output across builder versions/platforms.

```bash
.venv/bin/python scripts/verify_worker_supply_chain.py
.venv/bin/python scripts/verify_worker_supply_chain.py --online
podman build -f sandbox_manager/runtime/Dockerfile \
  -t localhost/foxory-worker:verification sandbox_manager/runtime
podman image inspect localhost/foxory-worker:verification --format '{{.Id}}'
```

In a managed cloud build requiring an injected CA, pass it as the optional
`proxy_ca` build secret, without disabling TLS verification. No certificate,
credential or host configuration is copied into the image. The base is large;
the owner supplied a successful Ubuntu cached image build and all three fixed
runtime probes. Full host security/recovery acceptance is still pending.

Node supports dependency-free JavaScript and TypeScript type stripping (no
semantic type checking). The offline browser profile serves only supplied files
and blocks external requests, non-GET/HEAD methods, service workers, frames and
form submissions. Chromium's sandbox is required; no unsafe fallback is present.
Each run has a fresh browser session and a disposable container.

The manager drops all capabilities for JS/TS. Browser alone adds `SYS_CHROOT`
after dropping all capabilities, to permit Chromium's filesystem sandbox under
capability-conditioned runtime seccomp. Rootless/non-root execution,
no-new-privileges, default seccomp/AppArmor and all quotas remain required.
The owner supplied passing actual Ubuntu fixed probes for this correction.
Full host acceptance remains pending; see
[the investigation and rebuild procedure](../../docs/CHROMIUM_SANDBOX_UBUNTU.md).

Worker stdout/NDJSON and downloaded files remain untrusted. The manager validates
bounded envelopes, text/JSON/CSV content, PNG structure/CRC/decompression, names,
size and hashes. Application downloads revalidate bytes and require the owning
workspace/job/approval-derived manager ID. Images are fetched using authenticated
blob requests. Worker success cannot prove the adequacy of generated tests.

Never run `worker.mjs` with generated code directly on the host. Never mount a
Docker socket, disable the Chromium sandbox, allow arbitrary runtime flags or
remove cgroup limits. See [Ubuntu checklist](../../docs/SANDBOX_HOST_VERIFICATION.md)
for activation and real-host tests. Package licenses, vulnerabilities, image
provenance and upstream changes require review before release/distribution.
# Reviewed OS-library remediation

The Noble worker pins zlib1g `1:1.3.dfsg-3.1ubuntu2.3` for CVE-2026-85091
([USN-8954-1](https://ubuntu.com/security/notices/USN-8954-1)). This changes the
container library, not the owner's host OS. Rebuilds require a fresh exact-image
audit/runtime run. `deployment/required-security-fixes.json` adds reviewed
remediations to the existing HIGH/CRITICAL gate; MEDIUM findings are not relabeled.
The current policy digest is bound to accepted runtime provenance. An old report
cannot clear a new policy. Other lower findings, compiled copies and binary
license review remain separate; no production clearance follows from this patch.
