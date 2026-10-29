#!/usr/bin/env bash
set -Eeuo pipefail

# Check before the upstream entrypoint can chmod/chown/start a legacy cluster.
# A same-major libc -> musl move must use a NEW volume and logical restore.
if [[ "${1:-}" == postgres || "${1:-}" == -* ]]; then
  data="${PGDATA:-/var/lib/postgresql/data}"
  shopt -s nullglob dotglob
  entries=("$data"/*)
  if [[ -L "$data" ]] || (( ${#entries[@]} )); then
    marker="$data/.foxory-layout"
    if [[ -L "$data" || -L "$data/PG_VERSION" || ! -f "$data/PG_VERSION" ]] || \
       [[ "$(cat -- "$data/PG_VERSION")" != 17 ]] || \
       [[ -L "$marker" || ! -f "$marker" ]] || \
       [[ "$(cat -- "$marker")" != foxory-postgres17-alpine-v1 ]]; then
      printf '%s\n' 'FOXORY_DATABASE_LAYOUT_MISMATCH: legacy/unknown data directory refused before startup. Keep the original volume unchanged; follow docs/DATABASE_UPGRADE.md for logical export into a new volume.' >&2
      exit 78
    fi
  fi
fi
exec /usr/local/bin/docker-entrypoint.sh "$@"
