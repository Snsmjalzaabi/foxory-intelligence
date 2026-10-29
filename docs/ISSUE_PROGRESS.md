# Sequential issue verification

The owner requested one issue at a time, with an email only after each issue is
fixed and verified. Preserve accepted functionality and full Git history; do not
restart the repository, discard useful failure evidence or weaken isolation.

## Preliminary cleanup — cloud done, owner PC not connected

Git fsck passed. All46 tracked JSON,9 PNG and1 PDF files checked were valid;
both Git bundles were valid and preserved. No corrupted source was identified.
Removed five ignored cache trees and five proven duplicate temporary files:
1,337,655 bytes. Every deleted duplicate's original content remains in committed
evidence. Complete scanner archives needed for open reviews, source, user
uploads, credentials, databases, model/manager state and backups were retained.
The receipt is [cleanup-cloud-2026-10-29.json](evidence/cleanup-cloud-2026-10-29.json).

There is no configured VPN/SSH connection to the owner's Ubuntu PC. Nothing was
deleted there, and chat attachments themselves cannot be removed by these tools.
The owner chose reviewed local commands; those are now provided in
[LOCAL_CACHE_CLEANUP.md](LOCAL_CACHE_CLEANUP.md), backed by the guarded stdlib-only
cache utility and five filesystem/Git boundary tests. PC execution remains pending.
Do not describe cloud cleanup as PC cleanup or delete valid files merely because
their test run failed.

## Issue 1 — exact audited/executed worker identity

**Fixed and verified** in `614691db39e6475e38828faedf0c6f2257afe451`.

Previous successful CI scanned a separately built Docker worker and executed a
rootless Podman worker. Both used reviewed inputs, but image IDs differed. Those
reports were correctly qualified; they did not prove the exact executed image
passed its own image audit.

Fix: export the exact immutable rootless image, verify its config and every layer
hash, run the existing SBOM/vulnerability gate before runtime testing, then require
the audit, canonical integration, TCP and Unix summaries to name that same image.
Failed coverage, HIGH/CRITICAL findings, incomplete checks or cleanup failures
must fail the gate. Archive deletion removes only the owned temporary export;
SBOMs, license inventory and scan/runtime reports are retained.

The new report-consistency tests include the actual previously differing image
IDs and reject that old evidence combination. Synthetic report tests are not
actual image or runtime verification.

Actual Ubuntu26 run `40851799082` passed the exact-image scan and all seven
canonical integration, nine TCP and ten Unix runtime check groups, followed by
the new consistency gate. Image/config digest:
`sha256:0cc27c1f17d6b325abdc5fbaf3c074f65aa6d0981c7d9ffa805ba250cb3c7279`.
The2,564,278,784-byte stationary export's config and every layer hash were
verified before/after scanning. All cleanup passed. Static review reports zero
vendor HIGH/CRITICAL but633 lower findings; those are not silently accepted.
The actual report is
[issue1-verified-image-provenance-2026-10-29.json](evidence/issue1-verified-image-provenance-2026-10-29.json).

Verify `40851798371` passed all three jobs:212 core+17 Python-sandbox backend
tests (229 total), frontend builds,11 core/14 full browser journeys (overlapping,
OCI UI mocked), database/migrations/Compose and existing image gates. Local
targeted tests passed26; full backend passed229. The CLI also rejected the real
previously mixed reports without writing a successful provenance record.

Requested notification subject: **Issue 1 Fixed**. Email delivery is a separate
action, reported to the owner only after the verified fix/evidence is committed;
it is never inferred from test success. The requested Issue1 email was actually
sent after verification/commit; delivery was confirmed by the mail service.
This is one fixed issue, not project-
wide production clearance or owner-PC cleanup.
All runtime permissions, rootless identity, network/resource restrictions and
disabled application defaults remain unchanged.

## Next, not started

- Review the remaining image/compiled-browser findings and binary distribution
  license/source-delivery obligations using the exact accepted image evidence.
- Owner-PC cleanup/activation/reboot acceptance requires access to that machine
  or reviewed commands executed by its owner. No access or completion is assumed.

Phase4 remains open. No production readiness, Phase5, GPU verification or public
publication is implied by completion of a single numbered issue.
