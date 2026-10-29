# Installation and removal

## Linux Compose

Install Docker Engine + Compose v2 from your OS/vendor documentation. Run `python scripts/setup.py`, then `docker compose up -d --build`. Check `docker compose ps` and `docker compose logs app`. Open <http://localhost:8000>; the token is stored in `.env`. No model is downloaded automatically. Download one explicitly in Settings. Review its upstream model license first.

CPU inference works without a GPU configuration. A real cloud CPU smoke passed with `qwen2.5:0.5b` (context 2048, nonempty streamed response, 3 reported output tokens). This tiny model is a connectivity baseline, not evidence of business-task quality. A small quantized 1–3B model is a reasonable next candidate on limited hardware, subject to license and quality review. A quantized 7–8B model may fit an RTX 3060 12 GB at a modest context length, but no measurement on the reference i5-14400F/30 GB/RTX 3060 machine has been performed. Do not keep multiple large models resident. The default stack limits Ollama to one loaded model. Model download sizes and runtime RAM/VRAM are different quantities.

Optional NVIDIA configuration requires a compatible driver and NVIDIA Container Toolkit:

```sh
docker compose -f compose.yaml -f compose.gpu.yaml up -d --build
```

This override is configuration only until GPU verification is recorded in PROJECT_STATUS.md. It is not enabled automatically. Windows Docker Desktop/WSL2 and macOS Docker Desktop are compatibility targets, not verified supported platforms. On macOS, container Ollama does not use Apple Metal; native Ollama may be preferable, with an explicitly configured endpoint override.

## Native development

```sh
python -m venv .venv
# Activate using your platform's normal venv command.
python -m pip install -e 'backend[test]'
cd frontend
npm ci
npm run build
cd ../backend
# Set FOXORY_TOKEN to a fresh random secret in your shell, not source code.
alembic upgrade head
uvicorn foxory.main:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

Install/start Ollama separately. UI development can use `npm run dev` (Vite proxies `/api` to port 8000). Development uses SQLite unless DATABASE_URL is set. Keep one API worker and one replica. Do not expose either dev server externally.

## Cloud build certificate

A managed environment may intercept HTTPS. Keep TLS verification enabled and supply the trusted environment CA only as a BuildKit secret:

```sh
docker build --secret id=proxy_ca,src=/etc/ssl/certs/ca-certificates.crt -t foxory-intelligence-app:test .
```

The secret mount is not included in image layers. Normal local builds need no custom CA. No cloud credential is required.

## Back up and restore

Stop application writes first: `docker compose stop app`. For PostgreSQL, save a logical backup with `docker compose exec -T db pg_dump -U foxory -d foxory -Fc > foxory.dump`. Also copy `/data/uploads` from the stopped app container using `docker compose cp app:/data/uploads ./uploads-backup` when uploads exist. Keep `.env` securely and separately. Protect the dump and uploaded files; they contain private data. Restart with `docker compose start app`.

Restore into a clean compatible installation with the app stopped: use `docker compose exec -T db pg_restore -U foxory -d foxory --clean --if-exists < foxory.dump`, copy the uploads back to `/data/uploads`, set ownership to UID/GID 10001, then start the app. Perform a test restore before relying on a backup. Do not restore untrusted dumps or overwrite a live workspace. The documentation does not imply this entire process was verified; see status.

Native SQLite installations can use `python scripts/backup.py backup SOURCE_DIR DEST_DIR` and `python scripts/backup.py restore BACKUP_DIR NEW_DATA_DIR` while the app is stopped. Restore refuses an existing destination. This copies original uploads and uses SQLite's backup API.

## Uninstall

`docker compose down` removes containers and the project network while retaining application, PostgreSQL and model volumes. To remove all data deliberately, back it up first and run `docker compose down --volumes`. Delete `.env` and the repository only when no longer needed. No host-level service or recurring system task is installed.

## Phase 2 upgrade and verification

Back up PostgreSQL, uploads and `.env` first. Rebuild the canonical image and start one app process. Migration 0003 adds users/workspaces/membership/sessions and assigns historical audit records to Local; existing records/documents remain in Local. On first browser login, use the bootstrap token to create the administrator. Do not keep using the token as permanent API authentication after setup. Accounts in a restored database retain password hashes; old sessions may be present until expiry/revocation. Protect database backups accordingly.

The full Phase 2 base image was built in the cloud with the canonical Dockerfile and libseccomp2. The 32 GB cloud VFS filesystem required cache cleanup; final code-only fixes were verified using `Dockerfile.verify` on that locally built dependency base. This is a development verification overlay, not the installation Dockerfile. Normal installations and CI must build `Dockerfile` from source. No system Docker storage driver, privileged container or host socket access was introduced into the application.

Phase 2 integration uses a disposable Compose project on port 8003 with its own PostgreSQL/uploads volumes and the existing private Ollama service. `scripts/phase2_smoke.py` is intentionally restricted to that local verification port. It creates only a disposable test administrator and refuses an existing configured installation without its private test-run credential file. Never use it against an owner's workspace. Test-run credentials/evidence live in private `/tmp` files, never Git.

After administrator setup, native smoke helpers can log in using `FOXORY_SMOKE_USERNAME` and `FOXORY_SMOKE_PASSWORD` supplied privately in the shell environment; optional `FOXORY_SMOKE_WORKSPACE` selects an authorized test workspace. They never print credentials. Bootstrap-only smoke works only on an unconfigured installation. Do not put passwords in committed scripts or command-line arguments.

## Phase 3 upgrade

Back up PostgreSQL and uploaded originals before replacing the application. Phase 3 retains schema revision0003 and stores agent/schedule state in existing scoped records. The canonical Dockerfile remains the clean-install path; this cloud verification reused its Phase 2 dependency base with code overlays because of VFS space limits. Compose now enables an init process and accepts FOXORY_WORKER_CONCURRENCY (default1, maximum2); local model calls remain sequential. Use one API process/replica only. Existing standard zero-tool definitions load without deleting inert legacy fields; old draft task records remain archived and require a new explicitly scoped task.

New installations create their administrator through the existing first-run UI; tests do not create an administrator in the owner's database. Restricted uploads require Linux/libseccomp. See docs/PHASE3_CHECKLIST.md and PROJECT_STATUS.md for exact executed scope and limitations.

### Optional Computer Mode

The application does not provision a sandbox manager or expose a Docker socket.
Restricted Python execution requires a separate, dedicated non-root Linux x86_64
manager and explicit configuration/approval. Follow [the manager installation and
security boundary](docs/SANDBOX_MANAGER.md). Native app-to-manager loopback is the
verified topology. Container-to-host routing and Windows/macOS Linux VM setups
require separate verification. Browser and JavaScript execution remain disabled.

To uninstall the optional manager, stop/disable its service and preserve its
private state alongside the application backup before removing configuration.
Core container removal does not remove external manager state. Delete keys/state
only as an explicit owner operation, never as an automatic application uninstall.


Phase 4 now connects optional JavaScript/TypeScript and offline Playwright profiles
through the authenticated manager, approval gates and Computer Mode. They remain
disabled by default and require actual Ubuntu isolation verification; Codex tests
use a mocked OCI boundary. See [host activation and acceptance checklist](docs/SANDBOX_HOST_VERIFICATION.md)
for pinned image builds, lifecycle/ownership controls and remaining limitations.

## Core and optional execution

For offline native SQLite backup/restore, stop the application first and use
`scripts/backup.py`. It refuses existing destinations and symlinks/special files,
preserves stationary committed WAL data and copies originals with private
permissions. It requires POSIX no-follow directory support; run inside the Linux
environment on unsupported native hosts. Restore only trusted backups, and do
not infer online consistency while the application is running. Compose uses
PostgreSQL: follow its separate database-and-uploads backup procedure instead.

The normal Compose stack needs no Podman, dedicated execution OS account or
sandbox manager. Leave `FOXORY_ENABLE_SANDBOX=0`. Chat, search, Deep Research,
Council, document intelligence and safe agents operate independently. Missing
local models are handled in Settings; model weights are not downloaded silently.

Rootless Podman, delegated cgroups, a dedicated execution account and manager
secrets are requirements only when deliberately enabling advanced Computer Mode.
See [the host checklist](docs/SANDBOX_HOST_VERIFICATION.md). Its remaining
security/recovery work does not prevent installing the core product.
