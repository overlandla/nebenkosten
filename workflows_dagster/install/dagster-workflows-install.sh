#!/usr/bin/env bash

# Copyright (c) 2024
# Author: overlandla
# License: MIT
# https://github.com/overlandla/nebenkosten
#
# This script installs the Dagster Utility Analysis Workflows inside an LXC container
# Native systemd deployment (no Docker) for better performance and simplicity

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
    if [ -d /opt/dagster-workflows/nebenkosten/.git ]; then
      # Existing installation found - run update
      msg_info "Existing installation detected - running update"

      msg_info "Stopping services"
      systemctl stop dagster-webserver.service 2>/dev/null || true
      systemctl stop dagster-daemon.service 2>/dev/null || true
      systemctl stop dagster-user-code.service 2>/dev/null || true
      msg_ok "Stopped services"

      if [ -d /opt/dagster-workflows/nebenkosten/secrets ]; then
        msg_info "Backing up secrets"
        cp -r /opt/dagster-workflows/nebenkosten/secrets /opt/dagster-workflows/nebenkosten/secrets.backup.$(date +%Y%m%d_%H%M%S)
        msg_ok "Secrets backed up"
      fi
      if [ -d /opt/dagster-workflows/nebenkosten/config ]; then
        msg_info "Backing up config"
        cp -r /opt/dagster-workflows/nebenkosten/config /opt/dagster-workflows/nebenkosten/config.backup.$(date +%Y%m%d_%H%M%S)
        msg_ok "Config backed up"
      fi

      msg_info "Updating code"
      cd /opt/dagster-workflows/nebenkosten
      git fetch origin
      git reset --hard origin/main
      msg_ok "Updated code"

      msg_info "Updating Python dependencies"
      /opt/dagster-workflows/venv/bin/pip install -q --upgrade -r requirements-dagster.txt
      msg_ok "Updated dependencies"

      msg_info "Starting services"
      systemctl start dagster-user-code.service
      systemctl start dagster-daemon.service
      systemctl start dagster-webserver.service
      msg_ok "Started services"

      echo -e "\n${GN}╔════════════════════════════════════════════════════════════╗${CL}"
      echo -e "${GN}║  Dagster Workflows - Update Complete!                     ║${CL}"
      echo -e "${GN}╚════════════════════════════════════════════════════════════╝${CL}\n"

      IP_ADDR=$(hostname -I | awk '{print $1}')
      echo -e "${BL}Dagster UI:${CL} ${GN}http://$IP_ADDR:3000${CL}\n"
      exit 0
    fi

    # Fresh install - continue with normal installation
    msg_info "Updating system packages"
    apt-get update
    apt-get -y upgrade
    msg_ok "System packages updated"
fi

msg_info "Installing Dependencies"
apt-get install -y curl >/dev/null 2>&1
apt-get install -y sudo >/dev/null 2>&1
apt-get install -y mc >/dev/null 2>&1
apt-get install -y git >/dev/null 2>&1
apt-get install -y ca-certificates >/dev/null 2>&1
apt-get install -y gnupg >/dev/null 2>&1
apt-get install -y lsb-release >/dev/null 2>&1
msg_ok "Installed Dependencies"

msg_info "Installing Python 3.11 and development tools"
apt-get install -y python3 python3-pip python3-venv python3-dev build-essential libpq-dev >/dev/null 2>&1
msg_ok "Installed Python 3.11"

msg_info "Installing PostgreSQL"
# Download and run PostgreSQL setup script
curl -fsSL https://raw.githubusercontent.com/overlandla/nebenkosten/main/workflows_dagster/install/setup-postgresql.sh -o /tmp/setup-postgresql.sh
chmod +x /tmp/setup-postgresql.sh
bash /tmp/setup-postgresql.sh
rm /tmp/setup-postgresql.sh
msg_ok "PostgreSQL installed and configured"

msg_info "Creating dagster user and group"
if ! id -u dagster >/dev/null 2>&1; then
    useradd -r -s /bin/bash -d /opt/dagster-workflows -m dagster
    msg_ok "Created dagster user"
else
    msg_ok "Dagster user already exists"
fi

msg_info "Setting up Dagster Workflows"
INSTALL_DIR="/opt/dagster-workflows"
REPO_DIR="$INSTALL_DIR/nebenkosten"
mkdir -p $INSTALL_DIR
cd $INSTALL_DIR

# Clone the repository (fresh installation)
msg_info "Cloning repository"
$STD git clone https://github.com/overlandla/nebenkosten.git
cd nebenkosten
msg_ok "Cloned repository"

msg_info "Creating Python virtual environment"
python3 -m venv $INSTALL_DIR/venv
msg_ok "Created virtual environment"

msg_info "Installing Python dependencies (this may take a few minutes)"
$INSTALL_DIR/venv/bin/pip install -q --upgrade pip
$INSTALL_DIR/venv/bin/pip install -q -r requirements-dagster.txt
msg_ok "Installed Python dependencies"

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

msg_info "Creating Tibber secrets file"
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

msg_info "Creating logs and storage directories"
mkdir -p logs storage
msg_ok "Created directories"

msg_info "Setting ownership to dagster user"
chown -R dagster:dagster $INSTALL_DIR
msg_ok "Set ownership"

msg_info "Installing systemd service files"
cp $REPO_DIR/workflows_dagster/systemd/dagster-webserver.service /etc/systemd/system/
cp $REPO_DIR/workflows_dagster/systemd/dagster-daemon.service /etc/systemd/system/
cp $REPO_DIR/workflows_dagster/systemd/dagster-user-code.service /etc/systemd/system/
systemctl daemon-reload
msg_ok "Installed systemd services"

msg_info "Enabling and starting Dagster services"
systemctl enable dagster-user-code.service
systemctl enable dagster-daemon.service
systemctl enable dagster-webserver.service

systemctl start dagster-user-code.service
sleep 3
systemctl start dagster-daemon.service
sleep 2
systemctl start dagster-webserver.service
msg_ok "Dagster services started"

msg_info "Waiting for services to be ready"
sleep 10

# Check if services are running
if systemctl is-active --quiet dagster-webserver.service; then
    msg_ok "Dagster webserver is running"
else
    msg_error "Dagster webserver failed to start - check logs with: journalctl -u dagster-webserver -n 50"
fi

msg_info "Installing management scripts"
curl -fsSL https://raw.githubusercontent.com/overlandla/nebenkosten/main/workflows_dagster/configure-dagster.sh -o /usr/local/bin/configure-dagster
chmod +x /usr/local/bin/configure-dagster
msg_ok "Configuration wizard installed"

# Only run motd and customize if functions are available (Proxmox environment)
if command -v motd_ssh &> /dev/null; then
    motd_ssh
fi
if command -v customize &> /dev/null; then
    customize
fi

msg_info "Cleaning up"
apt-get -y autoremove >/dev/null 2>&1
apt-get -y autoclean >/dev/null 2>&1
msg_ok "Cleaned"

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
echo -e "   ${GN}systemctl restart dagster-user-code dagster-daemon dagster-webserver${CL}\n"

echo -e "${BL}3.${CL} Enable schedules in Dagster UI:"
echo -e "   - Navigate to Automation → Schedules"
echo -e "   - Enable 'analytics_daily' and optionally 'tibber_sync_hourly'\n"

echo -e "${YW}📋 Useful Commands:${CL}"
echo -e "  ${BL}configure-dagster${CL}                         - Run configuration wizard"
echo -e "  ${BL}systemctl status dagster-*${CL}                - Check all Dagster services"
echo -e "  ${BL}journalctl -u dagster-webserver -f${CL}        - View webserver logs"
echo -e "  ${BL}journalctl -u dagster-daemon -f${CL}           - View daemon logs"
echo -e "  ${BL}journalctl -u dagster-user-code -f${CL}        - View user code logs"
echo -e "  ${BL}systemctl restart dagster-*${CL}               - Restart all services\n"

echo -e "${YW}🔧 Service Management:${CL}"
echo -e "  ${BL}systemctl start dagster-webserver${CL}         - Start webserver"
echo -e "  ${BL}systemctl stop dagster-webserver${CL}          - Stop webserver"
echo -e "  ${BL}systemctl restart dagster-*${CL}               - Restart all Dagster services\n"

echo -e "${YW}💾 Resource Usage:${CL}"
echo -e "  ${BL}Memory:${CL} ~1-1.5GB (vs 2-3GB with Docker)"
echo -e "  ${BL}Disk:${CL} ~500MB (vs 2GB+ with Docker images)\n"

echo -e "${YW}📚 Documentation:${CL}"
echo -e "  ${BL}https://github.com/overlandla/nebenkosten/blob/main/workflows_dagster/README.md${CL}\n"
