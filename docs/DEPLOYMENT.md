# Deployment operations

The supported baseline is a private, single-host Linux installation with one
API process, PostgreSQL and local Ollama. Do not scale API replicas: scheduling,
inference coordination and rate limits are process-local. Optional Computer Mode
stays disabled. Public production release remains subject to the unresolved
image, security and license gates in [the blocker register](BLOCKER_REGISTER.md).
This runbook does not clear those gates.

## Install and validate

Use Docker Engine with Compose v2, Python 3.11+ and sufficient disk for source
builds, persistent database/uploads, model weights and backups. The default
container memory ceilings total 19 GiB; allow additional host/build headroom.
Choose models against available RAM/VRAM; none download automatically.

For a new installation, from the repository root:

```sh
python scripts/setup.py
docker compose config --quiet
docker compose up -d --build --wait --wait-timeout 300
docker compose ps
curl --fail http://127.0.0.1:8000/api/ready
```

Keep `.env` mode 0600 and outside source control. `compose config --quiet`
validates without printing secrets. Existing installations must follow
[database upgrade instructions](DATABASE_UPGRADE.md); never change the database
layout on an existing physical volume. Start locally, use the private bootstrap
token to create the administrator, and explicitly choose/download licensed models.

`/api/health` measures API liveness. `/api/ready` is unauthenticated and returns
200 only when the database answers, its migration revision matches this build,
and core/account tables are queryable; otherwise it returns a generic 503.
The image healthcheck uses readiness. Ollama/model availability is separate:
an empty model library does not prevent login, settings or document access.
Docker marks unhealthy containers but does not automatically restart a running
unhealthy container; monitor health and investigate `docker compose logs --tail
100 app`. Do not send tokens or connection strings to monitoring systems.

## Private HTTPS behind a reverse proxy

Provision DNS and a trusted certificate on the host. Adapt
[the nginx example](../deployment/nginx.conf.example), validate with `nginx -t`,
and use network access controls appropriate to the private deployment. The
example keeps HTTP streaming unbuffered and replaces incoming forwarding headers.
Leave PostgreSQL/Ollama unpublished and the application port bound to loopback.

Add these values to `.env`, replacing the example DNS name and proxy address:

```dotenv
FOXORY_ALLOWED_HOSTS=localhost,127.0.0.1,[::1],intelligence.example.com
FOXORY_SECURE_COOKIES=1
FORWARDED_ALLOW_IPS=172.18.0.1
```

`172.18.0.1` is illustrative: use the exact source peer address the application
container sees from your proxy. Host nginx commonly appears as the Compose
network gateway; inspect `docker network inspect foxory-intelligence_default`
and confirm your topology. For a containerized proxy use its stable private
address or a dedicated trusted proxy network CIDR, not a shared untrusted network.
Never use `*` for forwarded-header trust or allowed hosts. Preserve `127.0.0.1`
in allowed hosts for image health probes. Recreate app after environment changes:

```sh
docker compose up -d --no-deps app --wait --wait-timeout 300
curl --fail https://intelligence.example.com/api/ready
```

Verify browser login and a streaming chat over HTTPS. A trusted proxy must supply
the HTTPS scheme for same-origin validation; forcing secure cookies alone does
not fix incorrect forwarding. Confirm `foxory_session` has Secure, HttpOnly and
SameSite=Strict. Do not enable secure cookies for plain HTTP localhost use.

## Upgrade, backup and rollback

Record the deployed Git revision and exact image IDs. Keep database/uploads and
the private environment file together as a coordinated recovery set; retain model
volume configuration too. Before upgrading, stop app writes and follow
[backup/restore instructions](../INSTALLATION.md#back-up-and-restore). Test a restore
in a separate Compose project with separate volumes before relying on it.

Build the new images before the maintenance window. Stop the app, take the
coordinated backup, then recreate the stack with the new images and `--wait`.
Startup runs Alembic before starting the single Uvicorn worker; migration failures
prevent serving requests. Verify readiness, administrator login, existing records,
document download, model access and one bounded chat before ending maintenance.

If migrations have run, rolling back only the image may be incompatible. Stop
writes and restore the matching database/uploads snapshot into clean volumes
with the recorded previous images. Preserve failed-upgrade data for diagnosis;
do not run `down --volumes` or overwrite the only recovery copy. Review
[coordinated recovery](COORDINATED_RECOVERY.md) for optional manager deployments.

## Release validation

The existing Verify workflow covers core tests, strict UI build, browser journeys,
fresh Compose installation, PostgreSQL migrations/restore and image audits.
The deployment tests additionally check migration/database readiness failure,
trusted/untrusted proxy schemes, secure sessions and host rejection. Run the
workflow on the final source and retain its artifacts. Fresh image/runtime audits
and real host acceptance remain necessary; source tests cannot substitute for
them. Consult PROJECT_STATUS.md and the blocker register before distribution.

### Verification of this change — 2026-10-31

- Core backend suite: 303 passed, 17 actual sandbox-runtime tests deselected.
  Includes six new deployment regression tests. Execution sandbox restrictions
  stalled initial runs; the network-enabled rerun completed in 26.23 seconds.
- Locked Python dependency consistency, strict TypeScript/Vite production build,
  default and HTTPS-environment Compose validation, and whitespace checks passed.
- Disposable PostgreSQL 17 smoke passed migration 0003, workspace isolation,
  duplicate constraints, restart persistence and logical dump/restore including
  account/membership/session/approval records. Used stock `postgres:17-bookworm`
  digest `sha256:839fbb5a4942a7758dd93e18b42ea5649807491a0545b5eeeb8f0b8bb11857a5`;
  this does not validate the modern custom database image or layout conversion.
- No fresh application/worker/model image build, CVE scan, nginx TLS integration,
  browser suite or actual sandbox/GPU acceptance was performed for this change.
  The managed workspace has an 8 GiB disk and an initially empty VFS image cache;
  pulling the PostgreSQL test image alone left about 3 GiB. Final image checks
  remain in CI and must pass before rollout. No production deployment was made.
