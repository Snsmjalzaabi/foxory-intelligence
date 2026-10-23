# Supply a reviewed Node 22 Debian image by immutable digest; no default tag.
ARG BASE_IMAGE
FROM ${BASE_IMAGE}
USER root
WORKDIR /opt/foxory
# Version is exact. Runtime task dependency installation is never permitted.
RUN npm install --ignore-scripts --no-audit --no-fund --save-exact playwright@1.64.1 \
    && ./node_modules/.bin/playwright install --with-deps chromium \
    && chmod -R a+rX /opt/foxory /root/.cache/ms-playwright \
    && mv /root/.cache/ms-playwright /opt/foxory/browsers
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/foxory/browsers
COPY worker.mjs /opt/foxory/worker.mjs
USER 1000:1000
WORKDIR /work
ENTRYPOINT ["node", "/opt/foxory/worker.mjs"]
