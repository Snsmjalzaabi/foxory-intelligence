# Coordinated application and sandbox recovery

A PostgreSQL dump alone is not a complete FOXORY backup. Preserve together:

1. PostgreSQL logical dump, including accounts, memberships, sessions, approvals,
   records, schedules and jobs.
2. The application's `/data` tree, including original uploads and document data.
3. The dedicated manager's private state tree, excluding its transient `.lock`.
4. Private application/manager configuration and matching source/image identifiers.
   Manager keys must match restored approvals and job records.

Model weights are separate replaceable storage. Record their exact manifests and
licenses; do not confuse model-directory persistence with an application backup.
Do not publish backup files, environment files, account hashes or model weights.
Use owner-controlled encrypted storage and private directory/file permissions.

## Consistency and boundaries

Stop application writes/background scheduling before capturing any component.
Stop both the manager socket and service so an incoming connection cannot
reactivate it while copying. Require successful worker cleanup; an interrupted
or unavailable engine must not be called a clean snapshot. Preserve the original
installation and exact configuration throughout rehearsal and rollback.

For Compose, a stopped application container still supports `docker cp` for
`/data`; keep PostgreSQL available for `pg_dump -Fc`. The dedicated manager
account can archive its own state, but must never receive Docker/sudo membership
or access to the owner's credentials. The owner/admin provisioner coordinates
these separate backups. Never mount a runtime socket into the application.

Restore only trusted, integrity-checked backups into a **new** database, app
volume and manager directory. Reject symlinks, special files and escaping paths.
Never overlay an existing destination or attach an old physical PostgreSQL
directory to a different layout. See [DATABASE_UPGRADE.md](DATABASE_UPGRADE.md)
for the guarded logical database transition and collation/index considerations.

The trusted fixture restore helper runs in a separate networkless, read-only
maintenance container with only the private backup (read-only) and new app volume
mounted. It has CHOWN/DAC_OVERRIDE, not FOWNER, SYS_ADMIN or a runtime socket.
It requires an empty target, temporarily owns that new volume root for metadata
copy, then restores UID/GID10001. This is administrator-controlled maintenance,
not an agent tool or a permission available to generated code. App and worker
capability policies do not change.

## Acceptance before cutover

Keep execution disabled during core restoration. Verify authentication and
membership boundaries, original document bytes, artifact downloads, consumed
approval rejection, schedules and completed jobs before enabling a separately
verified manager. Restore manager state and its key together: an empty manager
directory is not a substitute for restored idempotency history.

The actual fixture checks that replaying a completed request returns the same
completed record and `finished_at`, rather than executing code again. Interrupted
requests must remain interrupted and require a newly reviewed task. Never reset
approvals or delete manager history to force a retry. Root-directory changes also
change manager ownership labels; reconcile any old-root workers before moving
state, and never remove foreign-owner containers.

Retain original data, new targets and backup manifests until all checks pass.
Rollback after accepting new writes needs explicit logical reconciliation; old
backups cannot contain later writes. Do not run `down --volumes` on an owner
installation as a recovery step.

## Verification scope

`scripts/compose_manager_acceptance.py` is an **ephemeral hosted-fixture-only**
provisioner, not an installer/backup script for the owner's machine. It exercises
the procedure with fictional data and private test keys, preserving its source
DB/volumes until verification, then removing only its own labeled resources.

The trusted helper's actual local Docker smoke verified bytes, UID/private mode,
nonempty-target rejection, symlink rejection and owned-volume cleanup without
FOWNER; see `docs/evidence/trusted-restore-helper-2026-10-29.json`. This is not a
rootless sandbox security test. The initial smoke failed during fixture setup
before running the helper; that failure is retained separately.

Full coordinated Ubuntu26 restoration passed in run `40838680397`: restored
authentication, original document bytes, artifacts, consumed-approval denial and
completed manager-request no-replay. No owner backup, cutover, reboot recovery or
GPU operation is claimed. See [the evidence record](UBUNTU26_INTEGRATION_EVIDENCE.md).
