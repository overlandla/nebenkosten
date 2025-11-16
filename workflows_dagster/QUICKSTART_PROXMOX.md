# Dagster Workflows - Proxmox LXC Quick Start Guide

Get your Dagster utility analysis workflows running in under 10 minutes!

## 🚀 One-Line Installation

### 1. Create LXC Container in Proxmox

In Proxmox web interface:
- Click "Create CT"
- **Template**: Debian 12 (download if needed)
- **Disk**: 8 GB minimum
- **CPU**: 2 cores
- **RAM**: 4096 MB (4 GB)
- **Network**: Default (bridge)
- **Unprivileged container**: Yes (recommended)
- **Features**: Enable "Nesting" (required for Docker)

### 2. Start Container & Run Install Script

Open the LXC console and run:

```bash
bash -c "$(wget -qLO - https://raw.githubusercontent.com/overlandla/nebenkosten/main/workflows_dagster/proxmox-lxc-install.sh)"
```

Wait for installation to complete (~5-7 minutes).

### 3. Configure InfluxDB Connection

Run the configuration wizard:

```bash
configure-dagster
```

Follow the prompts to enter:
- **InfluxDB URL** (e.g., `http://192.168.1.75:8086`)
- **InfluxDB Token** (from InfluxDB UI: Data → API Tokens)
- **Organization name**
- **Bucket names** (raw and processed)
- **Tibber API Token** (optional - only if you want Tibber sync)

The wizard will:
- Test the InfluxDB connection
- Save your configuration
- Restart all Dagster services automatically

### 4. Access Dagster UI

Open in your browser:

```
http://YOUR_LXC_IP:3000
```

### 5. Enable Schedules

In the Dagster UI:

1. Navigate to **Automation** → **Schedules**
2. Enable the following schedules:
   - **analytics_daily** - Runs daily at 2:00 AM UTC (recommended)
   - **tibber_sync_hourly** - Runs every hour at :05 (only if you configured Tibber)

Or enable via command line:

```bash
cd /opt/dagster-workflows/nebenkosten
docker exec dagster-daemon dagster schedule start analytics_daily
docker exec dagster-daemon dagster schedule start tibber_sync_hourly
```

### 6. Trigger Your First Job (Optional)

Want to run analytics immediately?

**Via UI:**
1. Go to **Jobs** tab
2. Click on `analytics_processing`
3. Click **Launch Run**
4. Watch it execute in real-time!

**Via CLI:**
```bash
cd /opt/dagster-workflows/nebenkosten
docker exec dagster-user-code dagster job execute -j analytics_processing
```

That's it! 🎉

## 🔄 Updating an Existing Installation

The same script can be used to update an existing installation! Simply run it again:

```bash
bash -c "$(wget -qLO - https://raw.githubusercontent.com/overlandla/nebenkosten/main/workflows_dagster/proxmox-lxc-install.sh)"
```

The script will automatically:
- ✅ Detect the existing installation
- ✅ Stop running containers gracefully
- ✅ Backup your `secrets/` and `config/` directories with timestamps
- ✅ Pull the latest code
- ✅ Preserve all your settings
- ✅ Rebuild Docker images and restart services

**Your secrets and configuration are safe - they will be preserved during updates!**

Backups are created with timestamps like `secrets.backup.20241116_143022` for easy rollback if needed.

## 📊 What You Get

- **Real-time data orchestration** with Dagster
- **Asset lineage visualization** - see how data flows through your pipeline
- **Automated workflows**:
  - Hourly Tibber electricity sync
  - Daily utility meter analytics
- **Data quality checks** and anomaly detection
- **Job scheduling** with cron expressions
- **Modern UI** with execution monitoring and logs

## 🔧 Quick Commands

```bash
# View all running containers
docker ps

# View live logs for all services
cd /opt/dagster-workflows/nebenkosten
docker compose -f docker-compose.dagster.yml logs -f

# View logs for specific service
docker compose -f docker-compose.dagster.yml logs -f dagster-webserver

# Restart all services
docker compose -f docker-compose.dagster.yml restart

# Stop all services
docker compose -f docker-compose.dagster.yml down

# Start all services
docker compose -f docker-compose.dagster.yml up -d

# Reconfigure settings
configure-dagster

# Check service status
systemctl status dagster-workflows.service
```

## 📋 Dagster UI Features

### Assets Tab
- View all data assets
- See dependency graph and lineage
- Check last materialization time
- Manually trigger asset materialization

### Jobs Tab
- View all available jobs
- Launch jobs manually
- See job run history
- Monitor execution progress

### Runs Tab
- See all job runs (past and current)
- Filter by status (success, failed, in progress)
- View detailed logs for each run
- Gantt chart for execution timeline

### Automation Tab
- **Schedules**: Enable/disable scheduled jobs
- **Sensors**: View sensor status (future use)

## 🆘 Troubleshooting

### Services won't start

```bash
# Check Docker is running
systemctl status docker

# Check container logs
cd /opt/dagster-workflows/nebenkosten
docker compose -f docker-compose.dagster.yml logs

# Rebuild containers
docker compose -f docker-compose.dagster.yml up -d --build
```

### Can't access Dagster UI

```bash
# Check if webserver is running
docker ps | grep dagster-webserver

# Check webserver logs
docker logs dagster-webserver

# Verify port 3000 is accessible
curl http://localhost:3000
```

### Can't connect to InfluxDB

1. Verify InfluxDB is accessible from the LXC:
   ```bash
   curl http://YOUR_INFLUX_IP:8086/health
   ```

2. Check your configuration:
   ```bash
   cat /opt/dagster-workflows/nebenkosten/secrets/influxdb.env
   ```

3. Verify InfluxDB token has read/write permissions

4. Run configuration wizard again:
   ```bash
   configure-dagster
   ```

### Jobs are failing

1. Check the run logs in Dagster UI:
   - Go to **Runs** tab
   - Click on the failed run
   - View the detailed logs

2. Common issues:
   - **InfluxDB connection**: Verify token and URL
   - **Missing configuration**: Check `config/config.yaml` exists
   - **Permission issues**: Ensure secrets files are readable

3. View container logs:
   ```bash
   docker compose -f docker-compose.dagster.yml logs dagster-user-code
   ```

## 📦 Container Specs

| Resource | Value |
|----------|-------|
| OS       | Debian 12 |
| Disk     | 8 GB |
| CPU      | 2 cores |
| RAM      | 4 GB |
| Port     | 3000 (Dagster UI) |

## 💡 Pro Tips

- **Asset materialization**: You can materialize individual assets instead of running entire jobs
- **Custom schedules**: Edit `workflows_dagster/dagster_project/schedules/__init__.py` to customize timing
- **Partitioned assets**: Future enhancement for incremental processing
- **Backups**: Secrets and config are automatically backed up during updates with timestamps
- **Updates**: Just re-run the install script - it will automatically detect and update the existing installation
- **Rollback**: If an update causes issues, restore from timestamped backup directories

## 🔐 Security Tips

1. **Firewall**: Only allow access from trusted networks
   ```bash
   ufw allow from 192.168.1.0/24 to any port 3000
   ```

2. **Secrets**: Never commit `secrets/*.env` files to git

3. **Read-only tokens**: Use minimal InfluxDB permissions needed

4. **Regular updates**: Keep Docker and system packages updated
   ```bash
   apt-get update && apt-get upgrade -y
   ```

## 📚 More Information

- **Full Installation Guide**: [PROXMOX_INSTALLATION.md](PROXMOX_INSTALLATION.md)
- **Dagster Workflows README**: [README.md](README.md)
- **Repository**: https://github.com/overlandla/nebenkosten
- **Dagster Documentation**: https://docs.dagster.io/

---

Need help? Check the logs first, then consult the full documentation!
