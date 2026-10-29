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
Do not describe cloud cleanup as PC cleanup or delete valid files merely because
their test run failed.

## Issue 1 — exact audited/executed worker identity

**In progress; completion email not sent.**

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
actual image or runtime verification. Actual Ubuntu26 verification is pending.
All runtime permissions, rootless identity, network/resource restrictions and
disabled application defaults remain unchanged.

## Next, not started

- Review the remaining image/compiled-browser findings and binary distribution
  license/source-delivery obligations using the exact accepted image evidence.
- Owner-PC cleanup/activation/reboot acceptance requires access to that machine
  or reviewed commands executed by its owner. No access or completion is assumed.

Phase4 remains open. No production readiness, Phase5, GPU verification or public
publication is implied by completion of a single numbered issue.
