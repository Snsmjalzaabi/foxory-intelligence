# Image review and limits of severity gates

A passing Syft/Trivy job means no HIGH/CRITICAL findings **under the scanner's
selected data-source severity**, not no vulnerabilities. Distribution priorities
can differ from NVD CVSS, and a distribution change alone does not prove a CVE
was fixed. Actual reports, lower findings, package versions, exploit conditions,
licenses and upstream status require review before production acceptance.

On 29 October 2026 the Ubuntu 24.04 application image reported 26 lower findings;
the worker reported 633. These remain recorded, not waived. Representative
cross-distribution follow-up against Canonical's public tracker established:

| CVE | Canonical status for Ubuntu 24.04 | Review implication |
| --- | --- | --- |
| [CVE-2026-76642](https://ubuntu.com/security/CVE-2026-76642) | Medium priority; needs evaluation; CVSS 7.8 | util-linux mount-helper/post-mount-hook issue remains unresolved in vendor triage. |
| [CVE-2026-78408](https://ubuntu.com/security/CVE-2026-78408) | Medium; needs evaluation; CVSS 7.9 | Privileged nsenter/cgroup descriptor inheritance; do not infer patched from severity alone. |
| [CVE-2026-78409](https://ubuntu.com/security/CVE-2026-78409) | Medium; needs evaluation; CVSS 7.0 | fstab-authorized mount/subdirectory traversal preconditions. |
| [CVE-2026-78410](https://ubuntu.com/security/CVE-2026-78410) | Medium; needs evaluation; CVSS 7.8 | Privileged fstab bind-mount path race preconditions. |
| [CVE-2026-54369](https://ubuntu.com/security/CVE-2026-54369) | Medium; ignored: backport too intrusive; CVSS 7.1 | ACL pathname/symlink issue is not established fixed. |
| [CVE-2026-16742](https://ubuntu.com/security/CVE-2026-16742) | Fixed in 255.4-1ubuntu8.17 | Check installed version; systemd-homed exploit context is distinct from a library package flag. |
| [CVE-2025-69720](https://ubuntu.com/security/CVE-2025-69720) | Fixed in 6.4+20240113-1ubuntu2.1; vendor Low | Vulnerable infocmp command, despite a higher CVSS score. |

The default application runs non-root, read-only, cap-drop ALL and
no-new-privileges. Workers additionally use rootless namespaces, task-only mounts,
no networking and quotas; only Chromium has SYS_CHROOT, never SYS_ADMIN. These
controls constrain the privileged mount/nsenter/ACL exploit preconditions and
are preserved. This is contextual mitigation, **not** proof all affected paths
are unreachable or an approved vulnerability exception. Do not add privileged
mount helpers, user fstab entries or host mounts to make a task work. Dedicated
host/runtime packages need their own updates and review.

`Review default infrastructure images` is an additional manual static workflow
for the actual PostgreSQL/Ollama references in Compose. Application/worker scans
do not cover these images. It records their exact local IDs/repository digests,
SBOMs, licenses and findings, never starts them or touches owner data. At creation
its results are pending. Any infrastructure update must preserve model/data
compatibility and pass disposable migration/restore and actual-model checks;
never switch the owner's database image/volumes merely to obtain a green scan.

First run `40813368693` actually found 98 vendor HIGH/CRITICAL PostgreSQL package
findings (461 total), including the old gosu binary's Go standard library as well
as Debian packages. The summary is committed; severity/actual exploit context
still need review. Ollama analysis failed ENOSPC during Trivy layer export, so it
has **unknown** vulnerability status, not zero findings. The next hosted Ollama
audit reserves space by removing only unused Android/.NET/Haskell SDKs on that
new ephemeral GitHub VM, then requires 24 GiB free. No owner or Cloud data/cache/
image/volume cleanup is performed. If capacity is still insufficient the scan
must fail; do not substitute a partial report for a completed audit.

Production remains blocked on review of these findings, infrastructure coverage,
compiled-browser/runtime advisories, license obligations and the remaining
Phase 4 acceptance criteria. No blanket security clearance is asserted.

## Review-only upgrade candidates

Current Compose/defaults remain unchanged. Candidate audit mode reviews official
Ollama 0.40.13 and a digest-pinned PostgreSQL 17 Alpine derivative; it is not an
owner deployment. Stock PostgreSQL 17 Alpine still reported 26 HIGH/CRITICAL
findings in the old embedded Go runtime of `gosu`, despite newer OS packages.
That unsuccessful scan is retained. The derivative removes that binary and uses
signed Alpine `su-exec=0.3-r0` for the entrypoint's existing user/exec operation.
No scanning metadata is removed; no advisory exception is introduced. MIT license
text was retrieved from ncopa/su-exec v0.3 and is shipped in the candidate.

Only after the image gate passes, candidate CI runs fresh PostgreSQL migrations,
tenant/duplicate guards, restart and logical restore in its own disposable data.
This does **not** establish an existing Bookworm/glibc cluster can be physically
reused under Alpine/musl. Never attach the owner's old database volume. A tested
logical export/import, roles/extensions/collations and actual owner backups are
required before proposing that transition.

Ollama candidate CI, after its gate, explicitly downloads the free Apache-2.0
qwen2.5:0.5b and nomic-embed-text models into quota-limited temporary storage and
checks actual CPU completion/embedding metadata. It runs non-root, read-only,
cap-drop ALL/no-new-privileges with no GPU devices and loopback-only publication.
It never executes generated code, uses owner weights or claims model persistence/
GPU/quality compatibility from this narrow smoke. Candidate results are pending.

Verified follow-up: official Ollama 0.40.13's first completed static scan has zero
vendor HIGH/CRITICAL and 32 total findings (`40815264275`, job `123254727478`).
The revised PostgreSQL derivative has **zero reported findings**, 868 components,
and passed actual fresh revision0003 migration, tenant/duplicate guards, restart
and same-image logical restore (`40816168164`, job `123257626385`). Exact image
and test summaries are committed under `docs/evidence`. These successes do not
validate an owner database transition or model API compatibility.

Two repeat candidate Ollama runs, plus a core CI job, were canceled; check-run
annotations explicitly attribute cancellation to `@Snsmjalzaabi`. Their skipped
runtime tests are not passes. Additional hosted runs/pushes that restart CI are
paused pending clarification of that cancellation intent. A separate-volume
Bookworm-to-candidate logical restore harness is staged and syntax-checked, but
has not executed. No default image or owner volume was changed.
