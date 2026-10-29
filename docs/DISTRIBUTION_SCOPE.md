# Distribution and license review scope

FOXORY application source is Apache-2.0. Dependency, operating-system, browser,
GPU runtime and model licenses remain separate; the stack is not being relicensed
as Apache. No public publication is performed by development tests.

The proposed first distribution is the repository/source archive with LICENSE,
NOTICE and THIRD_PARTY_NOTICES.txt intact. Notice coverage checks all 44 locked
Python runtime packages and 114 frontend runtime packages against retained
version-specific license texts. Frontend runtime licenses are MIT, ISC and
BSD-3-Clause. Python conditional obligations include:

- psycopg/psycopg-binary LGPL-3.0-only: preserve library licenses, replacement/
  relinking rights and corresponding-source obligations when conveying binaries.
  FOXORY source permits modification/reverse engineering. Replacement may need a
  rebuild with appropriate libpq/dependencies; Dockerfiles remain editable. This
  inventory is not a corresponding-source bundle.
- certifi MPL-2.0: preserve file-level notices and covered source under its terms.
- Compiled wheels and OS packages retain bundled-component licenses too; full
  image source/license review remains necessary.

`scripts/review_source_licenses.py` checks notice/version coverage and unknown
metadata without importing dependency code. It is an inventory, not universal
legal clearance. Dependency changes require renewed review.

Exact qwen2.5:0.5b and nomic-embed-text manifests used by CPU integration were
checked against public registry license layers. Blob hashes were verified and
Apache2 terms compared to retained Apache2 text. Full texts/manifests are in
`docs/evidence`. Other digests/models require separate review. Weights are not in
the repository/source archive; no automatic purchase/subscription is required.

**Public prebuilt image/model redistribution is not cleared by this inventory.**
Before conveying binaries, retain exact SBOMs, copyright/license files and
corresponding sources/offers required for GPL/LGPL/MPL components; review CUDA
and compiled-browser terms. A generic Apache label or upstream URL alone does
not replace source-delivery obligations. Review artifacts remain private and
must not become public releases automatically.

Security acceptance, supported-host installation, backup/recovery and Phase4
remain independent gates. Attribution or scanning does not establish production
readiness.
