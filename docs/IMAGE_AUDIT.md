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
Docker daemon by default; it clears alternate Docker endpoint/context/TLS selectors.
Do not grant Docker access to the dedicated rootless sandbox account. CI reports
describe their exact Docker image ID, not the owner's separately built Podman
image. For that image the CLI now accepts a stationary private rootless export,
without granting this account Docker access:

```bash
umask 077
podman --remote=false save --format docker-archive --output "$HOME/worker-review.tar" "$image_id"
.venv/bin/python scripts/image_audit.py --image "$image_id" \
  --archive "$HOME/worker-review.tar" --output "$HOME/worker-audit-NEW"
```

The export must be an operator-owned regular file, not writable by others, at
most 8 GiB; no compression/multiple images/symlink metadata. Config SHA-256 must
match the given image ID and each layer must match the config's diff ID. The
tool extracts no layer, passes a stable inherited descriptor to both scanners,
records the archive hash and checks it again after scanning. This is a trusted
operator verification CLI, not an arbitrary image-upload endpoint. Preserve the
original image ID, report and archive hash. Do not execute the exported
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

## First actual findings and remediation candidate (29 October 2026)

Hosted run `40809535648` completed both static scans. The gate correctly failed:
core had 61 HIGH/CRITICAL package findings (276 total), worker nine HIGH (655
total). Full SBOM/license/vulnerability reports are private run artifacts; blocking
summaries are retained in `docs/evidence/*-image-audit-2026-10-29.json`. Backend,
browser, real Python sandbox, PostgreSQL and pristine Compose checks passed first.

The remediation candidate keeps Python 3.12 but replaces the Bookworm runtime
with a digest-pinned Trixie base and applies available OS repository upgrades.
Repository packages can change between rebuilds; each resulting image must pass
the audit and its exact versions/ID are recorded. This is not a bit-reproducible
OS package snapshot. No advisory is suppressed to accommodate an old distribution.

The worker retains the pinned Playwright/Chromium/Node base and application lock.
It installs the pinned Brotli security update `1.1.0-2ubuntu0.1`, removes unused
WebKit GStreamer bad-plugin packages, and deletes build-only global npm/npx after
the locked Playwright installation. The npm-owned vulnerable `brace-expansion`
and `undici` paths were confirmed in the actual Trivy report. Worker execution
uses Node directly; installing arbitrary dependencies inside a task remains
unsupported. No caps, sandbox flags, quotas or network policies change.

These changes require new image scans and actual rootless Chromium/JS/TS probes;
the owner's earlier image/probe result does not certify a rebuilt image. Image
audit success alone will not complete Phase 4 or authorize execution.

Follow-up run `40811156834`: the worker passed with zero HIGH/CRITICAL findings,
633 lower findings retained, and 18,450 SBOM components. Core Trixie passed real
Compose checks but still had **44 unfixed HIGH findings**, 170 total. Its report
is retained separately; the unsuccessful candidate was not accepted as safe.

The next core candidate uses digest-pinned Ubuntu 24.04 security-maintained
Python 3.12 packages. Runtime and dependency-builder use the same base/ABI;
only a private installed venv is copied from the builder. Build-only pip and
distribution venv-wheel packages are absent from the final runtime. OS inventory
and metadata remain intact for scanning; no vulnerable installed package is
hidden from the scanner. Application source, Python dependency lock, non-root
UID, migrations, authentication and sandbox policies remain unchanged. Fresh
canonical installation/document/persistence and image gates are required.

Run `40811943218` confirms the Ubuntu candidate passes the actual core gate:
zero HIGH/CRITICAL, 26 lower findings and 3,831 SBOM components, after actual
canonical Compose installation/restart checks. The worker also passed again.
These are report-feed results, not universal vulnerability/license clearance.
The added rootless-archive route has six deterministic identity/metadata/layer
tampering tests; an actual exported-image scan remains pending its hosted run.
