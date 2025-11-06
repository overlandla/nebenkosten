# Utility Meter System - Deployment Guide

Complete guide for deploying the Prefect-based utility meter analytics system to your home NAS.

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Configuration](#configuration)
4. [Deployment](#deployment)
5. [Verification](#verification)
6. [Monitoring](#monitoring)
7. [Troubleshooting](#troubleshooting)
8. [Maintenance](#maintenance)

---

## Prerequisites

### Hardware Requirements
- **NAS** with Docker support (Synology, QNAP, TrueNAS, etc.)
- **Minimum specs:**
  - 2 GB RAM available for containers
  - 10 GB disk space for images and data
  - Network connectivity to InfluxDB instance

### Software Requirements
- **Docker** 20.10+ and **Docker Compose** 1.29+
- **Existing InfluxDB v2** instance running and accessible
- **(Optional)** Existing Grafana instance for visualization

### Access Requirements
- SSH access to NAS
- InfluxDB admin credentials
- Tibber API token (if using Tibber integration)

---

## Initial Setup

### Step 1: Create InfluxDB Bucket

The system needs a separate bucket for processed data:

```bash
# Option 1: Using InfluxDB UI
1. Open InfluxDB UI: http://your-nas-ip:8086
2. Go to "Data" > "Buckets"
3. Click "Create Bucket"
4. Name: lampfi_processed
5. Retention: Infinite
6. Click "Create"

# Option 2: Using InfluxDB CLI
influx bucket create \
  --name lampfi_processed \
  --org your_org_id \
  --retention 0

# Option 3: Using API
curl -X POST "http://your-nas-ip:8086/api/v2/buckets" \
  -H "Authorization: Token YOUR_INFLUX_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "orgID": "YOUR_ORG_ID",
    "name": "lampfi_processed",
    "retentionRules": []
  }'
```

### Step 2: Clone Repository to NAS

```bash
# SSH into your NAS
ssh user@your-nas-ip

# Navigate to your docker apps directory (adjust path for your NAS)
# Synology: /volume1/docker/
# QNAP: /share/Container/
# TrueNAS: /mnt/tank/apps/
cd /volume1/docker/

# Clone repository
git clone <your-repo-url> utility-meters
cd utility-meters
```

### Step 3: Create Secrets

**IMPORTANT:** Never commit secrets to git!

```bash
# Create secrets directory (should already exist from repo)
mkdir -p secrets

# Create InfluxDB secrets
cat > secrets/influxdb.env <<EOF
INFLUX_TOKEN=your_influxdb_token_here
INFLUX_ORG=your_influxdb_org_id_here
EOF

# Create Tibber secrets (optional - skip if not using Tibber)
cat > secrets/tibber.env <<EOF
TIBBER_API_TOKEN=your_tibber_token_here
EOF

# Secure the secrets
chmod 600 secrets/*.env
```

**How to get secrets:**

1. **InfluxDB Token:**
   - Open InfluxDB UI: http://your-nas-ip:8086
   - Go to "Data" > "API Tokens"
   - Click "Generate API Token" > "All Access Token"
   - Copy the token (starts with letters/numbers, very long)

2. **InfluxDB Org ID:**
   - In InfluxDB UI, click your organization name (top-left)
   - Copy the org ID from the URL or settings

3. **Tibber API Token:**
   - Go to https://developer.tibber.com/
   - Sign in with your Tibber account
   - Create "Personal Access Token"
   - Copy the token

---

## Configuration

### Step 1: Update Main Configuration

Edit `config/config.yaml`:

```yaml
influxdb:
  url: "http://192.168.1.75:8086"  # <-- UPDATE THIS to your InfluxDB IP
  bucket_raw: "lampfi"              # Your existing raw data bucket
  bucket_processed: "lampfi_processed"  # Bucket created in Step 1
  timeout: 30
  retry_attempts: 3

tibber:
  polling_interval: 3600            # 1 hour
  lookback_hours: 48
  meter_id: "haupt_strom"           # <-- UPDATE THIS if different

workflows:
  analytics:
    schedule: "0 2 * * *"           # Daily at 2 AM
    start_year: 2020                # <-- UPDATE THIS to your desired start year
  tibber_sync:
    schedule: "5 * * * *"           # Every hour at :05

logging:
  level: "INFO"                     # Change to DEBUG for troubleshooting
  format: "json"
```

### Step 2: Verify Meter Configuration

Check `config/meters.yaml` to ensure all your meters are defined correctly:

```bash
# List all configured meters
grep "meter_id:" config/meters.yaml

# You should see entries like:
#   - meter_id: "strom_total"
#   - meter_id: "gas_total"
#   - meter_id: "haupt_strom"
#   etc.
```

Update meter definitions if needed (add/remove meters, adjust dates, etc.)

### Step 3: Verify Seasonal Patterns (Optional)

Check `config/seasonal_patterns.yaml` - these patterns are used for intelligent gap-filling during interpolation. Update if you have better consumption patterns for your location.

---

## Deployment

### Step 1: Build Images

```bash
cd /volume1/docker/utility-meters

# Build the worker image
docker-compose build

# This will take 2-5 minutes depending on your NAS specs
```

### Step 2: Start Services

```bash
# Start all services in detached mode
docker-compose up -d

# Services starting:
#   - prefect-server (workflow orchestration)
#   - prefect-worker (executes workflows)
```

### Step 3: Check Service Status

```bash
# Check if containers are running
docker-compose ps

# Expected output:
# NAME                          STATUS              PORTS
# utility-prefect-server        Up (healthy)        0.0.0.0:4200->4200/tcp
# utility-prefect-worker        Up                  -

# View logs
docker-compose logs -f

# Press Ctrl+C to stop following logs
```

---

## Verification

### Step 1: Access Prefect UI

1. Open browser: `http://your-nas-ip:4200`
2. You should see the Prefect dashboard

### Step 2: Verify Deployments

In Prefect UI:

1. Go to **Deployments** in left sidebar
2. You should see:
   - `tibber-sync-scheduled` (if Tibber configured)
   - `analytics-scheduled`
3. Check that schedules are shown correctly

### Step 3: Trigger Manual Run (Optional)

Test the system before waiting for scheduled runs:

**Option 1: Via Prefect UI**
1. Go to **Deployments**
2. Click on `analytics-scheduled`
3. Click "Run" button (top-right)
4. Click "Run" again to confirm
5. Monitor progress in "Flow Runs" section

**Option 2: Via CLI**
```bash
# Enter worker container
docker exec -it utility-prefect-worker /bin/bash

# Run analytics flow manually
python /app/workflows/analytics_flow.py

# Exit container
exit
```

### Step 4: Check InfluxDB for Results

```bash
# Query processed bucket to verify data was written
curl -X POST "http://your-nas-ip:8086/api/v2/query?org=YOUR_ORG_ID" \
  -H "Authorization: Token YOUR_INFLUX_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "from(bucket: \"lampfi_processed\") |> range(start: -1d) |> limit(n: 10)"
  }'
```

Or use InfluxDB UI:
1. Go to "Data Explorer"
2. Select bucket: `lampfi_processed`
3. Select measurement: `meter_consumption`
4. Run query
5. You should see processed consumption data

---

## Monitoring

### Monitor via Prefect UI

**Dashboard:** http://your-nas-ip:4200

- **Flow Runs:** See all workflow executions
  - Green = Success
  - Red = Failed
  - Yellow = Running
- **Deployments:** View schedules and trigger manual runs
- **Work Pools:** Check worker status
- **Logs:** View detailed execution logs

### Monitor via Docker Logs

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f prefect-worker
docker-compose logs -f prefect-server

# View last 100 lines
docker-compose logs --tail=100 prefect-worker
```

### Monitor via Application Logs

```bash
# View JSON logs
tail -f logs/utility_analyzer.log

# Pretty-print JSON logs
tail -f logs/utility_analyzer.log | jq '.'

# Filter by level
tail -f logs/utility_analyzer.log | jq 'select(.level == "ERROR")'
```

### Key Metrics to Watch

| Metric | Expected Value | Check Command |
|--------|----------------|---------------|
| Tibber sync runs | Every hour | Check Prefect UI "Flow Runs" |
| Analytics runs | Daily at 2 AM | Check Prefect UI "Flow Runs" |
| Points written | Varies by meters | Check workflow logs |
| Anomalies detected | 0-5 per run (varies) | Check `meter_anomaly` measurement |
| Container health | All "healthy" | `docker-compose ps` |
| Disk usage | < 5 GB | `docker system df` |

---

## Troubleshooting

### Problem: Containers won't start

**Symptoms:**
```
Error: Cannot start service prefect-worker: ...
```

**Solutions:**
```bash
# Check logs
docker-compose logs

# Common issues:
# 1. Secrets missing
ls -la secrets/
# Should see: influxdb.env, tibber.env

# 2. Port conflicts
sudo netstat -tulpn | grep 4200
# If port 4200 is in use, update docker-compose.yml

# 3. Permissions
chmod 600 secrets/*.env
chmod +r config/*.yaml
```

### Problem: Flow fails with "INFLUX_TOKEN not set"

**Symptoms:**
```
ValueError: Missing required secrets: INFLUX_TOKEN
```

**Solutions:**
```bash
# 1. Check secrets file exists
cat secrets/influxdb.env

# 2. Check env_file in docker-compose.yml
grep "env_file" docker-compose.yml

# 3. Recreate containers
docker-compose down
docker-compose up -d
```

### Problem: No data written to InfluxDB

**Symptoms:**
- Flow runs successfully but no data in `lampfi_processed` bucket

**Solutions:**
```bash
# 1. Check bucket exists
curl -X GET "http://your-nas-ip:8086/api/v2/buckets?name=lampfi_processed" \
  -H "Authorization: Token YOUR_INFLUX_TOKEN"

# 2. Check worker logs for errors
docker-compose logs prefect-worker | grep ERROR

# 3. Run analytics flow with DEBUG logging
# Edit config/config.yaml: set logging.level to DEBUG
docker-compose restart prefect-worker

# 4. Check InfluxDB is accessible from container
docker exec utility-prefect-worker ping influxdb-host -c 3
```

### Problem: Tibber sync fails

**Symptoms:**
```
Failed to fetch Tibber data: 401 Unauthorized
```

**Solutions:**
```bash
# 1. Verify Tibber token
curl -X POST https://api.tibber.com/v1-beta/gql \
  -H "Authorization: Bearer YOUR_TIBBER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ viewer { userId } }"}'

# Should return: {"data": {"viewer": {"userId": "..."}}}

# 2. Check token in secrets
cat secrets/tibber.env

# 3. Recreate containers with new token
docker-compose down
# Update secrets/tibber.env
docker-compose up -d
```

### Problem: Analytics flow runs but produces incorrect results

**Symptoms:**
- Consumption values look wrong
- Master meters not combining correctly

**Solutions:**
```bash
# 1. Enable DEBUG logging
# Edit config/config.yaml
logging:
  level: "DEBUG"

# 2. Run manual test
docker exec -it utility-prefect-worker python /app/workflows/analytics_flow.py

# 3. Check meter configuration
cat config/meters.yaml

# 4. Verify source meters exist
# Check Prefect UI logs for warnings like:
#   "Source meter X not found"

# 5. Check unit conversions
# Verify gas_conversion values in config/config.yaml
```

### Problem: High memory usage

**Symptoms:**
```
docker stats
# Shows prefect-worker using > 1 GB RAM
```

**Solutions:**
```bash
# 1. Reduce data range
# Edit config/config.yaml
workflows:
  analytics:
    start_year: 2023  # Process less history

# 2. Add memory limits to docker-compose.yml
services:
  prefect-worker:
    mem_limit: 1g
    mem_reservation: 512m

# 3. Restart containers
docker-compose restart
```

---

## Maintenance

### Regular Tasks

**Daily:**
- Check Prefect UI for failed runs
- Monitor disk space: `docker system df`

**Weekly:**
- Review logs for errors: `docker-compose logs --since 7d | grep ERROR`
- Check anomaly counts in InfluxDB

**Monthly:**
- Review and rotate logs: `docker-compose logs --tail=0 > /dev/null`
- Update Docker images: `docker-compose pull && docker-compose up -d`

### Backup Strategy

**Configuration:**
```bash
# Backup configuration (includes meters, patterns)
tar -czf config-backup-$(date +%Y%m%d).tar.gz config/

# Store backup off-NAS (e.g., cloud storage)
```

**InfluxDB Data:**
```bash
# Backup InfluxDB buckets (existing process, not changed)
# Use InfluxDB backup command or UI export
```

**Prefect Database:**
```bash
# Backup Prefect workflow history
docker-compose down
cp -r /volume1/docker/utility-meters/prefect-data/ prefect-backup-$(date +%Y%m%d)/
docker-compose up -d
```

### Update Procedure

**Update application code:**
```bash
cd /volume1/docker/utility-meters

# Pull latest changes
git pull

# Rebuild images
docker-compose build

# Restart services
docker-compose down
docker-compose up -d

# Check logs
docker-compose logs -f
```

**Update configuration:**
```bash
# 1. Edit configuration files
nano config/config.yaml

# 2. Restart worker to pick up changes
docker-compose restart prefect-worker

# 3. Verify in Prefect UI
```

### Rotating Secrets

**When to rotate:**
- Annually (best practice)
- If token is compromised
- After team member leaves (if shared)

**How to rotate:**
```bash
# 1. Generate new token in InfluxDB/Tibber UI
# 2. Update secrets file
nano secrets/influxdb.env

# 3. Restart services
docker-compose restart

# 4. Verify with test run
docker exec -it utility-prefect-worker python /app/workflows/analytics_flow.py
```

---

## Advanced Configuration

### Custom Schedules

Edit `config/config.yaml` to change workflow schedules:

```yaml
workflows:
  analytics:
    schedule: "0 3 * * *"  # Change to 3 AM instead of 2 AM
  tibber_sync:
    schedule: "*/30 * * * *"  # Change to every 30 minutes
```

Cron format: `minute hour day-of-month month day-of-week`

Examples:
- `"0 2 * * *"` - Daily at 2:00 AM
- `"0 */6 * * *"` - Every 6 hours
- `"0 2 * * 1"` - Weekly on Monday at 2:00 AM
- `"0 2 1 * *"` - Monthly on 1st at 2:00 AM

### Disable Tibber Integration

If you don't use Tibber:

1. Don't create `secrets/tibber.env`
2. System will automatically skip Tibber sync

### Add Custom Meters

Edit `config/meters.yaml`:

```yaml
meters:
  - meter_id: "my_new_meter"
    type: "physical"
    output_unit: "kWh"
    installation_date: "2025-01-01"
    description: "New meter description"
```

---

## Support

**Documentation:**
- Architecture: `SIMPLIFIED_ARCHITECTURE.md`
- Main README: `README.md`

**Logs:**
- Application: `logs/utility_analyzer.log`
- Docker: `docker-compose logs`
- Prefect UI: http://your-nas-ip:4200

**Health Checks:**
- Prefect API: http://your-nas-ip:4200/api/health
- Docker: `docker-compose ps`

---

## Quick Reference

### Common Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart services
docker-compose restart

# View logs
docker-compose logs -f

# Enter worker container
docker exec -it utility-prefect-worker /bin/bash

# Manual flow run
docker exec utility-prefect-worker python /app/workflows/analytics_flow.py

# Check service status
docker-compose ps

# View resource usage
docker stats

# Clean up old images
docker system prune -a
```

### File Locations

| File/Directory | Purpose | Backup? |
|---------------|---------|---------|
| `config/` | Configuration (YAML) | ✅ Yes |
| `secrets/` | Credentials (.env) | ⚠️ Securely |
| `logs/` | Application logs | ❌ No |
| `workflows/` | Python flow code | ✅ Yes (in git) |
| `docker-compose.yml` | Service definitions | ✅ Yes (in git) |

---

**Deployment complete! Access Prefect UI at http://your-nas-ip:4200**
