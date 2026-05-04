#!/usr/bin/env bash
set -euo pipefail

# Deploy the Dagster-side migration after the branch has been merged to main.
#
# This intentionally uses the production update command on the Dagster LXC
# instead of editing code directly on the host.

DAGSTER_HOST="${DAGSTER_HOST:-dagster-lxc}"
DAGSTER_REPO="${DAGSTER_REPO:-/opt/dagster-workflows/nebenkosten}"
DAGSTER_VENV="${DAGSTER_VENV:-/opt/dagster-workflows/venv}"
UPDATE_COMMAND="${UPDATE_COMMAND:-/usr/local/sbin/update-dagster-workflows}"

ssh "$DAGSTER_HOST" "${UPDATE_COMMAND}"

ssh "$DAGSTER_HOST" "cd '$DAGSTER_REPO' && \
  python3 -m compileall workflows_dagster/src workflows_dagster/dagster_project && \
  systemctl restart dagster-user-code dagster-daemon dagster-webserver && \
  sleep 5 && \
  systemctl --no-pager --full status dagster-user-code dagster-daemon dagster-webserver"

ssh "$DAGSTER_HOST" "cd '$DAGSTER_REPO' && \
  export \$(systemctl show -p Environment --value dagster-daemon.service) && \
  set -a && . secrets/influxdb.env && set +a && \
  '$DAGSTER_VENV/bin/python' workflows_dagster/scripts/backfill_tibber_energy_from_kwh.py"

ssh "$DAGSTER_HOST" "cd '$DAGSTER_REPO' && \
  export \$(systemctl show -p Environment --value dagster-daemon.service) && \
  set -a && . secrets/influxdb.env && [ -f secrets/tibber.env ] && . secrets/tibber.env || true && set +a && \
  '$DAGSTER_VENV/bin/dagster' schedule start water_temp_sync_15min -w workflows_dagster/workspace.yaml || true && \
  '$DAGSTER_VENV/bin/dagster' schedule list -w workflows_dagster/workspace.yaml"

cat <<'NEXT'

Deployment completed and backfill dry-run executed.

Next manual checks:
  1. Inspect the dry-run output above.
  2. If missing_energy_rows is expected, execute the backfill on dagster-lxc:
     cd /opt/dagster-workflows/nebenkosten
     export $(systemctl show -p Environment --value dagster-daemon.service)
     set -a && . secrets/influxdb.env && set +a
     /opt/dagster-workflows/venv/bin/python workflows_dagster/scripts/backfill_tibber_energy_from_kwh.py --derive-missing-cost --execute
  3. Run the Dagster tibber_sync job once.
  4. After validation, run workflows_dagster/scripts/retire_legacy_crons.sh --execute.
NEXT
