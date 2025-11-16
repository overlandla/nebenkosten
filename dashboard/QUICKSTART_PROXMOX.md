# Proxmox LXC Quick Start Guide

Get your Utility Meter Dashboard running in under 5 minutes!

## 🚀 One-Line Installation

### 1. Create LXC Container in Proxmox

In Proxmox web interface:
- Click "Create CT"
- **Template**: Debian 12 (download if needed)
- **Disk**: 4 GB
- **CPU**: 2 cores
- **RAM**: 2048 MB
- **Network**: Default (bridge)
- **Unprivileged container**: Yes (recommended)

### 2. Start Container & Run Install Script

Open the LXC console and run:

```bash
bash -c "$(wget -qLO - https://raw.githubusercontent.com/overlandla/nebenkosten/main/dashboard/proxmox-lxc-install.sh)"
```

Wait for installation to complete (~2-3 minutes).

### 3. Configure InfluxDB Connection

Run the configuration wizard:

```bash
configure-dashboard
```

Follow the prompts to enter:
- InfluxDB URL (e.g., `http://192.168.1.100:8086`)
- InfluxDB Token
- Organization name
- Bucket name

The wizard will test the connection and restart the service automatically.

### 4. Access Dashboard

Open in your browser:

```
http://YOUR_LXC_IP:3000
```

That's it! 🎉

## 🔄 Updating an Existing Installation

The same script can be used to update an existing installation! Simply run it again:

```bash
bash -c "$(wget -qLO - https://raw.githubusercontent.com/overlandla/nebenkosten/main/dashboard/proxmox-lxc-install.sh)"
```

The script will automatically:
- ✅ Detect the existing installation
- ✅ Backup your `.env.local` configuration to `.env.local.backup`
- ✅ Pull the latest code
- ✅ Preserve all your settings
- ✅ Rebuild and restart the service

**Your configuration is safe - it will be preserved during updates!**

## 📊 What You Get

- **Real-time charts** for all utility meters
- **Time range selector** (7 days, 30 days, 3 months, custom, etc.)
- **Meter selection** - choose which meters to display
- **Water temperature tracking** from Bavarian lakes
- **Responsive design** - works on phone, tablet, desktop

## 🔧 Quick Commands

```bash
# View dashboard status
systemctl status utility-dashboard.service

# View live logs
journalctl -u utility-dashboard.service -f

# Restart dashboard
systemctl restart utility-dashboard.service

# Reconfigure settings
configure-dashboard

# Edit configuration manually
nano /opt/utility-meter-dashboard/.env.local
```

## 🆘 Troubleshooting

### Dashboard won't start

```bash
# Check the logs
journalctl -u utility-dashboard.service -n 50

# Verify configuration
cat /opt/utility-meter-dashboard/.env.local
```

### Can't see data

1. Verify InfluxDB connection:
   ```bash
   curl http://YOUR_INFLUX_IP:8086/health
   ```

2. Check if meters exist in InfluxDB with the correct entity_ids

3. Verify time range has data

### Build errors

```bash
cd /opt/utility-meter-dashboard
rm -rf .next node_modules
npm install
npm run build
systemctl restart utility-dashboard.service
```

## 📚 More Information

- **Full Installation Guide**: [PROXMOX_INSTALLATION.md](PROXMOX_INSTALLATION.md)
- **Dashboard Documentation**: [README.md](README.md)
- **Repository**: https://github.com/overlandla/nebenkosten

## 🔐 Security Tips

1. **Firewall**: Only allow access from trusted networks
2. **HTTPS**: Use a reverse proxy for production
3. **Read-only token**: Use minimal permissions for InfluxDB
4. **Regular updates**: Keep system packages updated

## 📦 Container Specs

| Resource | Value |
|----------|-------|
| OS       | Debian 12 |
| Disk     | 4 GB |
| CPU      | 2 cores |
| RAM      | 2 GB |
| Port     | 3000 |

## 💡 Pro Tips

- **Custom port**: Edit `/etc/systemd/system/utility-dashboard.service` and change the `PORT` environment variable
- **Reverse proxy**: Use Nginx or Caddy for HTTPS and custom domain
- **Backups**: Configuration is automatically backed up during updates
- **Updates**: Just re-run the install script - it will automatically detect and update the existing installation

---

Need help? Check the logs first, then consult the full documentation!
