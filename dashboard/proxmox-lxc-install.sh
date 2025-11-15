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

source /dev/stdin <<< "$FUNCTIONS_FILE_PATH"
color
verb_ip6
catch_errors
setting_up_container
network_check
update_os

msg_info "Installing Dependencies"
$STD apt-get install -y curl
$STD apt-get install -y sudo
$STD apt-get install -y mc
$STD apt-get install -y git
msg_ok "Installed Dependencies"

msg_info "Installing Node.js v20 LTS"
$STD bash <(curl -fsSL https://deb.nodesource.com/setup_20.x)
$STD apt-get install -y nodejs
msg_ok "Installed Node.js v20 LTS"

msg_info "Setting up Utility Meter Dashboard"
INSTALL_DIR="/opt/utility-meter-dashboard"
mkdir -p $INSTALL_DIR
cd $INSTALL_DIR

# Clone the repository
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

systemctl enable -q --now utility-dashboard.service
msg_ok "Created systemd service"

msg_info "Checking service status"
sleep 3
if systemctl is-active --quiet utility-dashboard.service; then
    msg_ok "Service is running"
else
    msg_error "Service failed to start. Check logs with: journalctl -u utility-dashboard.service"
fi

motd_ssh
customize

msg_info "Cleaning up"
$STD apt-get -y autoremove
$STD apt-get -y autoclean
msg_ok "Cleaned"

msg_info "Downloading configuration wizard"
curl -fsSL https://raw.githubusercontent.com/overlandla/nebenkosten/main/dashboard/configure-dashboard.sh -o /usr/local/bin/configure-dashboard
chmod +x /usr/local/bin/configure-dashboard
msg_ok "Configuration wizard installed"

msg_info "Utility Meter Dashboard Installation Complete"

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
