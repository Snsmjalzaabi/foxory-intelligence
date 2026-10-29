# Static image audit gate

Phase 4 image verification now builds the pinned optional worker in hosted CI and
audits both it and the canonical core application image. This is static inspection:
no generated code or browser worker is run in rootful Docker. Actual rootless
Ubuntu execution remains a separate gate.

The explicit verification CLI downloads Syft 1.55.0 and Trivy 0.76.1 from their
official public GitHub releases. The reviewed Linux AMD64 archive SHA-256 values
are pinned in `deployment/security-tools.json` (GitHub release asset metadata).
Only the expected regular binary is extracted; symlinks and oversized inputs are
rejected. The tools are temporary, do not enter product images, do not load
application plugins and do not publish images or call paid services.

For an already built, reviewed local Docker image:

```bash
image_id="$(docker image inspect foxory-worker:ci --format '{{.Id}}')"
.venv/bin/python scripts/image_audit.py --image "$image_id" --output /tmp/worker-audit
```

Use a new output directory. The CLI currently supports Linux AMD64 and the local
Docker daemon only; it clears alternate Docker endpoint/context/TLS selectors.
Do not grant Docker access to the dedicated rootless sandbox account. CI reports
describe their exact Docker image ID, not the owner's separately built Podman
image. For that image, an administrator can export a private Docker-format archive
with rootless `podman save --format docker-archive`, then use the same reviewed
Syft/Trivy versions' archive-input options in a separate review environment.
Record both the original image ID and archive hash. Do not execute the exported
image under rootful/privileged settings as a compatibility workaround.

Outputs:

- `sbom.cdx.json`: CycloneDX component inventory.
- `vulnerabilities.json`: complete Trivy findings, not just the blocking subset.
- `license-inventory.json`: reported licenses, explicitly awaiting compatibility
  and attribution review; absence of license metadata is not approval.
- `summary.json`: immutable image ID, pinned tools, coverage and blocking findings.

HIGH/CRITICAL findings, including unfixed vulnerabilities, fail the gate. Empty or
unsupported coverage, end-of-life OS metadata, tool/download/checksum failure or
empty SBOM cannot produce a pass. Medium/low findings remain visible for review;
the gate does not silently exclude them or create exceptions. Reports are uploaded
as private GitHub Actions artifacts even when the job fails.

A successful scanner gate establishes only the named tool/feed coverage. It does
not prove that bundled Chromium/Node binaries have no vulnerabilities, fulfill
copyleft/source-offer obligations, certify isolation, or complete Phase 4. Review
browser/runtime versions, all license terms and findings before accepting an image.
Changing worker inputs/image ID requires the actual startup probes again.
