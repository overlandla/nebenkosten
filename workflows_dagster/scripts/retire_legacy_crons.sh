#!/usr/bin/env bash
set -euo pipefail

# Disable the legacy Tibber and water-temp cron writers on the old Python LXC.
# Dry-run by default. Pass --execute after Dagster has been validated as the
# single writer.

LEGACY_HOST="${LEGACY_HOST:-root@192.168.1.78}"
LEGACY_IDENTITY="${LEGACY_IDENTITY:-$HOME/.ssh/id_ed25519_proxmox_lxc}"
EXECUTE=0

if [[ "${1:-}" == "--execute" ]]; then
  EXECUTE=1
elif [[ $# -gt 0 ]]; then
  echo "Usage: $0 [--execute]" >&2
  exit 2
fi

REMOTE_SCRIPT='
set -eu
backup="/root/crontab.before-dagster-retire-legacy-syncs.$(date +%Y%m%d%H%M%S)"
current="$(mktemp)"
next="$(mktemp)"
crontab -l > "$current" 2>/dev/null || true
grep -v -F "/opt/water-temp-lakes/run_temp_sync.sh" "$current" \
  | grep -v -F "/opt/tibber_sync/run_tibber_sync.sh" > "$next" || true

echo "Current legacy cron entries:"
grep -F "/opt/water-temp-lakes/run_temp_sync.sh" "$current" || true
grep -F "/opt/tibber_sync/run_tibber_sync.sh" "$current" || true

if [ "${EXECUTE_REMOTE}" = "1" ]; then
  cp "$current" "$backup"
  crontab "$next"
  echo "Updated crontab. Backup: $backup"
  echo "Remaining crontab:"
  crontab -l || true
else
  echo "Dry-run only. Pass --execute to install the filtered crontab."
fi
'

ssh \
  -o StrictHostKeyChecking=accept-new \
  -i "$LEGACY_IDENTITY" \
  "$LEGACY_HOST" \
  "EXECUTE_REMOTE=$EXECUTE sh -c '$REMOTE_SCRIPT'"
