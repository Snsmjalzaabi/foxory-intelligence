# syntax=docker/dockerfile:1
FROM node:22-bookworm-slim AS ui
WORKDIR /build
COPY frontend/package*.json ./
RUN --mount=type=secret,id=proxy_ca if [ -f /run/secrets/proxy_ca ]; then NODE_EXTRA_CA_CERTS=/run/secrets/proxy_ca npm ci; else npm ci; fi
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 FOXORY_DATA_DIR=/data
WORKDIR /app/backend
COPY backend/requirements.lock ./
RUN --mount=type=secret,id=proxy_ca if [ -f /run/secrets/proxy_ca ]; then PIP_CERT=/run/secrets/proxy_ca pip install --no-cache-dir -r requirements.lock; else pip install --no-cache-dir -r requirements.lock; fi
COPY --chown=10001:10001 backend/ ./
RUN --mount=type=secret,id=proxy_ca if [ -f /run/secrets/proxy_ca ]; then PIP_CERT=/run/secrets/proxy_ca pip install --no-cache-dir --no-deps .; else pip install --no-cache-dir --no-deps .; fi
COPY --from=ui --chown=10001:10001 /build/dist /app/frontend/dist
RUN groupadd --gid 10001 foxory && useradd --uid 10001 --gid 10001 --no-create-home foxory && mkdir /data && chown foxory:foxory /data
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=5s --start-period=30s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=3)"
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn foxory.main:app --host 0.0.0.0 --port 8000 --workers 1 --no-access-log --limit-concurrency 32"]
