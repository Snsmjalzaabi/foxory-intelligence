# syntax=docker/dockerfile:1
# Reviewed upstream index: Chromium/OS/Node pinned together. Apply the reviewed
# Brotli security update; remove unused WebKit media packages and build-only npm.
FROM mcr.microsoft.com/playwright:v1.64.1-noble@sha256:47b510dd9230bf0b9bfc9b20102241e577ea7a99334ab4c3ca19f19770e9b8ea
USER root
WORKDIR /opt/foxory
RUN apt-get update \
    && apt-get install -y --no-install-recommends libbrotli1=1.1.0-2ubuntu0.1 \
    && apt-get purge -y gstreamer1.0-plugins-bad libgstreamer-plugins-bad1.0-0 \
    && rm -rf /var/lib/apt/lists/*
COPY package.json package-lock.json ./
# Optional session CA is only mounted during installation, never stored in layers.
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/proxy_ca; fi; \
    npm ci --ignore-scripts --omit=dev --no-audit --no-fund --strict-ssl=true \
    && node -e 'if(Number(process.versions.node.split(".")[0])<22)process.exit(1)' \
    && npm cache clean --force \
    && rm -rf /usr/lib/node_modules/npm /usr/local/lib/node_modules/npm \
    && rm -f /usr/bin/npm /usr/bin/npx /usr/local/bin/npm /usr/local/bin/npx
COPY worker.mjs /opt/foxory/worker.mjs
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
USER 1000:1000
WORKDIR /work
ENTRYPOINT ["node", "/opt/foxory/worker.mjs"]
