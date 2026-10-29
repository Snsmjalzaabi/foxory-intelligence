# Sourced by the upstream entrypoint AFTER initdb, as the postgres OS user.
# Never add files to an empty PGDATA before initdb (it refuses non-empty dirs).
(
  umask 077
  printf '%s\n' foxory-postgres17-alpine-v1 > "$PGDATA/.foxory-layout.tmp"
  mv -- "$PGDATA/.foxory-layout.tmp" "$PGDATA/.foxory-layout"
)
