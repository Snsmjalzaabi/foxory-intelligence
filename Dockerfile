# syntax=docker/dockerfile:1
FROM node:22-bookworm-slim AS ui
WORKDIR /build
COPY frontend/package*.json ./
RUN --mount=type=secret,id=proxy_ca if [ -f /run/secrets/proxy_ca ]; then NODE_EXTRA_CA_CERTS=/run/secrets/proxy_ca npm ci; else npm ci; fi
COPY frontend/ ./
RUN npm run build

# Bookworm's scanned runtime has unfixed HIGH/CRITICAL OS findings. Keep Python
# 3.12, use the reviewed supported Trixie index, then apply repository updates.
FROM python:3.12-slim-trixie@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 FOXORY_DATA_DIR=/data
WORKDIR /app/backend
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends libseccomp2 && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.lock ./
RUN --mount=type=secret,id=proxy_ca if [ -f /run/secrets/proxy_ca ]; then PIP_CERT=/run/secrets/proxy_ca pip install --no-cache-dir -r requirements.lock; else pip install --no-cache-dir -r requirements.lock; fi
COPY --chown=10001:10001 backend/ ./
RUN --mount=type=secret,id=proxy_ca if [ -f /run/secrets/proxy_ca ]; then PIP_CERT=/run/secrets/proxy_ca pip install --no-cache-dir --no-deps .; else pip install --no-cache-dir --no-deps .; fi
COPY --from=ui --chown=10001:10001 /build/dist /app/frontend/dist
COPY --chmod=0444 LICENSE NOTICE THIRD_PARTY_NOTICES.txt /usr/share/doc/foxory/
RUN groupadd --gid 10001 foxory && useradd --uid 10001 --gid 10001 --no-create-home foxory && mkdir /data && chown foxory:foxory /data
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=5s --start-period=30s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=3)"
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn foxory.main:app --host 0.0.0.0 --port 8000 --workers 1 --no-access-log --limit-concurrency 32"]
