# Utility Meter Analytics System

Complete home utility monitoring solution combining **Dagster data pipelines** with a **Next.js dashboard** for processing, analyzing, and visualizing electricity, gas, water, and heat meter data.

[![Dagster](https://img.shields.io/badge/Dagster-1.10.16-blue)](https://dagster.io/)
[![Next.js](https://img.shields.io/badge/Next.js-16.0.3-black)](https://nextjs.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-green)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://www.python.org/)

---

## Overview

A production-ready system for multi-unit building utility management, featuring:

- 🔄 **Dagster Workflows** - Backend data processing, interpolation, anomaly detection, and API integration
- 📊 **Next.js Dashboard** - Modern web interface for real-time visualization and cost analysis
- 📈 **39 Meters Supported** - Electricity, gas, water, heat, solar, and environmental sensors
- 🏢 **Multi-Household Support** - Track and allocate costs across multiple units/floors
- 💰 **Cost Integration** - Tibber API integration for real-time electricity pricing
- 🔍 **Anomaly Detection** - Multi-method statistical analysis for unusual consumption patterns

### How They Work Together

```
┌──────────────┐
│ Meter Sources│
│ - Physical   │
│ - Tibber API │
│ - Sensors    │
└──────┬───────┘
       │
       ▼
┌─────────────────────────────────────┐
│    Dagster Workflows (Backend)      │
│  ┌──────────────────────────────┐   │
│  │ • Data Ingestion             │   │
│  │ • Interpolation & Gap Fill   │   │
│  │ • Master/Virtual Meters      │   │
│  │ • Consumption Calculation    │   │
│  │ • Anomaly Detection          │   │
│  └──────────────────────────────┘   │
└─────────────┬───────────────────────┘
              │
              ▼
       ┌─────────────┐
       │  InfluxDB   │
       │  Processed  │
       │    Data     │
       └──────┬──────┘
              │
              ▼
┌─────────────────────────────────────┐
│   Next.js Dashboard (Frontend)      │
│  ┌──────────────────────────────┐   │
│  │ • Real-time Visualization    │   │
│  │ • Multi-household View       │   │
│  │ • Cost Analysis & Allocation │   │
│  │ • Anomaly Alerts             │   │
│  │ • Export & Reporting         │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
```

### Key Features

#### Backend (Dagster Workflows)
- ✅ **Workflow Orchestration** - Modern data orchestration with comprehensive web UI
- ✅ **Multi-Meter Support** - Physical, master (combined), and virtual (calculated) meters
- ✅ **Intelligent Interpolation** - Statistical gap-filling using seasonal patterns
- ✅ **Meter Replacement Handling** - Seamless transition between old and new meters
- ✅ **Tibber Integration** - Automatic hourly sync of electricity prices and consumption
- ✅ **Anomaly Detection** - Multi-method statistical analysis (Z-score, IQR, rolling)
- ✅ **95 Comprehensive Tests** - Unit and integration tests for all critical paths

#### Frontend (Next.js Dashboard)
- ✅ **Real-time Visualization** - Recharts-based interactive charts
- ✅ **Household Management** - Multi-unit cost tracking and allocation
- ✅ **Time Range Selection** - Flexible date range picker with presets
- ✅ **Cost Analysis** - Tibber cost integration and breakdown
- ✅ **Responsive Design** - Mobile-friendly, works on all devices
- ✅ **Type Safe** - Full TypeScript with centralized type definitions

#### Infrastructure
- ✅ **Docker Deployment** - Production-ready containers for NAS deployment
- ✅ **Systemd Services** - Native service management for Proxmox LXC
- ✅ **Security Hardened** - Secrets separated from configuration
- ✅ **Structured Logging** - JSON logs with timestamps, levels, and context

---

## Quick Start

You'll need to deploy **both components** for a complete solution:
1. **Dagster workflows** (backend processing)
2. **Next.js dashboard** (frontend visualization)

### Option 1: Proxmox LXC Deployment (Recommended)

Deploy in separate LXC containers for isolation and easy management.

#### Step 1: Deploy Dagster Workflows (Backend)

```bash
# On Proxmox host, create LXC for Dagster
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

**Access:** Dagster UI at `http://<dagster-lxc-ip>:3000`

See [workflows_dagster/PROXMOX_INSTALLATION.md](workflows_dagster/PROXMOX_INSTALLATION.md) for detailed setup.

#### Step 2: Deploy Next.js Dashboard (Frontend)

```bash
# On Proxmox host, create LXC for Dashboard
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

**Access:** Dashboard at `http://<dashboard-lxc-ip>:3001`

See [dashboard/PROXMOX_INSTALLATION.md](dashboard/PROXMOX_INSTALLATION.md) for detailed setup.

### Option 2: Docker Deployment

For Docker/NAS deployment of both components:

#### Prerequisites

- Docker & Docker Compose installed
- InfluxDB v2 running
- Node.js 18+ (for dashboard)

#### Step 1: Deploy Dagster Workflows

```bash
# Clone repository
git clone https://github.com/overlandla/nebenkosten.git
cd nebenkosten

# Create secrets
cat > secrets/influxdb.env <<SECRETS
INFLUX_TOKEN=your_influxdb_api_token
INFLUX_ORG=your_influxdb_org_id
SECRETS

cat > secrets/tibber.env <<SECRETS
TIBBER_API_TOKEN=your_tibber_api_token
SECRETS

chmod 600 secrets/*.env

# Configure InfluxDB connection
# Edit config/config.yaml with your InfluxDB URL

# Start Dagster
docker-compose -f docker-compose.dagster.yml up -d
```

**Access:** Dagster UI at `http://localhost:3000`

#### Step 2: Deploy Next.js Dashboard

```bash
cd dashboard

# Configure environment
cp .env.example .env.local
# Edit .env.local with your InfluxDB credentials

# Install and build
npm install
npm run build

# Run in production
npm start
```

**Access:** Dashboard at `http://localhost:3001`

---

## Documentation

### 📚 Component Documentation

| Component | Document | Description |
|-----------|----------|-------------|
| **Backend** | [workflows_dagster/README.md](workflows_dagster/README.md) | Dagster workflows, assets, testing guide ⭐ |
| **Backend** | [workflows_dagster/TESTING.md](workflows_dagster/TESTING.md) | Comprehensive testing documentation |
| **Backend** | [workflows_dagster/QUICKSTART_PROXMOX.md](workflows_dagster/QUICKSTART_PROXMOX.md) | Proxmox LXC installation for Dagster |
| **Frontend** | [dashboard/README.md](dashboard/README.md) | Next.js dashboard features and setup ⭐ |
| **Frontend** | [dashboard/PROXMOX_INSTALLATION.md](dashboard/PROXMOX_INSTALLATION.md) | Proxmox LXC installation for dashboard |
| **Frontend** | [dashboard/TEST_COVERAGE.md](dashboard/TEST_COVERAGE.md) | Dashboard testing status and plans |
| **Config** | [secrets/README.md](secrets/README.md) | Secrets and environment configuration |

### 🎯 Quick Links

- **Getting Started:** Follow [Quick Start](#quick-start) above
- **Dagster UI:** Monitor workflows at `http://<dagster-ip>:3000`
- **Dashboard:** View metrics at `http://<dashboard-ip>:3001`
- **InfluxDB:** Configure connection in `config/config.yaml` and `dashboard/.env.local`

---

## Architecture

### Complete System Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                     DATA SOURCES                               │
│  • Physical Meters (InfluxDB: lampfi bucket)                   │
│  • Tibber API (electricity prices & consumption)               │
│  • Water Temperature Sensors (Bavarian lakes)                  │
└────────────────────────┬───────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────────┐
│              DAGSTER WORKFLOWS (Backend)                       │
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐ │
│  │ Tibber Sync      │  │ Water Temp Sync  │  │ Analytics    │ │
│  │ (Hourly)         │  │ (Daily)          │  │ (Daily 2 AM) │ │
│  └──────────────────┘  └──────────────────┘  └──────────────┘ │
│                                                                 │
│  Processing Pipeline:                                          │
│  1. Data Ingestion from APIs and InfluxDB                      │
│  2. Interpolation (gap-filling, extrapolation)                 │
│  3. Master Meters (combine meter replacements)                 │
│  4. Virtual Meters (calculated consumption)                    │
│  5. Consumption Calculation (daily/monthly)                    │
│  6. Anomaly Detection (3-method consensus)                     │
│                                                                 │
│  Output: Processed data to InfluxDB                            │
└────────────────────────┬───────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────────┐
│                    INFLUXDB (Data Store)                       │
│  • lampfi (raw meter readings)                                 │
│  • lampfi_processed (processed data)                           │
│    - meter_interpolated_daily                                  │
│    - meter_interpolated_monthly                                │
│    - meter_consumption                                         │
│    - meter_anomaly                                             │
│    - tibber_consumption / tibber_costs                         │
│    - water_temperature                                         │
└────────────────────────┬───────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────────┐
│              NEXT.JS DASHBOARD (Frontend)                      │
│                                                                 │
│  Features:                                                     │
│  • Real-time meter visualization (39 meters)                   │
│  • Multi-household cost allocation                             │
│  • Electricity, gas, water, heat charts                        │
│  • Tibber cost analysis                                        │
│  • Anomaly alerts and notifications                            │
│  • Time range selection (7d / 30d / 3mo / 1yr / custom)        │
│  • Responsive design (mobile + desktop)                        │
│                                                                 │
│  Tech Stack: Next.js 16 + React 19 + TypeScript + Recharts    │
└────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Ingestion:** Dagster fetches data from Tibber API, sensors, and InfluxDB raw bucket
2. **Processing:** Smart interpolation, meter combination, consumption calculation
3. **Storage:** Processed data written to InfluxDB `lampfi_processed` bucket
4. **Visualization:** Next.js dashboard queries processed data for real-time charts
5. **Analysis:** Users view consumption trends, costs, and anomalies in the dashboard

---

## Quick Commands

### Dagster Workflows (Backend)

```bash
# Start Dagster services
docker-compose -f docker-compose.dagster.yml up -d

# Stop Dagster services
docker-compose -f docker-compose.dagster.yml down

# View Dagster logs
docker-compose -f docker-compose.dagster.yml logs -f

# Check Dagster status
docker-compose -f docker-compose.dagster.yml ps

# Run Dagster tests
cd workflows_dagster && pytest

# Access Dagster container
docker exec -it dagster-code-location /bin/bash
```

### Next.js Dashboard (Frontend)

```bash
# Development mode
cd dashboard && npm run dev

# Production build
cd dashboard && npm run build && npm start

# Run linting
cd dashboard && npm run lint

# View dashboard logs (if using systemd)
journalctl -u utility-dashboard -f
```

### Combined Operations

```bash
# Start both services (requires separate terminals or use systemd)
docker-compose -f docker-compose.dagster.yml up -d  # Dagster
cd dashboard && npm start &                          # Dashboard

# View all logs
docker-compose -f docker-compose.dagster.yml logs -f &  # Dagster logs
cd dashboard && npm run dev                              # Dashboard logs (dev mode)
```

---

## Monitoring

### Dagster UI (Backend Monitoring)

**URL:** `http://<dagster-host>:3000`

- **Asset Catalog** - View all 39 meters and their processing status
- **Runs** - Detailed execution history with logs
- **Schedules** - Daily analytics (2 AM), hourly Tibber sync
- **Sensors** - Failure detection, anomaly alerts
- **Logs** - Structured JSON logs with context

### Next.js Dashboard (User Interface)

**URL:** `http://<dashboard-host>:3001`

- **Real-time Charts** - Electricity, gas, water, heat visualization
- **Cost Analysis** - Tibber cost breakdown and allocation
- **Anomaly Alerts** - Visual indicators for unusual consumption
- **Household View** - Multi-unit tracking and cost sharing
- **Time Ranges** - Flexible date selection (7d to custom)

### Health Checks

```bash
# Check Dagster is running
curl http://localhost:3000/server_info

# Check Dashboard is running
curl http://localhost:3001/api/meters

# Check InfluxDB connectivity
docker exec dagster-code-location python -c "from influxdb_client import InfluxDBClient; ..."
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

### Dagster Issues

**Container won't start:**
```bash
# Check logs
docker-compose -f docker-compose.dagster.yml logs

# Verify secrets exist
ls -la secrets/

# Restart
docker-compose -f docker-compose.dagster.yml down && docker-compose -f docker-compose.dagster.yml up -d
```

**Job fails with "secrets not set":**
```bash
# Check environment variables
docker exec dagster-code-location env | grep INFLUX

# Recreate containers
docker-compose -f docker-compose.dagster.yml down && docker-compose -f docker-compose.dagster.yml up -d
```

**No data in lampfi_processed:**
```bash
# Check bucket exists (InfluxDB UI > Data > Buckets)
# Trigger manual run (Dagster UI > Assets > Materialize)
# Check code location logs
docker-compose -f docker-compose.dagster.yml logs dagster-code-location | grep "Writing results"
```

### Dashboard Issues

**Dashboard won't start:**
```bash
# Check Node.js version (need 18+)
node --version

# Check environment file
cat dashboard/.env.local

# Reinstall dependencies
cd dashboard && rm -rf node_modules package-lock.json && npm install
```

**No data showing in charts:**
```bash
# Verify InfluxDB connection
curl http://localhost:8086/health

# Check API routes
curl http://localhost:3001/api/meters

# Verify processed data exists in InfluxDB
# Check InfluxDB UI > Data Explorer > lampfi_processed bucket
```

**TypeScript errors:**
```bash
# Run type checking
cd dashboard && npm run build

# Check for missing dependencies
cd dashboard && npm install
```

---

## Maintenance

### Regular Tasks

- **Daily:**
  - Check Dagster UI for failed workflow runs
  - Monitor dashboard for anomaly alerts

- **Weekly:**
  - Review Dagster logs for errors
  - Check disk space on InfluxDB
  - Review dashboard error logs

- **Monthly:**
  - Update Docker images (`docker-compose pull`)
  - Update npm dependencies (`npm update`)
  - Backup configuration files
  - Review and rotate API tokens

- **Annually:**
  - Rotate all secrets (InfluxDB, Tibber)
  - Review meter configuration for changes
  - Archive old data if needed

### Backup Checklist

Important files to backup:
- `config/config.yaml` - Dagster configuration
- `config/meters.yaml` - Meter definitions
- `dashboard/.env.local` - Dashboard configuration
- Household configuration (if stored in localStorage or DB)

---

## Performance

### Dagster Workflows
- **Tibber sync:** 5-10 seconds per run (hourly)
- **Analytics (39 meters, 4 years):** 2-5 minutes per run (daily @ 2 AM)
- **Resource usage:** 200-600 MB RAM, <30% CPU peak
- **InfluxDB writes:** ~1000 points per analytics run

### Next.js Dashboard
- **Initial page load:** <2 seconds
- **Chart rendering:** 100-500ms per chart
- **API response time:** 200-800ms (depends on InfluxDB query)
- **Resource usage:** 150-300 MB RAM (Node.js process)

### System Requirements

| Component | CPU | RAM | Disk | Network |
|-----------|-----|-----|------|---------|
| **Dagster** | 2 cores | 4 GB | 8 GB | 100 Mbps |
| **Dashboard** | 2 cores | 2 GB | 4 GB | 100 Mbps |
| **InfluxDB** | 2 cores | 4 GB | 50+ GB | 100 Mbps |

---

## Support & Resources

### Getting Started
- **Dagster:** Read [workflows_dagster/README.md](workflows_dagster/README.md)
- **Dashboard:** Read [dashboard/README.md](dashboard/README.md)
- **Testing:** See [workflows_dagster/TESTING.md](workflows_dagster/TESTING.md)

### Monitoring URLs
- **Dagster UI:** `http://<dagster-host>:3000`
- **Dashboard:** `http://<dashboard-host>:3001`
- **InfluxDB:** `http://<influxdb-host>:8086`

### Community & Help
- **Issues:** Report bugs or request features via GitHub Issues
- **Documentation:** Check component READMEs in subfolders
- **Logs:** Review structured logs for debugging information

---

**Status:** ✅ Production Ready
**Version:** 4.0.0 (Dagster + Next.js)
**Components:**
- Dagster Workflows: v1.10.16
- Next.js Dashboard: v16.0.3

**Last Updated:** 2025-11-16
