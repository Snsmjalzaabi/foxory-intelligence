# Review-only PostgreSQL 17 candidate. Never mount an existing glibc cluster into
# this musl image. Logical backup/import and collation compatibility are required.
FROM postgres:17-alpine@sha256:266d3c257594e195b309ae9d1805e54c788f1d7b375f56bf6c367aac6c917e7b
# Upstream gosu carries an old embedded Go runtime. Replace its single entrypoint
# invocation with signed Alpine su-exec and remove the binary entirely.
RUN apk add --no-cache su-exec=0.3-r0 \
    && test "$(command -v gosu)" = /usr/local/bin/gosu \
    && test "$(grep -Fc 'exec gosu postgres ' /usr/local/bin/docker-entrypoint.sh)" = 1 \
    && sed -i 's/exec gosu postgres /exec su-exec postgres /' /usr/local/bin/docker-entrypoint.sh \
    && rm /usr/local/bin/gosu \
    && test ! -e /usr/local/bin/gosu \
    && su-exec nobody id
COPY deployment/postgres/SU_EXEC_LICENSE /usr/share/licenses/su-exec/LICENSE
