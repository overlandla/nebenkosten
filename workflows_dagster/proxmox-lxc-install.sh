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
REPO_DIR="$INSTALL_DIR/nebenkosten"
mkdir -p $INSTALL_DIR
cd $INSTALL_DIR

# Detect if this is an update or fresh install
if [ -d "$REPO_DIR/.git" ]; then
    IS_UPDATE=true
    msg_info "Existing installation detected - running update"

    # Stop services if running
    if systemctl is-active --quiet dagster-workflows.service; then
        msg_info "Stopping services for update"
        systemctl stop dagster-workflows.service
        cd "$REPO_DIR"
        docker compose -f docker-compose.dagster.yml down
    fi

    # Backup existing configuration
    if [ -d "$REPO_DIR/secrets" ]; then
        msg_info "Backing up existing secrets"
        cp -r "$REPO_DIR/secrets" "$REPO_DIR/secrets.backup.$(date +%Y%m%d_%H%M%S)"
        msg_ok "Secrets backed up"
    fi
    if [ -d "$REPO_DIR/config" ]; then
        msg_info "Backing up existing config"
        cp -r "$REPO_DIR/config" "$REPO_DIR/config.backup.$(date +%Y%m%d_%H%M%S)"
        msg_ok "Config backed up"
    fi

    # Pull latest changes
    msg_info "Pulling latest code from repository"
    cd "$REPO_DIR"
    $STD git fetch origin
    $STD git reset --hard origin/main
    msg_ok "Code updated"
else
    IS_UPDATE=false
    msg_info "Fresh installation detected"

    # Clone the repository
    msg_info "Cloning repository"
    $STD git clone https://github.com/overlandla/nebenkosten.git
    cd nebenkosten
    msg_ok "Cloned repository"
fi

cd "$REPO_DIR"

# Only create secrets if they don't exist (fresh install or if missing)
if [ ! -f secrets/influxdb.env ]; then
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
    chmod 600 secrets/influxdb.env
    msg_ok "Created influxdb.env"
else
    msg_ok "Preserving existing InfluxDB configuration"
fi

if [ ! -f secrets/tibber.env ]; then
    msg_info "Creating Tibber secrets file"
    mkdir -p secrets
    cat <<EOF > secrets/tibber.env
# Tibber API Configuration
# Edit this file with your actual values (optional - only needed for Tibber sync)

# Tibber API Token
TIBBER_API_TOKEN=your-tibber-api-token-here

# Optional: Tibber API URL (override default)
# TIBBER_API_URL=https://api.tibber.com/v1-beta/gql
EOF
    chmod 600 secrets/tibber.env
    msg_ok "Created tibber.env"
else
    msg_ok "Preserving existing Tibber configuration"
fi

# Only create config if it doesn't exist
if [ ! -f config/config.yaml ]; then
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
else
    msg_ok "Preserving existing config"
fi

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

systemctl daemon-reload
systemctl enable dagster-workflows.service

if [ "$IS_UPDATE" = true ]; then
    msg_info "Restarting Dagster services after update"
else
    msg_info "Starting Dagster services"
fi
cd "$REPO_DIR"
docker compose -f docker-compose.dagster.yml up -d
msg_ok "Dagster services started"

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

if [ "$IS_UPDATE" = true ]; then
    msg_info "Dagster Utility Workflows Update Complete"
else
    msg_info "Dagster Utility Workflows Installation Complete"
fi

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
