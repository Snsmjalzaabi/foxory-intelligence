# Sequential issue verification

The owner requested one issue at a time, with an email only after each issue is
fixed and verified. Preserve accepted functionality and full Git history; do not
restart the repository, discard useful failure evidence or weaken isolation.

## Preliminary cleanup — cloud done; owner checkout checked locally

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
cache utility and five filesystem/Git boundary tests. The owner has now supplied
successful execution: pre-pull fsck passed, source fast-forwarded4b57d90→3a59e19,
both cache commands found zero candidates/removed zero bytes, final Git status
was clean. This verifies that checkout's cache check, not a whole-PC scan or a
new application/sandbox runtime test. The SSH/Tailscale session was the owner's
phone connection and does not configure cloud access. See
[owner-pc-cache-check-2026-10-29.json](evidence/owner-pc-cache-check-2026-10-29.json).
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

## Issue 2 — Ubuntu worker zlib security update

**Fixed and verified** in `d277a214c155e723a8c831cbdca756dbe91a1a8b`. The exact Issue1 image reports
CVE-2026-85091 in zlib1g1:1.3.dfsg-3.1ubuntu2.2. Canonical's CVE page and
USN-8954-1 confirm the Noble fix1:1.3.dfsg-3.1ubuntu2.3. The worker now pins
that signed Ubuntu package. This scope is the OS library, not a claim about all
bundled copies in Node/Chromium or all633 findings.

The scanner now blocks this specifically reviewed remediation even though its
vendor severity is MEDIUM, without relabeling severity or suppressing other
findings. Exact-image runtime verification additionally requires the current
required-fixes policy hash, so an older-policy report cannot be reused.
Targeted synthetic/archive tests passed31; full local backend passed239. Actual
Ubuntu26 run `40859366853` passed the new exact image's audit,7/9/10 canonical/
TCP/Unix runtime check groups and current-policy provenance gate. All owned
cleanup passed. SBOM confirms zlib1g1:1.3.dfsg-3.1ubuntu2.3; the specific package
finding is absent. Remaining findings are632, not zero. Verify `40859365775`
passed all three jobs. Reports:
[issue2-zlib-verified-2026-10-29.json](evidence/issue2-zlib-verified-2026-10-29.json)
and [issue2-image-provenance-2026-10-29.json](evidence/issue2-image-provenance-2026-10-29.json).
Image: `sha256:b88a2c2566edaad442c3e9bef6d0287c713d1b365e588547abb67e21d8a0599a`.
The requested **Issue 2 Fixed** email was sent after the evidence commit; the mail
service confirmed delivery. Existing owner-PC images are unchanged until rebuilt.

## Issue 3 — remove unused system FFmpeg libraries

**Fixed and verified** in `e4e112f28570cd4e7eb522b3fe71f9261702c1c9`. The Issue2 scan had455 package findings
across seven system FFmpeg libraries. The pinned Playwright1.64.1 Ubuntu24
dependency table lists libavcodec60 under Firefox, not Chromium. The worker only
exposes Chromium; video/FFmpeg and Firefox/WebKit profiles are not supported.

A trusted build-only helper simulates removal first and refuses removal of any
of the21 reviewed Chromium packages, incomplete plans or unexpected installations.
It then checks actual package changes and absence of the shared libraries on the
merged filesystem. It is removed from the final runtime. No autoremove, metadata
stripping, source rewrite or isolation relaxation. Build helper and package policy
are included in reviewed input hashes. The helper is never used for host package
management in unit tests.

Worker audits now require all21 Chromium packages present and all seven excluded
packages absent in the SBOM. Runtime provenance must carry the current package-
policy hash. Bundled browser codecs, lower image layers and binary distribution
obligations are separate; removing merged files does not erase these obligations.

Actual Ubuntu26 run `40863818827` passed7 canonical,9 TCP and10 Unix check
groups with real rootless execution, current-policy provenance and owned cleanup.
The exact image is
`sha256:472c9b4c7a277acdc5cbeb425b44a2c1b23cc4fce32d24961b5fad1436f0c5e2`.
SBOM retains all21 Chromium dependencies and the fixed zlib; seven FFmpeg packages
are absent. Findings decrease632→177 (455 package findings,65 unique CVEs).
Verify `40863816928` passed all three jobs. Local backend250 and targeted42 tests
passed; OCI UI fixtures are separate from actual runtime checks. See
[issue3-media-removal-verified-2026-10-29.json](evidence/issue3-media-removal-verified-2026-10-29.json).
Requested subject: **Issue 3 Fixed**; send only after this evidence is committed.
Existing owner-PC images remain unchanged until rebuilt. No production clearance.

## Remaining, not started

- Review the remaining image/compiled-browser findings and binary distribution
  license/source-delivery obligations using the exact accepted image evidence.
- Owner-PC application/manager activation/reboot acceptance requires access to that machine
  or reviewed commands executed by its owner. No access or completion is assumed.

Phase4 remains open. No production readiness, Phase5, GPU verification or public
publication is implied by completion of a single numbered issue.
