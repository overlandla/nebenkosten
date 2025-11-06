# Simplified Architecture - Prefect-Based Utility Meter System

## Overview

Focused architecture for home NAS deployment with:
- ✅ Prefect for workflow orchestration
- ✅ InfluxDB for all data storage (no PostgreSQL needed)
- ✅ Configuration via YAML/JSON
- ✅ Comprehensive logging
- ❌ No Streamlit
- ❌ No Grafana work (you already have it)
- ❌ No PostgreSQL

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Home NAS (Docker)                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌────────────────────────────────────────────────────┐     │
│  │         Prefect Server Container                   │     │
│  │  • Workflow scheduling                             │     │
│  │  • Execution monitoring                            │     │
│  │  • SQLite backend (no Postgres needed)            │     │
│  │  • Web UI: http://nas-ip:4200                     │     │
│  └────────────────────────────────────────────────────┘     │
│                           │                                  │
│            ┌──────────────┴──────────────┐                   │
│            ▼                              ▼                   │
│  ┌──────────────────┐         ┌─────────────────────────┐   │
│  │ Tibber Sync      │         │ Analytics Worker        │   │
│  │ Worker           │         │ Container               │   │
│  │                  │         │                         │   │
│  │ • Prefect Flow   │         │ • Prefect Flows:        │   │
│  │ • Hourly run     │         │   - Daily analysis      │   │
│  │ • GraphQL API    │         │   - Monthly reports     │   │
│  │ • Write to       │         │   - On-demand           │   │
│  │   InfluxDB       │         │ • Read from InfluxDB    │   │
│  └──────────────────┘         │ • Process & calculate   │   │
│            │                  │ • Write back to InfluxDB│   │
│            │                  └─────────────────────────┘   │
│            │                              │                  │
│            └──────────────┬───────────────┘                  │
│                           ▼                                  │
│  ┌────────────────────────────────────────────────────┐     │
│  │     Your Existing InfluxDB Instance                │     │
│  │  Buckets:                                          │     │
│  │   • lampfi (raw meter readings)                    │     │
│  │   • lampfi_processed (calculated results)          │     │
│  └────────────────────────────────────────────────────┘     │
│                           │                                  │
│                           ▼                                  │
│  ┌────────────────────────────────────────────────────┐     │
│  │     Your Existing Grafana Instance                 │     │
│  │  (connects to InfluxDB for visualization)          │     │
│  └────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### 1. Tibber Sync Flow (Hourly)
```
Tibber GraphQL API
    │
    ├─ Query last 48h consumption data
    │
    ▼
Check last InfluxDB timestamp
    │
    ├─ Compare with fetched data
    │
    ▼
Write only new data points → InfluxDB (lampfi bucket)
    │
    └─ Tag: entity_id=haupt_strom
```

### 2. Analytics Flow (Daily @ 2 AM)
```
InfluxDB (lampfi bucket)
    │
    ├─ Fetch all configured meter readings
    │
    ▼
Data Processing Tasks
    │
    ├─ Interpolation (daily/monthly series)
    ├─ Master meter composition
    ├─ Virtual meter calculations
    └─ Consumption calculations
    │
    ▼
Write Results → InfluxDB (lampfi_processed bucket)
    │
    ├─ Interpolated series (measurement: meter_interpolated)
    ├─ Consumption metrics (measurement: meter_consumption)
    └─ Anomalies (measurement: meter_anomalies)
```

---

## Configuration Structure

### Directory Layout
```
/opt/utility-meters/
├── config/
│   ├── config.yaml                 # Main configuration
│   ├── meters.yaml                 # Meter definitions
│   └── seasonal_patterns.yaml      # Consumption patterns
├── secrets/
│   ├── .gitignore                  # Ignore all secrets
│   ├── influxdb.env                # InfluxDB credentials
│   └── tibber.env                  # Tibber API token
├── docker-compose.yml
├── .env.example                    # Template for secrets
└── logs/                           # Mounted volume for logs
```

### config/config.yaml
```yaml
influxdb:
  url: "http://192.168.1.75:8086"  # Your existing InfluxDB
  bucket_raw: "lampfi"              # Existing bucket for raw data
  bucket_processed: "lampfi_processed"  # New bucket for results
  timeout: 30
  retry_attempts: 3

tibber:
  polling_interval: 3600            # 1 hour
  lookback_hours: 48
  meter_id: "haupt_strom"           # Entity ID to write to

gas_conversion:
  energy_content: 11.504            # kWh/m³
  z_factor: 0.8885

workflows:
  analytics:
    schedule: "0 2 * * *"           # Daily at 2 AM
    start_year: 2020
  tibber_sync:
    schedule: "5 * * * *"           # Hourly at :05

logging:
  level: "INFO"
  format: "json"
  file: "/app/logs/utility_analyzer.log"
  max_bytes: 10485760               # 10 MB
  backup_count: 5
```

### config/meters.yaml
```yaml
meters:
  - meter_id: "strom_total"
    type: "master"
    output_unit: "kWh"
    description: "Total electricity across meter replacements"
    periods:
      - start_date: "2020-01-01"
        end_date: "2024-11-26"
        composition_type: "sum"
        source_meters:
          - "strom_1LOG0007013695_NT"
          - "strom_1LOG0007013695_HT"
        source_unit: "kWh"
      - start_date: "2024-11-27"
        end_date: "9999-12-31"
        composition_type: "single"
        source_meters:
          - "haupt_strom"
        source_unit: "kWh"
        apply_offset_from_previous_period: true

  - meter_id: "gas_total"
    type: "master"
    output_unit: "m³"
    description: "Total gas consumption"
    periods:
      - start_date: "2020-01-01"
        end_date: "2024-06-30"
        composition_type: "single"
        source_meters:
          - "gas_zahler_alt"
        source_unit: "m³"
      - start_date: "2024-07-01"
        end_date: "9999-12-31"
        composition_type: "single"
        source_meters:
          - "gas_zahler"
        source_unit: "m³"
        apply_offset_from_previous_period: true

  - meter_id: "eg_kalfire"
    type: "virtual"
    output_unit: "m³"
    description: "Fireplace gas consumption"
    calculation_type: "subtraction"
    base_meter: "gas_total"
    subtract_meters:
      - "gastherme_gesamt"
    subtract_meter_conversions:
      gastherme_gesamt:
        from_unit: "kWh"
        to_unit: "m³"

  - meter_id: "strom_allgemein"
    type: "virtual"
    output_unit: "kWh"
    description: "General electricity consumption"
    calculation_type: "subtraction"
    base_meter: "strom_total"
    subtract_meters:
      - "eg_strom"
      - "og1_strom"
      - "og2_strom"

  - meter_id: "haupt_strom"
    type: "physical"
    output_unit: "kWh"
    installation_date: "2024-11-27"
    description: "Main electricity meter"

  # ... (all other meters from your current config)
```

### secrets/influxdb.env
```bash
INFLUX_TOKEN=your_token_here
INFLUX_ORG=your_org_id_here
```

### secrets/tibber.env
```bash
TIBBER_API_TOKEN=your_tibber_token_here
```

---

## Prefect Workflows

### Flow 1: Tibber Sync (tibber_sync_flow.py)
```python
from prefect import flow, task, get_run_logger
from prefect.task_runners import SequentialTaskRunner
import requests
from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient, Point

@task(retries=3, retry_delay_seconds=60)
def fetch_tibber_data(api_token: str, lookback_hours: int = 48):
    """Fetch consumption data from Tibber GraphQL API"""
    logger = get_run_logger()
    logger.info(f"Fetching Tibber data for last {lookback_hours} hours")

    query = """
    {
      viewer {
        homes {
          consumption(resolution: HOURLY, last: %d) {
            nodes {
              from
              to
              consumption
              cost
            }
          }
        }
      }
    }
    """ % lookback_hours

    response = requests.post(
        "https://api.tibber.com/v1-beta/gql",
        json={"query": query},
        headers={"Authorization": f"Bearer {api_token}"},
        timeout=30
    )
    response.raise_for_status()

    data = response.json()
    consumptions = data["data"]["viewer"]["homes"][0]["consumption"]["nodes"]
    logger.info(f"Fetched {len(consumptions)} data points from Tibber")

    return consumptions

@task(retries=3, retry_delay_seconds=30)
def get_last_influxdb_timestamp(influx_url: str, influx_token: str,
                                  influx_org: str, bucket: str, meter_id: str):
    """Get the most recent timestamp from InfluxDB"""
    logger = get_run_logger()

    with InfluxDBClient(url=influx_url, token=influx_token, org=influx_org) as client:
        query_api = client.query_api()
        query = f'''
        from(bucket: "{bucket}")
            |> range(start: -30d)
            |> filter(fn: (r) => r["entity_id"] == "{meter_id}")
            |> filter(fn: (r) => r["_field"] == "value")
            |> last()
        '''

        result = query_api.query(query)

        if result and len(result) > 0 and len(result[0].records) > 0:
            last_time = result[0].records[0].get_time()
            logger.info(f"Last InfluxDB timestamp: {last_time}")
            return last_time

        logger.warning("No existing data found in InfluxDB")
        return None

@task(retries=3, retry_delay_seconds=30)
def write_to_influxdb(influx_url: str, influx_token: str, influx_org: str,
                      bucket: str, meter_id: str, data_points: list,
                      last_timestamp: datetime):
    """Write new data points to InfluxDB"""
    logger = get_run_logger()

    # Filter for new data only
    new_points = []
    for point in data_points:
        point_time = datetime.fromisoformat(point["from"].replace("Z", "+00:00"))
        if last_timestamp is None or point_time > last_timestamp:
            new_points.append(point)

    if not new_points:
        logger.info("No new data points to write")
        return 0

    logger.info(f"Writing {len(new_points)} new data points to InfluxDB")

    with InfluxDBClient(url=influx_url, token=influx_token, org=influx_org) as client:
        write_api = client.write_api()

        for point in new_points:
            p = Point("kWh") \
                .tag("entity_id", meter_id) \
                .tag("domain", "input_number") \
                .field("value", point["consumption"]) \
                .time(datetime.fromisoformat(point["from"].replace("Z", "+00:00")))

            write_api.write(bucket=bucket, record=p)

    logger.info(f"Successfully wrote {len(new_points)} points")
    return len(new_points)

@flow(name="Tibber Sync", task_runner=SequentialTaskRunner())
def tibber_sync_flow(config: dict):
    """Main flow for syncing Tibber data to InfluxDB"""
    logger = get_run_logger()
    logger.info("Starting Tibber sync flow")

    # Fetch Tibber data
    tibber_data = fetch_tibber_data(
        api_token=config["tibber_token"],
        lookback_hours=config["tibber"]["lookback_hours"]
    )

    # Get last InfluxDB timestamp
    last_timestamp = get_last_influxdb_timestamp(
        influx_url=config["influxdb"]["url"],
        influx_token=config["influx_token"],
        influx_org=config["influx_org"],
        bucket=config["influxdb"]["bucket_raw"],
        meter_id=config["tibber"]["meter_id"]
    )

    # Write new data
    points_written = write_to_influxdb(
        influx_url=config["influxdb"]["url"],
        influx_token=config["influx_token"],
        influx_org=config["influx_org"],
        bucket=config["influxdb"]["bucket_raw"],
        meter_id=config["tibber"]["meter_id"],
        data_points=tibber_data,
        last_timestamp=last_timestamp
    )

    logger.info(f"Tibber sync completed. {points_written} new points written.")
    return points_written
```

### Flow 2: Analytics (analytics_flow.py)
```python
from prefect import flow, task, get_run_logger
from prefect.task_runners import ConcurrentTaskRunner
from typing import Dict, List
import pandas as pd
from datetime import datetime

@task
def fetch_meter_data(influx_client, meter_id: str, start_date: datetime):
    """Fetch raw meter data from InfluxDB"""
    logger = get_run_logger()
    logger.info(f"Fetching data for meter: {meter_id}")

    # Use existing InfluxClient code
    data = influx_client.fetch_all_meter_data(meter_id, start_date)
    logger.info(f"Fetched {len(data)} data points for {meter_id}")

    return data

@task
def interpolate_meter_data(data: pd.DataFrame, meter_config: dict):
    """Interpolate meter data to daily/monthly series"""
    logger = get_run_logger()
    logger.info(f"Interpolating data for {meter_config['meter_id']}")

    # Use existing DataProcessor code
    from src.data_processor import DataProcessor
    processor = DataProcessor()

    daily_series = processor.interpolate_series(
        data,
        meter_config['meter_id'],
        frequency='D'
    )

    monthly_series = processor.aggregate_daily_to_frequency(
        daily_series,
        'M'
    )

    logger.info(f"Generated {len(daily_series)} daily points, {len(monthly_series)} monthly points")

    return {
        'daily': daily_series,
        'monthly': monthly_series
    }

@task
def process_master_meter(master_config: dict, period_data: Dict[str, pd.DataFrame]):
    """Combine multiple physical meters into master meter"""
    logger = get_run_logger()
    logger.info(f"Processing master meter: {master_config['meter_id']}")

    # Use existing UtilityAnalyzer master meter logic
    combined_series = []

    for period in master_config['periods']:
        logger.info(f"Processing period: {period['start_date']} to {period['end_date']}")

        # Combine source meters for this period
        period_series = None
        if period['composition_type'] == 'single':
            period_series = period_data[period['source_meters'][0]]
        elif period['composition_type'] == 'sum':
            period_series = sum([period_data[m] for m in period['source_meters']])

        # Apply offset if needed
        if period.get('apply_offset_from_previous_period') and combined_series:
            offset = combined_series[-1].iloc[-1] - period_series.iloc[0]
            period_series = period_series + offset

        combined_series.append(period_series)

    result = pd.concat(combined_series)
    logger.info(f"Master meter {master_config['meter_id']} created with {len(result)} points")

    return result

@task
def calculate_consumption(series: pd.DataFrame, meter_id: str):
    """Calculate consumption from meter readings"""
    logger = get_run_logger()
    logger.info(f"Calculating consumption for {meter_id}")

    # Use existing ConsumptionCalculator code
    from src.calculator import ConsumptionCalculator
    calculator = ConsumptionCalculator()

    consumption = calculator.calculate_period_consumption(series)
    logger.info(f"Calculated {len(consumption)} consumption values")

    return consumption

@task
def write_results_to_influxdb(influx_client, meter_id: str,
                               interpolated: pd.DataFrame,
                               consumption: pd.DataFrame):
    """Write processed results back to InfluxDB"""
    logger = get_run_logger()
    logger.info(f"Writing results for {meter_id} to InfluxDB")

    # Write interpolated series
    for timestamp, row in interpolated.iterrows():
        point = {
            'measurement': 'meter_interpolated',
            'tags': {'meter_id': meter_id},
            'fields': {'value': row['value']},
            'time': timestamp
        }
        influx_client.write_point(point)

    # Write consumption
    for timestamp, row in consumption.iterrows():
        point = {
            'measurement': 'meter_consumption',
            'tags': {'meter_id': meter_id},
            'fields': {'consumption': row['consumption']},
            'time': timestamp
        }
        influx_client.write_point(point)

    logger.info(f"Successfully wrote {len(interpolated)} interpolated + {len(consumption)} consumption points")

@task
def detect_anomalies(consumption: pd.DataFrame, meter_id: str) -> List[dict]:
    """Detect consumption anomalies"""
    logger = get_run_logger()
    logger.info(f"Detecting anomalies for {meter_id}")

    # Simple anomaly detection: consumption > 2x rolling average
    rolling_avg = consumption['consumption'].rolling(window=7).mean()
    threshold = rolling_avg * 2

    anomalies = consumption[consumption['consumption'] > threshold]

    if len(anomalies) > 0:
        logger.warning(f"Found {len(anomalies)} anomalies for {meter_id}")
    else:
        logger.info(f"No anomalies detected for {meter_id}")

    return anomalies.to_dict('records')

@flow(name="Daily Analytics", task_runner=ConcurrentTaskRunner())
def analytics_flow(config: dict):
    """Main analytics workflow"""
    logger = get_run_logger()
    logger.info("Starting daily analytics flow")

    # Initialize clients
    from src.influx_client import InfluxClient
    from src.config import Config

    influx_client = InfluxClient(
        url=config['influxdb']['url'],
        token=config['influx_token'],
        org=config['influx_org'],
        bucket=config['influxdb']['bucket_raw']
    )

    # Load meter configuration
    meters = config['meters']
    start_year = config['workflows']['analytics']['start_year']
    start_date = datetime(start_year, 1, 1)

    results = {}

    # Process physical meters
    physical_meters = [m for m in meters if m['type'] == 'physical']
    logger.info(f"Processing {len(physical_meters)} physical meters")

    for meter in physical_meters:
        # Fetch and interpolate
        raw_data = fetch_meter_data(influx_client, meter['meter_id'], start_date)
        interpolated = interpolate_meter_data(raw_data, meter)
        consumption = calculate_consumption(interpolated['daily'], meter['meter_id'])

        # Detect anomalies
        anomalies = detect_anomalies(consumption, meter['meter_id'])

        # Write to InfluxDB
        write_results_to_influxdb(
            influx_client,
            meter['meter_id'],
            interpolated['daily'],
            consumption
        )

        results[meter['meter_id']] = {
            'interpolated': interpolated,
            'consumption': consumption,
            'anomalies': anomalies
        }

    # Process master meters
    master_meters = [m for m in meters if m['type'] == 'master']
    logger.info(f"Processing {len(master_meters)} master meters")

    for master in master_meters:
        # Fetch source meter data
        period_data = {}
        for period in master['periods']:
            for source_meter in period['source_meters']:
                if source_meter not in period_data:
                    period_data[source_meter] = results[source_meter]['interpolated']['daily']

        # Process master meter
        master_series = process_master_meter(master, period_data)
        consumption = calculate_consumption(master_series, master['meter_id'])
        anomalies = detect_anomalies(consumption, master['meter_id'])

        # Write to InfluxDB
        write_results_to_influxdb(
            influx_client,
            master['meter_id'],
            master_series,
            consumption
        )

        results[master['meter_id']] = {
            'interpolated': master_series,
            'consumption': consumption,
            'anomalies': anomalies
        }

    # Process virtual meters
    virtual_meters = [m for m in meters if m['type'] == 'virtual']
    logger.info(f"Processing {len(virtual_meters)} virtual meters")

    for virtual in virtual_meters:
        # Calculate virtual meter (subtraction)
        base_consumption = results[virtual['base_meter']]['consumption']

        for subtract_meter in virtual['subtract_meters']:
            subtract_consumption = results[subtract_meter]['consumption']
            base_consumption = base_consumption - subtract_consumption

        # Clip to zero
        base_consumption = base_consumption.clip(lower=0)

        anomalies = detect_anomalies(base_consumption, virtual['meter_id'])

        # Write to InfluxDB
        write_results_to_influxdb(
            influx_client,
            virtual['meter_id'],
            None,  # No interpolated series for virtual meters
            base_consumption
        )

        results[virtual['meter_id']] = {
            'consumption': base_consumption,
            'anomalies': anomalies
        }

    # Summary
    total_anomalies = sum(len(r.get('anomalies', [])) for r in results.values())
    logger.info(f"Analytics flow completed. Processed {len(results)} meters, found {total_anomalies} anomalies")

    return results
```

---

## Why No PostgreSQL?

You're absolutely right - we don't need PostgreSQL because:

1. **Prefect can use SQLite** - Prefect Server stores workflow metadata in SQLite by default (lightweight, perfect for home NAS)

2. **All meter data goes to InfluxDB** - Both raw and processed data are time-series, which is what InfluxDB is designed for

3. **Workflow logs in Prefect** - Prefect already stores execution logs

4. **Simplicity** - One less service to manage, backup, and maintain

The only trade-off is that SQLite doesn't support multiple concurrent write operations, but for a home system with a few workflows, this is perfectly fine.

---

## InfluxDB Bucket Strategy

### Option 1: Two Buckets (Recommended)
```
lampfi (existing)           - Raw meter readings from HA/Tibber
lampfi_processed (new)      - Interpolated + consumption results
```

**Pros:** Clear separation, easy to debug, can delete processed data and regenerate

### Option 2: Single Bucket with Measurements
```
lampfi (single bucket)
  ├─ measurement: kWh, m³, MWh (raw readings)
  ├─ measurement: meter_interpolated (processed)
  └─ measurement: meter_consumption (calculated)
```

**Pros:** Simpler configuration, easier queries in Grafana

**Recommendation:** Start with Option 1 (two buckets) for clarity during development.

---

## Logging Strategy

### Structured JSON Logging
```python
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_obj)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.FileHandler('/app/logs/utility_analyzer.log'),
        logging.StreamHandler()  # Also print to console for Docker logs
    ]
)

for handler in logging.root.handlers:
    handler.setFormatter(JSONFormatter())
```

**Benefits:**
- Easy to parse with log aggregation tools
- Structured for debugging
- Timestamps in UTC for consistency
- Can filter by level, module, function

---

## Next Steps

1. ✅ Review this simplified architecture
2. Create new directory structure
3. Refactor core code to Prefect tasks/flows
4. Create Docker Compose setup
5. Test locally
6. Deploy to NAS

**Should I proceed with implementation?**
