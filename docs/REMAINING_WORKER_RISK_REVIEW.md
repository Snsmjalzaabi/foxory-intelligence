# Remaining worker dependency risk — unresolved

The exact Issue5 image has71 package findings across43 unique CVEs. Trivy uses
Ubuntu's package-specific severities:41 MEDIUM/30 LOW. This does **not** mean all
published CVSS scores are low or that production distribution is cleared.
Actual execution, isolation and cleanup tests passing are separate evidence.

On29 October2026, bounded first-party retrieval verified30 Ubuntu CVE pages;
13 remained unverified after one retry (timeouts/HTTP503). The normalized status
rows, source URLs and response hashes are retained in
[evidence](evidence/remaining-worker-cve-upstream-review-2026-10-29.json).
Some pages contain multiple source packages with different Noble statuses;
those rows must not be treated as automatic installed-package clearance.
No scanner entry, severity, exception or runtime permission was changed by this
review. No vulnerability is declared fixed by a network request failing.

## Next sequential issue: PCRE2 source remediation

The image still has `libpcre2-8-0`10.42-4ubuntu2.1. Ubuntu marks Noble vulnerable
for all seven PCRE2 CVEs in the retained scan, including:

- [CVE-2026-86145](https://ubuntu.com/security/CVE-2026-86145): published CVSS8.2;
  upstream DFA-workspace overflow fix
  [c932e70451eafef922ebef364ac25042f0031135](https://github.com/PCRE2Project/pcre2/commit/c932e70451eafef922ebef364ac25042f0031135).
  The retrieved commit changes `src/pcre2_dfa_match.c` and adds an upstream
  regression expecting `PCRE2_ERROR_HEAPLIMIT`(-63). It was read, not applied,
  compiled or verified against the older Ubuntu source. The global GitHub advisory
  API returned404; this does not invalidate the fetched commit/Ubuntu record or
  establish advisory clearance.
- [CVE-2026-103111](https://ubuntu.com/security/CVE-2026-103111): published CVSS7.6.
- [CVE-2026-89161](https://ubuntu.com/security/CVE-2026-89161): published CVSS7.4.
- CVE-2026-89156, CVE-2026-89157, CVE-2026-89158 and CVE-2026-89160 also remain
  vulnerable in Noble according to their retrieved records.

The safe next work is a reviewed supported package update or a maintained,
versioned source backport covering **all seven** findings. PCRE2 is a dependency
of required Chromium/GLib components; deleting it or overriding package dependency
checks is not a fix. The upstream change above alone does not cover every CVE.
Do not relabel an unchanged library as patched or hide its package metadata.

A custom backport requires exact source/patch hashes, license/source retention,
compatibility and upstream regression tests (including sanitizer checks inside a
restricted disposable build/test environment), truthful package metadata and a
fresh exact-image SBOM/runtime/security/recovery run. Do not run a memory-
corruption proof of concept inside the main application or on the owner host.
No PCRE2 runtime change or Issue6 completion email has been made.

## Other gates remain independent

Review the remaining findings and13 unresolved upstream lookups, bundled browser
coverage and binary license/corresponding-source obligations. The previous image
passes only its documented scanner criteria; it is not approved for production.
Keep optional OCI execution disabled by default. Source-only distribution scope
is documented separately; no public publication or deployment is authorized.
Owner-PC final image/activation/reboot acceptance remains outstanding; hosted
Ubuntu evidence does not replace it. Reviewed owner commands are in
[UBUNTU_FINAL_VALIDATION.md](UBUNTU_FINAL_VALIDATION.md).
