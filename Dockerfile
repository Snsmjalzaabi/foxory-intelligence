# syntax=docker/dockerfile:1
FROM node:22-bookworm-slim AS ui
WORKDIR /build
COPY frontend/package*.json ./
RUN --mount=type=secret,id=proxy_ca if [ -f /run/secrets/proxy_ca ]; then NODE_EXTRA_CA_CERTS=/run/secrets/proxy_ca npm ci; else npm ci; fi
COPY frontend/ ./
RUN npm run build

# Debian 12 and 13 both have unfixed blocking OS findings in the actual scans.
# Ubuntu provides the same Python 3.12 ABI with its maintained security packages.
FROM ubuntu:24.04@sha256:24737cef17f4e22b1977df7d9a05e77c4e28b7da5b8911f8d8ccda136bf3573c AS python-base
RUN apt-get update && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends python3.12 libseccomp2 ca-certificates \
    && rm -rf /var/lib/apt/lists/*
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 FOXORY_DATA_DIR=/data PATH=/opt/foxory-venv/bin:$PATH

FROM python-base AS pcre2-build
RUN apt-get update && apt-get install -y --no-install-recommends build-essential binutils python3 gnupg bzip2 libpcre2-8-0 \
    && install -d -o 1000 -g 1000 /build /out
COPY sandbox_manager/runtime/pcre2 /opt/foxory-pcre2
USER 1000:1000
RUN --mount=type=secret,id=proxy_ca FOXORY_WORKER_IMAGE_BUILD=1 python3 /opt/foxory-pcre2/prepare.py
RUN --network=none FOXORY_WORKER_IMAGE_BUILD=1 sh /opt/foxory-pcre2/build.sh

FROM python-base AS python-runtime
COPY --from=pcre2-build /out/libpcre2-8-0.deb /tmp/foxory-pcre2.deb
RUN dpkg -i /tmp/foxory-pcre2.deb && rm /tmp/foxory-pcre2.deb && test -z "$(dpkg --audit)"

FROM python-runtime AS api-build
RUN apt-get update && apt-get install -y --no-install-recommends python3.12-venv \
    && python3.12 -m venv /opt/foxory-venv && rm -rf /var/lib/apt/lists/*
WORKDIR /app/backend
COPY backend/requirements.lock ./
RUN --mount=type=secret,id=proxy_ca if [ -f /run/secrets/proxy_ca ]; then PIP_CERT=/run/secrets/proxy_ca pip install --no-cache-dir -r requirements.lock; else pip install --no-cache-dir -r requirements.lock; fi
COPY backend/ ./
RUN --mount=type=secret,id=proxy_ca if [ -f /run/secrets/proxy_ca ]; then PIP_CERT=/run/secrets/proxy_ca pip install --no-cache-dir --no-deps .; else pip install --no-cache-dir --no-deps .; fi
# Runtime never installs packages. Do not ship build-only pip or its vendor graph.
RUN python -m pip uninstall -y pip

# Keep the same reviewed inference runtime; only replace its affected PCRE2 library.
FROM ollama/ollama:0.40.13@sha256:b2f0122c476bc9fe7ce679d8bb4bd555351e25e2554eefb156f61cb0a89cf429 AS ollama
COPY --from=pcre2-build /out/libpcre2-8-0.deb /tmp/foxory-pcre2.deb
RUN dpkg -i /tmp/foxory-pcre2.deb && rm /tmp/foxory-pcre2.deb && test -z "$(dpkg --audit)"

FROM python-runtime AS application
WORKDIR /app/backend
COPY --from=api-build /opt/foxory-venv /opt/foxory-venv
COPY --from=api-build --chown=10001:10001 /app/backend /app/backend
COPY --from=ui --chown=10001:10001 /build/dist /app/frontend/dist
COPY --chmod=0444 LICENSE NOTICE THIRD_PARTY_NOTICES.txt /usr/share/doc/foxory/
RUN groupadd --gid 10001 foxory && useradd --uid 10001 --gid 10001 --no-create-home foxory && mkdir /data && chown foxory:foxory /data
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=5s --start-period=30s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/ready',timeout=3)"
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn foxory.main:app --host 0.0.0.0 --port 8000 --workers 1 --no-access-log --limit-concurrency 32"]
