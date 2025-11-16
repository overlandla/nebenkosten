#!/usr/bin/env bash

# Copyright (c) 2024
# Author: Your Name
# License: MIT
# https://github.com/overlandla/nebenkosten
#
# This script installs the Utility Meter Dashboard inside an LXC container
# It is called automatically by the proxmox-lxc-install.sh wrapper script

# Detect if running in Proxmox helper script environment or standalone
if [ -n "$FUNCTIONS_FILE_PATH" ]; then
    # Running as Proxmox helper script (fresh install from host)
    source /dev/stdin <<< "$FUNCTIONS_FILE_PATH"
    color
    verb_ip6
    catch_errors
    setting_up_container
    network_check
    update_os
else
    # Running standalone (update inside existing LXC)
    # Define minimal functions for standalone operation
    set -e
    BL="\033[36m"
    GN="\033[1;92m"
    CL="\033[m"
    YW="\033[1;33m"
    RD="\033[01;31m"

    msg_info() { echo -e "${BL}[INFO]${CL} $1"; }
    msg_ok() { echo -e "${GN}[OK]${CL} $1"; }
    msg_error() { echo -e "${RD}[ERROR]${CL} $1"; }

    # Check if this is an update
    if [ -f /opt/utility-meter-dashboard/package.json ]; then
      # Existing installation found - run update
      msg_info "Existing installation detected - running update"

      msg_info "Stopping service"
      systemctl stop utility-dashboard.service 2>/dev/null || true
      msg_ok "Stopped service"

      if [ -f /opt/utility-meter-dashboard/.env.local ]; then
        msg_info "Backing up configuration"
        cp /opt/utility-meter-dashboard/.env.local /opt/utility-meter-dashboard/.env.local.backup
        msg_ok "Configuration backed up"
      fi

      msg_info "Updating code"
      cd /opt/utility-meter-dashboard
      REPO_DIR="/tmp/nebenkosten-update"
      rm -rf "$REPO_DIR"
      git clone https://github.com/overlandla/nebenkosten.git "$REPO_DIR"
      rsync -av --exclude='.env.local' --exclude='.env.local.backup' "$REPO_DIR/dashboard/" /opt/utility-meter-dashboard/
      rm -rf "$REPO_DIR"
      msg_ok "Updated code"

      msg_info "Installing dependencies"
      npm install
      msg_ok "Installed dependencies"

      msg_info "Building application"
      npm run build
      msg_ok "Built application"

      msg_info "Starting service"
      systemctl start utility-dashboard.service
      msg_ok "Started service"

      echo -e "\n${GN}╔════════════════════════════════════════════════════════════╗${CL}"
      echo -e "${GN}║  Utility Meter Dashboard - Update Complete!               ║${CL}"
      echo -e "${GN}╚════════════════════════════════════════════════════════════╝${CL}\n"

      IP_ADDR=$(hostname -I | awk '{print $1}')
      echo -e "${BL}Dashboard URL:${CL} ${GN}http://$IP_ADDR:3000${CL}\n"
      exit 0
    fi

    # Fresh install - continue with normal installation
    msg_info "Updating system packages"
    apt-get update
    apt-get -y upgrade
    msg_ok "System packages updated"
fi

# Set $STD for quiet operation if not already set
STD="${STD:- >/dev/null 2>&1}"

msg_info "Installing Dependencies"
eval apt-get install -y curl $STD
eval apt-get install -y sudo $STD
eval apt-get install -y mc $STD
eval apt-get install -y git $STD
eval apt-get install -y rsync $STD
msg_ok "Installed Dependencies"

msg_info "Installing Node.js v20 LTS"
eval bash <(curl -fsSL https://deb.nodesource.com/setup_20.x) $STD
eval apt-get install -y nodejs $STD
msg_ok "Installed Node.js v20 LTS"

msg_info "Setting up Utility Meter Dashboard"
INSTALL_DIR="/opt/utility-meter-dashboard"
mkdir -p $INSTALL_DIR
cd $INSTALL_DIR

# Clone the repository (fresh installation)
msg_info "Cloning repository"
$STD git clone https://github.com/overlandla/nebenkosten.git temp-repo
mv temp-repo/dashboard/* .
mv temp-repo/dashboard/.* . 2>/dev/null || true
rm -rf temp-repo
msg_ok "Cloned repository"

msg_info "Installing npm dependencies"
$STD npm install
msg_ok "Installed npm dependencies"

msg_info "Creating environment configuration"
cat <<EOF > .env.local
# InfluxDB Configuration
INFLUX_URL=http://localhost:8086
INFLUX_TOKEN=your_influx_token_here
INFLUX_ORG=your_org_name
INFLUX_BUCKET_RAW=homeassistant_raw
INFLUX_BUCKET_PROCESSED=homeassistant_processed

# Gas Conversion Parameters
GAS_ENERGY_CONTENT=10.3
GAS_Z_FACTOR=0.95
EOF
msg_ok "Created environment configuration"

msg_info "Building Next.js application"
$STD npm run build
msg_ok "Built Next.js application"

msg_info "Creating systemd service"
cat <<EOF >/etc/systemd/system/utility-dashboard.service
[Unit]
Description=Utility Meter Dashboard
After=network.target

[Service]
Type=exec
User=root
WorkingDirectory=$INSTALL_DIR
Environment="NODE_ENV=production"
Environment="PORT=3000"
ExecStart=/usr/bin/npm start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable utility-dashboard.service
msg_info "Starting service"
systemctl start utility-dashboard.service
msg_ok "Service configured"

msg_info "Checking service status"
sleep 3
if systemctl is-active --quiet utility-dashboard.service; then
    msg_ok "Service is running"
else
    msg_error "Service failed to start. Check logs with: journalctl -u utility-dashboard.service"
fi

# Only run motd and customize if functions are available (Proxmox environment)
if command -v motd_ssh &> /dev/null; then
    motd_ssh
fi
if command -v customize &> /dev/null; then
    customize
fi

msg_info "Cleaning up"
$STD apt-get -y autoremove
$STD apt-get -y autoclean
msg_ok "Cleaned"

msg_info "Downloading configuration wizard"
curl -fsSL https://raw.githubusercontent.com/overlandla/nebenkosten/main/dashboard/configure-dashboard.sh -o /usr/local/bin/configure-dashboard
chmod +x /usr/local/bin/configure-dashboard
msg_ok "Configuration wizard installed"

# Get the IP address
IP_ADDR=$(hostname -I | awk '{print $1}')

echo -e "\n${GN}╔════════════════════════════════════════════════════════════╗${CL}"
echo -e "${GN}║  Utility Meter Dashboard - Installation Complete!         ║${CL}"
echo -e "${GN}╚════════════════════════════════════════════════════════════╝${CL}\n"

echo -e "${BL}Dashboard URL:${CL} ${GN}http://$IP_ADDR:3000${CL}\n"

echo -e "${YW}⚠️  NEXT STEPS:${CL}\n"
echo -e "${BL}1.${CL} Configure InfluxDB connection:"
echo -e "   Run: ${GN}configure-dashboard${CL}"
echo -e "   Or edit manually: ${BL}$INSTALL_DIR/.env.local${CL}\n"

echo -e "${BL}2.${CL} After configuration, restart the service:"
echo -e "   ${GN}systemctl restart utility-dashboard.service${CL}\n"

echo -e "${YW}📋 Useful Commands:${CL}"
echo -e "  ${BL}configure-dashboard${CL}                           - Run configuration wizard"
echo -e "  ${BL}systemctl status utility-dashboard.service${CL}    - Check service status"
echo -e "  ${BL}journalctl -u utility-dashboard.service -f${CL}    - View live logs"
echo -e "  ${BL}systemctl restart utility-dashboard.service${CL}   - Restart service\n"

echo -e "${YW}📚 Documentation:${CL}"
echo -e "  ${BL}https://github.com/overlandla/nebenkosten/blob/main/dashboard/README.md${CL}\n"
