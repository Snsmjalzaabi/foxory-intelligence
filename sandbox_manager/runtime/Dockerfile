# syntax=docker/dockerfile:1
# Reviewed upstream index: Chromium/OS/Node pinned together. Apply the reviewed
# Brotli/zlib security updates; remove unused optional media/parser/HTTP packages and build-only npm.
FROM mcr.microsoft.com/playwright:v1.64.1-noble@sha256:47b510dd9230bf0b9bfc9b20102241e577ea7a99334ab4c3ca19f19770e9b8ea AS upstream
FROM upstream AS pcre2-build
USER root
RUN apt-get update && apt-get install -y --no-install-recommends build-essential binutils python3 gnupg ca-certificates bzip2 \
    && install -d -o 1000 -g 1000 /build /out
COPY pcre2 /opt/foxory-pcre2
USER 1000:1000
RUN --mount=type=secret,id=proxy_ca FOXORY_WORKER_IMAGE_BUILD=1 python3 /opt/foxory-pcre2/prepare.py
# Reviewed upstream tests run without network; no agent-generated code or host mounts.
RUN --network=none FOXORY_WORKER_IMAGE_BUILD=1 sh /opt/foxory-pcre2/build.sh

FROM upstream AS xrender-build
USER root
RUN apt-get update && apt-get install -y --no-install-recommends build-essential binutils python3 gnupg ca-certificates xz-utils pkg-config libx11-dev libxext-dev x11proto-dev xvfb \
    && install -d -o 1000 -g 1000 /build /out
COPY pcre2/prepare.py /opt/foxory-pcre2/prepare.py
COPY xrender /opt/foxory-xrender
USER 1000:1000
RUN --mount=type=secret,id=proxy_ca FOXORY_WORKER_IMAGE_BUILD=1 python3 /opt/foxory-xrender/prepare.py
RUN --network=none FOXORY_WORKER_IMAGE_BUILD=1 sh /opt/foxory-xrender/build.sh

FROM upstream
USER root
WORKDIR /opt/foxory
COPY --from=pcre2-build /out/libpcre2-8-0.deb /tmp/foxory-pcre2.deb
COPY --from=xrender-build /out/libxrender1.deb /tmp/foxory-xrender.deb
RUN dpkg -i /tmp/foxory-pcre2.deb /tmp/foxory-xrender.deb && rm /tmp/foxory-pcre2.deb /tmp/foxory-xrender.deb \
    && test -z "$(dpkg --audit)"
COPY worker-packages.json prune-media.mjs /opt/foxory-build/
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libbrotli1=1.1.0-2ubuntu0.1 zlib1g=1:1.3.dfsg-3.1ubuntu2.3 \
    && apt-get purge -y gstreamer1.0-plugins-bad libgstreamer-plugins-bad1.0-0 \
    && FOXORY_WORKER_IMAGE_BUILD=1 node /opt/foxory-build/prune-media.mjs /opt/foxory-build/worker-packages.json \
    && rm -rf /var/lib/apt/lists/* /opt/foxory-build
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
