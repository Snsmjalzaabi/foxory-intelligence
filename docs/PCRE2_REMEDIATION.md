# Issue 6 — PCRE2 upstream-source replacement

Status: verified in source `40603a043c3b0485951d72f67114be1ec0ece6b7` by CI
`40928966386` and actual Ubuntu26 integration `40928967215`. See
[the image-specific evidence](evidence/issue6-pcre2-remediation-2026-10-29.json).
This resolves the installed PCRE2 issue in the three revised managed images;
owner-PC rollout, unrelated findings and general production acceptance remain
separate. Only PCRE2 is in scope.

## Why a source build

The retained worker, application and Ollama baseline scans each report the same
seven CVEs in Ubuntu's libpcre2-8-0 10.42-4ubuntu2.1. Noble's CVE pages still mark
that package vulnerable. PCRE2 upstream recommends the current10.49 release;
10.48 and earlier contain the growable-JIT-stack issue. The fixes for all seven
reviewed CVEs are ancestors of the pinned10.49 release commit, as recorded in
`sandbox_manager/runtime/pcre2/source.json`.

The release archive SHA256 is
`53c156e1ba416a20da8e65395daa132da0d80e76910424caca3fcdae7831d384`.
Its detached GPG signature is verified using primary fingerprint
`A95536204A3BB489715231282A98E77EB6F24CA8` and signing subkey
`BACF71F10404D5761C09D392021DE40BFB63B406`. The committed **public** key came
from Ubuntu's public keyserver; the upstream maintainer's signing instructions
identify the FB63B406 signing key. GitHub reported the tag key as unknown; we
verify the archive signature locally instead of claiming GitHub verified it.
The source recipe never executes a downloaded installer or disables TLS checks.

## Build and verification boundary

A non-root, network-disabled build step compiles the signed source. The normal
and ASan+UBSan builds each run the configured8-bit/JIT upstream test suite
(RunTest, POSIX, JIT and grep harnesses), then a fixed native regression probe.
The probe checks actual loaded version, Unicode, the DFA heap-limit failure and
the growable-JIT-stack limit regression. It rejects arguments and exits before
the regressions if the loaded library version is not10.49. Upstream/sanitizer suites run only in builder containers. The fixed argument-free
loaded-library smoke check runs in disposable application/model containers and
restricted rootless probes; it refuses an older version before those cases.
It never runs directly on the owner host or inside an application request handler.

Packaging checks the existing public symbols remain available and SONAME stays
`libpcre2-8.so.0`. The custom DEB is truthfully versioned10.49-0foxory1, with
`Source: pcre2`; this is not a Canonical-issued update. It installs the compiled
normal library, fixed verifier, source/hash/test metadata and complete PCRE2/
SLJIT license notices. Build tools, source trees and sanitizers stay in builder
stages. Existing OCI capabilities, quotas, network, filesystem and approval
controls are unchanged; profiles remain disabled by default.

Application and model-service verification checks the installed native library,
source/build manifest and matching file hash in running disposable containers.
Worker startup checks the same inside its existing restricted rootless profiles.
The final host evidence gate binds the native probe to the exact audited image.
A version string in package metadata alone is insufficient.

## Scanner interpretation

All raw scanner entries are retained. Ubuntu's advisory mapping may continue to
report these seven entries for a custom upstream package even after its actual
library is10.49. Do not erase entries, falsify the version or globally suppress
PCRE2 CVEs. Record image-specific source/native remediation evidence separately
from distribution-feed output. The mandatory exact-version and native-regression
gates reject the previous affected package. Other findings and binary-license
reviews are separate, and are not cleared by this fix.

## Owner Ubuntu rebuild and verification

These commands build/test images only; they do not start the application, enable
execution, alter host libraries or replace model/database volumes. Require free
build/scanner disk space, local Docker access, and the existing dedicated rootless
manager account. GPG is required for online input verification. Do not use a
privileged fallback or execute build helpers directly on the host.

From the owner checkout:

```bash
cd "$HOME/Projects/foxory-intelligence"
git diff --quiet && git diff --cached --quiet
git switch development
git pull --ff-only origin development
docker --host=unix:///var/run/docker.sock build --target application \
  -t foxory-intelligence:pcre2-verification .
docker --host=unix:///var/run/docker.sock build --target ollama \
  -t foxory-ollama:0.40.13-pcre2-10.49-community .

for image in foxory-intelligence:pcre2-verification foxory-ollama:0.40.13-pcre2-10.49-community; do
  docker --host=unix:///var/run/docker.sock run --rm --network=none --read-only \
    --user=10001:10001 --cap-drop=ALL --security-opt=no-new-privileges \
    --memory=1g --memory-swap=1g --cpus=1 --pids-limit=64 \
    --entrypoint=/opt/foxory/pcre2-verify "$image"
done
```

Require version10.49, Unicode/JIT true, dfa_error=-63 and jit_stack_error=-46.
These fixed Docker checks do not establish rootless worker isolation. Rebuild the
worker as foxory-sandbox under the existing delegated scope using
[UBUNTU_FINAL_VALIDATION.md](UBUNTU_FINAL_VALIDATION.md); its fixed probes now
require the installed PCRE2 evidence too. Keep source, raw scan and runtime logs.
Do not activate the owner services/profiles solely because these limited probes
passed; complete the existing final acceptance checks.

## Maintenance

The custom version is intentionally newer than Noble's10.42 packages. Ordinary
Ubuntu package updates will not maintain it automatically. Maintainers must
review each upstream PCRE2 security release, renew source/signature/key pins,
recheck all fix ancestors and licensing, update the native expected version and
package policy, and rerun source/sanitizer/ABI/image/runtime gates. Do not simply
bump a version or adopt a new signing key automatically. Moving back to a vendor
package needs an explicit reviewed migration; never force dependency removal.

Only Linux AMD64 execution demonstrated by retained evidence may be claimed.
No GPU, ARM64,32-bit, Windows/macOS, complete sandbox-escape assurance or production
clearance follows from these checks. The host OS PCRE2 package is unchanged.
