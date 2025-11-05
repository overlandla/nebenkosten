# Utility Meter Analytics System

Modern, Prefect-based workflow system for home utility meter monitoring and analysis.

[![Prefect](https://img.shields.io/badge/Prefect-2.14-blue)](https://www.prefect.io/)
[![Docker](https://img.shields.io/badge/Docker-Ready-green)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://www.python.org/)

---

## Overview

This system processes electricity, gas, water, and heat meter readings from InfluxDB, performs intelligent interpolation and gap-filling, handles meter replacements seamlessly, calculates consumption patterns, and detects anomalies - all orchestrated with Prefect workflows and ready for Docker deployment on your home NAS.

### Key Features

- ✅ **Prefect Workflow Orchestration** - Scheduled workflows with web UI monitoring
- ✅ **Multi-Meter Support** - Physical, master (combined), and virtual (calculated) meters
- ✅ **Intelligent Interpolation** - Statistical gap-filling using seasonal patterns
- ✅ **Meter Replacement Handling** - Seamless transition between old and new meters
- ✅ **Tibber Integration** - Automatic hourly sync of electricity prices and consumption
- ✅ **Anomaly Detection** - Automatic flagging of unusual consumption patterns
- ✅ **Docker Deployment** - Production-ready containers for NAS deployment
- ✅ **Structured Logging** - JSON logs with timestamps, levels, and context
- ✅ **Security Hardened** - Secrets separated from configuration
- ✅ **No Streamlit/Frontend** - Data written to InfluxDB for Grafana visualization

---

## Quick Start

### Prerequisites

- Docker & Docker Compose installed on NAS
- InfluxDB v2 running (existing)
- Grafana running (existing, optional)

### 1. Clone Repository

```bash
git clone <your-repo-url> utility-meters
cd utility-meters
```

### 2. Create Secrets

```bash
# InfluxDB credentials
cat > secrets/influxdb.env <<SECRETS
INFLUX_TOKEN=your_influxdb_api_token
INFLUX_ORG=your_influxdb_org_id
SECRETS

# Tibber API token (optional)
cat > secrets/tibber.env <<SECRETS
TIBBER_API_TOKEN=your_tibber_api_token
SECRETS

chmod 600 secrets/*.env
```

### 3. Configure

Edit `config/config.yaml`:
```yaml
influxdb:
  url: "http://192.168.1.75:8086"  # <-- Change to your InfluxDB IP
```

### 4. Create InfluxDB Bucket

```bash
# In InfluxDB UI: Data > Buckets > Create Bucket
# Name: lampfi_processed
# Retention: Infinite
```

### 5. Deploy

```bash
docker-compose up -d
```

### 6. Access Prefect UI

Open browser: `http://your-nas-ip:4200`

---

## Documentation

| Document | Purpose | Start Here |
|----------|---------|------------|
| **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** | What was built, how it works, next steps | ⭐ **YES** |
| **[DEPLOYMENT.md](DEPLOYMENT.md)** | Complete deployment guide (200+ lines) | For deployment |
| **[SIMPLIFIED_ARCHITECTURE.md](SIMPLIFIED_ARCHITECTURE.md)** | Architecture details, data flow | For understanding |
| **[ARCHITECTURE_REVIEW.md](ARCHITECTURE_REVIEW.md)** | Security analysis, recommendations | For reference |

---

## Architecture

```
┌───────────────────────────────────────────────┐
│      Prefect Server (Port 4200)               │
│  • Web UI for workflow monitoring             │
│  • Scheduling engine                          │
│  • SQLite backend (no PostgreSQL needed)      │
└───────────────────────────────────────────────┘
                    │
                    ▼
┌───────────────────────────────────────────────┐
│      Prefect Worker                           │
│                                                │
│  Workflows:                                    │
│  1. Tibber Sync (Hourly)                      │
│     - Fetch from Tibber API                   │
│     - Write to InfluxDB                       │
│                                                │
│  2. Analytics (Daily @ 2 AM)                  │
│     - Fetch raw meter data                    │
│     - Interpolate & process                   │
│     - Calculate consumption                   │
│     - Detect anomalies                        │
│     - Write to lampfi_processed               │
└───────────────────────────────────────────────┘
                    │
                    ▼
┌───────────────────────────────────────────────┐
│      InfluxDB (Your Existing Instance)        │
│  • lampfi (raw readings)                      │
│  • lampfi_processed (results) ← NEW           │
└───────────────────────────────────────────────┘
                    │
                    ▼
┌───────────────────────────────────────────────┐
│      Grafana (Your Existing Instance)         │
│  Connect to lampfi_processed                  │
└───────────────────────────────────────────────┘
```

---

## Quick Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# Check status
docker-compose ps

# Manual flow run
docker exec utility-prefect-worker python /app/workflows/analytics_flow.py

# Enter worker shell
docker exec -it utility-prefect-worker /bin/bash
```

---

## Monitoring

### Prefect UI

**URL:** http://your-nas-ip:4200

- Dashboard - Recent flow runs
- Flow Runs - Detailed execution history
- Deployments - View schedules, trigger manual runs

### Docker Logs

```bash
# All logs
docker-compose logs -f

# Worker logs only
docker-compose logs -f prefect-worker

# Search for errors
docker-compose logs | grep ERROR
```

---

## Grafana Integration

### Example Queries

**Monthly consumption:**
```flux
from(bucket: "lampfi_processed")
  |> range(start: -1y)
  |> filter(fn: (r) => r["_measurement"] == "meter_consumption")
  |> filter(fn: (r) => r["meter_id"] == "strom_total")
```

**Anomalies:**
```flux
from(bucket: "lampfi_processed")
  |> range(start: -30d)
  |> filter(fn: (r) => r["_measurement"] == "meter_anomaly")
```

---

## Troubleshooting

### Container won't start

```bash
# Check logs
docker-compose logs

# Verify secrets exist
ls -la secrets/

# Restart
docker-compose down && docker-compose up -d
```

### Flow fails with "secrets not set"

```bash
# Check environment
docker exec utility-prefect-worker env | grep INFLUX

# Recreate containers
docker-compose down && docker-compose up -d
```

### No data in lampfi_processed

```bash
# Check bucket exists (InfluxDB UI > Data > Buckets)
# Trigger manual run (Prefect UI > Deployments > analytics-scheduled > Run)
# Check worker logs
docker-compose logs prefect-worker | grep "Writing results"
```

**For more:** See [DEPLOYMENT.md](DEPLOYMENT.md) - "Troubleshooting" section

---

## Maintenance

- **Daily:** Check Prefect UI for failed runs
- **Weekly:** Review logs for errors
- **Monthly:** Update images, backup config
- **Annually:** Rotate secrets

---

## Performance

- **Tibber sync:** 5-10 seconds per run
- **Analytics (27 meters, 4 years):** 2-5 minutes per run
- **Resource usage:** 150-500 MB RAM, <30% CPU peak

---

## Support

**Getting Started:** Read [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)  
**Deployment:** Follow [DEPLOYMENT.md](DEPLOYMENT.md)  
**Monitoring:** Access Prefect UI at http://your-nas-ip:4200

---

**Status:** ✅ Production Ready  
**Version:** 2.0.0 (Prefect-based)  
**Last Updated:** 2025-11-05
