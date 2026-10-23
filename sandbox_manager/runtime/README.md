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
image build and execution are pending on the Ubuntu verification host.

Node supports dependency-free JavaScript and TypeScript type stripping (no
semantic type checking). The offline browser profile serves only supplied files
and blocks external requests, non-GET/HEAD methods, service workers, frames and
form submissions. Chromium's sandbox is required; no unsafe fallback is present.
Each run has a fresh browser session and a disposable container.

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
