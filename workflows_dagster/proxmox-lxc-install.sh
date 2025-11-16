#!/usr/bin/env bash

# Copyright (c) 2024
# Author: overlandla
# License: MIT
# https://github.com/overlandla/nebenkosten
#
# Source: https://github.com/overlandla/nebenkosten/tree/main/workflows_dagster
# This script installs the Dagster Utility Analysis Workflows as a Proxmox LXC container
#
# name: dagster-utility-workflows
# var_disk: 8
# var_cpu: 2
# var_ram: 4096
# var_os: debian
# var_version: 12
# var_unprivileged: 1
#
# Documentation: https://github.com/overlandla/nebenkosten/blob/main/workflows_dagster/PROXMOX_INSTALLATION.md

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
$STD apt-get install -y ca-certificates
$STD apt-get install -y gnupg
$STD apt-get install -y lsb-release
msg_ok "Installed Dependencies"

msg_info "Installing Docker"
# Add Docker's official GPG key
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
$STD apt-get update
$STD apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
msg_ok "Installed Docker"

msg_info "Starting Docker service"
systemctl enable docker
systemctl start docker
msg_ok "Docker service started"

msg_info "Setting up Dagster Workflows"
INSTALL_DIR="/opt/dagster-workflows"
mkdir -p $INSTALL_DIR
cd $INSTALL_DIR

# Clone the repository
msg_info "Cloning repository"
$STD git clone https://github.com/overlandla/nebenkosten.git
cd nebenkosten
msg_ok "Cloned repository"

msg_info "Creating secrets directory"
mkdir -p secrets
cat <<EOF > secrets/influxdb.env
# InfluxDB Configuration
# Edit this file with your actual values

# InfluxDB Authentication Token
INFLUX_TOKEN=your-influxdb-token-here

# InfluxDB Organization Name
INFLUX_ORG=your-org-name

# Optional: InfluxDB URL (override default in config.yaml)
# INFLUX_URL=http://192.168.1.75:8086

# Optional: Bucket names (override defaults in config.yaml)
# INFLUX_BUCKET_RAW=lampfi
# INFLUX_BUCKET_PROCESSED=lampfi_processed
EOF

cat <<EOF > secrets/tibber.env
# Tibber API Configuration
# Edit this file with your actual values (optional - only needed for Tibber sync)

# Tibber API Token
TIBBER_API_TOKEN=your-tibber-api-token-here

# Optional: Tibber API URL (override default)
# TIBBER_API_URL=https://api.tibber.com/v1-beta/gql
EOF

chmod 600 secrets/*.env
msg_ok "Created secrets directory"

msg_info "Creating config directory with defaults"
mkdir -p config
cat <<EOF > config/config.yaml
# Configuration will be generated on first run
# Or you can add your custom configuration here
influx:
  url: "http://192.168.1.75:8086"
  bucket_raw: "lampfi"
  bucket_processed: "lampfi_processed"
  timeout: 30000
  retry_attempts: 3
EOF
msg_ok "Created config directory"

msg_info "Building Docker images (this may take a few minutes)"
$STD docker compose -f docker-compose.dagster.yml build
msg_ok "Built Docker images"

msg_info "Creating systemd service"
cat <<EOF >/etc/systemd/system/dagster-workflows.service
[Unit]
Description=Dagster Utility Analysis Workflows
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$INSTALL_DIR/nebenkosten
ExecStart=/usr/bin/docker compose -f docker-compose.dagster.yml up -d
ExecStop=/usr/bin/docker compose -f docker-compose.dagster.yml down
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl enable dagster-workflows.service
msg_ok "Created systemd service"

msg_info "Starting Dagster services"
cd $INSTALL_DIR/nebenkosten
docker compose -f docker-compose.dagster.yml up -d
msg_ok "Started Dagster services"

msg_info "Waiting for services to be healthy"
sleep 15

# Check if services are running
if docker ps | grep -q dagster-webserver; then
    msg_ok "Dagster services are running"
else
    msg_info "Services may still be starting, check status with: docker ps"
fi

msg_info "Downloading configuration wizard"
curl -fsSL https://raw.githubusercontent.com/overlandla/nebenkosten/main/workflows_dagster/configure-dagster.sh -o /usr/local/bin/configure-dagster
chmod +x /usr/local/bin/configure-dagster
msg_ok "Configuration wizard installed"

motd_ssh
customize

msg_info "Cleaning up"
$STD apt-get -y autoremove
$STD apt-get -y autoclean
msg_ok "Cleaned"

msg_info "Dagster Utility Workflows Installation Complete"

# Get the IP address
IP_ADDR=$(hostname -I | awk '{print $1}')

echo -e "\n${GN}╔════════════════════════════════════════════════════════════╗${CL}"
echo -e "${GN}║  Dagster Utility Workflows - Installation Complete!       ║${CL}"
echo -e "${GN}╚════════════════════════════════════════════════════════════╝${CL}\n"

echo -e "${BL}Dagster UI:${CL} ${GN}http://$IP_ADDR:3000${CL}\n"

echo -e "${YW}⚠️  NEXT STEPS:${CL}\n"
echo -e "${BL}1.${CL} Configure InfluxDB connection:"
echo -e "   Run: ${GN}configure-dagster${CL}"
echo -e "   Or edit manually: ${BL}$INSTALL_DIR/nebenkosten/secrets/influxdb.env${CL}\n"

echo -e "${BL}2.${CL} After configuration, restart the services:"
echo -e "   ${GN}cd $INSTALL_DIR/nebenkosten && docker compose -f docker-compose.dagster.yml restart${CL}\n"

echo -e "${BL}3.${CL} Enable schedules in Dagster UI:"
echo -e "   - Navigate to Automation → Schedules"
echo -e "   - Enable 'analytics_daily' and optionally 'tibber_sync_hourly'\n"

echo -e "${YW}📋 Useful Commands:${CL}"
echo -e "  ${BL}configure-dagster${CL}                                    - Run configuration wizard"
echo -e "  ${BL}systemctl status dagster-workflows.service${CL}          - Check service status"
echo -e "  ${BL}docker ps${CL}                                            - View running containers"
echo -e "  ${BL}docker compose -f docker-compose.dagster.yml logs -f${CL} - View live logs"
echo -e "  ${BL}docker compose -f docker-compose.dagster.yml restart${CL} - Restart services\n"

echo -e "${YW}🐳 Container Management:${CL}"
echo -e "  ${BL}cd $INSTALL_DIR/nebenkosten${CL}"
echo -e "  ${BL}docker compose -f docker-compose.dagster.yml ps${CL}     - List services"
echo -e "  ${BL}docker compose -f docker-compose.dagster.yml logs [service]${CL} - View logs\n"

echo -e "${YW}📚 Documentation:${CL}"
echo -e "  ${BL}https://github.com/overlandla/nebenkosten/blob/main/workflows_dagster/README.md${CL}\n"
