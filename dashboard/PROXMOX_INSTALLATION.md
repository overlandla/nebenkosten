# Proxmox LXC Installation Guide - Dashboard

This guide explains how to install the Utility Meter Dashboard in a Proxmox LXC container.

## Quick Installation

### Step 1: Create LXC Container

On your Proxmox host, create a new LXC container:

```bash
pct create <CTID> local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst \
  --hostname utility-dashboard \
  --cores 2 \
  --memory 2048 \
  --rootfs local-lvm:4 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --unprivileged 1 \
  --features nesting=1 \
  --onboot 1

pct start <CTID>
```

**Container Specifications:**
- **OS**: Debian 12
- **CPU**: 2 cores
- **RAM**: 2 GB
- **Disk**: 4 GB
- **Network**: DHCP on vmbr0
- **Unprivileged**: Yes
- **Nesting**: Enabled

### Step 2: Install Dashboard

Enter the container and run the installation:

```bash
pct enter <CTID>

# Install prerequisites
apt-get update && apt-get install -y git make

# Clone repository
git clone https://github.com/overlandla/nebenkosten.git
cd nebenkosten

# Install dashboard
make install-dashboard
```

The installation will:
- Install Node.js v20 LTS
- Install system dependencies (curl, sudo, mc, git, rsync)
- Copy dashboard files to `/opt/utility-meter-dashboard`
- Install npm dependencies
- Build the Next.js application
- Create and start systemd service

### Step 3: Configure InfluxDB Connection

Edit the environment file:

```bash
nano /opt/utility-meter-dashboard/.env.local
```

Add your InfluxDB configuration:

```env
# InfluxDB Configuration
INFLUX_URL=http://your-influxdb-server:8086
INFLUX_TOKEN=your_token_here
INFLUX_ORG=your_organization
INFLUX_BUCKET_RAW=homeassistant_raw
INFLUX_BUCKET_PROCESSED=homeassistant_processed

# Gas Conversion Parameters
GAS_ENERGY_CONTENT=10.3
GAS_Z_FACTOR=0.95
```

### Step 4: Restart Service

```bash
systemctl restart utility-meter-dashboard
```

### Step 5: Access Dashboard

Open your browser to:
```
http://YOUR_LXC_IP:3000
```

## Updating the Dashboard

To update to the latest version:

```bash
cd /root/nebenkosten
make update-dashboard
```

This will:
- Pull latest code from GitHub
- Stop the service
- Update files in `/opt/utility-meter-dashboard`
- Reinstall dependencies
- Rebuild the application
- Restart the service

## Service Management

```bash
# Check status
systemctl status utility-meter-dashboard

# View logs
journalctl -u utility-meter-dashboard -f

# Restart service
systemctl restart utility-meter-dashboard

# Stop service
systemctl stop utility-meter-dashboard

# Start service
systemctl start utility-meter-dashboard
```

## Configuration

### Environment Variables

All configuration is done via `/opt/utility-meter-dashboard/.env.local`:

- **INFLUX_URL**: InfluxDB server URL (e.g., `http://192.168.1.100:8086`)
- **INFLUX_TOKEN**: InfluxDB API token (create in InfluxDB UI: Data → API Tokens)
- **INFLUX_ORG**: Your InfluxDB organization name
- **INFLUX_BUCKET_RAW**: Bucket containing raw meter data
- **INFLUX_BUCKET_PROCESSED**: Bucket containing processed data

### Changing Port

To run on a different port, edit the systemd service:

```bash
nano /etc/systemd/system/utility-meter-dashboard.service
```

Change the PORT environment variable:
```ini
Environment=PORT=8080
```

Then reload and restart:
```bash
systemctl daemon-reload
systemctl restart utility-meter-dashboard
```

## Troubleshooting

### Service Won't Start

Check logs:
```bash
journalctl -u utility-meter-dashboard -n 50
```

Verify Node.js installation:
```bash
node --version
npm --version
```

### Can't Connect to InfluxDB

Test InfluxDB connectivity:
```bash
curl http://your-influxdb-server:8086/health
```

Verify configuration:
```bash
cat /opt/utility-meter-dashboard/.env.local
```

### No Data Showing

1. Verify meters exist in InfluxDB with correct entity_ids
2. Check bucket names match your InfluxDB configuration
3. Ensure time range selected has data
4. Check browser console for API errors (F12)

### Build Errors

Clear cache and rebuild:
```bash
cd /opt/utility-meter-dashboard
rm -rf .next node_modules package-lock.json
npm install
npm run build
systemctl restart utility-meter-dashboard
```

## Manual Commands

If you need to perform operations manually:

```bash
cd /opt/utility-meter-dashboard

# Install dependencies
npm install

# Build for production
npm run build

# Start in development mode (for testing)
npm run dev

# Start in production mode
npm start
```

## File Locations

- **Application**: `/opt/utility-meter-dashboard/`
- **Configuration**: `/opt/utility-meter-dashboard/.env.local`
- **Service**: `/etc/systemd/system/utility-meter-dashboard.service`
- **Repository**: `/root/nebenkosten/`
- **Logs**: `journalctl -u utility-meter-dashboard`

## Security Recommendations

1. **Firewall**: Only allow access from trusted networks
   ```bash
   apt-get install -y ufw
   ufw allow from 192.168.1.0/24 to any port 3000
   ufw enable
   ```

2. **HTTPS**: Use reverse proxy with SSL/TLS

3. **InfluxDB Token**: Use read-only token with minimal permissions

4. **Regular Updates**: Keep system updated
   ```bash
   apt-get update && apt-get upgrade -y
   ```

## Support

- **Main README**: [README.md](README.md)
- **Repository**: https://github.com/overlandla/nebenkosten
- **Service Logs**: `journalctl -u utility-meter-dashboard -f`
