# Proxmox LXC Installation Guide - Dagster Workflows

This guide explains how to install the Dagster Utility Analysis Workflows in a Proxmox LXC container.

## Quick Installation

### Step 1: Create LXC Container

On your Proxmox host, create a new LXC container:

```bash
pct create <CTID> local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst \
  --hostname dagster-workflows \
  --cores 2 \
  --memory 2048 \
  --rootfs local-lvm:8 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --unprivileged 1 \
  --onboot 1

pct start <CTID>
```

**Container Specifications:**
- **OS**: Debian 12
- **CPU**: 2 cores minimum
- **RAM**: 2 GB (reduced from 4 GB - no Docker overhead)
- **Disk**: 8 GB (16 GB recommended)
- **Network**: DHCP on vmbr0
- **Unprivileged**: Yes
- **Nesting**: Not required (native systemd deployment)

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
- Install PostgreSQL database (for Dagster state)
- Install Dagster and system dependencies
- Copy workflow files to `/opt/dagster-workflows/nebenkosten`
- Install and start systemd services for Dagster components

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
# Restart Dagster services
systemctl restart dagster-webserver
systemctl restart dagster-daemon
systemctl restart dagster-user-code
systemctl restart postgresql
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
- Stop systemd services gracefully
- Backup your secrets and config directories (with timestamps)
- Update files in `/opt/dagster-workflows/nebenkosten`
- Restart systemd services with latest code

## Service Management

### Systemd Services

```bash
# Start all Dagster services
systemctl start dagster-webserver
systemctl start dagster-daemon
systemctl start dagster-user-code
systemctl start postgresql

# Stop all services
systemctl stop dagster-webserver
systemctl stop dagster-daemon
systemctl stop dagster-user-code

# Restart services
systemctl restart dagster-webserver
systemctl restart dagster-daemon
systemctl restart dagster-user-code

# View logs (all services)
journalctl -u dagster-webserver -f
journalctl -u dagster-daemon -f
journalctl -u dagster-user-code -f

# Check service status
systemctl status dagster-webserver
systemctl status dagster-daemon
systemctl status dagster-user-code
systemctl status postgresql

# Enable services to start on boot
systemctl enable dagster-webserver
systemctl enable dagster-daemon
systemctl enable dagster-user-code
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
# Real-time logs from services
journalctl -u dagster-webserver -f
journalctl -u dagster-daemon -f
journalctl -u dagster-user-code -f

# Logs from specific timeframe (last hour)
journalctl -u dagster-webserver --since "1 hour ago"

# Export logs
journalctl -u dagster-webserver > dagster-webserver-logs.txt
journalctl -u dagster-daemon > dagster-daemon-logs.txt
```

### Health Checks

```bash
# Check service status
systemctl status dagster-webserver
systemctl status dagster-daemon
systemctl status dagster-user-code
systemctl status postgresql

# Check Dagster webserver
curl http://localhost:3000

# Check PostgreSQL
pg_isready -U dagster
```

## Troubleshooting

### Services Not Starting

Check service status:
```bash
systemctl status dagster-webserver
systemctl status dagster-daemon
systemctl status dagster-user-code
```

View detailed logs:
```bash
journalctl -u dagster-webserver -n 50
journalctl -u dagster-daemon -n 50
journalctl -u dagster-user-code -n 50
```

Restart services:
```bash
systemctl restart dagster-webserver
systemctl restart dagster-daemon
systemctl restart dagster-user-code
```

### Can't Access Dagster UI

Check webserver is running:
```bash
systemctl status dagster-webserver
journalctl -u dagster-webserver -f
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
cat /opt/dagster-workflows/nebenkosten/secrets/influxdb.env
env | grep INFLUX
```

Check configuration:
```bash
cat /opt/dagster-workflows/nebenkosten/config/config.yaml
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
systemctl restart dagster-webserver
systemctl restart dagster-daemon
systemctl restart dagster-user-code
```

### Resource Monitoring

```bash
# Process resource usage
ps aux --sort=-%mem | head -20

# Memory usage
free -h

# Disk usage
df -h

# System load
top

# Service resource usage
systemctl status dagster-webserver
systemctl status dagster-daemon
```

### PostgreSQL Maintenance

```bash
# Check PostgreSQL status
systemctl status postgresql

# Backup Dagster database
sudo -u postgres pg_dump dagster > dagster-db-backup.sql

# Restore Dagster database
sudo -u postgres psql dagster < dagster-db-backup.sql
```

## File Locations

- **Application**: `/opt/dagster-workflows/nebenkosten/`
- **Secrets**: `/opt/dagster-workflows/nebenkosten/secrets/`
- **Config**: `/opt/dagster-workflows/nebenkosten/config/`
- **Repository**: `/root/nebenkosten/`
- **Systemd Services**: `/etc/systemd/system/dagster-*.service`

## Systemd Services

The installation creates 4 systemd services:

- **postgresql**: PostgreSQL database for Dagster state management
- **dagster-webserver**: Dagster UI (port 3000)
- **dagster-daemon**: Schedules and sensor execution
- **dagster-user-code**: Workflow code location server

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
   ls -la secrets/
   ```

3. **InfluxDB Token**: Use minimal permissions (read raw, write processed)

4. **PostgreSQL**: Ensure tight access controls
   ```bash
   sudo -u postgres psql -c "ALTER USER dagster WITH ENCRYPTED PASSWORD 'strong-password';"
   ```

5. **Regular Updates**:
   ```bash
   apt-get update && apt-get upgrade -y
   ```

## Support

- **Main README**: [README.md](README.md)
- **Repository**: https://github.com/overlandla/nebenkosten
- **Dagster Documentation**: https://docs.dagster.io/
- **Useful Commands**: `cd /opt/dagster-workflows/nebenkosten && make help`
