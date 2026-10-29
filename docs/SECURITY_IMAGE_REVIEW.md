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
