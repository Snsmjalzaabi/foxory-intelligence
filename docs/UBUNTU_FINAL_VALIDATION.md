# Remaining Ubuntu validation — existing dedicated account

This updates source from the owner's Git checkout into the already provisioned
`foxory-sandbox` account, preserving its venv, private environment and data.
Do not run git commands inside the dedicated account's archive-only source copy.
No production service is enabled. Do not rerun host provisioning or weaken policy
to make a failing fixture pass. The rebuilt image differs from the older accepted
Chromium image and needs these active tests.

From the owner's Ubuntu shell (review before executing):

```bash
bash <<'BASH'
set -euo pipefail
cd "$HOME/Projects/foxory-intelligence"
git diff --quiet
git diff --cached --quiet
git switch development
git pull --ff-only origin development
git rev-parse HEAD

sandbox_uid="$(id -u foxory-sandbox)"
manager_home="$(getent passwd foxory-sandbox | cut -d: -f6)"
test -n "$manager_home"
test "$sandbox_uid" -ne 0
git archive HEAD | sudo -u foxory-sandbox -H tar -x -C "$manager_home/foxory-intelligence"

sudo -u foxory-sandbox -H env -i HOME="$manager_home" USER=foxory-sandbox LOGNAME=foxory-sandbox \
  PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  XDG_RUNTIME_DIR="/run/user/$sandbox_uid" DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$sandbox_uid/bus" \
  systemd-run --user --scope --property=Delegate=yes --expand-environment=no bash -c '
    set -euo pipefail
    umask 077
    cd "$HOME/foxory-intelligence"
    logs="$HOME/foxory-verification/final-$(date -u +%Y%m%dT%H%M%SZ)"
    mkdir -p "$logs"
    .venv/bin/python scripts/verify_worker_supply_chain.py --online > "$logs/supply-chain.json"
    podman --remote=false build -f sandbox_manager/runtime/Dockerfile \
      -t localhost/foxory-worker:verification sandbox_manager/runtime 2>&1 | tee "$logs/build.log"
    image_id="$(podman --remote=false image inspect localhost/foxory-worker:verification --format "{{.Id}}")"
    case "$image_id" in sha256:*) ;; *) image_id="sha256:$image_id" ;; esac
    printf "%s\n" "$image_id" | tee "$logs/image-id.txt"
    archive_dir="$(mktemp -d "$HOME/foxory-image-review.XXXXXX")"
    trap "rm -f \"$archive_dir/worker.tar\"; rmdir \"$archive_dir\"" EXIT
    podman --remote=false save --format docker-archive --output "$archive_dir/worker.tar" "$image_id"
    .venv/bin/python scripts/image_audit.py --image "$image_id" --archive "$archive_dir/worker.tar" --worker --output "$logs/image-audit" 2>&1 | tee "$logs/image-audit.log"
    .venv/bin/python scripts/oci_host_acceptance.py --image "$image_id" --evidence "$logs/tcp" 2>&1 | tee "$logs/tcp.log"
    .venv/bin/python scripts/oci_host_acceptance.py --image "$image_id" --transport unix --evidence "$logs/unix" 2>&1 | tee "$logs/unix.log"
    printf "Evidence retained at %s\n" "$logs"
  '
BASH
```

The application must remain disabled for execution until full acceptance. Review
both runtime summaries, image findings/licenses, manager logs and screenshots.
The fixed probes execute real CPU/PID/memory exhaustion inside a 1-GiB rootless
container. Only the disposable test manager is killed/restarted. Accounts,
database volumes, original manager state and application configuration are not
used. A failure must be investigated, not converted to a skip.

Still required after these fixtures: combined real local-model browser/JS/code/
research exports; final application-to-manager topology; separate application and
manager backup/restore; upstream CVE/license review and full Phase 4 checklist.
Ubuntu 24.04 hosted evidence does not certify this Ubuntu 26.04 machine.
