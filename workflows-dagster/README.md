# Dagster Utility Analysis Workflows

Alternative implementation of utility meter processing using [Dagster](https://dagster.io/) - a modern data orchestration platform.

## Overview

This Dagster implementation provides the same functionality as the Prefect-based workflows but with Dagster's asset-centric approach, offering better data lineage visualization and built-in data quality checks.

### Workflows Included

1. **Tibber Sync** - Hourly ingestion of electricity consumption from Tibber API
2. **Analytics Processing** - Daily processing of all utility meters (interpolation, master/virtual meters, consumption calculations, anomaly detection)

## Architecture

### Assets (Data-Centric Approach)

**Ingestion Assets:**
- `tibber_consumption_raw` - Fetch Tibber data and write to InfluxDB

**Analytics Pipeline:**
- `meter_discovery` - Discover available meters in InfluxDB
- `fetch_meter_data` - Fetch raw meter data
- `interpolated_meter_series` - Create daily & monthly interpolated series
- `master_meter_series` - Combine physical meters across time periods
- `consumption_data` - Calculate consumption from readings
- `virtual_meter_data` - Calculate derived meters (e.g., fireplace gas)
- `anomaly_detection` - Detect consumption anomalies
- `write_processed_data_to_influxdb` - Write all results to InfluxDB

### Resources

- `InfluxDBResource` - InfluxDB client configuration and access
- `TibberResource` - Tibber API client with GraphQL support
- `ConfigResource` - YAML configuration loader (meters, patterns, settings)

### Jobs

- `tibber_sync` - Materializes Tibber ingestion asset
- `analytics_processing` - Materializes entire analytics pipeline

### Schedules

- `tibber_sync_hourly` - Runs every hour at :05 minutes
- `analytics_daily` - Runs daily at 2:00 AM UTC

## Prerequisites

- Docker and Docker Compose
- Existing InfluxDB instance (same as Prefect setup)
- Secrets configured in `secrets/` directory:
  - `secrets/influxdb.env` - Contains `INFLUX_TOKEN` and `INFLUX_ORG`
  - `secrets/tibber.env` - Contains `TIBBER_API_TOKEN` (optional)
- Configuration files in `config/`:
  - `config/config.yaml` - Main configuration
  - `config/meters.yaml` - Meter definitions
  - `config/seasonal_patterns.yaml` - Seasonal consumption patterns

## Installation & Setup

### 1. Build and Start Services

```bash
# From repository root
docker-compose -f docker-compose.dagster.yml up -d --build
```

This will start:
- **dagster-postgres** - PostgreSQL database for Dagster metadata (port 5432)
- **dagster-webserver** - Dagster UI (port 3000)
- **dagster-daemon** - Runs schedules and sensors
- **dagster-user-code** - User code server (your pipelines)

### 2. Access Dagster UI

Open your browser to: **http://localhost:3000**

The UI provides:
- Asset lineage graph
- Job run history
- Asset materialization history
- Logs and execution details
- Manual job triggering

### 3. Verify Asset Definitions

In the Dagster UI:
1. Navigate to **Assets** tab
2. You should see all 9 assets in the dependency graph
3. Asset groups: ingestion, discovery, processing, analysis, storage

### 4. Enable Schedules

By default, schedules are **disabled** for testing. To enable:

1. In Dagster UI, go to **Automation** → **Schedules**
2. Toggle on:
   - `tibber_sync_hourly` (if you have Tibber API token)
   - `analytics_daily`

Or via CLI in the dagster-daemon container:
```bash
docker exec dagster-daemon dagster schedule start tibber_sync_hourly
docker exec dagster-daemon dagster schedule start analytics_daily
```

## Usage

### Manual Job Execution

**Via UI:**
1. Navigate to **Jobs** tab
2. Select `tibber_sync` or `analytics_processing`
3. Click **Launch Run**
4. Monitor execution in real-time

**Via CLI:**
```bash
# Run Tibber sync manually
docker exec dagster-user-code dagster job execute -j tibber_sync

# Run analytics processing
docker exec dagster-user-code dagster job execute -j analytics_processing
```

### Materialize Specific Assets

You can materialize individual assets or asset groups:

**Via UI:**
1. Go to **Assets** tab
2. Select one or more assets
3. Click **Materialize selected**

**Via CLI:**
```bash
# Materialize just meter discovery
docker exec dagster-user-code dagster asset materialize -a meter_discovery

# Materialize entire analytics pipeline
docker exec dagster-user-code dagster asset materialize --select "*"
```

### View Asset Lineage

The **Asset Lineage Graph** shows:
- Dependencies between assets
- Last materialization time
- Upstream/downstream relationships
- Data freshness indicators

Navigate to **Assets** → **View Graph** to see the full pipeline visualization.

## Running in Parallel with Prefect

You can run both Dagster and Prefect simultaneously for validation:

### 1. Start Both Systems

```bash
# Start Prefect
docker-compose up -d

# Start Dagster
docker-compose -f docker-compose.dagster.yml up -d
```

### 2. Access Both UIs

- **Prefect**: http://localhost:4200
- **Dagster**: http://localhost:3000

### 3. Validation Strategy

**Phase 1: Disable Overlapping Schedules**
- Disable Dagster schedules initially
- Run Dagster jobs manually
- Compare outputs in InfluxDB

**Phase 2: Stagger Schedules**
```yaml
# Option A: Run Dagster slightly after Prefect
Prefect analytics: 2:00 AM
Dagster analytics: 2:05 AM

# Option B: Run on different days
Prefect: Daily
Dagster: Every other day for validation
```

**Phase 3: Cutover**
- Disable Prefect schedules
- Enable Dagster schedules
- Monitor for 1-2 weeks
- Decommission Prefect if satisfied

## Configuration

### Resource Configuration

Edit `workflows-dagster/dagster_project/__init__.py` to customize:

```python
resources={
    "influxdb": InfluxDBResource(
        url="http://192.168.1.75:8086",  # InfluxDB URL
        bucket_raw="lampfi",              # Raw data bucket
        bucket_processed="lampfi_processed",  # Processed data bucket
        timeout=30000,
        retry_attempts=3
    ),
    "config": ConfigResource(
        config_path="config/config.yaml",
        start_year=2020  # Historical data start year
    )
}
```

### Schedule Configuration

Edit `workflows-dagster/dagster_project/schedules/__init__.py`:

```python
tibber_sync_schedule = ScheduleDefinition(
    name="tibber_sync_hourly",
    job=tibber_sync_job,
    cron_schedule="5 * * * *",  # Modify cron expression
    execution_timezone="UTC"
)
```

## Monitoring & Observability

### Dagster UI Features

1. **Run Status Dashboard**
   - Success/failure rates
   - Execution times
   - Run history

2. **Asset Health**
   - Freshness checks
   - Materialization status
   - Staleness indicators

3. **Logs**
   - Structured logging per asset/job
   - Searchable and filterable
   - Real-time streaming during runs

4. **Runs Timeline**
   - Gantt chart of task execution
   - Parallelism visualization
   - Performance bottleneck identification

### Health Checks

All services include health checks:

```bash
# Check service status
docker-compose -f docker-compose.dagster.yml ps

# View logs
docker-compose -f docker-compose.dagster.yml logs -f dagster-webserver
docker-compose -f docker-compose.dagster.yml logs -f dagster-daemon
docker-compose -f docker-compose.dagster.yml logs -f dagster-user-code
```

## Data Flow

```
Tibber API → tibber_consumption_raw → InfluxDB (raw bucket)

InfluxDB (raw) → meter_discovery → fetch_meter_data →
interpolated_meter_series → master_meter_series →
consumption_data → virtual_meter_data →
anomaly_detection → write_processed_data_to_influxdb →
InfluxDB (processed bucket)
```

## Troubleshooting

### Issue: Schedules Not Running

**Solution:**
- Check dagster-daemon container is running: `docker ps`
- Check daemon logs: `docker logs dagster-daemon`
- Ensure schedules are enabled in UI or via CLI

### Issue: Assets Failing to Materialize

**Solution:**
- Check asset logs in Dagster UI
- Verify secrets are loaded: `docker exec dagster-user-code env | grep INFLUX`
- Verify InfluxDB connectivity: `docker exec dagster-user-code curl http://192.168.1.75:8086/health`
- Check configuration file paths exist

### Issue: Import Errors

**Solution:**
- Verify PYTHONPATH includes both `/app` and `/app/Nebenkosten`
- Rebuild container: `docker-compose -f docker-compose.dagster.yml up -d --build`

### Issue: PostgreSQL Connection Failed

**Solution:**
- Check dagster-postgres health: `docker ps`
- Verify environment variables in docker-compose.dagster.yml
- Reset database volume if corrupted:
  ```bash
  docker-compose -f docker-compose.dagster.yml down -v
  docker-compose -f docker-compose.dagster.yml up -d
  ```

## Development

### Testing Changes Locally

```bash
# Rebuild after code changes
docker-compose -f docker-compose.dagster.yml up -d --build dagster-user-code

# View updated assets in UI
# Navigate to http://localhost:3000 and reload
```

### Adding New Assets

1. Create asset in `workflows-dagster/dagster_project/assets/`
2. Import in `workflows-dagster/dagster_project/assets/__init__.py`
3. Add to repository in `workflows-dagster/dagster_project/__init__.py`
4. Rebuild and restart services

### Adding New Schedules

1. Create schedule in `workflows-dagster/dagster_project/schedules/__init__.py`
2. Add to repository schedules list
3. Restart services
4. Enable in UI

## Advantages Over Prefect

1. **Asset-Centric Design** - Better data lineage and dependency tracking
2. **Type Safety** - Dagster's type system catches errors at definition time
3. **Built-in Data Quality** - Asset checks and data validation framework
4. **Better UI** - Modern, responsive interface with better visualization
5. **Partitioning Support** - Native time-based partitioning for incremental processing
6. **Software-Defined Assets** - Assets are first-class citizens, not just task outputs

## Support & Documentation

- **Dagster Documentation**: https://docs.dagster.io/
- **Dagster GitHub**: https://github.com/dagster-io/dagster
- **Project Issues**: Report issues with this implementation in the project repository

## License

Same license as the parent utility analysis project.
