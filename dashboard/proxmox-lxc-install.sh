#!/usr/bin/env bash

# Copyright (c) 2024
# Author: Your Name
# License: MIT
# https://github.com/overlandla/nebenkosten
#
# Source: https://github.com/overlandla/nebenkosten/tree/main/dashboard
# This script installs the Utility Meter Dashboard as a Proxmox LXC container
#
# name: utility-meter-dashboard
# var_disk: 4
# var_cpu: 2
# var_ram: 2048
# var_os: debian
# var_version: 12
# var_unprivileged: 1
#
# Documentation: https://github.com/overlandla/nebenkosten/blob/main/dashboard/PROXMOX_INSTALLATION.md

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

    # Update OS when running standalone
    msg_info "Updating system packages"
    apt-get update
    apt-get -y upgrade
    msg_ok "System packages updated"
fi

# Set $STD for quiet operation if not already set
STD="${STD:--qq}"

msg_info "Installing Dependencies"
$STD apt-get install -y curl
$STD apt-get install -y sudo
$STD apt-get install -y mc
$STD apt-get install -y git
$STD apt-get install -y rsync
msg_ok "Installed Dependencies"

msg_info "Installing Node.js v20 LTS"
$STD bash <(curl -fsSL https://deb.nodesource.com/setup_20.x)
$STD apt-get install -y nodejs
msg_ok "Installed Node.js v20 LTS"

msg_info "Setting up Utility Meter Dashboard"
INSTALL_DIR="/opt/utility-meter-dashboard"
mkdir -p $INSTALL_DIR
cd $INSTALL_DIR

# Detect if this is an update or fresh install
if [ -f "$INSTALL_DIR/package.json" ]; then
    IS_UPDATE=true
    msg_info "Existing installation detected - running update"

    # Stop service if running
    if systemctl is-active --quiet utility-dashboard.service; then
        msg_info "Stopping service for update"
        systemctl stop utility-dashboard.service
    fi

    # Backup existing configuration
    if [ -f .env.local ]; then
        msg_info "Backing up existing configuration"
        cp .env.local .env.local.backup
        msg_ok "Configuration backed up to .env.local.backup"
    fi

    # Pull latest changes
    msg_info "Pulling latest code from repository"
    REPO_DIR="$INSTALL_DIR/../nebenkosten-temp"
    rm -rf "$REPO_DIR"
    $STD git clone https://github.com/overlandla/nebenkosten.git "$REPO_DIR"

    # Update files (preserve .env.local)
    rsync -av --exclude='.env.local' --exclude='.env.local.backup' "$REPO_DIR/dashboard/" "$INSTALL_DIR/"
    rm -rf "$REPO_DIR"
    msg_ok "Code updated"
else
    IS_UPDATE=false
    msg_info "Fresh installation detected"

    # Clone the repository
    msg_info "Cloning repository"
    $STD git clone https://github.com/overlandla/nebenkosten.git temp-repo
    mv temp-repo/dashboard/* .
    mv temp-repo/dashboard/.* . 2>/dev/null || true
    rm -rf temp-repo
    msg_ok "Cloned repository"
fi

msg_info "Installing npm dependencies"
$STD npm install
msg_ok "Installed npm dependencies"

# Only create .env.local if it doesn't exist (fresh install)
if [ ! -f .env.local ]; then
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
else
    msg_ok "Preserving existing configuration"
fi

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

if [ "$IS_UPDATE" = true ]; then
    msg_info "Restarting service after update"
    systemctl start utility-dashboard.service
else
    msg_info "Starting service"
    systemctl start utility-dashboard.service
fi
msg_ok "Service configured"

msg_info "Checking service status"
sleep 3
if systemctl is-active --quiet utility-dashboard.service; then
    msg_ok "Service is running"
else
    msg_error "Service failed to start. Check logs with: journalctl -u utility-dashboard.service"
fi

if [ "$IS_UPDATE" != true ]; then
    # Only run motd and customize if functions are available (Proxmox environment)
    if command -v motd_ssh &> /dev/null; then
        motd_ssh
    fi
    if command -v customize &> /dev/null; then
        customize
    fi
fi

msg_info "Cleaning up"
$STD apt-get -y autoremove
$STD apt-get -y autoclean
msg_ok "Cleaned"

msg_info "Downloading configuration wizard"
curl -fsSL https://raw.githubusercontent.com/overlandla/nebenkosten/main/dashboard/configure-dashboard.sh -o /usr/local/bin/configure-dashboard
chmod +x /usr/local/bin/configure-dashboard
msg_ok "Configuration wizard installed"

if [ "$IS_UPDATE" = true ]; then
    msg_info "Utility Meter Dashboard Update Complete"
else
    msg_info "Utility Meter Dashboard Installation Complete"
fi

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
