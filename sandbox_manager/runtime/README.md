# Optional OCI worker implementation — not activated

`worker.mjs` contains dependency-free Node execution, Node 22 TypeScript type
stripping, and offline Playwright actions against a supplied fixture website.
It is an OCI entrypoint, **never a host execution helper**. Do not run it on the
host with generated code. Type stripping does not type-check TypeScript.

The browser profile requires the Apache-2.0 `playwright` package and its Chromium
runtime inside a reviewed immutable image. Chromium's sandbox must work; there
is no `--no-sandbox` fallback. Network is disabled by the fixed OCI policy and
browser requests are restricted to GET/HEAD on the in-container fixture origin.
External submissions and public internet browsing are unsupported. Dependencies
cannot be installed by tasks. No third-party runtime image is distributed here.

This implementation is deliberately not connected to authenticated dispatch yet.
Before activation, implement and verify: active rootless/cgroup probes, immutable
image configuration, manager wall timeout and whole-container cancellation,
startup orphan-container cleanup, independently bounded parent artifact parsing
(including PNG decoding), approval-bound dispatch and frontend profile controls.
A worker's JSON or zero exit code cannot attest its own isolation or correctness.
The manager's existing Python profile remains unchanged and separately gated.
