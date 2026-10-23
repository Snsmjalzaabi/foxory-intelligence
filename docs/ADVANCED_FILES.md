# Advanced file and data tools

`data.table` is a statically registered, deterministic tool requiring `calculate`.
Input: `rows` (at most 500 objects/20 columns, 20,000 serialized characters),
`column`, optional `group_by`, `minimum`, `maximum`. Non-numeric/missing/non-finite
values are counted as invalid; filtered rows are counted separately. It returns
at most 50 groups with count, compensated sum, mean, median, min/max, population standard deviation and
an escaped, self-contained SVG showing absolute group totals with signed labels.
It accepts supplied rows, not filesystem paths or executable code. Uploaded
spreadsheet extraction remains in the existing sealed parser; automatic mapping
of uploaded tables into this tool is outstanding. Outputs remain untrusted data.

`source.package` requires `documents.write` and immutable per-step approval.
Input: `title`, `files` mapping relative ASCII paths to UTF-8 text. At most 50 files
and 20,000 bytes are permitted. Absolute, traversal, alternate separator, hidden
credential `.env` and Git metadata paths are rejected. Files are ZIP members only;
no checkout, subprocess, installation, repository write or code execution occurs.
After approval, the task returns an artifact ID. Download from
`GET /api/artifacts/{id}/export?format=zip` or Workforce > Tasks > Generated artifacts.
Source code may be unsafe when the user executes it later; generation does not
establish correctness. Do not package private uploaded material without consent.

All artifacts support existing Markdown/PDF/DOCX/XLSX exports and new JSON/CSV
exports. CSV cells beginning with spreadsheet control prefixes are escaped. JSON
and CSV contain title and report body, not original source documents. Source ZIP
availability is metadata only in the overview; source bodies are excluded there.
Existing session, workspace and viewer restrictions apply. No new dependency,
privileged service, paid API, database migration or network policy was introduced.

## Execution boundary still required

The current managed daemon reports seccomp/cgroup namespaces but no rootless
security option. This is not sufficient evidence for a general untrusted-code
sandbox. An exploratory rootless Bubblewrap 0.12.0 process did run in new
namespaces with network unreachable and a reduced mount tree; that probe is not
a deployed/authenticated manager or a completed isolation test suite. No Docker socket is exposed to the application. Browser/coding execution
and Computer Mode remain unavailable pending a separately authenticated,
constrained manager, rootless isolation deployment, network enforcement and
security integration tests. Do not enable a host-shell fallback.
