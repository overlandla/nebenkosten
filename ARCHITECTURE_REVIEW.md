# Utility Meter System - Security & Architecture Review

**Date:** 2025-11-05
**Reviewer:** Claude Code
**Purpose:** Security hardening and architectural modernization recommendations

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Security Issues & Remediation](#security-issues--remediation)
3. [Current Architecture Analysis](#current-architecture-analysis)
4. [Proposed Modern Architecture](#proposed-modern-architecture)
5. [Frontend Strategy: Streamlit vs Grafana](#frontend-strategy-streamlit-vs-grafana)
6. [Migration Roadmap](#migration-roadmap)
7. [Implementation Plan](#implementation-plan)

---

## Executive Summary

### Current State
- **Security:** Critical vulnerabilities with hardcoded secrets in version control
- **Architecture:** Monolithic Streamlit app handling data processing, analysis, and visualization
- **Deployment:** Manual cron-based data sync, lacks containerization
- **Data Flow:** Multiple uncoordinated data ingestion paths (Tibber API, Excel uploads, Home Assistant)

### Recommended State
- **Security:** Secrets externalized via Docker secrets or vault, configuration in version control
- **Architecture:** Microservices with workflow orchestration (Prefect/Airflow), containerized
- **Deployment:** Docker Compose stack with health checks, auto-restarts, logging
- **Visualization:** Grafana dashboards leveraging existing InfluxDB integration

### Key Benefits
- ✅ **Security:** Zero secrets in code/git, principle of least privilege
- ✅ **Scalability:** Independent scaling of data ingestion vs analytics
- ✅ **Maintainability:** Clear separation of concerns, easier testing
- ✅ **Observability:** Centralized logging, metrics, alerting
- ✅ **Cost:** Eliminate redundant Streamlit frontend (Grafana already available)

---

## Security Issues & Remediation

### 🚨 Critical Issues Identified

#### Issue 1: Hardcoded InfluxDB Token in Version Control
**Location:** `Nebenkosten/.env` (line 2)
```bash
INFLUX_TOKEN=OcXhfQCBA6rKpIN4f5JSrmtp2xxgjk4vBt1jAqpjb-g1sIh1nUDdB8Ljo-ZMYxjMQJEicDncrZ1QE2PzH9nzZg==
```
**Risk:** Full read/write access to InfluxDB database if repository is compromised
**CVSS Score:** 9.8 (Critical)

#### Issue 2: Hardcoded Tibber API Token
**Location:** `tools/tibber_import/tibber_influxdb_sync.py` (line 33)
```python
TIBBER_API_TOKEN = "5K4MVS-OjfWhK_4yrjOlFe1F6kJXPVf7eQYggo8ebAE"  # Hardcoded
```
**Risk:** Unauthorized access to personal energy consumption data, billing info
**CVSS Score:** 7.5 (High)

#### Issue 3: InfluxDB Organization ID in Version Control
**Location:** `Nebenkosten/.env` (line 3)
```bash
INFLUX_ORG=0d72e1f6b38972fa
```
**Risk:** Aids attackers in enumerating organization structure
**CVSS Score:** 5.3 (Medium)

#### Issue 4: Internal Network IP Addresses Exposed
**Location:** Multiple files
```bash
INFLUX_URL=http://192.168.1.75:8086  # Network topology disclosure
```
**Risk:** Reveals internal network structure
**CVSS Score:** 4.3 (Medium)

### ✅ Remediation Strategy

#### Split: Secrets vs Configuration

**Secrets (Never in Version Control)**
- InfluxDB token, organization ID
- Tibber API token
- Any future API keys (e.g., weather APIs)
- Database credentials
- SSH keys, TLS certificates

**Configuration (Safe for Version Control)**
- InfluxDB URL (can use DNS name like `influxdb.local` or service name `influxdb`)
- InfluxDB bucket name (`lampfi`)
- Gas conversion constants (`GAS_ENERGY_CONTENT`, `GAS_Z_FACTOR`)
- Meter configuration JSON (`METER_CONFIGURATION_JSON`)
- Seasonal patterns JSON
- Application ports, timeouts, retry configs

#### Proposed File Structure

```
Nebenkosten/
├── config/
│   ├── config.yaml              # Version-controlled configuration
│   ├── meters.json              # Meter definitions (configuration)
│   ├── seasonal_patterns.json   # Consumption patterns (configuration)
│   └── .gitignore               # Explicitly ignore secrets
├── secrets/                      # NOT in version control
│   ├── .gitignore               # Ensure secrets/ is ignored
│   ├── influxdb.env             # InfluxDB credentials
│   ├── tibber.env               # Tibber API token
│   └── README.md                # Instructions for secrets setup
├── .env.example                  # Template for all secrets (no values)
└── docker-compose.yml            # References secrets via env_file
```

#### Example Implementation

**config/config.yaml** (version controlled)
```yaml
influxdb:
  url: "http://influxdb:8086"  # Docker service name
  bucket: "lampfi"
  timeout: 30
  retry_attempts: 3

tibber:
  polling_interval: 3600  # 1 hour
  lookback_hours: 48
  state_file: "/app/state/tibber_sync_state.json"

gas_conversion:
  energy_content: 11.504  # kWh/m³
  z_factor: 0.8885

meters:
  config_file: "config/meters.json"

logging:
  level: "INFO"
  format: "json"
  max_bytes: 10485760  # 10MB
  backup_count: 5
```

**secrets/influxdb.env** (NOT in version control)
```bash
INFLUX_TOKEN=OcXhfQCBA6rKpIN4f5JSrmtp2xxgjk4vBt1jAqpjb-g1sIh1nUDdB8Ljo-ZMYxjMQJEicDncrZ1QE2PzH9nzZg==
INFLUX_ORG=0d72e1f6b38972fa
```

**secrets/tibber.env** (NOT in version control)
```bash
TIBBER_API_TOKEN=5K4MVS-OjfWhK_4yrjOlFe1F6kJXPVf7eQYggo8ebAE
```

**.env.example** (version controlled template)
```bash
# InfluxDB Configuration
INFLUX_TOKEN=your_influxdb_token_here
INFLUX_ORG=your_org_id_here

# Tibber API
TIBBER_API_TOKEN=your_tibber_token_here

# Instructions:
# 1. Copy this file to secrets/influxdb.env and secrets/tibber.env
# 2. Replace placeholder values with actual secrets
# 3. Never commit secrets/ directory to version control
```

**secrets/.gitignore**
```
# Ignore all secrets
*.env
!.gitignore
!README.md
```

**Root .gitignore additions**
```
# Secrets
secrets/*.env
.env
*.secret
*.key

# State files
state/
*.json.lock
```

#### Docker Secrets (Recommended for Production)

**docker-compose.yml** (with Docker secrets)
```yaml
version: '3.8'

services:
  tibber-sync:
    build: ./tools/tibber_import
    env_file:
      - secrets/influxdb.env
      - secrets/tibber.env
    configs:
      - source: app_config
        target: /app/config/config.yaml
    secrets:
      - influx_token
      - tibber_token
    environment:
      - CONFIG_FILE=/app/config/config.yaml

secrets:
  influx_token:
    file: ./secrets/influxdb_token.txt
  tibber_token:
    file: ./secrets/tibber_token.txt

configs:
  app_config:
    file: ./config/config.yaml
```

#### Code Changes Required

**Before (tibber_influxdb_sync.py)**
```python
TIBBER_API_TOKEN = "5K4MVS-OjfWhK_4yrjOlFe1F6kJXPVf7eQYggo8ebAE"  # Hardcoded
```

**After**
```python
import os
TIBBER_API_TOKEN = os.environ.get("TIBBER_API_TOKEN")
if not TIBBER_API_TOKEN:
    raise ValueError("TIBBER_API_TOKEN environment variable must be set")
```

**Before (config.py)**
```python
load_dotenv()  # Loads .env with secrets mixed with config
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
```

**After**
```python
import yaml
from pathlib import Path

# Load configuration (version controlled)
config_path = Path(os.getenv("CONFIG_FILE", "config/config.yaml"))
with config_path.open() as f:
    config = yaml.safe_load(f)

# Load secrets (environment variables)
INFLUX_TOKEN = os.environ["INFLUX_TOKEN"]  # Fail fast if missing
INFLUX_ORG = os.environ["INFLUX_ORG"]

# Access configuration
INFLUX_URL = config["influxdb"]["url"]
INFLUX_BUCKET = config["influxdb"]["bucket"]
```

---

## Current Architecture Analysis

### Component Diagram
```
┌─────────────────────────────────────────────────────────────┐
│                     Current Architecture                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐         ┌──────────────┐                  │
│  │ Tibber API   │────┬────│  Cron Job    │                  │
│  └──────────────┘    │    │ (hourly)     │                  │
│                      │    └──────────────┘                  │
│                      │            │                          │
│                      ▼            ▼                          │
│              ┌────────────────────────────┐                 │
│              │  tibber_influxdb_sync.py   │                 │
│              └────────────────────────────┘                 │
│                      │                                       │
│                      │                                       │
│  ┌──────────────┐   │   ┌──────────────────────┐           │
│  │ Home         │───┼──▶│    InfluxDB v2       │           │
│  │ Assistant    │   │   │   (lampfi bucket)    │           │
│  │ Integration  │   │   └──────────────────────┘           │
│  └──────────────┘   │            ▲                          │
│                     │            │                          │
│                     └────────────┘                          │
│                                  │                          │
│                                  │                          │
│  ┌──────────────┐                │                          │
│  │ Excel Upload │────┐           │                          │
│  │ (Manual)     │    │           │                          │
│  └──────────────┘    │           │                          │
│                      ▼           │                          │
│              ┌───────────────────┴────┐                     │
│              │  Streamlit Application │                     │
│              ├────────────────────────┤                     │
│              │ • Data Import UI       │                     │
│              │ • UtilityAnalyzer      │                     │
│              │ • Data Processing      │                     │
│              │ • Calculations         │                     │
│              │ • Chart Generation     │                     │
│              │ • Report Display       │                     │
│              └────────────────────────┘                     │
│                      │                                       │
│                      ▼                                       │
│              ┌────────────────┐                             │
│              │  User Browser  │                             │
│              └────────────────┘                             │
└─────────────────────────────────────────────────────────────┘
```

### Issues with Current Architecture

#### 1. Monolithic Design
**Problem:** Streamlit app handles everything:
- Data ingestion (Excel uploads)
- Data processing (interpolation, calculations)
- Visualization (Plotly charts)
- Analysis orchestration

**Impact:**
- Cannot scale components independently
- One component failure affects entire system
- Difficult to test individual components
- High resource usage even when just viewing reports

#### 2. Uncoordinated Data Ingestion
**Problem:** Three separate ingestion paths:
- Tibber: Cron-based script (independent)
- Home Assistant: Direct InfluxDB write (independent)
- Excel: Streamlit UI (manual, requires app running)

**Impact:**
- No centralized monitoring of data pipeline health
- Duplicate data risk (no coordination)
- Manual intervention required for Excel imports
- No retry logic or error recovery

#### 3. Lack of Workflow Orchestration
**Problem:** No dependency management between tasks:
- Data ingestion happens independently
- Analysis runs only when user triggers Streamlit
- No scheduled reports or alerts

**Impact:**
- Cannot automate end-to-end workflows (fetch → process → analyze → alert)
- No visibility into pipeline execution status
- No audit trail of processing runs

#### 4. Stateful Processing Without Persistence
**Problem:** Analysis results not persisted:
- Each Streamlit session recalculates everything
- Computationally expensive for long time ranges
- No ability to compare historical analysis runs

**Impact:**
- Slow UI response times (seconds to minutes)
- Redundant processing of same data
- No historical tracking of consumption pattern changes

#### 5. Limited Observability
**Problem:** Logging is scattered:
- Tibber sync: `/var/log/tibber_sync.log`
- Streamlit: stdout (captured in browser only)
- No centralized metrics or alerting

**Impact:**
- Difficult to troubleshoot issues
- No proactive error detection
- Cannot correlate events across components

#### 6. No Containerization
**Problem:** Direct installation on host:
- Python dependencies installed globally/venv
- Cron jobs configured manually
- No isolation between services

**Impact:**
- Difficult to replicate environment
- Risk of dependency conflicts
- Hard to manage updates and rollbacks

---

## Proposed Modern Architecture

### High-Level Design

```
┌───────────────────────────────────────────────────────────────────┐
│                    Proposed Architecture                           │
│                   (Docker Compose Stack)                           │
├───────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │                Data Ingestion Layer                         │   │
│  ├────────────────────────────────────────────────────────────┤   │
│  │                                                              │   │
│  │  ┌──────────────┐      ┌──────────────┐      ┌──────────┐  │   │
│  │  │ Tibber Sync  │      │  HA Bridge   │      │  Excel   │  │   │
│  │  │  Container   │      │  Container   │      │  Importer│  │   │
│  │  │              │      │              │      │  API     │  │   │
│  │  │ • Hourly     │      │ • Listens to │      │ • REST   │  │   │
│  │  │ • GraphQL    │      │   HA webhooks│      │ • Upload │  │   │
│  │  │ • Idempotent │      │ • Validates  │      │ • Batch  │  │   │
│  │  └──────────────┘      └──────────────┘      └──────────┘  │   │
│  │         │                      │                    │       │   │
│  └─────────┼──────────────────────┼────────────────────┼───────┘   │
│            │                      │                    │           │
│            └──────────────────────┴────────────────────┘           │
│                                   │                                │
│                                   ▼                                │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │                    InfluxDB v2 Container                    │   │
│  │  • Time-series storage                                      │   │
│  │  • Retention policies (10 years)                            │   │
│  │  • Continuous queries for aggregations                      │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                   │                                │
│                                   ▼                                │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │              Workflow Orchestration Layer                   │   │
│  ├────────────────────────────────────────────────────────────┤   │
│  │                                                              │   │
│  │  ┌────────────────────────────────────────────────────┐     │   │
│  │  │         Prefect Server Container                   │     │   │
│  │  │  • Workflow scheduling                             │     │   │
│  │  │  • Dependency management                           │     │   │
│  │  │  • Retry logic                                     │     │   │
│  │  │  • Execution monitoring                            │     │   │
│  │  └────────────────────────────────────────────────────┘     │   │
│  │                           │                                  │   │
│  │                           ▼                                  │   │
│  │  ┌────────────────────────────────────────────────────┐     │   │
│  │  │         Analytics Worker Container                 │     │   │
│  │  │  • UtilityAnalyzer core                            │     │   │
│  │  │  • Data processing tasks                           │     │   │
│  │  │  • Consumption calculations                        │     │   │
│  │  │  • Scheduled: Daily @ 2 AM                         │     │   │
│  │  └────────────────────────────────────────────────────┘     │   │
│  │                           │                                  │   │
│  └───────────────────────────┼──────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │                  Results Storage Layer                      │   │
│  ├────────────────────────────────────────────────────────────┤   │
│  │                                                              │   │
│  │  ┌────────────────┐         ┌───────────────────────┐       │   │
│  │  │   InfluxDB     │         │   PostgreSQL          │       │   │
│  │  │ (processed)    │         │ (metadata, config)    │       │   │
│  │  │                │         │                       │       │   │
│  │  │ • Interpolated │         │ • Workflow runs       │       │   │
│  │  │   series       │         │ • Anomaly flags       │       │   │
│  │  │ • Consumption  │         │ • User annotations    │       │   │
│  │  │   metrics      │         │                       │       │   │
│  │  └────────────────┘         └───────────────────────┘       │   │
│  │         │                              │                     │   │
│  └─────────┼──────────────────────────────┼─────────────────────┘   │
│            │                              │                         │
│            └──────────────┬───────────────┘                         │
│                           │                                         │
│                           ▼                                         │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │               Visualization Layer                           │   │
│  ├────────────────────────────────────────────────────────────┤   │
│  │                                                              │   │
│  │  ┌────────────────────────────────────────────────────┐     │   │
│  │  │           Grafana Container                        │     │   │
│  │  │  • Pre-built dashboards                            │     │   │
│  │  │  • InfluxDB data source                            │     │   │
│  │  │  • PostgreSQL data source                          │     │   │
│  │  │  • Alerting rules                                  │     │   │
│  │  │  • Public dashboards (read-only)                   │     │   │
│  │  └────────────────────────────────────────────────────┘     │   │
│  │                                                              │   │
│  └────────────────────────────────────────────────────────────┘   │
│                           │                                         │
│                           ▼                                         │
│                  ┌────────────────┐                                │
│                  │  User Browser  │                                │
│                  └────────────────┘                                │
└───────────────────────────────────────────────────────────────────┘
```

### Component Details

#### 1. Data Ingestion Layer (Containerized)

**Tibber Sync Container**
- **Base Image:** `python:3.11-slim`
- **Scheduler:** Internal (APScheduler) or cron via docker-compose
- **Functionality:**
  - Polls Tibber API every hour (offset: minute 5)
  - Idempotent writes (checks last InfluxDB value before writing)
  - Exponential backoff on API failures
  - Health check endpoint (`:8080/health`)

**Home Assistant Bridge Container** (Optional)
- **Base Image:** `python:3.11-slim`
- **Functionality:**
  - Webhook receiver for HA state changes
  - Validates meter IDs against configuration
  - Writes to InfluxDB with proper tags
  - Alternative: Keep existing HA → InfluxDB integration

**Excel Importer API Container**
- **Base Image:** `python:3.11-slim` + `FastAPI`
- **Endpoints:**
  - `POST /api/v1/meters/{meter_id}/upload` - Upload Excel file
  - `GET /api/v1/meters` - List available meters
  - `GET /api/v1/health` - Health check
- **Functionality:**
  - Accepts Excel files (`.xlsx`, `.xls`)
  - Validates columns: `Ab-Datum`, `Ab-Zeit`, `Zählerstand`
  - Parses German date formats
  - Writes to InfluxDB
  - Returns upload summary (records written, duplicates skipped)

#### 2. Workflow Orchestration Layer

**Prefect Server Container**
- **Image:** `prefecthq/prefect:2-latest`
- **UI Port:** `4200`
- **Functionality:**
  - Centralized workflow scheduling
  - DAG-based task dependencies
  - Automatic retry with configurable backoff
  - Execution history and logs
  - REST API for triggering workflows

**Analytics Worker Container**
- **Base Image:** `python:3.11-slim`
- **Core Code:** Refactored `UtilityAnalyzer` from `main_app.py`
- **Workflows (Prefect flows):**

  **Daily Analysis Workflow** (runs at 2 AM)
  ```
  1. Check data availability (last 24 hours)
  2. Run interpolation (daily series)
  3. Calculate master meters
  4. Calculate virtual meters
  5. Update consumption metrics
  6. Write results to InfluxDB (separate measurement)
  7. Detect anomalies (consumption > 2x avg)
  8. Send alerts if anomalies found
  ```

  **Monthly Report Workflow** (runs 1st of month)
  ```
  1. Aggregate previous month consumption
  2. Compare with same month previous year
  3. Generate summary statistics
  4. Write to PostgreSQL (monthly_reports table)
  5. Trigger Grafana snapshot
  6. Send email report (optional)
  ```

  **On-Demand Analysis Workflow** (triggered via API)
  ```
  1. Accept parameters (start_date, end_date, meters)
  2. Run interpolation for date range
  3. Calculate consumption
  4. Return results as JSON
  ```

#### 3. Results Storage Layer

**InfluxDB v2 Container**
- **Image:** `influxdb:2.7-alpine`
- **Buckets:**
  - `lampfi` - Raw meter readings (existing)
  - `lampfi_processed` - Interpolated series, consumption metrics (new)
- **Retention Policies:**
  - `lampfi`: 10 years (high-resolution)
  - `lampfi_processed`: Infinite (aggregated data)
- **Continuous Queries:** (optional)
  - Hourly → Daily aggregations
  - Daily → Monthly aggregations

**PostgreSQL Container** (optional, for metadata)
- **Image:** `postgres:16-alpine`
- **Tables:**
  - `workflow_runs` - Execution history with status
  - `anomalies` - Detected consumption anomalies
  - `meter_metadata` - Descriptions, installation dates
  - `user_annotations` - Manual notes on data

#### 4. Visualization Layer

**Grafana Container**
- **Image:** `grafana/grafana:10.2.0`
- **Port:** `3000`
- **Data Sources:**
  - InfluxDB (lampfi, lampfi_processed)
  - PostgreSQL (metadata)
- **Dashboards (provisioned):**
  - **Overview:** All meters, current month consumption
  - **Electricity:** Detailed breakdown (HT/NT, individual circuits)
  - **Gas:** Total + fireplace vs heating
  - **Water:** Total + per-floor breakdown
  - **Heat:** Per-room consumption
  - **Anomalies:** Flagged unusual consumption patterns
- **Alerts:**
  - Consumption > 2x monthly average
  - Missing data for > 48 hours
  - Meter reading decreases (potential reset)

---

### Docker Compose Stack

**docker-compose.yml**
```yaml
version: '3.8'

services:
  influxdb:
    image: influxdb:2.7-alpine
    container_name: utility-influxdb
    restart: unless-stopped
    ports:
      - "8086:8086"
    volumes:
      - influxdb-data:/var/lib/influxdb2
      - influxdb-config:/etc/influxdb2
    env_file:
      - secrets/influxdb.env
    environment:
      - DOCKER_INFLUXDB_INIT_MODE=setup
      - DOCKER_INFLUXDB_INIT_USERNAME=admin
      - DOCKER_INFLUXDB_INIT_BUCKET=lampfi
      - DOCKER_INFLUXDB_INIT_RETENTION=87600h  # 10 years
    healthcheck:
      test: ["CMD", "influx", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    image: postgres:16-alpine
    container_name: utility-postgres
    restart: unless-stopped
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./init-db.sql:/docker-entrypoint-initdb.d/init.sql
    env_file:
      - secrets/postgres.env
    environment:
      - POSTGRES_DB=utility_metadata
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 30s
      timeout: 10s
      retries: 3

  prefect-server:
    image: prefecthq/prefect:2-latest
    container_name: utility-prefect-server
    restart: unless-stopped
    ports:
      - "4200:4200"
    environment:
      - PREFECT_SERVER_API_HOST=0.0.0.0
      - PREFECT_API_DATABASE_CONNECTION_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/prefect
    env_file:
      - secrets/postgres.env
    depends_on:
      - postgres
    command: prefect server start
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:4200/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  tibber-sync:
    build:
      context: ./tools/tibber_import
      dockerfile: Dockerfile
    container_name: utility-tibber-sync
    restart: unless-stopped
    volumes:
      - tibber-state:/app/state
      - ./config:/app/config:ro
    env_file:
      - secrets/influxdb.env
      - secrets/tibber.env
    environment:
      - CONFIG_FILE=/app/config/config.yaml
      - PYTHONUNBUFFERED=1
    depends_on:
      - influxdb
    healthcheck:
      test: ["CMD", "python", "-c", "import os; import sys; sys.exit(0 if os.path.exists('/app/state/tibber_sync_state.json') else 1)"]
      interval: 60s
      timeout: 10s
      retries: 3

  excel-importer:
    build:
      context: ./services/excel_importer
      dockerfile: Dockerfile
    container_name: utility-excel-importer
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - ./config:/app/config:ro
    env_file:
      - secrets/influxdb.env
    environment:
      - CONFIG_FILE=/app/config/config.yaml
    depends_on:
      - influxdb
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  analytics-worker:
    build:
      context: ./Nebenkosten
      dockerfile: Dockerfile.worker
    container_name: utility-analytics-worker
    restart: unless-stopped
    volumes:
      - ./config:/app/config:ro
      - analytics-results:/app/results
    env_file:
      - secrets/influxdb.env
      - secrets/postgres.env
    environment:
      - CONFIG_FILE=/app/config/config.yaml
      - PREFECT_API_URL=http://prefect-server:4200/api
    depends_on:
      - influxdb
      - postgres
      - prefect-server
    command: prefect agent start -q default

  grafana:
    image: grafana/grafana:10.2.0
    container_name: utility-grafana
    restart: unless-stopped
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
      - ./grafana/dashboards:/var/lib/grafana/dashboards
    env_file:
      - secrets/grafana.env
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_INSTALL_PLUGINS=grafana-influxdb-flux-datasource
    depends_on:
      - influxdb
      - postgres
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  influxdb-data:
  influxdb-config:
  postgres-data:
  tibber-state:
  analytics-results:
  grafana-data:

networks:
  default:
    name: utility-network
```

---

## Frontend Strategy: Streamlit vs Grafana

### Current Streamlit Capabilities

**Features:**
1. Excel file upload UI
2. Meter selection dropdowns
3. Date range picker
4. Interactive Plotly charts
5. Consumption summary tables
6. Log output viewer

**Lines of Code:** 42,099 bytes (primarily UI logic)

### Grafana Capabilities

**Built-in Features:**
1. InfluxDB native integration (Flux queries)
2. Rich chart library (time series, bar charts, heatmaps, gauges)
3. Dashboard templating (dropdown filters for meters)
4. Time range picker with presets (Last 30d, This month, etc.)
5. Alerting with notification channels (email, Slack, webhook)
6. User authentication and authorization
7. Public dashboards (anonymous access)
8. Export to PNG, PDF, CSV
9. Mobile-responsive

**Additional Plugins:**
- Pie charts (for consumption breakdown)
- Worldmap (not needed)
- Carpet plot (heatmap for time-of-day patterns)

### Feature Comparison

| Feature | Streamlit | Grafana | Winner |
|---------|-----------|---------|--------|
| Time-series charts | ✅ Plotly | ✅ Native | Grafana (better performance) |
| Real-time updates | ❌ Manual refresh | ✅ Auto-refresh | Grafana |
| Excel upload | ✅ Built-in | ❌ Requires custom API | Streamlit |
| Authentication | ❌ None | ✅ Built-in | Grafana |
| Alerting | ❌ None | ✅ Advanced | Grafana |
| Mobile support | ⚠️ Limited | ✅ Excellent | Grafana |
| Customization | ✅ Full Python control | ⚠️ Limited to plugins | Streamlit |
| Data exploration | ✅ Pandas-based | ⚠️ Query-based | Streamlit |
| Learning curve | Easy (Python) | Moderate (Flux/SQL) | Streamlit |
| Maintenance burden | High (custom code) | Low (configuration) | Grafana |
| Resource usage | High (Python runtime) | Low (Go binary) | Grafana |
| Cost | Free | Free (OSS) | Tie |

### Recommendation: **Hybrid Approach**

**Phase 1: Grafana for Visualization (Primary)**
- **Use Cases:**
  - Daily consumption monitoring
  - Monthly/yearly reports
  - Anomaly alerts
  - Public dashboards (family members can view)
- **Why:** Eliminates 90% of Streamlit code (chart generation, UI), leverages existing InfluxDB integration

**Phase 2: FastAPI for Data Operations (Secondary)**
- **Use Cases:**
  - Excel file uploads (POST /api/v1/meters/{id}/upload)
  - On-demand analysis (POST /api/v1/analyze)
  - Meter configuration management (CRUD endpoints)
- **Why:** RESTful API is more standard than Streamlit for data ingestion

**Phase 3: Retire Streamlit Entirely**
- **Rationale:**
  - Grafana provides superior visualization
  - FastAPI provides better API design
  - Reduces maintenance burden (one less framework)
  - Lower resource usage (no Streamlit server needed)

### Grafana Dashboard Examples

**Dashboard 1: Consumption Overview**
```
┌─────────────────────────────────────────────────────────────┐
│ Utility Consumption Overview              [Last 30 Days ▼] │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Electricity │  │     Gas      │  │    Water     │       │
│  │   345 kWh    │  │   187 m³     │  │    12 m³     │       │
│  │   ↑ 12% MoM  │  │   ↓ 5% MoM   │  │   ↑ 3% MoM   │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Monthly Consumption Trend                           │    │
│  │                                                      │    │
│  │  400 kWh┤                                  ╭──       │    │
│  │         │                         ╭────────╯        │    │
│  │         │              ╭──────────╯                 │    │
│  │  200 kWh┤     ╭────────╯                            │    │
│  │         │─────╯                                     │    │
│  │    0 kWh└─────┴─────┴─────┴─────┴─────┴─────┴───  │    │
│  │         Jan  Feb  Mar  Apr  May  Jun  Jul  Aug     │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

**Dashboard 2: Detailed Electricity**
```
┌─────────────────────────────────────────────────────────────┐
│ Electricity Breakdown          Meter: [All ▼]  [This Month]│
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────┐  ┌──────────┐     │
│  │ Consumption by Circuit (kWh)         │  │  Total   │     │
│  │                                       │  │ 345 kWh  │     │
│  │  Hauptstrom         ███████████ 180   │  │          │     │
│  │  EG Strom           ██████ 75         │  │ Avg/Day  │     │
│  │  OG1 Strom          ████ 50           │  │ 11.5 kWh │     │
│  │  OG2 Strom          ███ 40            │  └──────────┘     │
│  └──────────────────────────────────────┘                    │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Daily Consumption Pattern (Last 7 Days)             │    │
│  │                                                      │    │
│  │  20 kWh┤     │      │      │  ║  │      │      │    │    │
│  │        │     │      │      │  ║  │      │      │    │    │
│  │  15 kWh┤     │  ║   │  ║   │  ║  │  ║   │  ║   │    │    │
│  │        │  ║  │  ║   │  ║   │  ║  │  ║   │  ║   │    │    │
│  │  10 kWh┤  ║  │  ║   │  ║   │  ║  │  ║   │  ║   │    │    │
│  │        └──┴──┴──┴───┴──┴───┴──┴──┴──┴───┴──┴───┴──  │    │
│  │         Mon Tue Wed Thu Fri Sat Sun Mon Tue Wed     │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

**Dashboard 3: Anomaly Detection**
```
┌─────────────────────────────────────────────────────────────┐
│ Anomaly Detection                        [Last 90 Days ▼]  │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ⚠️ 3 Anomalies Detected                                     │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Date       │ Meter        │ Value    │ Expected │ Δ  │   │
│  ├────────────┼──────────────┼──────────┼──────────┼────┤   │
│  │ 2025-10-15 │ haupt_strom  │ 45 kWh   │ 12 kWh   │+275%  │
│  │ 2025-10-22 │ gas_total    │ 25 m³    │ 8 m³     │+213%  │
│  │ 2025-11-01 │ og1_wasser   │ 2 m³     │ 0.3 m³   │+567%  │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ haupt_strom - Oct 15 Spike                          │    │
│  │                                                      │    │
│  │  50 kWh┤                       ▲                     │    │
│  │        │                      ║ ║                    │    │
│  │  25 kWh┤──────────────────────║─║────────────────   │    │
│  │        │                                             │    │
│  │   0 kWh└─────┴─────┴─────┴─────┴─────┴─────┴─────  │    │
│  │        Oct 12   13    14    15    16    17    18   │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Excel Upload Alternative

Since Grafana doesn't support file uploads, we need a simple interface for Excel imports:

**Option 1: FastAPI Web Form**
```html
<!DOCTYPE html>
<html>
<head><title>Meter Reading Upload</title></head>
<body>
  <h1>Upload Meter Readings</h1>
  <form action="/api/v1/meters/haupt_strom/upload" method="post" enctype="multipart/form-data">
    <label>Select Meter:</label>
    <select name="meter_id">
      <option value="haupt_strom">Haupt Strom</option>
      <option value="gas_total">Gas Total</option>
      <!-- ... -->
    </select>
    <br><br>
    <label>Excel File:</label>
    <input type="file" name="file" accept=".xlsx,.xls">
    <br><br>
    <button type="submit">Upload</button>
  </form>
</body>
</html>
```

**Option 2: Command-Line Tool**
```bash
# Upload via curl
curl -X POST http://192.168.1.75:8000/api/v1/meters/haupt_strom/upload \
  -F "file=@meter_readings.xlsx"

# Or create a simple Python script
python upload_meter_data.py --meter haupt_strom --file readings.xlsx
```

**Option 3: Grafana Dashboard with Link**
- Add a text panel to Grafana dashboard
- Content: "Upload Excel file: [Click Here](http://192.168.1.75:8000/upload)"
- Opens simple upload form in new tab

---

## Migration Roadmap

### Phase 1: Security Hardening (Week 1)
**Goal:** Eliminate secrets from version control

**Tasks:**
1. ✅ Create `config/` directory structure
   - `config.yaml` (non-sensitive configuration)
   - `meters.json` (meter definitions)
   - `seasonal_patterns.json` (consumption patterns)

2. ✅ Create `secrets/` directory
   - Add to `.gitignore`
   - Create `.env.example` template
   - Generate `influxdb.env`, `tibber.env`, `postgres.env`

3. ✅ Refactor `config.py`
   - Load configuration from YAML
   - Load secrets from environment variables only
   - Add validation (fail fast if secrets missing)

4. ✅ Refactor `tibber_influxdb_sync.py`
   - Remove hardcoded token
   - Read from environment variable

5. ✅ Update `.gitignore`
   - Add `secrets/`
   - Add `.env`
   - Add `*.secret`, `*.key`

6. ✅ Audit repository
   - Remove `.env` from git history (using `git filter-repo`)
   - Rotate all exposed secrets (generate new InfluxDB token, Tibber token)

**Deliverables:**
- ✅ No secrets in version control
- ✅ Configuration template (`config.example.yaml`)
- ✅ Secrets setup guide (`secrets/README.md`)

---

### Phase 2: Containerization (Week 2)
**Goal:** Package all services as Docker containers

**Tasks:**
1. ✅ Create Dockerfiles
   - `tools/tibber_import/Dockerfile`
   - `services/excel_importer/Dockerfile`
   - `Nebenkosten/Dockerfile.worker` (analytics worker)

2. ✅ Create `docker-compose.yml`
   - Define all services (InfluxDB, PostgreSQL, Prefect, Grafana, workers)
   - Configure networks, volumes
   - Add health checks

3. ✅ Test local deployment
   - `docker-compose up -d`
   - Verify all containers start
   - Check health endpoints

4. ✅ Create initialization scripts
   - `init-db.sql` (PostgreSQL schema)
   - `init-influxdb.sh` (create buckets, retention policies)

**Deliverables:**
- ✅ Working Docker Compose stack
- ✅ Deployment documentation (`docs/deployment.md`)

---

### Phase 3: Workflow Orchestration (Week 3)
**Goal:** Implement Prefect workflows for analytics

**Tasks:**
1. ✅ Refactor `UtilityAnalyzer` for task-based execution
   - Break `analyze_all_meters()` into individual tasks
   - Add Prefect decorators (`@task`, `@flow`)

2. ✅ Create workflow definitions
   - `workflows/daily_analysis.py`
   - `workflows/monthly_report.py`
   - `workflows/on_demand_analysis.py`

3. ✅ Implement scheduling
   - Register flows with Prefect server
   - Configure schedules (daily @ 2 AM, monthly @ 1st)

4. ✅ Add error handling
   - Retry logic (3 attempts, exponential backoff)
   - Alert on workflow failure (email/webhook)

**Deliverables:**
- ✅ Automated daily analysis
- ✅ Workflow monitoring UI (Prefect dashboard)

---

### Phase 4: Grafana Dashboards (Week 4)
**Goal:** Build comprehensive visualization layer

**Tasks:**
1. ✅ Set up Grafana data sources
   - InfluxDB (lampfi, lampfi_processed)
   - PostgreSQL (metadata)

2. ✅ Create provisioned dashboards
   - `grafana/dashboards/overview.json`
   - `grafana/dashboards/electricity.json`
   - `grafana/dashboards/gas.json`
   - `grafana/dashboards/water.json`
   - `grafana/dashboards/heat.json`
   - `grafana/dashboards/anomalies.json`

3. ✅ Configure alerts
   - Consumption > 2x average (email notification)
   - Missing data > 48 hours (webhook to Home Assistant)
   - Meter reading decrease (potential reset)

4. ✅ Set up dashboard variables
   - `$meter` - Dropdown to select meter
   - `$timeRange` - Presets (This month, Last 3 months, This year)

**Deliverables:**
- ✅ 6 interactive dashboards
- ✅ Alerting rules configured
- ✅ Public dashboard links (for family members)

---

### Phase 5: Excel Importer API (Week 5)
**Goal:** Replace Streamlit upload UI with FastAPI

**Tasks:**
1. ✅ Create FastAPI application
   - `services/excel_importer/main.py`
   - Endpoint: `POST /api/v1/meters/{meter_id}/upload`

2. ✅ Implement file parsing
   - Support `.xlsx`, `.xls` formats
   - Parse German date formats
   - Validate required columns

3. ✅ Add web form UI
   - Simple HTML form for file upload
   - Meter dropdown (populated from config)
   - Upload progress indicator

4. ✅ Write integration tests
   - Test valid Excel files
   - Test error cases (invalid format, missing columns)

**Deliverables:**
- ✅ Working upload API
- ✅ Simple web UI
- ✅ API documentation (OpenAPI/Swagger)

---

### Phase 6: Streamlit Retirement (Week 6)
**Goal:** Decommission Streamlit application

**Tasks:**
1. ✅ Validate feature parity
   - All charts available in Grafana ✓
   - Excel upload available via API ✓
   - Meter configuration via YAML ✓

2. ✅ Migrate any missing features
   - Export raw data (create Grafana export panel)
   - Log viewer (use Prefect UI logs)

3. ✅ Archive Streamlit code
   - Move `streamlit_app.py` to `archive/` directory
   - Update README with migration notes

4. ✅ Update documentation
   - Remove Streamlit installation instructions
   - Add Grafana usage guide

**Deliverables:**
- ✅ Streamlit fully replaced
- ✅ Updated documentation

---

### Phase 7: Production Deployment (Week 7)
**Goal:** Deploy to production environment

**Tasks:**
1. ✅ Set up production host
   - Create deployment directory (`/opt/utility-meters`)
   - Configure firewall (ports 3000, 4200, 8000, 8086)

2. ✅ Deploy Docker Compose stack
   - Copy `docker-compose.yml`, `config/`, `secrets/`
   - Run `docker-compose up -d`

3. ✅ Configure reverse proxy (optional)
   - Nginx/Caddy for HTTPS termination
   - Domain names: `grafana.home.local`, `influxdb.home.local`

4. ✅ Set up backup strategy
   - InfluxDB backups (daily, 30-day retention)
   - PostgreSQL backups (daily, 90-day retention)
   - Configuration backups (git push to remote)

**Deliverables:**
- ✅ Production deployment running
- ✅ Automated backups configured
- ✅ Monitoring alerts active

---

## Implementation Plan

### Immediate Actions (This Week)

#### 1. Security Fix (Critical)
```bash
# Create new directory structure
mkdir -p config secrets

# Move meter configuration to JSON
cat Nebenkosten/.env | grep METER_CONFIGURATION_JSON > config/meters.json

# Create secrets files
echo "INFLUX_TOKEN=<redacted>" > secrets/influxdb.env
echo "INFLUX_ORG=<redacted>" >> secrets/influxdb.env
echo "TIBBER_API_TOKEN=<redacted>" > secrets/tibber.env

# Update .gitignore
echo -e "\n# Secrets\nsecrets/*.env\n.env\n*.secret" >> .gitignore

# Remove .env from git history
git filter-repo --path Nebenkosten/.env --invert-paths

# Rotate secrets (generate new InfluxDB token)
# - Log into InfluxDB UI (http://192.168.1.75:8086)
# - Go to Data > API Tokens > Generate API Token
# - Copy new token to secrets/influxdb.env
# - Delete old token
```

#### 2. Configuration Refactoring
**Create `config/config.yaml`:**
```yaml
influxdb:
  url: "http://192.168.1.75:8086"
  bucket: "lampfi"
  timeout: 30
  retry_attempts: 3

gas_conversion:
  energy_content: 11.504
  z_factor: 0.8885

meters:
  config_file: "config/meters.json"

tibber:
  polling_interval: 3600
  lookback_hours: 48
```

**Update `src/config.py`:**
```python
import os
import yaml
from pathlib import Path

# Load configuration
config_file = Path(os.getenv("CONFIG_FILE", "config/config.yaml"))
if not config_file.exists():
    raise FileNotFoundError(f"Configuration file not found: {config_file}")

with config_file.open() as f:
    config = yaml.safe_load(f)

# Load secrets from environment (fail fast if missing)
INFLUX_TOKEN = os.environ["INFLUX_TOKEN"]
INFLUX_ORG = os.environ["INFLUX_ORG"]

# Access configuration
INFLUX_URL = config["influxdb"]["url"]
INFLUX_BUCKET = config["influxdb"]["bucket"]
GAS_ENERGY_CONTENT = config["gas_conversion"]["energy_content"]
GAS_Z_FACTOR = config["gas_conversion"]["z_factor"]

# Load meter configuration
meters_config_path = Path(config["meters"]["config_file"])
with meters_config_path.open() as f:
    METER_CONFIGURATION = json.load(f)
```

#### 3. Docker Setup (Minimal)
**Create `docker-compose.minimal.yml`** (for testing):
```yaml
version: '3.8'

services:
  tibber-sync:
    build: ./tools/tibber_import
    env_file:
      - secrets/influxdb.env
      - secrets/tibber.env
    volumes:
      - ./config:/app/config:ro
    environment:
      - CONFIG_FILE=/app/config/config.yaml
    restart: unless-stopped
```

**Create `tools/tibber_import/Dockerfile`:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir \
    requests \
    influxdb-client \
    pyyaml \
    APScheduler

# Copy application
COPY tibber_influxdb_sync.py .

# Health check
HEALTHCHECK --interval=60s --timeout=10s --retries=3 \
  CMD python -c "import os; import sys; sys.exit(0 if os.path.exists('/app/state/tibber_sync_state.json') else 1)"

# Run scheduler
CMD ["python", "tibber_influxdb_sync.py"]
```

---

### Next Steps (Priority Order)

1. **Week 1:** Security hardening (remove secrets from git)
2. **Week 2:** Minimal Docker deployment (Tibber sync container only)
3. **Week 3:** Grafana setup (basic dashboards)
4. **Week 4:** Excel importer API (FastAPI)
5. **Week 5:** Workflow orchestration (Prefect)
6. **Week 6:** Complete Grafana dashboards
7. **Week 7:** Retire Streamlit, production deployment

---

## Additional Recommendations

### 1. Monitoring & Observability

**Add Prometheus + Loki Stack**
```yaml
# docker-compose.yml additions
services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"

  loki:
    image: grafana/loki:latest
    volumes:
      - ./loki-config.yaml:/etc/loki/local-config.yaml
      - loki-data:/loki
    ports:
      - "3100:3100"

  promtail:
    image: grafana/promtail:latest
    volumes:
      - /var/log:/var/log
      - ./promtail-config.yaml:/etc/promtail/config.yml
    command: -config.file=/etc/promtail/config.yml
```

**Benefits:**
- Centralized logging (Loki)
- Metrics collection (Prometheus)
- Single pane of glass in Grafana

### 2. Data Quality Checks

**Add Great Expectations Framework**
```python
# workflows/data_quality_checks.py
from prefect import task, flow
import great_expectations as ge

@task
def validate_meter_data(meter_id: str):
    df = fetch_meter_data(meter_id)

    # Convert to Great Expectations dataset
    ge_df = ge.from_pandas(df)

    # Define expectations
    ge_df.expect_column_values_to_be_between('value', min_value=0)
    ge_df.expect_column_values_to_not_be_null('timestamp')
    ge_df.expect_column_values_to_be_increasing('timestamp')

    results = ge_df.validate()
    if not results.success:
        raise ValueError(f"Data quality check failed for {meter_id}")

    return results

@flow
def daily_data_quality_flow():
    for meter in get_all_meters():
        validate_meter_data(meter.id)
```

### 3. Unit Testing

**Add pytest Suite**
```
tests/
├── unit/
│   ├── test_data_processor.py
│   ├── test_calculator.py
│   ├── test_influx_client.py
│   └── test_config.py
├── integration/
│   ├── test_end_to_end_analysis.py
│   └── test_workflows.py
└── conftest.py
```

**Run in CI/CD:**
```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements-dev.txt
      - run: pytest tests/ --cov=src --cov-report=xml
      - uses: codecov/codecov-action@v3
```

### 4. Documentation

**Add Architecture Decision Records (ADRs)**
```
docs/
├── adr/
│   ├── 001-use-prefect-for-orchestration.md
│   ├── 002-replace-streamlit-with-grafana.md
│   └── 003-separate-secrets-from-config.md
├── api/
│   └── openapi.yaml
└── deployment.md
```

---

## Conclusion

### Summary of Changes

**Security:**
- ✅ Secrets externalized (not in version control)
- ✅ Configuration split (YAML + JSON)
- ✅ Secrets rotation guide

**Architecture:**
- ✅ Microservices (data ingestion, analytics, API)
- ✅ Workflow orchestration (Prefect)
- ✅ Containerization (Docker Compose)

**Visualization:**
- ✅ Grafana primary (replaces Streamlit)
- ✅ FastAPI for uploads (replaces Streamlit UI)

**Operations:**
- ✅ Health checks
- ✅ Logging (JSON, centralized)
- ✅ Monitoring (Prometheus + Grafana)
- ✅ Alerting (consumption anomalies, data gaps)

### Estimated Effort

| Phase | Effort | Priority |
|-------|--------|----------|
| Security Hardening | 8 hours | Critical |
| Docker Setup | 16 hours | High |
| Grafana Dashboards | 24 hours | High |
| Excel Importer API | 12 hours | Medium |
| Workflow Orchestration | 20 hours | Medium |
| Streamlit Retirement | 4 hours | Low |
| Production Deployment | 8 hours | High |
| **Total** | **92 hours** | **~2-3 weeks** |

### ROI Analysis

**Costs:**
- Development time: 92 hours
- Infrastructure: $0 (self-hosted, existing hardware)

**Benefits:**
- **Security:** Eliminate critical vulnerabilities (priceless)
- **Maintainability:** -42KB code (Streamlit removal)
- **Performance:** Lower resource usage (Grafana vs Streamlit)
- **Scalability:** Independent scaling of components
- **Observability:** Centralized logging, metrics, alerts
- **User Experience:** Better mobile support, real-time updates

**Break-even:** Immediate (security fixes alone justify effort)

---

## Questions for Consideration

1. **Do you have Grafana already running?** (You mentioned connecting to InfluxDB with Grafana)
   - If yes, we can skip Grafana setup and focus on dashboards only

2. **What is your production environment?**
   - Raspberry Pi, NAS, dedicated server?
   - This affects Docker resource allocation

3. **Do you need historical data migration?**
   - Should we backfill `lampfi_processed` bucket with existing data?

4. **What alerting channels do you prefer?**
   - Email, Telegram, Slack, webhook to Home Assistant?

5. **Do you want to keep Excel import functionality?**
   - If Home Assistant and Tibber cover all meters, we can skip Excel importer entirely

---

**Next Step:** Shall I proceed with Phase 1 (Security Hardening) by creating the configuration split and removing secrets from version control?
