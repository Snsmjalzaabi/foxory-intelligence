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
