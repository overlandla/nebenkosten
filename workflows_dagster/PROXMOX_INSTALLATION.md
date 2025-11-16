# Proxmox LXC Installation Guide - Dagster Workflows

This guide explains how to install the Dagster Utility Analysis Workflows in a Proxmox LXC container.

## Quick Installation

### Step 1: Create LXC Container

On your Proxmox host, create a new LXC container:

```bash
pct create <CTID> local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst \
  --hostname dagster-workflows \
  --cores 2 \
  --memory 4096 \
  --rootfs local-lvm:8 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --unprivileged 1 \
  --features nesting=1 \
  --onboot 1

pct start <CTID>
```

**Container Specifications:**
- **OS**: Debian 12
- **CPU**: 2 cores minimum
- **RAM**: 4 GB
- **Disk**: 8 GB (16 GB recommended)
- **Network**: DHCP on vmbr0
- **Unprivileged**: Yes
- **Nesting**: **REQUIRED** (for Docker)

### Step 2: Install Dagster

Enter the container and run the installation:

```bash
pct enter <CTID>

# Install prerequisites
apt-get update && apt-get install -y git make

# Clone repository
git clone https://github.com/overlandla/nebenkosten.git
cd nebenkosten

# Install Dagster workflows
make install-dagster
```

The installation will:
- Install Docker and Docker Compose
- Install system dependencies
- Copy workflow files to `/opt/dagster-workflows/nebenkosten`
- Start Docker containers via docker compose

### Step 3: Configure Secrets

Create InfluxDB secrets:

```bash
cd /opt/dagster-workflows/nebenkosten

nano secrets/influxdb.env
```

Add your configuration:

```env
# InfluxDB Configuration
INFLUX_TOKEN=your-influxdb-token-here
INFLUX_ORG=your-org-name
INFLUX_URL=http://192.168.1.75:8086
INFLUX_BUCKET_RAW=lampfi
INFLUX_BUCKET_PROCESSED=lampfi_processed
```

(Optional) Create Tibber secrets:

```bash
nano secrets/tibber.env
```

```env
# Tibber API Configuration
TIBBER_API_TOKEN=your-tibber-api-token-here
```

Secure the secrets:
```bash
chmod 600 secrets/*.env
```

### Step 4: Restart Services

```bash
cd /opt/dagster-workflows/nebenkosten
docker compose down
docker compose up -d
```

### Step 5: Access Dagster UI

Open your browser to:
```
http://YOUR_LXC_IP:3000
```

### Step 6: Enable Schedules

In the Dagster UI:
1. Navigate to **Automation** → **Schedules**
2. Enable the schedules you want:
   - `analytics_daily` - Daily processing at 2:00 AM
   - `tibber_sync_hourly` - Hourly Tibber sync

## Updating Dagster

To update to the latest version:

```bash
cd /root/nebenkosten
make update-dagster
```

This will:
- Pull latest code from GitHub
- Stop Docker containers
- Update files in `/opt/dagster-workflows/nebenkosten`
- Rebuild and restart containers

## Service Management

### Docker Compose Commands

```bash
cd /opt/dagster-workflows/nebenkosten

# Start services
docker compose up -d

# Stop services
docker compose down

# Restart services
docker compose restart

# View logs (all services)
docker compose logs -f

# View logs (specific service)
docker compose logs -f dagster-webserver
docker compose logs -f dagster-daemon
docker compose logs -f dagster-user-code

# Check status
docker compose ps

# Rebuild after changes
docker compose up -d --build
```

### Individual Containers

```bash
# List containers
docker ps

# View logs
docker logs dagster-webserver -f
docker logs dagster-daemon -f
docker logs dagster-user-code -f

# Restart container
docker restart dagster-webserver
```

## Configuration

### InfluxDB Connection

Configure in `/opt/dagster-workflows/nebenkosten/secrets/influxdb.env`:

- **INFLUX_URL**: InfluxDB server URL
- **INFLUX_TOKEN**: API token (create in InfluxDB UI: Data → API Tokens)
- **INFLUX_ORG**: Organization name
- **INFLUX_BUCKET_RAW**: Bucket with raw meter data
- **INFLUX_BUCKET_PROCESSED**: Bucket for processed data

**Token Permissions Required:**
- Read access to raw bucket
- Write access to processed bucket

### Tibber API (Optional)

Configure in `/opt/dagster-workflows/nebenkosten/secrets/tibber.env`:

- **TIBBER_API_TOKEN**: Get from https://developer.tibber.com/settings/access-token

### Main Configuration

Edit `/opt/dagster-workflows/nebenkosten/config/config.yaml`:

```yaml
influx:
  url: "http://192.168.1.75:8086"
  bucket_raw: "lampfi"
  bucket_processed: "lampfi_processed"
  timeout: 30000
  retry_attempts: 3

start_year: 2020

processing:
  enable_anomaly_detection: true
  interpolation_method: "linear"
```

## Monitoring

### Dagster UI

Access at `http://YOUR_LXC_IP:3000`

**Key Features:**
- **Assets**: View all data assets and dependencies
- **Runs**: Execution history and detailed logs
- **Schedules**: Enable/disable scheduled jobs
- **Jobs**: Manual job execution

### Logs

```bash
# Real-time logs (all services)
cd /opt/dagster-workflows/nebenkosten
docker compose logs -f

# Logs from specific timeframe
docker compose logs --since 1h

# Export logs
docker compose logs > dagster-logs.txt
```

### Health Checks

```bash
# Check all containers
docker ps

# Check Dagster webserver
curl http://localhost:3000

# Check PostgreSQL
docker exec dagster-postgres pg_isready -U dagster
```

## Troubleshooting

### Services Not Starting

Check Docker is running:
```bash
systemctl status docker
systemctl start docker
```

Check nesting is enabled (on Proxmox host):
```bash
pct config <CTID> | grep features
# Should show: features: nesting=1
```

View logs:
```bash
cd /opt/dagster-workflows/nebenkosten
docker compose logs
```

Rebuild containers:
```bash
docker compose down
docker compose up -d --build
```

### Can't Access Dagster UI

Check webserver is running:
```bash
docker ps | grep dagster-webserver
docker logs dagster-webserver
```

Test locally:
```bash
curl http://localhost:3000
```

### Can't Connect to InfluxDB

Test connectivity:
```bash
curl http://YOUR_INFLUX_IP:8086/health
```

Verify secrets are loaded:
```bash
docker exec dagster-user-code env | grep INFLUX
```

Check configuration:
```bash
cat /opt/dagster-workflows/nebenkosten/secrets/influxdb.env
```

### Jobs Failing

View run logs in Dagster UI:
1. Go to **Runs** tab
2. Click on failed run
3. View detailed error messages

Common issues:
- Missing configuration files
- Invalid InfluxDB token
- Network connectivity
- Insufficient token permissions

## Maintenance

### Backup Configuration

```bash
cd /opt/dagster-workflows/nebenkosten
tar -czf dagster-backup-$(date +%Y%m%d).tar.gz secrets/ config/
cp dagster-backup-*.tar.gz ~/backups/
```

### Restore Configuration

```bash
cd /opt/dagster-workflows/nebenkosten
tar -xzf dagster-backup-YYYYMMDD.tar.gz
docker compose restart
```

### Resource Monitoring

```bash
# Container resource usage
docker stats

# Memory usage
free -h

# Disk usage
df -h

# System load
top
```

### Clean Up Docker

```bash
# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune

# Complete cleanup
docker system prune -a --volumes
```

## File Locations

- **Application**: `/opt/dagster-workflows/nebenkosten/`
- **Secrets**: `/opt/dagster-workflows/nebenkosten/secrets/`
- **Config**: `/opt/dagster-workflows/nebenkosten/config/`
- **Repository**: `/root/nebenkosten/`
- **Docker Compose**: `/opt/dagster-workflows/nebenkosten/docker-compose.yml`

## Docker Containers

The installation creates 4 containers:

- **dagster-postgres**: PostgreSQL database for Dagster
- **dagster-webserver**: Dagster UI (port 3000)
- **dagster-daemon**: Schedules and sensors
- **dagster-user-code**: Your workflow code

## Security Recommendations

1. **Firewall**: Only allow access from trusted networks
   ```bash
   apt-get install -y ufw
   ufw allow from 192.168.1.0/24 to any port 3000
   ufw enable
   ```

2. **Secrets**: Never commit secrets to version control
   ```bash
   chmod 600 secrets/*.env
   ```

3. **InfluxDB Token**: Use minimal permissions (read raw, write processed)

4. **Regular Updates**:
   ```bash
   apt-get update && apt-get upgrade -y
   ```

## Support

- **Main README**: [README.md](README.md)
- **Repository**: https://github.com/overlandla/nebenkosten
- **Dagster Documentation**: https://docs.dagster.io/
- **Useful Commands**: `cd /opt/dagster-workflows/nebenkosten && make help`
