# FOXORY Intelligence — core product recovery; Phase 4 acceptance still pending

## Issue6 implementation in progress — PCRE2 only

Signed upstream10.49 contains the seven reviewed PCRE2 fixes; all fix commits
were verified ancestors of the pinned release. Source archive SHA256 and detached
GPG signature were checked against the pinned primary/signing fingerprints.
The worker, application and Ollama baseline scans all contain the same seven
10.42 findings, so this one dependency fix covers all three managed images.

A non-root source builder now packages10.49 with truthful Debian version/source
metadata, retained licenses, upstream normal/ASan+UBSan checks, ABI/SONAME
preservation and fixed native DFA/growable-JIT regressions. Final images get no
compiler/source/test suite. Image gates require the exact package version;
startup probes verify the actual installed library bytes and native version/
regressions under existing rootless controls. All scanner entries remain intact.
Actual image compilation, sanitizer success, scan and full runtime verification
are pending. No Issue6 completion or email is claimed. No other blocker, owner
host package, data volume, GPU setting or sandbox permission has been changed.

## Current checkpoint — Issues3/4/5 verified; next dependency issue unresolved

Requested **Issue 3 Fixed**, **Issue 4 Fixed** and **Issue 5 Fixed** emails were
sent only after their verified evidence commits were pushed; the mail service
confirmed sending. Latest runtime source is `0edf13b`; evidence is in `280e591`.
All272 backend tests, builds, browser suites, migration/Compose checks and the
actual Ubuntu26 exact-image7/9/10 runtime groups passed within their stated scope.

Production/distribution remain blocked. The worker's71 findings include PCRE2
issues with published CVSS scores above7 even though Ubuntu's scanner labels
them MEDIUM. First-party review verified30 of43 CVE pages;13 timed out/returned503
and remain unverified. Ubuntu marks Noble PCRE2 vulnerable; upstream patch
`c932e70451eafef922ebef364ac25042f0031135` was inspected, not applied or tested.
Do not delete required PCRE2, invent a patched version or suppress those findings.
Next: review a supported update/backport for all seven PCRE2 CVEs with restricted
regression/sanitizer tests and fresh exact-image verification. No Issue6 fix or
notification is claimed. Details and precise continuation requirements are in
[REMAINING_WORKER_RISK_REVIEW.md](docs/REMAINING_WORKER_RISK_REVIEW.md).
Binary licenses/sources, compiled-browser coverage and owner-PC activation/reboot
acceptance remain separate. No production/Phase4 completion, Phase5, GPU or
owner-PC image rebuild is claimed; unsafe profiles stay disabled by default.

## Issue 5 fixed and verified — inherited codec/parser dependencies

Source `0edf13b26c6b64fe07e10f9e4dc6ceed8557f73e` excludes17 unused optional
media/parser/crypto packages through the existing guarded apt removal, package
and literal shared-file checks. Actual removal includes their reverse dependents
(26 additional merged packages compared with Issue4). All21 reviewed Chromium
dependencies and the earlier Brotli/zlib/FFmpeg/HTTP fixes remain. No sandbox
permissions, quotas, disabled defaults, owner data or host OS were changed.

Actual Ubuntu26 run `40868918478` passed the exact-image audit,7 canonical,
9 TCP and10 Unix runtime check groups, current-policy provenance and all owned
cleanup. Image:
`sha256:0e87ba95854991b50577303c503de50286b449ecb3ef9be915aef7a31b6fd43c`.
All26 excluded packages are absent. Findings decrease133→71:62 package findings
across54 unique CVEs were associated with the additionally removed packages.
Remaining scan:41 MEDIUM/30 LOW; no finding is silently waived.
Verify `40868917095` passed all jobs:255 core+17 Python sandbox backend tests,
11 core/14 full overlapping browser journeys, strict builds, migrations, Compose
and image gates. OCI UI uses mocks; the Ubuntu26 checks use actual rootless
Node/TS/Chromium, local models, approval/tenant boundaries and recovery/restore.
Full local backend272 passed; online input integrity and Node syntax checks pass.
See [Issue5 evidence](docs/evidence/issue5-codec-removal-verified-2026-10-29.json).

Issue4's email was delivered. Issue5 notification follows this evidence commit.
Remaining findings, compiled-browser coverage and binary source/license review
stay open. Lower image layer bytes are not erased by merged-package removal.
Owner-PC image/activation/reboot acceptance remains separate. No GPU, production,
public distribution or Phase5 readiness is claimed; Phase4 remains open.

## Issue 4 fixed and verified — unused WebKit HTTP libraries

Source `4ea98da1d119ee723265cb856fc73977be64b5b2` excludes libsoup-3.0-0/common
using the existing guarded removal policy, plus independent shared-file checks.
The simulation and actual package checks preserve all21 Chromium dependencies.
Reverse-dependent WebKit networking packages are removed too; no
sandbox restrictions, default enablement, host OS or owner data changed.

Actual Ubuntu26 run `40866505641` passed the exact-image audit,7 canonical,
9 TCP and10 Unix runtime check groups, current-policy provenance and owned
cleanup. Image:
`sha256:8b914553b9f4b0850fe86871711e1ee33df63429dcec54ac9c42128ddb9e93cd`.
All nine excluded packages are absent; previous Brotli/zlib and FFmpeg fixes are
retained. Findings decrease177→133:44 package findings across22 unique CVEs.
Verify `40866504859` passed all three jobs. Full local backend254 and targeted61
tests passed; strict frontend build and online supply-chain integrity passed.
Actual runtime checks are separate from explicitly mocked OCI UI journeys.
See [Issue4 evidence](docs/evidence/issue4-libsoup-removal-verified-2026-10-29.json).

The remaining133 findings, compiled browser coverage and binary license/source-
delivery review remain open. Merged removal does not erase lower image layers.
The owner-PC image has not been rebuilt remotely; activation/reboot acceptance
remains separate. Issue3's email was delivered; Issue4 notification follows this
evidence commit. Phase4 remains open; no production/GPU/Phase5 claim.

## Issue 3 fixed and verified — unused system FFmpeg libraries

Source `e4e112f28570cd4e7eb522b3fe71f9261702c1c9` removes seven unused system
FFmpeg libraries and their gstreamer1.0-libav reverse dependency from the merged
worker runtime. A build-only helper checks the simulated and actual package
changes, preserves all21 reviewed Chromium dependencies and refuses unexpected
installs/removals. Independent SBOM and provenance gates enforce the reviewed
package-policy hash. No sandbox permissions or default enablement changed.

Actual Ubuntu26 run `40863818827` passed the exact-image audit,7 canonical,
9 TCP and10 Unix runtime check groups, provenance and all owned cleanup. Image:
`sha256:472c9b4c7a277acdc5cbeb425b44a2c1b23cc4fce32d24961b5fad1436f0c5e2`.
The scan decreased632→177 package findings:455 findings across65 unique CVEs
were associated with the removed packages. All21 Chromium dependencies remain,
and the previous zlib fix is retained. Verify `40863816928` passed all three
jobs; full local backend250 passed, targeted42 passed. Browser UI regressions
use mocked OCI; the separate Ubuntu26 runtime checks use real rootless execution.
See [Issue3 evidence](docs/evidence/issue3-media-removal-verified-2026-10-29.json).

This is merged-filesystem remediation, not erasure of lower image layers,
Chromium bundled codecs or binary license/source-delivery obligations. Remaining
177 findings need review. The owner's existing image was not rebuilt remotely;
no GPU or production clearance is claimed. Requested notification follows the
evidence commit; delivery is reported separately. Phase4 remains open.

## Issue 2 fixed and verified; owner checkout cache check received

The owner's terminal output confirms Ubuntu26.04.1/kernel7.0.0-38-generic,
successful pre-pull Git fsck, fast-forward4b57d90→3a59e19 and clean final working
tree. Both guarded cache passes found zero candidates and deleted zero bytes.
This is owner-supplied checkout evidence, not remote access or new runtime/GPU
acceptance. No authentication-check URL/credentials are retained in evidence.

Issue2 is the specific OS zlib1g CVE-2026-85091 remediation. Canonical confirms
Ubuntu24.04 fixed version1:1.3.dfsg-3.1ubuntu2.3; the old worker hasubuntu2.2.
Package pin and reviewed-fix regression/policy-identity gates are implemented.
Actual Ubuntu26 run40859366853 atd277a21 passed the same-image audit and7/9/10
canonical/TCP/Unix real runtime check groups, provenance and all owned cleanup.
SBOM confirms the fixed package; its CVE finding is absent. Remaining findings632
are not waived. Local backend239 passed; Verify40859365775 passed all jobs.
Image: `sha256:b88a2c2566edaad442c3e9bef6d0287c713d1b365e588547abb67e21d8a0599a`.
Requested per-issue email follows the evidence commit; actual delivery is
reported separately. The owner's existing image was not rebuilt remotely.
Other image/compiled-browser and license findings are not claimed resolved.

## Sequential work — Issue 1 fixed and verified

The requested **Issue 1 Fixed** email was sent and delivery confirmed after its
passing evidence was committed/pushed (`c2ab061`). The owner selected local PC
cleanup commands. A stdlib-only, preview-first utility now limits deletion to
recognized ignored caches and refuses symlinks/tracked files/unexpected contents;
five temporary-filesystem/Git guard tests passed. Commands are in
[LOCAL_CACHE_CLEANUP.md](docs/LOCAL_CACHE_CLEANUP.md). The owner subsequently
supplied the successful zero-candidate check recorded above; no remote PC access
or broad file deletion is claimed.

Owner requested cleanup followed by one verified issue at a time and a completion
email per issue. See [ISSUE_PROGRESS.md](docs/ISSUE_PROGRESS.md). Cloud integrity
audit found no corrupt tracked JSON/PNG/PDF or Git bundles. Only ignored caches
and proven temporary duplicates (1,337,655 bytes) were removed. Source, history,
backups, credentials, persistent data and useful raw review evidence are retained.
The owner's PC is not connected and has not been cleaned remotely.

Issue1 closed the provenance gap: scan and execute the **same** immutable
rootless worker image, then fail closed on any identity, coverage, check-count
or cleanup mismatch. Actual Ubuntu26 `40851799082` passed exact-image scanning,
7/9/10 canonical/TCP/Unix runtime check groups and the new binding gate.
Image: `sha256:0cc27c1f17d6b325abdc5fbaf3c074f65aa6d0981c7d9ffa805ba250cb3c7279`.
The source export's config/every layer hash matched; all owned cleanup passed.
Verify `40851798371` also passed all jobs (229 backend tests, builds,11/14
overlapping browser suites, database/migration/Compose regressions). Source
commit `614691d`; exact scan/provenance reports retained in docs/evidence.
Lower findings and binary-license review stay open. Issue-specific email is sent
only after a verified commit; delivery is reported separately, not inferred.
No other issue was implemented in parallel. Owner-PC access remains unavailable.

## Current verified result — technical host blockers fixed

**Actual Ubuntu26 integration `40838680397` passed** at `1466e67`: seven
canonical systemd/Compose/local-model/workspace/approval/restart/coordinated-
restore checks, followed by nine TCP and ten Unix real rootless security/recovery
check groups. These are real execution, not mocked OCI. All owned cleanup passed.
Worker image: `sha256:9ff8be0552673bae7d3de0ad67c32d3d5ee78dd068ddf29d3a168d2fa0f25469`.
Host: Ubuntu26.04.1 x86_64, kernel7.0.0-1017-azure, CPU only, disposable hosted
VM. This is not access to or verification of the owner's PC/GPU.

**Verify `40838103014` passed all three jobs** at `5309912`: 195 core +17 actual
Python-sandbox backend tests (**212 total**), strict frontend builds, 11 core
and14 full sandbox browser journeys (overlapping suites; OCI UI is mocked),
PostgreSQL0003 migration/isolation/persistence/logical restore, pristine canonical
Compose and actual core/worker image gates. Reports retain26/633 lower findings;
zero vendor HIGH/CRITICAL is not universal vulnerability clearance.

The failed runtime stages were resolved without weakening isolation: dedicated
user-manager identity/child environment; explicit coding-specialist model with
bounded actual-test feedback; retained execution errors and fresh-approval retry
policy; dedicated controller CWD; empty new-volume ownership before restore.
qwen2.5-coder:1.5b produced the corrected module on its first recorded attempt;
qwen2.5:0.5b coordinated the reviewed delegated plan. This is a small functional
example, not broad autonomous coding/planning or GPU performance evidence.

Bandit1.8.6 Python AST review completed: zero HIGH, three MEDIUM/five LOW,
no skipped tests/nosec suppressions. Findings concern deliberate subprocess and
isolated `/tmp` use; contextual review is in
[UBUNTU26_INTEGRATION_EVIDENCE.md](docs/UBUNTU26_INTEGRATION_EVIDENCE.md).
This is self-review, not an independent security audit.

**Distribution/production remain uncleared.** Remaining work: compiled-browser/
OS lower-finding and binary-license/source-delivery review; owner-installation
activation/reboot validation before enabling its profiles; supported-scope and
quality acceptance. No public browsing/submissions, GPU, Windows/macOS or general
escape certification is claimed. Phase4 stays open; Phase5 has not started.
Full-project completion has not been announced; issue-specific notifications
follow the owner's later instruction above. Source/history remain private.

## Combined actual Ubuntu26 workflow passed; restore fixture correction

Run `40837443204` at `52432f4` passed six actual integration checks: canonical
systemd/Compose/OCI connectivity; failed tests block packaging; local coding-model
repair with three independently checked tests and matching ZIP; delegated real
browser/CSV/PDF outputs; scoped downloads/consumed approvals; app/manager restart
and persisted artifacts. The run then failed in the NEW-volume restore helper:
copytree could not set metadata on the app-owned volume root. No additional
capability is granted: require an empty new target and temporarily chown only its
root before copy, then restore UID10001 ownership. The controller now also waits
for actual manager profile readiness after restart, avoiding an intentional stop
in the middle of startup probes. Full restore and Ubuntu26 exhaustion/recovery
tests remain pending. No Phase4 or production completion claim.

## Native service passed; coding-model quality failure isolated

Real Ubuntu26 run `40835895873` at `1b6473b` passed canonical Compose
authentication, systemd socket activation/GID mapping, all three actual OCI
startup probes and an actual failed-JavaScript test/packaging denial. Thus the
native startup blocker is fixed on this hosted configuration. The run failed
later because the qwen2.5:0.5b repair still failed the reviewed arithmetic tests;
no failing source package was accepted. This is not full acceptance.
The retained failed summary also identified a controller cleanup-check error:
direct Podman inherited the inaccessible runner checkout as CWD. The provisioner
now changes to the dedicated home after dropping identity; no path permissions
are opened up. Earlier cleanup is not claimed verified.

The integration now explicitly assigns the coding role to the free local
qwen2.5-coder:1.5b, retaining small general-model sequential coordination. At
most three model repair attempts receive actual sandbox failure feedback; each
changed source needs a new immutable approval, and all generated modules/hashes
are retained as fixture evidence. The registry license blob is identical to the
already-reviewed Apache2 blob. Its actual runtime verification remains pending.
No manual correct-source fallback. A related real defect was fixed: successful
worker dispatch had cleared the agent's reported execution failure message.
The new regression preserves the failure and confirms packaging stays blocked.

Terminal failed agent execution now rejects generic in-place retry with a clear
409 requiring reviewed inputs and fresh approvals. Previously this transition
queued an unusable `done` stage. Workforce/general controls no longer offer that
invalid action; Computer Mode retains its working review-and-submit-new-task
flow. Targeted agent/OCI tests **50 passed** and strict frontend build passed.
Full local backend before this narrow transition change: **212 passed (28.17s)**.
Current CI/host results remain pending, not inferred from these local checks.

Superseded full-host run `40837192838` was deliberately canceled before task
verification to use the corrected provisioner CWD; duplicate Verify `40837311480`
was canceled while the same production-code Verify `40837192321` continued.
Canceled runs are not passes. Harness-only changes now use their dedicated
opt-in workflow rather than repeating unrelated image scans.

The same host workflow will run representative actual resource, network,
cancellation and crash/orphan suites on Ubuntu26 after integrated acceptance.
No sandbox policy is weakened. The owner's PC and GPU remain untested here.

## Native Ubuntu26 service investigation

Local backend suite: **211 passed (25.28s)**. Verify `40835894770` exposed a
timing-sensitive existing active-cancellation fixture: its 200ms budget could
expire before model dispatch. The fixture now gives dispatch 2s headroom and
checks both entry and cancellation; a separate overdue-job test requires zero
model calls. No production deadline was increased. Corrected CI is pending.

Run `40833749540` failed closed: Podman info timed out inside native preflight,
before task execution. The dedicated user manager inherited runner HOME/XDG
paths (journal showed attempts to read `/home/runner` and another UID's runtime).
The disposable-host provisioner now sets identity paths at user-manager startup;
service children receive only an explicit identity/locale/bus environment, not
activation metadata, remote-engine selectors or manager/GitHub credentials.
No timeout, resource, namespace or Chromium restriction has been relaxed.
Actual corrected service verification remains pending. Verify `40833728281`
passed all jobs at the preceding commit.

Added a fixture-only coordinated restore path for separate database, app-file
volume and manager directory, checking authentication, document bytes, artifacts,
consumed approvals and completed-job replay prevention. This path is syntax
checked but awaits execution after native preflight passes; it is not an owner
backup or a successful restore claim.

Latest full-host run `40832024253`: dedicated environment isolation fixed Podman
reconciliation, but native active preflight still failed; profiles remained
disabled. Added bounded/redacted preflight stdout/stderr diagnostics and a private
operator diagnostic file. The test now checks socket activation before expensive
Compose/model provisioning and always collects fixture diagnostics. No quotas,
seccomp/AppArmor, rootless UID or capability restrictions are relaxed.

GitHub's published Ubuntu26.04 runner is generally available (official runner
image metadata checked). Full-host workflow now permits only standard Ubuntu24.04
or26.04 labels, records actual OS/kernel and keeps GPU verification false. Actual
26.04 result remains pending; this is not access to the owner's PC.

## Native service fail-closed finding and source license coverage

Full host run `40829733249` reached canonical app/model/database and authenticated
socket transport, but the native service's Podman reconciliation failed and
correctly quarantined OCI. No unsafe fallback. Native user units now select their
own HOME/XDG/bus paths and discard inherited container connection/config selectors
and GitHub tokens. Runtime enumeration/recovery logs add bounded, key-redacted
operator diagnostics; web capability errors remain generic. Hosted diagnostics
read only the fixture UID/unit journal. Actual corrected topology run is pending.

Retained successful upgrade reports from `40828075459`: Ollama0.40.13 actual CPU
completion/stream/768-dimensional embeddings and persisted digests after restart;
separate-volume database migration with accounts/session/approval preservation
and unchanged legacy physical data after guard rejection. Source notice inventory
verifies all 44 locked Python and 114 frontend runtime packages have retained
versioned notices. Tested model manifest/license-layer digests match the actual
runtime manifests; Apache2 terms were compared and texts retained. New source
coverage gate and distribution-scope/conditional LGPL/MPL obligations documented.
This is not clearance for public binary/GPU/model redistribution or production.

## Corrected upgrade gates passed; full host topology next

At `055a512`, Verify `40828063598` passed all jobs and targeted compatibility
`40828075459` passed both jobs. Actual Ollama CPU completion, streaming,
embedding and model-directory restart now pass. The modern DB image passed
fresh scanning plus Bookworm logical restoration into a separate volume,
preserved accounts/memberships/sessions/consumed approvals/tenant guards and
refused physical reuse without changing legacy bytes/ownership. No owner data
was used. Local backend **206 passed (22.56s)**; new source/defaults are committed.

Added an opt-in ephemeral hosted integration for actual systemd socket activation,
Compose app/GID/socket mount, private rootless manager, local-model code repair,
real tests/source ZIP, delegated browser/CSV/PDF workflows, approval/tenant checks
and app/manager restart. Controller provisions resources; manager account has no
Docker/sudo membership and application never receives an engine socket. All code
execution remains in rootless workers after mandatory startup probes. Syntax
checked; this full integration remains pending its actual run.

## Safe upgrade implementation and discovered integration failures

Targeted workflow `40825766888` passed the separate-volume logical migration.
Its model test completed actual CPU completion/streaming/embedding, then failed
restart readiness because Docker reassigned its ephemeral host port. The harness
now re-inspects the endpoint after restart. Core workflow `40825750920` exposed
an existing pg_isready race (temporary initdb socket accepted before the foxory
database existed); readiness now requires final TCP and SELECT1 in that DB.
These failed runs are retained as failures, not compatibility clearance.

Modern database startup now refuses unknown/legacy/partial/wrong-major physical
directories BEFORE upstream chmod/chown/startup. Eleven trusted shell-fixture
tests passed. Integration additionally snapshots all fictional legacy file bytes,
ownership/modes before/after a refused modern mount, and verifies restored account
hash/membership/session/consumed approval/tenant boundaries. Actual guard run is
pending. Fresh setup selects modern; existing .env bytes are never edited, and
missing layout selection stops Compose before any service changes. Legacy is
explicit maintenance-only. New-volume override and owner migration guide added.

Ollama's reviewed digest is selected for the next fresh Compose verification;
cloud inference is explicitly disabled. Default execution remains off. Owner
services/data have not been touched or deployed; all hosted data is disposable.
Next required checks: corrected model persistence, guarded database migration,
canonical fresh stack, real socket topology and combined-model workflows.

## Active blocker resolution — hosted verification resumed

The owner's instruction to solve the blockers renews authorization for necessary
hosted tests and pushes, resolving the earlier cancellation ambiguity. Preserve
all previous results/history and avoid duplicate audits. Added a focused manual
compatibility workflow: exact digest/config-pinned previously scanned Ollama
0.40.13 → actual CPU completion/streaming/embeddings/model-directory restart;
freshly rebuilt/audited PostgreSQL derivative → Bookworm logical restore into a
separate owned volume. No owner installation, credentials or data are used.
Ollama fixture runs non-root, read-only/cap-drop ALL with private temporary model
storage and no GPU devices. Syntax checks passed; actual results pending.
Fresh-install/upgrade defaults will change only after relevant compatibility
evidence; no in-place glibc-to-musl database-volume reuse. Phase 4 remains open.

## Current handoff — candidate evidence retained; hosted execution paused

The revised PostgreSQL candidate at `c33c009` passed **zero reported image
findings/868 SBOM components**, plus actual fresh PostgreSQL17 migration0003,
workspace/duplicate guards, restart and same-image logical restore. Its image is
`sha256:aa062455dd5d8628514d4b5fdc448c49537d197e24eb627ba691fece48342f09`.
Official Ollama0.40.13's completed static scan also passed (zero vendor HIGH/
CRITICAL, 32 total). Exact summaries are committed. Default images still carry
the earlier 98/53 HIGH/CRITICAL findings; candidate compatibility is not assumed.

GitHub check-run annotations for repeat candidate runs `40815744272` and
`40816168164` and core job `123257379521` attribute cancellation to
`@Snsmjalzaabi`. No later hosted run is launched after recognizing that signal.
Clarification is pending; do not treat canceled/skipped candidate model tests as
passed. Source changes can be committed locally, but a push would restart the
automatic Verify workflow and is held while that intent is unresolved.

Local continuation adds a separate-volume logical restore target to the safe
PostgreSQL smoke and wires a Bookworm-to-candidate fixture migration after fresh
candidate checks. Reviewed immutable image arguments/major17 guard, separate
random containers/volumes, and source/target cleanup remain enforced. Syntax
checked; actual cross-image execution is **pending**, not migration approval for
owner data. Candidate actual CPU model smoke is staged but never completed.

Latest full local backend: **193 passed (23.96s)**. Last fully successful Verify
observed: `40815695914` at `82b70a2` (core/sandbox/worker-image); later canceled
jobs are disclosed above. Actual rootless `40815268692` at `d1800a7` passed all
nine TCP/ten Unix checks, including new read-only cgroup write-open denials,
application adapter, quota exhaustion and crash/orphan recovery. UI/source and
prior real core-model evidence remain as separately scoped below.

Next continuation: clarify the GitHub cancellations before launching hosted CI;
then run only missing actual candidate model/cross-image DB compatibility tests
using exact reviewed images, avoiding duplicate static scans. Do not replace
owner volumes or switch defaults before compatibility/upgrade evidence. Finish
owner Ubuntu26.04/systemd/Compose mapping/independent restore and combined-model
workflows using `docs/UBUNTU_FINAL_VALIDATION.md`; review CVEs/licenses. Phase4
incomplete, Phase5 not started, production readiness not established, no external
deployment/publication. Current source/history/data are preserved.

First custom PostgreSQL candidate still reported gosu-path Go findings despite
the replacement symlink; it is not accepted. The next build removes that path
entirely and changes only the checked single upstream entrypoint invocation to
su-exec. No scanner exclusion/cache bypass is used. Fresh static and actual
database checks remain required. Default infrastructure/data are unchanged.

Candidate-engineering update: stock PostgreSQL 17 Alpine also failed its actual
scan (26 HIGH/CRITICAL, all the old gosu Go runtime). A review-only pinned Alpine
derivative replaces that helper with signed MIT su-exec 0.3-r0, retaining inventory
and the upstream user/exec entrypoint contract. Defaults/owner data are untouched.
The next candidate workflow adds fresh PostgreSQL migration/isolation/restart/
logical restore and actual quota-limited CPU Ollama completion/embedding checks
after successful image gates. Scripts/YAML syntax checked; actual candidate
build/scan/runtime results pending. No physical cross-libc DB migration claim.

## Latest verified increment and active blockers

Rootless workflow `40814461238` at `8d5ac6f` passed all **nine TCP and ten Unix
checks**, including the actual application adapter → private Unix manager → real
JS execution, resource exhaustion, Chromium artifacts, cancellation and crash/
orphan recovery. Full default Verify `40814448642` passed all three jobs. This
is Ubuntu 24.04/Podman 4.9.3; owner 26.04/final systemd/Compose GID mapping remain
separate. Evidence summary committed. No default execution enablement.

Additional guards: malformed HTTP manager URLs previously reproduced three
configuration crashes; now report disabled instead. Four regressions pass.
Current full backend: **193 passed (23.96s)**. Startup JS/TS probes now require
read-only cgroup control/membership files (open-for-write denial, no quotas are
changed). Probe syntax checked; updated actual host probe run pending.

Completed default infrastructure scan `40814464356` after fixing hosted scanner
storage: **Ollama 0.13.5 has 53 HIGH/CRITICAL findings, 410 total**; PostgreSQL
still has **98 HIGH/CRITICAL, 461 total**. These are now known blockers, not an
unknown Ollama scan or production clearance. Reports retained. A review-only
candidate mode audits PostgreSQL 17 Alpine and official Ollama 0.40.13 (latest
release observed 28 October), without changing Compose/defaults/owner data.
Candidate scan/runtime/model/data-upgrade compatibility remains unverified.

Continue by reviewing candidate findings, verifying safe disposable model and
logical database migration compatibility, finishing owner Ubuntu commands in
`docs/UBUNTU_FINAL_VALIDATION.md`, final topology/independent restore and combined
real-model workflows. Preserve all owner volumes and current source/history.
Do not infer patches from vendor-priority differences or bypass failed gates.
Phase 4 incomplete; Phase 5 not started; no production/public deployment.

PostgreSQL audit summary (98 HIGH/CRITICAL, 461 total) is retained under
`docs/evidence/postgres-image-audit-2026-10-29.json`. Ollama's first audit was
incomplete due to scanner temporary storage exhaustion. Its next ephemeral
hosted job removes unused SDK installations and requires 24 GiB free before
pulling/scanning; no owner/Cloud data, volumes, images or tool installations are
modified. The unsafe/unknown status remains until actual completed results.

## Current continuation: private manager connection and final Ubuntu commands

Actual exported-rootless-image audit and all nine runtime checks passed again
in `40812880482` at `e7c7a25`. Config/layer identity and archive hash were verified
before/after scanning; no Docker access was given to the dedicated account.
Exact archive/image evidence is committed separately. Verify workflow
`40812806745` passed core, real Python sandbox and worker-image jobs.

Added an optional authenticated Unix API transport to resolve Docker bridge vs
host-loopback connectivity without exposing a TCP listener. Explicit enablement,
same private key, workspace scope, private parent/socket permissions, no proxies
and ambiguous-config denial remain enforced. Default Compose stays disabled.
Optional socket-only read-only bind/GID override and systemd user socket/FD
templates are supplied; no manager home/state or engine socket is mounted.
Nine tests passed, including actual Unix HTTP with a controlled server. Complete
backend regression: **189 passed (26.58s)**. Actual rootless Unix manager/adapter
execution and owner systemd/Compose/GID mapping remain pending their real tests.

`docs/UBUNTU_FINAL_VALIDATION.md` contains syntax-checked commands updating the
owner checkout/source archive, rebuilding/auditing the exact rootless image and
running TCP/Unix active fixtures with separate disposable state and retained
evidence. Existing venv/data/environment and owner volumes are preserved.

Infrastructure audit `40813368693` found **98 PostgreSQL HIGH/CRITICAL findings**;
Ollama inspection failed with ENOSPC, so its vulnerability status is unknown.
No owner infrastructure was changed and no failed audit is treated as passed.
Final production readiness remains blocked; Phase 4 incomplete/Phase 5 not begun.

## Current security review scope

Full local regression now passed **180 tests (26.01s)**, including six export
identity/layer-tampering cases. The added actual rootless export scan/runtime
workflow is running; no result is inferred from the deterministic archive tests.

Follow-up of Canonical's public CVE tracker confirms a zero-HIGH/CRITICAL vendor
severity scan is not proof all earlier CVEs were patched. Several util-linux
issues are vendor Medium/needs-evaluation despite CVSS 7.0–7.9; ACL CVE-2026-54369
is vendor Medium/ignored. Privilege/capability/mount restrictions mitigate their
preconditions, but this is not a cleared exception. Details and actual official
links are in `docs/SECURITY_IMAGE_REVIEW.md`. Production acceptance still needs
the contextual review, not just a green scanner job.

Added a manual static audit for the exact default PostgreSQL/Ollama Compose
images. Core/worker scans do not cover those components. It records immutable
IDs/digests and reports without starting services, downloading models or touching
owner volumes. Results pending; no automatic infrastructure/data migration.

## Real rootless acceptance and remediated image evidence

Hosted `40812030339` at `f6190c6` passed **all nine real rootless checks** on
Ubuntu 24.04, Podman 4.9.3, kernel 7.0.0-1017-azure. No mocked OCI boundary:
actual JS/TS/Chromium startup and authenticated execution, workspace/key/duplicate
guards, filesystem/network denial, screenshot/download, queued/running/repeat
cancellation, 15.27-second bounded infinite task, real manager SIGKILL/restart,
owned orphan cleanup, foreign-owner preservation and no replay. Quota evidence:
15 CPU throttling periods, PID max event=1/current=128, memory oom_kill=1 with
child SIGKILL. Cleanup established. Private run artifact includes logs/states/PNG;
summary committed as `docs/evidence/rootless-ubuntu24-2026-10-29.json`.

Core Ubuntu packaging at `7589a8b` passed its actual image gate in run
`40811943218`: **zero HIGH/CRITICAL, 26 lower findings, 3,831 SBOM components**,
after canonical Compose install/restart checks. Worker scan also passed; its
first successful evidence has zero HIGH/CRITICAL, 633 lower findings. Reports
retain findings without exceptions; license/compiled-browser review is pending.

An added archive audit route verifies the actual rootless Podman image without
Docker access: operator-owned stationary export, bounded metadata, image config
and all layer digests, stable scanner descriptor and post-scan archive hash.
Six identity/tampering cases passed; hosted exported-image scan pending. Existing
174 backend tests passed again (27.80s), strict UI build passed (5.94s).

This is not the owner's Ubuntu 26.04 topology, a backup/restore of both live
services, or a combined real local-model/browser/JS workflow. Those gates, final
artifact/license/lower-finding review and broader quality checks remain before
Phase 4/production acceptance. Phase 5 not started, production profiles stay
disabled, no public release/deployment. Earlier failure/pending notes below are
historical evidence and superseded only within the specific scope above.

## Image remediation in progress — actual release blockers

First opt-in hosted OCI run `40811732631` stopped before build/execution: the
runner's inherited `CONTAINERS_STORAGE_CONF` referenced `/home/runner`, correctly
inaccessible to the dedicated account. The workflow now starts the user scope
with an explicit clean HOME/USER/PATH/runtime-bus environment. It does not grant
access to runner credentials/storage or weaken Podman isolation. Runtime checks
remain pending the corrected run.

Update: core Trixie scan in run `40811156834` finished and still blocked on
**44 unfixed HIGH findings** (170 total), despite passing canonical Compose.
Evidence retained separately. The next packaging candidate keeps Python 3.12
but uses pinned Ubuntu 24.04 security packages and a separate dependency-builder
venv; build-only pip/wheels are omitted, scanner metadata retained. No advisory
exception or security-control relaxation. Fresh hosted checks are pending.

The worker remediation at `94f4185` passed its actual hosted image gate
(`40811156834`, job `123241518956`): zero HIGH/CRITICAL findings, 633 total
remaining lower-severity findings, 18,450 SBOM components. This does not clear
license obligations or compiled-browser coverage. The core scan is still
running; no claim is made about its pending outcome.

Added opt-in `scripts/oci_host_acceptance.py` and a manual rootless Ubuntu 24.04
workflow. They use a dedicated account, ordinary systemd delegation, exact image,
private disposable manager, actual startup probes and fixed in-container fixtures
for CPU throttling/PID denial/OOM counters, JS/TS denial, browser artifacts,
queued/running cancellation, timeout and real kill/restart/owned-vs-foreign
orphan handling. They never execute task code in the host or change security
policies. Syntax/schema checks passed; runtime results are pending. This is a
separate host from the owner's Ubuntu 26.04, not a replacement for final topology,
combined-model and restore acceptance. Optional production profiles stay off.

Hosted run `40809535648` at `f927a6b` passed backend/core browser, real Python
sandbox/browser, PostgreSQL and canonical Compose acceptance. The new image gate
correctly blocked release: **61 core HIGH/CRITICAL package findings** and **nine
worker HIGH findings**. Summaries are committed under `docs/evidence`; full SBOM,
license and vulnerability reports are private run artifacts. These are actual
scan results, not fixture findings. No HIGH/CRITICAL exceptions were added.

Remediation candidate: digest-pinned Python 3.12 Trixie runtime with OS updates;
worker pinned Brotli fix and removal of unused WebKit media/global npm runtime
components. Worker policy, quotas and default-disabled execution are unchanged.
Reviewed-input hashes updated; three image-audit parser/archive tests passed.
Rebuilt image scans/integration checks are pending. Rootless host probes must be
rerun for the new worker ID; prior Ubuntu image evidence remains historical.
Phase 4 incomplete, Phase 5 not started; production readiness is not established.

## Current continuation: model compatibility, backup boundaries and image gates

Hosted workflow [40805258673](https://github.com/Snsmjalzaabi/foxory-intelligence/actions/runs/40805258673)
at `422939e` passed **both jobs**. Core: 139 backend tests, 10 browser journeys,
actual PostgreSQL revision0003/isolation/duplicate/restart/dump-restore, canonical
fresh Compose build/startup with six acceptance checks and owned cleanup.
Sandbox: actual Bubblewrap execution/attacks plus browser journeys. This resolves
the previous hosted preflight/installation blockage without changing security
policies or pretending the old failed runs passed. It does not certify Ubuntu
26.04 OCI recovery/exhaustion or complete Phase 4.

Current implementation adds bounded Ollama metadata inspection (32 models,
four metadata requests concurrently, three-second catalog deadline, two-MB
response cap, bounded short cache and digest invalidation). Known embedding-only
models are excluded from chat/Council/agent choices, completion-only models from
embedding choices. Generation/embedding adapters enforce reported capabilities
server-side and return a clear compatibility error. Unknown metadata stays
explicitly unknown and remains usable for older Ollama compatibility; reported
tools/vision metadata is not proof of task quality or a tool permission grant.

Offline SQLite backup/restore now refuses symlinks/special files and traverses
uploads with directory descriptors and O_NOFOLLOW. Source DB/WAL are copied into
a private snapshot before SQLite opens them, URI characters are handled, actual
connections close, private permissions and no-overwrite/rollback stay enforced.
Three pre-fix regressions demonstrated unrelated files/databases being copied via
symlinks. Tests now pass, including a stationary committed WAL and FIFO denial.
The application must still be stopped; this does not promise a concurrent online
backup or support untrusted databases. Native Windows lacks the required POSIX
boundary and fails closed; use the Linux container.

CI now builds the pinned worker and generates application/worker CycloneDX SBOM,
license inventory and vulnerability reports using checksum-pinned Syft 1.55.0 /
Trivy 0.76.1. Tools execute only as explicit verification CLIs, not application or
agent plugins. HIGH/CRITICAL findings (including unfixed ones), unsupported/empty
coverage or tool failure block the image job. License compatibility and compiled
Chromium coverage still need review; no scanner pass means universal safety.
Actual scans remain pending this candidate's CI run. Documentation-only updates
skip expensive builds; all runtime, dependency, policy and test changes still run
the gates, with manual workflow dispatch available.

Canonical images now include readable LICENSE/NOTICE/dependency notices; the
Compose acceptance checks their bytes. Nested data, databases, secrets and test
artifacts are excluded from the build context. The active roadmap now contains
exactly the five approved phases; the superseded seven-part plan is archived.

Local candidate validation: **174 backend tests passed (33.24s)**; **14 browser
journeys passed (2.3m)** with fixture models, actual Python and mocked OCI.
Core-only UI: **11 passed, 3 optional tests skipped**. Actual local-model/public
web acceptance passed all **14 checks** again with qwen2.5:0.5b, smollm2:135m and
nomic embeddings; [evidence](docs/evidence/core-acceptance-2026-10-29.json).
Strict frontend build passed (300.54kB main JS); syntax/Compose/pip checks passed.
The scanner parser/archive tests use fixtures, not a real local image scan.

29 October dependency lookups found no advisories in the npm production graph
or 44 pinned Python runtime packages via OSV. These limited lookups exclude OS,
browser, development/scanner tools and are not security/compatibility clearance.

Remaining production blockers: actual image-scan findings/review; final Ubuntu
resource/hostile-input/cancel/crash/orphan/restore and combined execution tests;
broader quality/accessibility/hardware evaluation. No approved Ubuntu execution
connection is configured here; owner execution or a connected environment is
needed for those gates. Optional execution remains disabled by default, Phase 4
incomplete, Phase 5 not started. No production deployment or public publication.

## Earlier continuation: independent core and sandbox CI gates

Hosted follow-up for `3398ab2`: sandbox job `123219877303` passed actual runtime
tests and browser journeys. Core job `123219877058` passed backend/browser work,
then stopped before PostgreSQL initialization because the fresh runner lacked
`postgres:17-bookworm` and the safe smoke harness uses `--pull=never`. CI now
explicitly pulls that standard core image before the smoke. Pristine Compose and
PostgreSQL hosted acceptance remain pending its next run.

On 29 October 2026, Cloud and GitHub development both matched `4b57d90` before
edits. Actual GitHub workflow `40038556044` was reviewed through its job logs:
**139 passed, 17 real sandbox fixture setup errors**. The namespace isolation
preflight failed on the hosted runner, and all frontend/build/install checks were
consequently skipped. Prior local success was not a hosted-CI success.

CI now has separate core (Ubuntu 24.04) and sandbox (Ubuntu 22.04) jobs. Both
contribute to overall workflow status; repository branch-protection settings are
unchanged. The default pytest command still runs all tests. A registered
`sandbox_runtime` marker selects the 17 tests requiring actual Bubblewrap; no
test is silently mocked/skipped or security policy weakened. Core includes the
remaining 139 tests, parser/authorization/default-disabled guards, manager-free
browser journeys, real PostgreSQL migration/restore and a new pristine Compose
installation harness. Sandbox still requires actual preflight/attack/cancel/
approval tests plus real Python and explicitly mocked OCI UI journeys.

`scripts/compose_smoke.py` creates a generated project name, independent secrets,
loopback port and fresh app/database/model volumes, uses the canonical Dockerfile
with `--build`, and removes only its own resources. It checks account creation,
Ollama availability without downloading weights, disabled execution, restricted
documents/invalid uploads, tenant download isolation and account/session/records/
originals across restart. It never reads the owner's .env or connects to the
owner installation. An explicit reviewed `--image` supports noncanonical checks.

Local verification of this CI change: **156 tests passed (45.60s)**; selection
identifies all 17 real-runtime tests separately. Compose harness syntax/CLI and
whitespace checks passed. Actual hosted jobs/pristine Compose execution are
pending the push; no fresh successful installation claim is made from script
existence. Existing Cloud disk limits are not worked around by deleting owner
data. Phase 4 remains incomplete; Phase 5 has not started.

## Current recovery increment

Branch: `development`. Before edits, the clean Cloud checkout, configured private
GitHub origin and actual remote development ref all matched
`aab7884e6a598f4cde1d9f06d4342cc20fb0be08`. The owner's supplied Ubuntu pull reached
that same commit; the pasted master directive's older Git-discrepancy assumption
was superseded by these checks. No history rewrite, reset, branch deletion or
unrelated repository modification was needed. GitHub remains canonical/private.

The owner subsequently supplied actual Ubuntu fixed runtime passes for JavaScript,
TypeScript and sandboxed Chromium on image
`sha256:248d4afc67fe3b0845b2cedd239d5b378eba4b0ad19e344891fb5fc0873ddbcb`.
See [the scope of that host evidence](docs/UBUNTU_OCI_RUNTIME_EVIDENCE.md).
Application execution stayed disabled. Full host security/recovery acceptance
remains pending; **Phase 4 is incomplete and Phase 5 has not started**.

### Core usability and feature matrix

Core chat/research/documents/accounts/Council/safe agents run independently of
Computer Mode. Default Compose has only app, PostgreSQL and Ollama, with loopback
web binding and persistent volumes. No execution OS account, Podman, sandbox
manager or delegated cgroups are needed for ordinary core installation.

| Capability | Status and evidence | Remaining limit |
| --- | --- | --- |
| Account setup, login/logout, workspace isolation | Implemented and verified: real disposable HTTP workflow plus API/browser authorization tests. | Local single-process deployment; not independently security-reviewed public hosting. |
| Ollama chat, model selection/history/export | Implemented and verified: actual qwen2.5:0.5b, persisted stream/history, Markdown download; stale-model/no-model UI repaired. | Known role mismatches are filtered and rejected server-side; unknown metadata stays explicit. Other runtime protocols not verified. |
| Web search and cited answers | Implemented and verified with actual Wikipedia API/public-page retrieval, saved source hashes and IDs. Uncited model prose now falls back to labeled source excerpts. | Default discovery is encyclopedia-scoped; citation validity is not claim truth. Live SearXNG is implemented but unverified in this increment. |
| Deep Research/history/reports | Implemented and verified: actual model planning, two searches/two pages/three model calls, pause/resume, duplicates/cancel, checked citations and PDF/Word/XLSX. | Tiny-model synthesis used extractive fallback. General research usefulness needs broader evidence/model evaluation. |
| Document intelligence | Implemented and verified: real isolated TXT parsing, JSON rejection, local nomic embeddings/Q&A; seven-format parsing/security regressions. | Linux sealed parser; OCR/macros/formula execution missing or intentionally unsupported. No unrestricted document execution. |
| Model Council | Implemented and verified: actual qwen2.5:0.5b + smollm2:135m independent analysis/comparison/synthesis, sequential. | Consensus is not factual verification; GPU/parallel performance unverified. |
| Safe agents and workspace memory | Implemented and verified: actual model arithmetic plan/tool result; actual web-search tool and model review with an explicit research plan. | Complex autonomous task quality remains experimental; model errors are bounded and visible. |
| Safe scheduling | Implemented: current unit/browser schedule controls and prior accepted real Phase 3 execution evidence. | Fixed intervals, one API process; real timed dispatch not rerun in this increment. |
| Persistence/recovery | Implemented and verified: real session/history/research process restart and consistent disposable SQLite snapshot restore. | Full final Ubuntu application/manager backup/restore acceptance remains pending. |
| Core Docker installation | Implemented and hosted-verified: canonical fresh Compose and PostgreSQL smoke at 422939e, plus local overlay hardening. | Final current-candidate image scans and owner Ubuntu installation remain pending. |
| Optional Computer Mode | Experimental and disabled by default. Real Ubuntu fixed JS/TS/browser probes supplied by owner; real Python + mocked OCI UI/lifecycle regressions in Cloud. | Live-manager tenant/approval, exhaustion, cancellation/orphans/recovery and combined model workflows still pending on Ubuntu. |
| Business modules | Existing optional secondary records/drafts preserved; no business-specific expansion. | No email sending, purchases or publication implementation. |
| Public browsing/submissions and production release | Disabled/unsupported; v1.0 and Phase 4 completion not claimed. | Security review, image SBOM/CVE/license review, broader compatibility and host acceptance remain outstanding. |

### Repairs and current evidence

The live audit exposed Search chat displaying inaccurate, uncited small-model
prose despite retrieved pages. Search/document chat now share Deep Research's
reference check and extractive fallback; empty document evidence skips inference.
Numeric citation examples reduce literal `[N]` output. This guards reference
integrity, not every claim's factual correctness. New unit/API regressions cover
uncited/forged evidence, release/persistence and bounded output requests.

Model refresh now recovers removed selections and prunes unavailable Council
choices. A connected empty installation has a visible model-setup action. Login
explains the private bootstrap token, Documents precedes Computer, Computer is
labeled optional, and Settings states that core tools work independently. A real
response-budget control reaches the validated local inference request. No new
runtime dependency, service, schema or paid provider was introduced.

The strict real acceptance harness, `scripts/core_acceptance.py`, passed **14
checks** with actual local qwen2.5:0.5b, smollm2:135m and nomic-embed-text:latest;
no model/web fixture and no sandbox manager. Evidence with actual public source
URLs/hashes is saved in [core-acceptance.json](docs/evidence/core-acceptance.json).
It uses private disposable SQLite/files, an ephemeral loopback API and already
installed models. The owner application/database/credentials are not accessed; the explicitly
supplied existing Ollama endpoint serves local inference.

The initial exploratory harness did not assert citation validity; its successful
exit is not full core acceptance. Its uncited result prompted the stricter checks
and fix. A targeted browser regression also failed before stale-model recovery was
fixed. These failures are retained in [the recovery report](docs/CORE_PRODUCT_RECOVERY.md),
along with eight inspected UI screenshots, architecture findings and limits.

Final checks executed for this increment:

| Check | Result and scope |
| --- | --- |
| `.venv/bin/pytest -q backend/tests` | **156 passed (71.72s)**: API, grounding, auth/tenant, approvals, jobs, migration and parser/security regressions. |
| `FOXORY_E2E_SANDBOX=1 FOXORY_E2E_OCI=1 npm run test:e2e` in frontend | **13 passed (2.3m)**: actual HTTP UI, fixture Ollama, real restricted Python and explicitly mocked OCI. Intermediate response-budget selector failure was corrected; no timeout/security relaxation. After the final mobile copy-layout fix, the focused mobile journey passed again (13.5s). |
| Core-only browser run | **10 passed, 3 optional tests skipped (2.1m)** without manager; prior to the final response-budget UI addition. Final core independence is also checked by the real native harness. |
| `npm --prefix frontend run build` | Strict TypeScript/Vite passed (7.35s), final main JS 299.98kB. |
| `scripts/core_acceptance.py --ollama-url OPERATOR_LOCAL_OLLAMA` | **14 actual local-model/public-web checks passed**, no model/web/OCI fixture, sandbox disabled. SQLite restart/restore and logout/login included. |
| `scripts/phase4_docker_smoke.py --build --image foxory-intelligence-app:core-recovery` | Passed backend-current overlay image `sha256:e3ddcd099ef22077a043eab8af34df878e452b26f345e46d1609490421d4f13b`: health, disabled sandbox, persisted memory, core/agent source and frontend hashes, UID10001/read-only/init/cap-drop/no socket. Disposable container/volume removed. This is not a fresh canonical build; its frontend snapshot predates the final mobile paragraph-layout adjustment, checked separately. |
| `scripts/phase4_postgres_smoke.py` | **Blocked, not passed**: first readiness failure; diagnostic retry exited with `initdb` ENOSPC creating pg_wal, before migrations. Both disposable containers/volumes removed. Existing accepted PostgreSQL evidence below is historical only. Rerun on sufficient container storage; do not remove owner volumes. |
| Other checks | CPU/GPU Compose syntax, pip dependency consistency, offline worker input integrity, Node syntax, Python compilation, documentation shell syntax and whitespace passed. No GPU runtime or fresh dependency/image security audit. |

Structured evidence: [real core](docs/evidence/core-acceptance.json),
[Docker overlay](docs/evidence/core-docker-check.json),
[PostgreSQL blocker](docs/evidence/postgres-recovery-check.json).
No owner application/database records were accessed by these disposable harnesses.
The authorized local Ollama endpoint was used for actual inference. Prior
increment evidence below remains historical, not rerun claims.

### Continuation and Phase 4 boundaries

Use normal GitHub fast-forwards, not bundles when authenticated push is available.
On Ubuntu, pull development and install/upgrade the core through the documented
Compose workflow with sandbox enablement off. Review larger local completion
models and broader search quality when resources permit. Do not redo already
passing rootless provisioning/Chromium diagnostics. Continue the remaining
host-only checklist for security, cancellation, orphan/restart handling and actual
integrated Computer Mode workflows, keeping optional execution disabled until
accepted. No Phase 5/public release/production readiness claim is justified.

## Historical Chromium correction increment (before owner runtime evidence)

### Original browser-only chroot implementation record

Branch: `development`. Baseline: `d5503e8f785571a146444666b873f13789c60517`.
Phase 4 remains **incomplete**; Phase 5 has not started. The operator reports
rootless Podman/delegation/static checks and an immutable image build on Ubuntu
26.04, with JS/TS apparently passing before Chromium fails at
`sys_chroot("/proc/self/fdinfo/") == 0`. This is supplied host evidence, not a
successful rerun of the correction.

Upstream Chromium uses that chroot to remove filesystem access. Upstream
containers/common seccomp conditions chroot allow/deny on `CAP_SYS_CHROOT`;
dropping every capability can therefore deny the syscall even inside Chromium's
nested user namespace. AppArmor or a different installed seccomp policy may
still deny it. The assertion alone does not establish the actual errno/cause.

Implemented a required validated profile in the shared OCI command builder:
only browser adds `--cap-add=SYS_CHROOT` after `--cap-drop=ALL`. Authenticated
manager dispatch and fixed probes both pass that profile. JS/TS command policies
remain identical to each other and retain every previous restriction. No
privileged mode, SYS_ADMIN, no-sandbox, unconfined policy or resource relaxation.
The Python profile, image inputs, dependencies, approvals and data are unchanged.

Both code-profile fixtures now check all five capability masks are zero,
NoNewPrivs=1 and Seccomp=2, plus existing effective quota/filesystem/network
checks. The verifier emits separate stderr pass markers without corrupting its
machine-readable stdout; browser failure cannot report overall success or enable
execution. No automatic activation was introduced.

Verification executed for this increment in Codex Cloud:

- `.venv/bin/pytest -q backend/tests`: **148 passed in 57.86 seconds**, including
  policy equality/negative cases, authenticated dispatch, probe command building,
  partial failure reporting and existing migration/security/recovery regressions.
  OCI execution is explicitly mocked in these tests; it is not isolation proof.
- `npm --prefix frontend run build`: passed strict TypeScript and Vite build
  (14.50 seconds). No frontend source changed. The previous 12 UI journeys below
  are historical evidence, not rerun results for this increment.
- Offline worker supply-chain verification: passed, pinned inputs unchanged.
  Node worker and fixed JS probe syntax, Python compilation, documentation bash
  syntax and `git diff --check`: passed. Bash procedures were parsed, not run.
- Actual rootless Chromium/JS/TS, image rebuild, Docker integration and local-model
  workflows were **not rerun** for this correction. Known Codex host limitations
  were not re-probed. No Ubuntu runtime success or production readiness is claimed.

Security implications, exact changed-file manifest, source references, update
transfer and dedicated-account Ubuntu rebuild/reverification commands are in
[CHROMIUM_SANDBOX_UBUNTU.md](docs/CHROMIUM_SANDBOX_UBUNTU.md). Keep OCI disabled
until fixed probes and the full remaining host acceptance checks pass. If the
browser still fails, retain logs and inspect installed seccomp/AppArmor denials;
do not weaken isolation. Next action: transfer this commit to the Ubuntu owner's
checkout, refresh the dedicated account's tracked source without replacing its
virtualenv/state, rebuild and run the fixed verifier in the delegated scope.

## Preserved evidence from the prior connected-OCI increment

Branch: `development`. Starting commit:
`09b707da144b72e481117ce7b0dd19cfef96bb73`.
Phases 1–3 remain accepted; Phase 5 has not started. Phase 4 is **not complete**
and production readiness is not claimed. Prior evidence is preserved in
[the previous increment](docs/PHASE4_OCI_GROUNDWORK.md) and
[Phase 3 status](docs/PHASE3_STATUS.md).

## Implemented in this continuation

- Authenticated manager dispatch for JavaScript, Node type-stripped TypeScript
  and offline Playwright, sharing the existing single execution slot with Python.
  New profiles require explicit operator opt-in, an immutable local worker image
  and active startup probes; defaults remain disabled. No host-code fallback.
- Rootless OCI create/attach lifecycle with source-only read-only mounts, network
  denial, fixed CPU/memory/PID/tmpfs quotas, engine and manager wall deadlines,
  bounded streamed logs, status persistence and whole-container cancellation.
- Ownership labels restrict removal to this manager/task. Cleanup must establish
  absence before reporting completion. Failures quarantine OCI execution. Startup
  and periodic reconciliation detect owned orphans; interrupted records remain
  auditable without silent code replay. Foreign containers are not removed.
- Shared artifact validation: fixed names, exact metadata, base64/size/SHA-256,
  UTF-8, strict JSON, safe CSV cells, bounded PNG structure/CRC/decompression.
  Download APIs revalidate bytes and owning workspace/job/approval-derived manager
  ID, prevent cross-workspace access, audit downloads and set no-store/nosniff.
- Explicit agent tool scopes and immutable expiring approval gates for all new
  profiles. Failed/interrupted execution stops the workflow and prevents source
  packaging. JS/TS packaging requires successful execution of identical sources.
- Computer Mode profile configuration, availability/limits, reviewed source and
  browser actions, plans/timelines/live logs, approvals, pause/cancel, failures,
  newly approved retry, authenticated screenshot previews and artifact downloads.
- Pinned upstream worker image index, locked Playwright dependency graph, reviewed
  source/build hashes and online registry-byte checks. Optional image recipe has
  no runtime dependency install. Complete Ubuntu setup/security acceptance
  checklist and a separate rootless systemd user-unit example are supplied.

## Verified in Codex Cloud

- Backend final full run: **142 passed (47.58 seconds)**, including real Python
  sandbox tests, SQLite migrations and mocked OCI lifecycle/approval/tenant cases.
- **12 Chromium UI journeys passed (2.4 minutes)**. Existing Python execution
  uses real Bubblewrap/seccomp. The additional JS packaging/browser screenshot
  and failure/retry/pause/cancel journeys use the explicit test-only mocked OCI
  boundary, with real HTTP manager,
  backend, scopes, approval persistence and artifact downloads. Ollama is a fixture
  in browser journeys. These results do not prove actual OCI/browser isolation.
- Combined multi-agent workflow test passed: web/model/OCI fixtures, real durable
  delegation and four approval gates, deterministic calculation, actual PDF
  generation/parsing and source ZIP integrity. No live web/browser task is claimed.
- Frontend strict TypeScript/Vite production build passed; Node worker syntax,
  pip dependency check, CPU and GPU Compose syntax passed. GPU syntax is not GPU
  execution. CI now includes mocked OCI UI journeys and worker input checks;
  remote CI has not been run.
- Worker supply-chain checks passed offline and online: pinned upstream manifest
  digest plus exact Playwright/playwright-core archive SHA-512 integrity. Worker
  image build/runtime, SBOM/vulnerability audit and real-host isolation remain
  pending. The npm bulk advisory query returned no advisories for the two pinned
  packages; this excludes OS/Chromium vulnerabilities. No worker image was pulled/built here: the large base does not fit the
  available disk budget safely alongside owner data.

During development, the regression suite exposed repeated shutdown cancellation
interrupting Python process-map cleanup (128 passed, 3 teardown errors). Cleanup
is now shielded and repeated cancellation is guarded; the subsequent full 136-test
run passed. Final compatibility review also retained downloads of accepted Python artifact
records that predate the explicit workspace field, while checking their scoped
record, consumed approval and workspace-derived manager ID. Rejected approvals
still prevent downloads. No isolation controls or tests were weakened.

## Docker, database and actual local-model verification

Current-source application overlay image built and verified:
`sha256:4c40f0258785d9a7d3fd7192a0914a2264111367064f99c2205a9b32a5fd09aa`.
Health, default-disabled execution, memory persistence after restart, source/UI
hashes, actual non-root UID, read-only filesystem, init/cap-drop and absence of
runtime socket mounts passed. This reuses the accepted dependency image; it is
not a fresh canonical Dockerfile build or a worker-image isolation test. Disposable
smoke resources were removed. A separate PostgreSQL 17 container passed revision
0003 migrations, workspace isolation, duplicate constraints, restart persistence
and custom-format dump/restore; its container/volume were removed. Owner database
and application were not accessed by that harness. Real local-model rerun results
passed with actual `qwen2.5:0.5b`: intentionally failing Python source exited 1
and was blocked from packaging; model-repaired source exited 0 after real tests,
consumed separate execution/packaging approvals and produced a matching CRC-valid
ZIP. Account/session/completed task survived restart. Acceptance tests were
reviewed deterministic tests, not autonomously generated tests. This verifies
Python, not the new OCI worker or GPU performance. Owner containers/volumes remain
untouched.

## Remaining Phase 4 acceptance

Application wiring and deterministic tests are complete. Actual Ubuntu-host
acceptance remains **unchecked** in [PHASE4_CHECKLIST.md](docs/PHASE4_CHECKLIST.md)
and [SANDBOX_HOST_VERIFICATION.md](docs/SANDBOX_HOST_VERIFICATION.md):

1. Build/review the pinned worker image and run actual rootless JS/TS/Chromium
   fixtures; verify effective aggregate controls, Chromium sandbox and artifact
   validity. A static host capability result is never sufficient.
2. Demonstrate real cancellation, deadlines, descendants/staging cleanup,
   manager process-crash/orphan recovery and restart persistence on that host.
3. Exercise malicious inputs, cross-workspace/approval boundaries, network/host
   denial, PID/memory exhaustion and the final manager/container topology.
4. Run actual local-model combined workflows and retain real screenshots,
   calculations, tests, reports and source packages with evidence of each stage.
5. Complete final-image regression, image vulnerability/license review and the
   independent security review appropriate before a proposed public release.

Public network browsing, external form submission, runtime package installation,
privileged tools and remote communications remain unsupported/blocked. The
browser profile is deliberately an offline supplied-site environment. No GPU,
Windows/macOS or production compatibility verification is claimed.

## Prior continuation (superseded by current recovery notes)

Continue on development HEAD. Do not rebuild the architecture or repeat the known
Codex cgroup diagnostics. The next work is the Ubuntu checklist against the pinned
image and connected manager; investigate failures while keeping quotas, namespace
isolation and Chromium sandbox intact. Record actual host evidence before marking
Phase 4 complete. Do not begin Phase 5 or publish/deploy publicly.

## Verification commands executed

```bash
.venv/bin/pytest -q backend/tests
npm --prefix frontend run build
# Run from frontend/:
FOXORY_E2E_SANDBOX=1 FOXORY_E2E_OCI=1 npm run test:e2e
# Run from repository root:
.venv/bin/python scripts/verify_worker_supply_chain.py --online
.venv/bin/python scripts/phase4_postgres_smoke.py
.venv/bin/python scripts/phase4_docker_smoke.py --build --image foxory-intelligence-app:phase4-oci-connected
# The Ollama URL is a discovered local disposable-test connection, supplied by the operator:
.venv/bin/python scripts/phase4_integration.py --ollama-url http://LOCAL_OLLAMA:11434
```

`pip check`, Node worker syntax, Compose CPU/GPU syntax and whitespace checks
also passed. Worker source was reviewed to make output-budget violations fail
explicitly, then syntax/input-integrity checks were rerun. Its runtime path still
requires Ubuntu verification. The optional user-service example is not installed.
No public publishing, production deployment, real communications or purchases.
