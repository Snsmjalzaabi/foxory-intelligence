# Sequential blocker register

Use PROJECT_STATUS.md and retained evidence as the source of verified results.
This lists known acceptance gates, not a claim that every possible defect is
known. No Phase5 work, public release or production deployment is authorized.
Phase4 is already implemented in part; it remains open until its acceptance gates
pass. The owner requested one active blocker and a separate completion email for
each verified, committed resolution.

| Work | Status | Completion evidence required |
|---|---|---|
| Issues1–6 | Verified in source/hosted tests; per-issue email sent | Retained image/runtime/CI records; owner rollout remains separate |
| Issue7: libXrender CVE-2026-88807 | Active; source replacement under verification | Authenticated release, actual vulnerable control, fixed normal/sanitizer regressions, ABI/hash/version gates, exact-image/rootless tests |
| Remaining dependency findings | Queued; select one bounded issue after Issue7 closes | Actual image/source mapping, vendor/upstream review, remediation or explicit supported-scope assessment; no silent suppressions |
| Bundled Chromium/browser security coverage | Queued | Actual executed revision and upstream advisory/build provenance; ordinary OS scanner success alone is insufficient |
| Binary license/copyright/corresponding-source delivery | Queued | Exact runtime SBOM and retained terms/source obligations; source-only scope remains distinct |
| Owner Ubuntu final installation/activation/reboot/restore | Requires reviewed owner-run commands | Latest local image/topology logs and safe disposable recovery checks; hosted Ubuntu does not replace owner-PC acceptance |
| Phase4 final supported-scope acceptance | Pending all relevant gates | Honest supported/experimental/unsupported features, passing critical regressions and deliberate owner approval before distribution |

Owner credentials, original data, models, backups, Git history and valid failed
evidence are preserved. Optional execution stays disabled by default. No cloud
VPN/SSH access to FoxPC is configured; do not infer it from the owner's phone SSH
session. Routine engineering proceeds without permission questions. Consequential
application actions keep their existing per-action approval enforcement.
