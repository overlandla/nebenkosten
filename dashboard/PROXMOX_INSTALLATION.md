# Proxmox LXC Installation Guide

This guide explains how to install the Utility Meter Dashboard as a Proxmox LXC container.

## Quick Installation

### Option 1: Using the Installation Script

1. **Create a new LXC container** in Proxmox:
   - OS: Debian 12
   - Disk: 4 GB minimum
   - CPU: 2 cores
   - RAM: 2048 MB
   - Network: Bridge (vmbr0)

2. **Start the container** and access the console

3. **Run the installation script:**
   ```bash
   bash -c "$(wget -qLO - https://raw.githubusercontent.com/overlandla/nebenkosten/main/dashboard/proxmox-lxc-install.sh)"
   ```

4. **Configure InfluxDB connection:**
   ```bash
   nano /opt/utility-meter-dashboard/.env.local
   ```

5. **Restart the service:**
   ```bash
   systemctl restart utility-dashboard.service
   ```

6. **Access the dashboard:**
   ```
   http://YOUR_LXC_IP:3000
   ```

### Option 2: Manual Installation

If you prefer to install manually, follow these steps:

#### 1. Prepare the Container

Create an LXC container with the following specifications:
- **OS**: Debian 12 (Bookworm)
- **Disk**: 4 GB minimum
- **CPU**: 2 cores
- **RAM**: 2048 MB minimum
- **Network**: Bridge to your network (vmbr0)
- **Unprivileged**: Yes (recommended)
- **Features**: Enable nesting if needed

#### 2. Install Dependencies

```bash
# Update system
apt-get update && apt-get upgrade -y

# Install required packages
apt-get install -y curl sudo git

# Install Node.js v20 LTS
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs

# Verify installation
node --version
npm --version
```

#### 3. Clone and Set Up the Dashboard

```bash
# Create installation directory
mkdir -p /opt/utility-meter-dashboard
cd /opt/utility-meter-dashboard

# Clone the repository
git clone https://github.com/overlandla/nebenkosten.git temp-repo
mv temp-repo/dashboard/* .
mv temp-repo/dashboard/.* . 2>/dev/null || true
rm -rf temp-repo

# Install dependencies
npm install

# Build the application
npm run build
```

#### 4. Configure Environment Variables

Create the environment configuration file:

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

#### 5. Create Systemd Service

Create the service file:

```bash
nano /etc/systemd/system/utility-dashboard.service
```

Add the following content:

```ini
[Unit]
Description=Utility Meter Dashboard
After=network.target

[Service]
Type=exec
User=root
WorkingDirectory=/opt/utility-meter-dashboard
Environment="NODE_ENV=production"
Environment="PORT=3000"
ExecStart=/usr/bin/npm start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 6. Enable and Start the Service

```bash
# Reload systemd
systemctl daemon-reload

# Enable service to start on boot
systemctl enable utility-dashboard.service

# Start the service
systemctl start utility-dashboard.service

# Check status
systemctl status utility-dashboard.service
```

## Configuration

### InfluxDB Connection

The dashboard requires access to an InfluxDB instance with your utility meter data. Configure the connection in `/opt/utility-meter-dashboard/.env.local`:

- **INFLUX_URL**: The URL of your InfluxDB server (e.g., `http://192.168.1.100:8086`)
- **INFLUX_TOKEN**: Your InfluxDB authentication token (create one in InfluxDB UI under Data > API Tokens)
- **INFLUX_ORG**: Your InfluxDB organization name
- **INFLUX_BUCKET_RAW**: The bucket containing your raw meter data

### Network Configuration

By default, the dashboard runs on port 3000. To change this:

1. Edit the service file:
   ```bash
   nano /etc/systemd/system/utility-dashboard.service
   ```

2. Change the `PORT` environment variable:
   ```ini
   Environment="PORT=8080"
   ```

3. Reload and restart:
   ```bash
   systemctl daemon-reload
   systemctl restart utility-dashboard.service
   ```

### Reverse Proxy (Optional)

For production use, consider setting up a reverse proxy with Nginx or Caddy:

#### Example Nginx Configuration

```nginx
server {
    listen 80;
    server_name dashboard.yourdomain.com;

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

## Maintenance

### Update the Dashboard

```bash
cd /opt/utility-meter-dashboard

# Pull latest changes
git pull

# Install any new dependencies
npm install

# Rebuild the application
npm run build

# Restart the service
systemctl restart utility-dashboard.service
```

### View Logs

```bash
# Follow service logs
journalctl -u utility-dashboard.service -f

# View recent logs
journalctl -u utility-dashboard.service -n 100

# View logs with timestamps
journalctl -u utility-dashboard.service -o short-iso
```

### Backup Configuration

Backup your environment configuration:

```bash
cp /opt/utility-meter-dashboard/.env.local ~/utility-dashboard-env-backup.txt
```

### Resource Monitoring

Monitor container resources:

```bash
# Check memory usage
free -h

# Check disk usage
df -h

# Check CPU usage
top

# Check service resource usage
systemctl status utility-dashboard.service
```

## Troubleshooting

### Service Won't Start

1. Check the service logs:
   ```bash
   journalctl -u utility-dashboard.service -n 50
   ```

2. Verify Node.js installation:
   ```bash
   node --version
   npm --version
   ```

3. Check for port conflicts:
   ```bash
   netstat -tulpn | grep 3000
   ```

### Can't Connect to InfluxDB

1. Verify InfluxDB is accessible:
   ```bash
   curl http://your-influxdb-server:8086/health
   ```

2. Check environment variables:
   ```bash
   cat /opt/utility-meter-dashboard/.env.local
   ```

3. Verify InfluxDB token permissions (needs read access to the buckets)

### No Data Showing

1. Verify meters exist in InfluxDB with correct entity_ids
2. Check that the bucket names match your InfluxDB configuration
3. Ensure the time range selected has data available
4. Check browser console for API errors (F12 in most browsers)

### Build Errors

If you encounter errors during `npm run build`:

```bash
cd /opt/utility-meter-dashboard

# Clear build cache
rm -rf .next

# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Try building again
npm run build
```

## Security Recommendations

1. **Firewall**: Configure firewall to only allow access from trusted networks
   ```bash
   # Example with ufw
   ufw allow from 192.168.1.0/24 to any port 3000
   ```

2. **HTTPS**: Use a reverse proxy with SSL/TLS certificates

3. **Authentication**: Consider adding authentication layer (e.g., with Nginx basic auth or OAuth proxy)

4. **InfluxDB Token**: Use a read-only token with minimal permissions

5. **Regular Updates**: Keep the system and dependencies updated
   ```bash
   apt-get update && apt-get upgrade -y
   ```

## Container Specifications

Recommended LXC container specifications:

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU      | 1 core  | 2 cores     |
| RAM      | 1 GB    | 2 GB        |
| Disk     | 4 GB    | 8 GB        |
| Network  | 100 Mbps | 1 Gbps     |

## Support

For issues or questions:
- Check the [README](README.md) for application-specific help
- Review logs: `journalctl -u utility-dashboard.service -f`
- Check InfluxDB connectivity and token permissions
- Ensure meter entity_ids in the dashboard match your InfluxDB data

## License

This project is part of the nebenkosten utility analysis system.
