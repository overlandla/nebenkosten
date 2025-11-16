# Dagster Workflows - Proxmox LXC Installation Guide

This guide explains how to install the Dagster Utility Analysis Workflows as a Proxmox LXC container.

## Table of Contents

- [Quick Installation](#quick-installation)
- [Manual Installation](#manual-installation)
- [Configuration](#configuration)
- [Service Management](#service-management)
- [Monitoring & Observability](#monitoring--observability)
- [Troubleshooting](#troubleshooting)
- [Maintenance](#maintenance)
- [Security Recommendations](#security-recommendations)

## Quick Installation

### Option 1: Using the Installation Script (Recommended)

1. **Create a new LXC container** in Proxmox:
   - OS: Debian 12
   - Disk: 8 GB minimum (16 GB recommended for production)
   - CPU: 2 cores
   - RAM: 4096 MB (4 GB)
   - Network: Bridge (vmbr0)
   - **Important**: Enable "Nesting" feature (required for Docker)

2. **Start the container** and access the console

3. **Run the installation script:**
   ```bash
   bash -c "$(wget -qLO - https://raw.githubusercontent.com/overlandla/nebenkosten/main/workflows_dagster/proxmox-lxc-install.sh)"
   ```

4. **Configure InfluxDB and Tibber:**
   ```bash
   configure-dagster
   ```

5. **Access the Dagster UI:**
   ```
   http://YOUR_LXC_IP:3000
   ```

6. **Enable schedules** in the Dagster UI under Automation → Schedules

## Manual Installation

If you prefer to install manually or want to understand each step:

### 1. Prepare the Container

Create an LXC container with the following specifications:

- **OS**: Debian 12 (Bookworm)
- **Disk**: 8 GB minimum, 16 GB recommended
- **CPU**: 2 cores minimum
- **RAM**: 4096 MB minimum
- **Network**: Bridge to your network (vmbr0)
- **Unprivileged**: Yes (recommended)
- **Features**: **Enable nesting=1** (REQUIRED for Docker)

**To enable nesting in Proxmox:**
- Via UI: CT → Options → Features → Check "Nesting"
- Via CLI: `pct set <CTID> -features nesting=1`

### 2. Install Dependencies

```bash
# Update system
apt-get update && apt-get upgrade -y

# Install required packages
apt-get install -y curl sudo git ca-certificates gnupg lsb-release
```

### 3. Install Docker

```bash
# Add Docker's official GPG key
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Enable and start Docker
systemctl enable docker
systemctl start docker

# Verify Docker installation
docker --version
docker compose version
```

### 4. Clone and Set Up Dagster Workflows

```bash
# Create installation directory
mkdir -p /opt/dagster-workflows
cd /opt/dagster-workflows

# Clone the repository
git clone https://github.com/overlandla/nebenkosten.git
cd nebenkosten
```

### 5. Create Secrets Configuration

```bash
# Create secrets directory
mkdir -p secrets

# Create InfluxDB secrets
cat > secrets/influxdb.env <<EOF
# InfluxDB Configuration
INFLUX_TOKEN=your-influxdb-token-here
INFLUX_ORG=your-org-name
INFLUX_URL=http://192.168.1.75:8086
INFLUX_BUCKET_RAW=lampfi
INFLUX_BUCKET_PROCESSED=lampfi_processed
EOF

# Create Tibber secrets (optional)
cat > secrets/tibber.env <<EOF
# Tibber API Configuration
TIBBER_API_TOKEN=your-tibber-api-token-here
EOF

# Secure the secrets
chmod 600 secrets/*.env
```

**Important**: Replace the placeholder values with your actual credentials.

### 6. Create Configuration Files

```bash
# Create config directory
mkdir -p config

# Create main configuration
cat > config/config.yaml <<EOF
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
EOF
```

### 7. Build and Start Docker Services

```bash
# Build Docker images
docker compose -f docker-compose.dagster.yml build

# Start services
docker compose -f docker-compose.dagster.yml up -d

# Verify services are running
docker ps
```

You should see 4 containers:
- `dagster-postgres` - PostgreSQL database
- `dagster-webserver` - Dagster UI (port 3000)
- `dagster-daemon` - Schedules and sensors
- `dagster-user-code` - Your pipeline code

### 8. Create Systemd Service

```bash
# Create service file
cat > /etc/systemd/system/dagster-workflows.service <<EOF
[Unit]
Description=Dagster Utility Analysis Workflows
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/dagster-workflows/nebenkosten
ExecStart=/usr/bin/docker compose -f docker-compose.dagster.yml up -d
ExecStop=/usr/bin/docker compose -f docker-compose.dagster.yml down
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable the service
systemctl daemon-reload
systemctl enable dagster-workflows.service
```

### 9. Install Configuration Wizard

```bash
# Download the wizard script
curl -fsSL https://raw.githubusercontent.com/overlandla/nebenkosten/main/workflows_dagster/configure-dagster.sh -o /usr/local/bin/configure-dagster
chmod +x /usr/local/bin/configure-dagster

# Run the wizard
configure-dagster
```

## Configuration

### InfluxDB Connection

The Dagster workflows require access to an InfluxDB instance. Configure the connection in `/opt/dagster-workflows/nebenkosten/secrets/influxdb.env`:

- **INFLUX_URL**: URL of your InfluxDB server (e.g., `http://192.168.1.75:8086`)
- **INFLUX_TOKEN**: InfluxDB authentication token (create in InfluxDB UI: Data → API Tokens)
- **INFLUX_ORG**: Your InfluxDB organization name
- **INFLUX_BUCKET_RAW**: Bucket containing raw meter data
- **INFLUX_BUCKET_PROCESSED**: Bucket for processed/analyzed data

**Required Token Permissions:**
- Read access to raw bucket
- Write access to processed bucket

### Tibber API (Optional)

If you want hourly electricity consumption sync from Tibber, configure `/opt/dagster-workflows/nebenkosten/secrets/tibber.env`:

- **TIBBER_API_TOKEN**: Get from https://developer.tibber.com/settings/access-token

### Configuration Wizard

The easiest way to configure everything:

```bash
configure-dagster
```

This interactive wizard will:
- Prompt for all required values
- Test the InfluxDB connection
- Save configuration files
- Restart services automatically

### Manual Configuration

Edit configuration files directly:

```bash
# Edit InfluxDB settings
nano /opt/dagster-workflows/nebenkosten/secrets/influxdb.env

# Edit Tibber settings
nano /opt/dagster-workflows/nebenkosten/secrets/tibber.env

# Edit main configuration
nano /opt/dagster-workflows/nebenkosten/config/config.yaml

# Restart services to apply changes
cd /opt/dagster-workflows/nebenkosten
docker compose -f docker-compose.dagster.yml restart
```

## Service Management

### Systemd Service

```bash
# Start services
systemctl start dagster-workflows.service

# Stop services
systemctl stop dagster-workflows.service

# Restart services
systemctl restart dagster-workflows.service

# Check status
systemctl status dagster-workflows.service

# Enable auto-start on boot
systemctl enable dagster-workflows.service
```

### Docker Compose Commands

```bash
# Always run from the installation directory
cd /opt/dagster-workflows/nebenkosten

# Start all services
docker compose -f docker-compose.dagster.yml up -d

# Stop all services
docker compose -f docker-compose.dagster.yml down

# Restart all services
docker compose -f docker-compose.dagster.yml restart

# View running services
docker compose -f docker-compose.dagster.yml ps

# View logs (all services)
docker compose -f docker-compose.dagster.yml logs -f

# View logs (specific service)
docker compose -f docker-compose.dagster.yml logs -f dagster-webserver
docker compose -f docker-compose.dagster.yml logs -f dagster-daemon
docker compose -f docker-compose.dagster.yml logs -f dagster-user-code

# Rebuild after code changes
docker compose -f docker-compose.dagster.yml up -d --build

# Stop and remove everything (including volumes)
docker compose -f docker-compose.dagster.yml down -v
```

### Individual Container Management

```bash
# List all containers
docker ps

# View logs for specific container
docker logs dagster-webserver -f
docker logs dagster-daemon -f
docker logs dagster-user-code -f

# Execute commands in container
docker exec dagster-user-code dagster job execute -j analytics_processing
docker exec dagster-daemon dagster schedule start analytics_daily

# Restart specific container
docker restart dagster-webserver
```

## Monitoring & Observability

### Dagster UI

Access the Dagster UI at `http://YOUR_LXC_IP:3000`

**Main Features:**

1. **Assets Tab**
   - View asset lineage graph
   - See last materialization time
   - Manually trigger asset materialization
   - Check asset dependencies

2. **Jobs Tab**
   - View all available jobs
   - Launch jobs manually
   - See job run history
   - Monitor execution progress

3. **Runs Tab**
   - See all job runs (current and historical)
   - Filter by status (success, failed, running)
   - View detailed logs for each run
   - Gantt chart showing execution timeline

4. **Automation Tab**
   - **Schedules**: View and enable/disable scheduled jobs
   - **Sensors**: View sensor status (future use)

### Enabling Schedules

**Via Dagster UI:**
1. Navigate to **Automation** → **Schedules**
2. Toggle on the schedules you want:
   - `analytics_daily` - Daily processing at 2:00 AM UTC
   - `tibber_sync_hourly` - Hourly Tibber sync at :05

**Via CLI:**
```bash
cd /opt/dagster-workflows/nebenkosten
docker exec dagster-daemon dagster schedule start analytics_daily
docker exec dagster-daemon dagster schedule start tibber_sync_hourly

# Check schedule status
docker exec dagster-daemon dagster schedule list
```

### Health Checks

```bash
# Check Docker services
docker ps

# Check Dagster webserver health
curl http://localhost:3000

# Check PostgreSQL health
docker exec dagster-postgres pg_isready -U dagster

# Check all service health
docker compose -f docker-compose.dagster.yml ps
```

### Logs

```bash
# Real-time logs (all services)
cd /opt/dagster-workflows/nebenkosten
docker compose -f docker-compose.dagster.yml logs -f

# Logs for specific timeframe
docker compose -f docker-compose.dagster.yml logs --since 1h

# Export logs to file
docker compose -f docker-compose.dagster.yml logs > dagster-logs.txt
```

## Troubleshooting

### Services Not Starting

**Check Docker is running:**
```bash
systemctl status docker
systemctl start docker
```

**Check nesting is enabled:**
```bash
# On Proxmox host (not in container)
pct config <CTID> | grep features
# Should show: features: nesting=1
```

**View service logs:**
```bash
cd /opt/dagster-workflows/nebenkosten
docker compose -f docker-compose.dagster.yml logs
```

**Rebuild containers:**
```bash
docker compose -f docker-compose.dagster.yml down
docker compose -f docker-compose.dagster.yml up -d --build
```

### Can't Access Dagster UI

**Check if webserver is running:**
```bash
docker ps | grep dagster-webserver
```

**Check webserver logs:**
```bash
docker logs dagster-webserver
```

**Test locally:**
```bash
curl http://localhost:3000
```

**Check firewall:**
```bash
# Ensure port 3000 is not blocked
ufw status
```

### Can't Connect to InfluxDB

**Test InfluxDB connectivity:**
```bash
curl http://YOUR_INFLUX_IP:8086/health
```

**Verify secrets are loaded:**
```bash
docker exec dagster-user-code env | grep INFLUX
```

**Check configuration:**
```bash
cat /opt/dagster-workflows/nebenkosten/secrets/influxdb.env
```

**Verify token permissions** in InfluxDB UI (Data → API Tokens)

### Jobs Failing

**View run logs in Dagster UI:**
1. Go to **Runs** tab
2. Click on the failed run
3. View detailed logs and error messages

**Common issues:**
- **Missing configuration files**: Ensure `config/config.yaml` exists
- **Invalid InfluxDB token**: Check token in secrets/influxdb.env
- **Network issues**: Verify InfluxDB is reachable
- **Insufficient permissions**: Token needs read/write access

**View container logs:**
```bash
docker logs dagster-user-code
docker logs dagster-daemon
```

### Import Errors

**Verify PYTHONPATH:**
```bash
docker exec dagster-user-code env | grep PYTHONPATH
# Should include: /app:/app/Nebenkosten
```

**Rebuild containers:**
```bash
cd /opt/dagster-workflows/nebenkosten
docker compose -f docker-compose.dagster.yml up -d --build
```

### PostgreSQL Issues

**Check PostgreSQL health:**
```bash
docker exec dagster-postgres pg_isready -U dagster
```

**View PostgreSQL logs:**
```bash
docker logs dagster-postgres
```

**Reset database (WARNING: loses run history):**
```bash
cd /opt/dagster-workflows/nebenkosten
docker compose -f docker-compose.dagster.yml down -v
docker compose -f docker-compose.dagster.yml up -d
```

## Maintenance

### Update Dagster Workflows

```bash
cd /opt/dagster-workflows/nebenkosten

# Backup current configuration
cp -r secrets secrets.backup
cp -r config config.backup

# Pull latest changes
git pull

# Rebuild and restart
docker compose -f docker-compose.dagster.yml up -d --build

# Verify services are running
docker ps
```

### Update System Packages

```bash
apt-get update
apt-get upgrade -y
apt-get autoremove -y
```

### Update Docker

```bash
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl restart docker
```

### Backup Configuration

```bash
# Backup secrets and config
cd /opt/dagster-workflows/nebenkosten
tar -czf dagster-backup-$(date +%Y%m%d).tar.gz secrets/ config/

# Copy to safe location
cp dagster-backup-*.tar.gz ~/backups/
```

### Restore Configuration

```bash
cd /opt/dagster-workflows/nebenkosten
tar -xzf dagster-backup-YYYYMMDD.tar.gz
docker compose -f docker-compose.dagster.yml restart
```

### Resource Monitoring

```bash
# Check memory usage
free -h

# Check disk usage
df -h

# Check container resource usage
docker stats

# Check system load
top
htop  # if installed
```

### Clean Up Docker Resources

```bash
# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune

# Remove unused containers
docker container prune

# Complete cleanup (be careful!)
docker system prune -a --volumes
```

## Security Recommendations

### 1. Network Security

**Firewall Configuration:**
```bash
# Install ufw if not present
apt-get install -y ufw

# Allow SSH (adjust port if needed)
ufw allow 22

# Allow Dagster UI only from trusted network
ufw allow from 192.168.1.0/24 to any port 3000

# Enable firewall
ufw enable

# Check status
ufw status
```

### 2. Secrets Management

- **Never commit** `secrets/*.env` files to version control
- Use **read-only InfluxDB tokens** when possible
- Restrict token permissions to minimum required:
  - Read access to raw bucket
  - Write access to processed bucket only
- Set restrictive file permissions:
  ```bash
  chmod 600 secrets/*.env
  ```

### 3. Container Security

- Run as **unprivileged LXC container**
- Use **minimal Docker images** (already using python:3.11-slim)
- Keep Docker and system packages **up to date**
- Enable **Docker security features** (already configured)

### 4. Reverse Proxy (Production)

For production deployments, use a reverse proxy:

**Example with Nginx:**
```nginx
server {
    listen 80;
    server_name dagster.yourdomain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name dagster.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 5. Authentication

Dagster doesn't include built-in authentication. For production:

- Use **network-level security** (VPN, firewall rules)
- Add **reverse proxy authentication** (Nginx basic auth, OAuth proxy)
- Consider **Dagster+ (Cloud)** for enterprise authentication features

## Container Specifications

### Minimum Requirements

| Resource | Minimum | Recommended | Production |
|----------|---------|-------------|------------|
| CPU      | 2 cores | 2 cores     | 4 cores    |
| RAM      | 4 GB    | 4 GB        | 8 GB       |
| Disk     | 8 GB    | 16 GB       | 32 GB      |
| Network  | 100 Mbps| 1 Gbps      | 1 Gbps     |

### Features Required

- **Nesting**: Yes (required for Docker)

### Port Requirements

- **3000**: Dagster UI (external access)
- **4000**: Code server (internal only)
- **5432**: PostgreSQL (internal only)

## Support

For issues or questions:

- **Dagster Workflows README**: [README.md](README.md)
- **Quick Start Guide**: [QUICKSTART_PROXMOX.md](QUICKSTART_PROXMOX.md)
- **Dagster Documentation**: https://docs.dagster.io/
- **Project Repository**: https://github.com/overlandla/nebenkosten

## License

This project is part of the nebenkosten utility analysis system.
