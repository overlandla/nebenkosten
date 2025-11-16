# Utility Meter Analytics System

Modern, Dagster-based workflow system for home utility meter monitoring and analysis.

[![Dagster](https://img.shields.io/badge/Dagster-Latest-blue)](https://dagster.io/)
[![Docker](https://img.shields.io/badge/Docker-Ready-green)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://www.python.org/)

---

## Overview

This system processes electricity, gas, water, and heat meter readings from InfluxDB, performs intelligent interpolation and gap-filling, handles meter replacements seamlessly, calculates consumption patterns, and detects anomalies - all orchestrated with Dagster workflows and ready for Docker deployment on your home NAS.

### Key Features

- ✅ **Dagster Workflow Orchestration** - Modern data orchestration with comprehensive web UI
- ✅ **Multi-Meter Support** - Physical, master (combined), and virtual (calculated) meters
- ✅ **Intelligent Interpolation** - Statistical gap-filling using seasonal patterns
- ✅ **Meter Replacement Handling** - Seamless transition between old and new meters
- ✅ **Tibber Integration** - Automatic hourly sync of electricity prices and consumption
- ✅ **Anomaly Detection** - Automatic flagging of unusual consumption patterns
- ✅ **Docker Deployment** - Production-ready containers for NAS deployment
- ✅ **Structured Logging** - JSON logs with timestamps, levels, and context
- ✅ **Security Hardened** - Secrets separated from configuration
- ✅ **Asset-based Architecture** - Software-defined assets with automatic dependency tracking

---

## Quick Start

### Option 1: Proxmox LXC Deployment (Recommended)

For Proxmox users, we provide simple Makefile-based installation:

**Dashboard:**
```bash
# On Proxmox host, create LXC
pct create 110 local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst \
  --hostname utility-dashboard --cores 2 --memory 2048 --rootfs local-lvm:4 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp --unprivileged 1 --features nesting=1

# Inside LXC
pct enter 110
apt-get update && apt-get install -y git make
git clone https://github.com/overlandla/nebenkosten.git
cd nebenkosten
make install-dashboard
```

**Dagster Workflows:**
```bash
# On Proxmox host, create LXC
pct create 111 local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst \
  --hostname dagster-workflows --cores 2 --memory 4096 --rootfs local-lvm:8 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp --unprivileged 1 --features nesting=1

# Inside LXC
pct enter 111
apt-get update && apt-get install -y git make
git clone https://github.com/overlandla/nebenkosten.git
cd nebenkosten
make install-dagster
```

See [dashboard/PROXMOX_INSTALLATION.md](dashboard/PROXMOX_INSTALLATION.md) and [workflows_dagster/PROXMOX_INSTALLATION.md](workflows_dagster/PROXMOX_INSTALLATION.md) for details.

### Option 2: Docker Deployment

For Docker/NAS deployment:

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
# Start Dagster services
docker-compose -f docker-compose.dagster.yml up -d
```

### 6. Access Dagster UI

Open browser: `http://your-nas-ip:3000`

---

## Documentation

| Document | Purpose | Start Here |
|----------|---------|------------|
| **[workflows-dagster/README.md](workflows-dagster/README.md)** | Dagster implementation details | ⭐ **YES** |
| **[SIMPLIFIED_ARCHITECTURE.md](SIMPLIFIED_ARCHITECTURE.md)** | Architecture details, data flow | For understanding |

---

## Architecture

```
┌───────────────────────────────────────────────┐
│      Dagster Daemon + Webserver              │
│  • Web UI for workflow monitoring            │
│  • Asset materialization tracking            │
│  • Schedule execution                         │
│  • Sensor-based triggering                    │
└───────────────────────────────────────────────┘
                    │
                    ▼
┌───────────────────────────────────────────────┐
│      Dagster Code Location                    │
│                                                │
│  Assets:                                       │
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
│  • lampfi_processed (results)                 │
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
docker-compose -f docker-compose.dagster.yml up -d

# Stop services
docker-compose -f docker-compose.dagster.yml down

# View logs
docker-compose -f docker-compose.dagster.yml logs -f

# Check status
docker-compose -f docker-compose.dagster.yml ps

# Run integration tests
./test-dagster-docker.sh

# Enter code location shell
docker exec -it dagster-code-location /bin/bash
```

---

## Monitoring

### Dagster UI

**URL:** http://your-nas-ip:3000

- Asset Catalog - View all data assets and their dependencies
- Runs - Detailed execution history
- Schedules - View and trigger scheduled jobs
- Sensors - Monitor event-based triggers

### Docker Logs

```bash
# All logs
docker-compose -f docker-compose.dagster.yml logs -f

# Code location logs only
docker-compose -f docker-compose.dagster.yml logs -f dagster-code-location

# Search for errors
docker-compose -f docker-compose.dagster.yml logs | grep ERROR
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
docker-compose -f docker-compose.dagster.yml logs

# Verify secrets exist
ls -la secrets/

# Restart
docker-compose -f docker-compose.dagster.yml down && docker-compose -f docker-compose.dagster.yml up -d
```

### Job fails with "secrets not set"

```bash
# Check environment
docker exec dagster-code-location env | grep INFLUX

# Recreate containers
docker-compose -f docker-compose.dagster.yml down && docker-compose -f docker-compose.dagster.yml up -d
```

### No data in lampfi_processed

```bash
# Check bucket exists (InfluxDB UI > Data > Buckets)
# Trigger manual run (Dagster UI > Assets > Materialize)
# Check code location logs
docker-compose -f docker-compose.dagster.yml logs dagster-code-location | grep "Writing results"
```

---

## Maintenance

- **Daily:** Check Dagster UI for failed runs
- **Weekly:** Review logs for errors
- **Monthly:** Update images, backup config
- **Annually:** Rotate secrets

---

## Performance

- **Tibber sync:** 5-10 seconds per run
- **Analytics (27 meters, 4 years):** 2-5 minutes per run
- **Resource usage:** 200-600 MB RAM, <30% CPU peak

---

## Support

**Getting Started:** Read [workflows-dagster/README.md](workflows-dagster/README.md)
**Monitoring:** Access Dagster UI at http://your-nas-ip:3000

---

**Status:** ✅ Production Ready
**Version:** 3.0.0 (Dagster-based)
**Last Updated:** 2025-11-15
