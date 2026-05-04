# Retire Legacy Tibber And Water Temperature Syncs

This runbook moves ownership from the Python cron LXC (`192.168.1.78`) to Dagster
(`192.168.1.94`) without rewriting cumulative meter history.

## Data Findings

- `lampfi.kWh.value` for `entity_id=haupt_strom` starts at `2025-06-04T23:00:00Z`.
- `lampfi.kWh.hourly_consumption` has the same hourly coverage as `kWh.value`.
- `lampfi.energy.consumption` is missing most historical rows and should be
  backfilled from `kWh.hourly_consumption`.
- `lampfi.°C.value` is schema-compatible between legacy and Dagster.

## Deployment

Run after the branch has been merged to `main`:

```bash
workflows_dagster/scripts/deploy_retire_legacy_syncs.sh
```

The deploy script:

- runs `/usr/local/sbin/update-dagster-workflows` on `dagster-lxc`
- restarts Dagster services
- runs the Tibber energy backfill in dry-run mode
- starts the new `water_temp_sync_15min` schedule

## Backfill

Review the dry-run counts first. If they look correct, execute:

```bash
ssh dagster-lxc
cd /opt/dagster-workflows/nebenkosten
export $(systemctl show -p Environment --value dagster-daemon.service)
set -a && . secrets/influxdb.env && set +a
/opt/dagster-workflows/venv/bin/python workflows_dagster/scripts/backfill_tibber_energy_from_kwh.py --derive-missing-cost --execute
```

This writes only missing `lampfi.energy` rows. It does not write or repair
`lampfi.kWh.value`.

## Cutover

1. Run `tibber_sync` once in Dagster.
2. Verify latest `lampfi.kWh.value` advanced monotonically.
3. Verify latest `lampfi.energy.consumption` exists for `haupt_strom`.
4. Disable legacy cron writers:

```bash
workflows_dagster/scripts/retire_legacy_crons.sh --execute
```

The cron retirement script backs up root's crontab on `192.168.1.78` before
removing only these entries:

- `/opt/water-temp-lakes/run_temp_sync.sh`
- `/opt/tibber_sync/run_tibber_sync.sh`
