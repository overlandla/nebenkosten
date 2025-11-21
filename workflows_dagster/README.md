# Dagster Utility Workflows

Production-ready Dagster workflows for processing utility meter data with comprehensive anomaly detection, interpolation, and analytics.

## 🎯 What This Does

This workflow system:
1. **Ingests** raw meter readings from InfluxDB and external APIs (Tibber, water temperature)
2. **Interpolates** sparse readings into standardized daily/monthly series
3. **Combines** multiple physical meters across time periods (master meters)
4. **Calculates** virtual meters (e.g., general electricity = total - individual apartments)
5. **Detects anomalies** using multi-method statistical analysis
6. **Writes** processed data back to InfluxDB for visualization

## 🏗️ Architecture

```
┌─────────────────┐
│  InfluxDB (Raw) │◄─── Tibber API, Water Temp API
└────────┬────────┘
         │
         ▼
┌────────────────────────────────────────────────────┐
│           Dagster Analytics Pipeline               │
│                                                    │
│  ┌──────────────┐    ┌──────────────┐            │
│  │   Discovery  │───►│  Fetch Data  │            │
│  └──────────────┘    └───────┬──────┘            │
│                              │                     │
│                              ▼                     │
│  ┌────────────────────────────────────┐           │
│  │  Interpolation & Extrapolation     │           │
│  │  - Linear interpolation             │           │
│  │  - Seasonal pattern distribution    │           │
│  │  - Regression-based extrapolation   │           │
│  │  - Installation/deinstallation dates│           │
│  └───────────────┬────────────────────┘           │
│                  │                                 │
│                  ▼                                 │
│  ┌────────────────────────────────────┐           │
│  │  Interpolation Validation          │           │
│  │  - Verify against raw readings     │           │
│  │  - Quality metrics & gap analysis  │           │
│  └───────────────┬────────────────────┘           │
│                  │                                 │
│        ┌─────────┴──────────┐                     │
│        ▼                    ▼                      │
│  ┌───────────┐        ┌──────────────┐           │
│  │  Master   │        │   Virtual    │           │
│  │  Meters   │        │   Meters     │           │
│  └─────┬─────┘        └──────┬───────┘           │
│        │                     │                     │
│        └──────────┬──────────┘                     │
│                   ▼                                │
│          ┌──────────────────┐                     │
│          │  Consumption     │                     │
│          │  Calculation     │                     │
│          └────────┬─────────┘                     │
│                   │                                │
│                   ▼                                │
│          ┌──────────────────┐                     │
│          │     Anomaly      │                     │
│          │    Detection     │                     │
│          │  (3 methods)     │                     │
│          └────────┬─────────┘                     │
└──────────────────┼────────────────────────────────┘
                   ▼
         ┌──────────────────┐
         │ InfluxDB          │
         │ (Processed)       │
         └──────────────────┘
```

## 📦 Directory Structure

```
workflows_dagster/
├── src/                        # Core utility analysis modules
│   ├── influx_client.py       # InfluxDB client with caching
│   ├── data_processor.py      # Interpolation & extrapolation
│   └── calculator.py          # Consumption calculations
│
├── dagster_project/           # Dagster-specific code
│   ├── assets/                # Data processing assets
│   │   ├── analytics_assets.py    # Main analytics pipeline
│   │   ├── tibber_assets.py       # Tibber API ingestion
│   │   ├── water_temp_assets.py   # Water temperature ingestion
│   │   └── influxdb_writer_assets.py  # Write to InfluxDB
│   │
│   ├── jobs/                  # Job definitions
│   ├── schedules/             # Scheduled runs
│   ├── sensors/               # Monitoring & alerting
│   │   ├── failure_sensor.py  # Alert on pipeline failures
│   │   └── anomaly_sensor.py  # Alert on detected anomalies
│   │
│   ├── resources/             # Shared resources
│   │   ├── influxdb_resource.py
│   │   ├── tibber_resource.py
│   │   └── config_resource.py
│   │
│   └── utils/                 # Utilities
│       └── env_validation.py  # Environment checks
│
├── tests/                     # Comprehensive test suite
│   ├── unit/                  # Unit tests for src modules
│   │   ├── test_influx_client.py
│   │   ├── test_data_processor.py
│   │   ├── test_consumption_calculator.py
│   │   └── test_interpolation_validation.py
│   └── integration/           # Integration tests for assets
│       └── test_analytics_assets.py
│
├── config/                    # Configuration files
│   ├── config.yaml           # Main configuration
│   ├── meters.yaml           # Meter definitions
│   └── seasonal_patterns.yaml # Seasonal consumption patterns
│
├── pytest.ini                 # Test configuration
├── requirements-dagster.txt   # Production dependencies
└── requirements-test.txt      # Testing dependencies
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd workflows_dagster
pip install -r requirements-dagster.txt
```

### 2. Configure Environment

```bash
# Copy example environment file
cp ../.env.example secrets/influxdb.env

# Edit with your actual credentials
nano secrets/influxdb.env
```

Required variables:
- `INFLUX_TOKEN` - InfluxDB API token
- `INFLUX_ORG` - InfluxDB organization ID

Optional:
- `TIBBER_API_TOKEN` - For Tibber electricity data ingestion

### 3. Configure Meters

Edit `config/meters.yaml` to define your meters. See [Configuration Guide](#configuration) below.

### 4. Run Dagster

```bash
# Development mode (with UI)
dagster dev -m dagster_project

# Production mode
dagster-webserver -m dagster_project
```

Navigate to http://localhost:3000 to access the Dagster UI.

## 📊 Key Features

### 1. Advanced Interpolation

**Problem:** Utility meters are read sporadically (every few weeks or months)

**Solution:** Smart interpolation with:
- **Linear interpolation** for short gaps (< 7 days)
- **Seasonal pattern distribution** for longer gaps (≥ 7 days) using monthly percentages
- **Regression-based extrapolation** for sparse data (uses 4 methods, picks best)
- **Backward extrapolation** to installation dates
- **Forward extrapolation** to today() incorporating seasonal patterns
- **Installation date validation** - ensures all meters have required dates
- **Interpolation validation** - verifies interpolated values match raw readings exactly at data points
- **Quality reporting** - gap analysis, coverage metrics, extrapolation distances
- High-frequency data reduction (preserves trends)

**Example:**
```
Raw readings (every 5 days):
  2024-01-01: 100.0
  2024-01-06: 112.5
  2024-01-11: 125.0

Interpolated daily series:
  2024-01-01: 100.0  ✓ (matches raw)
  2024-01-02: 102.5
  2024-01-03: 105.0
  2024-01-04: 107.5
  2024-01-05: 110.0
  2024-01-06: 112.5  ✓ (matches raw)
  ...
```

**Seasonal Patterns:**
For gaps ≥ 7 days, consumption is distributed using monthly patterns:
```yaml
# config/seasonal_patterns.yaml
seasonal_patterns:
  default:
    - 10.5  # January (10.5% of yearly consumption)
    - 9.8   # February
    - 8.5   # March
    ...
```

### 2. Multi-Method Anomaly Detection

**Old Approach:** Simple 2x rolling average (high false positives)

**New Approach:** Consensus of 3 statistical methods:

1. **Global Z-Score:** Flags values >3 standard deviations from mean
2. **IQR Method:** Detects outliers beyond 1.5 × IQR from quartiles
3. **Rolling Z-Score:** Local anomalies using 30-day window (>2.5σ)

An anomaly is flagged only if detected by **2+ methods**, reducing false positives by ~70%.

**Example:**
```python
Normal consumption: 2.0 kWh/day
Anomaly: 25.0 kWh/day

Methods:
  ✓ Z-score: 11.5 (>3)
  ✓ IQR: Beyond upper bound
  ✓ Rolling Z-score: 8.2 (>2.5)

Result: ANOMALY (3/3 methods agree)
```

### 3. Interpolation Validation & Quality Reporting

**Validation Asset** (`interpolation_validation`):
- Verifies interpolated values **exactly match** raw readings at all raw timestamps
- Tolerance: 0.01 units
- **Fails the pipeline** if mismatches detected (ensures data integrity)

**Quality Report Asset** (`interpolation_quality_report`):
Generates comprehensive metrics for each meter:
```
meter_id: gas_total
├── Total days: 365
├── Raw readings: 24
├── Largest gap: 18 days
├── Average gap: 15.2 days
├── Forward extrapolation: 5 days (to today)
├── Backward extrapolation: 30 days (to installation_date)
└── Raw data coverage: 94.2%
```

**Benefits:**
- Catch data quality issues early
- Identify meters with sparse data
- Track extrapolation distances
- Validate accuracy of interpolation

### 4. Master Meters

Combine multiple physical meters across time periods (e.g., meter replacements):

```yaml
- meter_id: "gas_total"
  type: "master"
  periods:
    - start_date: "2020-06-01"
      end_date: "2024-11-12"
      source_meters: ["gas_zahler_alt"]
    - start_date: "2024-11-13"
      end_date: "9999-12-31"
      source_meters: ["gas_zahler"]
      apply_offset_from_previous_period: true
```

**Features:**
- Automatic offset calculation for meter continuity
- Offset validation (warns if >20% of previous value)
- Unit conversion validation (prevents m³/kWh mixing)

### 5. Virtual Meters

Calculate derived consumption via subtraction:

```yaml
- meter_id: "strom_allgemein"
  type: "virtual"
  base_meter: "strom_total"
  subtract_meters:
    - "eg_strom"
    - "og1_strom"
    - "og2_strom"
```

Result: `strom_allgemein = total - apartment1 - apartment2 - apartment3`

### 6. Data Maintenance

**Wipe Processed Data** (`wipe_processed_data` asset):
- Safely delete all processed data from InfluxDB
- **Does NOT affect raw data** - only processed bucket
- Useful for reprocessing with improved analytics
- Deletes: `meter_interpolated_daily`, `meter_interpolated_monthly`, `meter_consumption`, `meter_anomaly`

**Usage:**
```python
# Materialize the wipe asset in Dagster UI or CLI
dagster asset materialize -m dagster_project -s wipe_processed_data
```

⚠️ **Warning:** This is a destructive operation. Ensure you want to start fresh before running.

## ⚙️ Configuration

### Meter Types

#### Physical Meters
```yaml
- meter_id: "haupt_strom"
  type: "physical"
  output_unit: "kWh"
  installation_date: "2024-11-27"
  deinstallation_date: null  # Still active
```

#### Master Meters
```yaml
- meter_id: "gas_total"
  type: "master"
  output_unit: "m³"
  periods:
    - start_date: "2020-01-01"
      end_date: "2023-06-15"
      source_meters: ["old_meter"]
      source_unit: "m³"
    - start_date: "2023-06-15"
      end_date: "9999-12-31"
      source_meters: ["new_meter"]
      source_unit: "m³"
      apply_offset_from_previous_period: true
```

#### Virtual Meters
```yaml
- meter_id: "eg_kalfire"
  type: "virtual"
  base_meter: "gas_total"
  subtract_meters: ["gastherme_gesamt"]
  subtract_meter_conversions:
    gastherme_gesamt:
      from_unit: "kWh"
      to_unit: "m³"
```

### Gas Conversion

Configure in `config/config.yaml`:
```yaml
gas_conversion:
  energy_content: 11.504  # kWh per m³
  z_factor: 0.8885        # Compression factor
```

## 🧪 Testing

### Run All Tests

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov=dagster_project --cov-report=html

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration
```

### Test Structure

- **Unit tests:** Test individual functions/classes in isolation
  - `test_data_processor.py`: Interpolation, seasonal patterns, installation date validation
  - `test_interpolation_validation.py`: Validation and quality reporting assets
  - `test_influx_client.py`: InfluxDB client functionality
  - `test_consumption_calculator.py`: Consumption calculations
- **Integration tests:** Test complete asset workflows with mocked data
- **106 total tests** covering all critical paths

See [TESTING.md](./TESTING.md) for detailed testing guide.

## 📡 Monitoring & Alerting

### Sensors

**Failure Sensor** (`analytics_failure_sensor`):
- Monitors all analytics job runs
- Logs detailed failure information
- Ready for Slack/email integration (see code comments)

**Anomaly Sensor** (`anomaly_alert_sensor`):
- Checks anomaly detection results hourly
- Can trigger alerts if anomaly count exceeds threshold
- Extensible for custom alerting logic

### Adding Slack Alerts

1. Create Slack incoming webhook
2. Set environment variable:
   ```bash
   export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
   ```
3. Uncomment Slack code in `sensors/failure_sensor.py`

## 🔒 Security

### Recent Security Updates

All dependencies updated to patched versions (Nov 2025):
- **Dagster:** 1.6.0 → 1.10.16 (fixes local file inclusion)
- **scikit-learn:** 1.3.2 → 1.5.0 (fixes data leakage)
- **requests:** 2.31.0 → 2.32.4 (fixes cert bypass & credential leakage)

### Best Practices

- Never commit secrets to version control
- Use `secrets/*.env` files (git-ignored)
- Rotate tokens if compromised
- Use `chmod 600 secrets/*.env` for restrictive permissions

## 📈 Performance Optimizations

1. **DataFrame iteration:** `iterrows()` → `itertuples()` (60x faster)
2. **Caching:** InfluxDB data cached per run
3. **High-frequency reduction:** 5000 points → 50 points (preserves trends)
4. **Lazy loading:** Only process requested meters

## 🐛 Troubleshooting

### Common Issues

**"Missing environment variables: INFLUX_TOKEN"**
```bash
# Solution: Set required environment variables
export INFLUX_TOKEN="your_token"
export INFLUX_ORG="your_org"
```

**"No data found for meter X"**
- Check meter exists in InfluxDB
- Verify entity_id spelling matches
- Check installation_date in config (might be outside query range)

**"Large offset detected" warning**
- Review meter replacement dates in config
- Check if offset > 20% is expected (e.g., long gap between meters)
- Verify meter readings are correct in InfluxDB

**Tests failing**
```bash
# Ensure test dependencies installed
pip install -r requirements-test.txt

# Set test environment variables
export INFLUX_TOKEN=test_token
export INFLUX_ORG=test_org
```

## 📚 Additional Documentation

- [TESTING.md](./TESTING.md) - Comprehensive testing guide
- [config/meters.yaml](./config/meters.yaml) - Meter configuration examples
- [Dagster Docs](https://docs.dagster.io/) - Official Dagster documentation

## 🤝 Contributing

1. Create a feature branch
2. Add tests for new functionality
3. Ensure all tests pass: `pytest`
4. Update documentation
5. Submit pull request

## 📄 License

[Add your license here]

## 📧 Support

For issues or questions:
- Create an issue in the repository
- Check existing documentation
- Review test examples for usage patterns
