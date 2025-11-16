#!/usr/bin/env bash

# Copyright (c) 2024
# Author: overlandla
# License: MIT
# https://github.com/overlandla/nebenkosten
#
# Source: https://github.com/overlandla/nebenkosten/tree/main/workflows_dagster
# This script installs the Dagster Utility Analysis Workflows as a Proxmox LXC container
#
# Usage:
#   - Run on Proxmox host: Creates LXC and installs Dagster workflows
#   - Run inside LXC: Updates existing installation
#
# Documentation: https://github.com/overlandla/nebenkosten/blob/main/workflows_dagster/PROXMOX_INSTALLATION.md

# Detect if we're running on Proxmox host (not inside container)
if [ -f /etc/pve/.version ] && [ ! -f /.dockerenv ] && [ ! -f /run/.containerenv ]; then
  # Running on Proxmox host - create LXC container
  source <(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/misc/build.func)

  # Application metadata
  APP="Dagster Workflows"
  var_tags="automation;data;dagster;docker"
  var_cpu="2"
  var_ram="4096"
  var_disk="8"
  var_os="debian"
  var_version="12"
  var_unprivileged="1"

  # Initialize Proxmox build environment
  header_info "$APP"
  variables
  color
  catch_errors

  # Update function - runs when script is executed inside existing LXC
  function update_script() {
    header_info
    check_container_storage
    check_container_resources

    if [[ ! -d /opt/dagster-workflows/nebenkosten/.git ]]; then
      msg_error "No ${APP} Installation Found!"
      exit
    fi

    msg_info "Stopping services"
    systemctl stop dagster-workflows.service 2>/dev/null || true
    cd /opt/dagster-workflows/nebenkosten
    $STD docker compose -f docker-compose.dagster.yml down
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

    msg_info "Updating ${APP}"
    cd /opt/dagster-workflows/nebenkosten

    # Update remote URL with stored auth if available
    if [ -f /root/.github_clone_url ]; then
      GITHUB_CLONE_URL=$(cat /root/.github_clone_url)
      git remote set-url origin "$GITHUB_CLONE_URL" 2>/dev/null || true
    fi

    $STD git fetch origin
    $STD git reset --hard origin/main
    msg_ok "Updated ${APP}"

    msg_info "Rebuilding Docker images"
    $STD docker compose -f docker-compose.dagster.yml build
    msg_ok "Rebuilt Docker images"

    msg_info "Starting services"
    docker compose -f docker-compose.dagster.yml up -d
    msg_ok "Started services"

    msg_ok "Updated Successfully!\n"
    exit
  }

  # Build the container (this creates LXC and runs install portion inside it)
  start
  build_container
  description

  # Show completion message
  msg_ok "Completed Successfully!\n"
  echo -e "${CREATING}${GN}${APP} setup has been successfully initialized!${CL}"
  echo -e "${INFO}${YW} Access it using the following URL:${CL}"
  echo -e "${TAB}${GATEWAY}${BGN}http://${IP}:3000${CL}"
  exit 0
fi

# ============================================================================
# INSTALLATION CODE (Runs inside LXC)
# ============================================================================

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
      systemctl stop dagster-workflows.service 2>/dev/null || true
      cd /opt/dagster-workflows/nebenkosten
      docker compose -f docker-compose.dagster.yml down 2>/dev/null || true
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

      # Update remote URL with stored auth if available
      if [ -f /root/.github_clone_url ]; then
        GITHUB_CLONE_URL=$(cat /root/.github_clone_url)
        git remote set-url origin "$GITHUB_CLONE_URL" 2>/dev/null || true
      fi

      git fetch origin
      git reset --hard origin/main
      msg_ok "Updated code"

      msg_info "Rebuilding Docker images"
      docker compose -f docker-compose.dagster.yml build
      msg_ok "Rebuilt Docker images"

      msg_info "Starting services"
      docker compose -f docker-compose.dagster.yml up -d
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

# Set $STD for quiet operation if not already set
STD="${STD:--qq}"

# GitHub Authentication Helper
# Checks if repo is accessible and prompts for token if needed
setup_github_auth() {
    REPO_URL="https://github.com/overlandla/nebenkosten.git"

    # Check if repo is accessible without auth
    if git ls-remote "$REPO_URL" >/dev/null 2>&1; then
        GITHUB_CLONE_URL="$REPO_URL"
        return 0
    fi

    # Repo requires authentication
    # Check for token in environment variable first
    if [ -n "$GITHUB_TOKEN" ]; then
        GITHUB_CLONE_URL="https://${GITHUB_TOKEN}@github.com/overlandla/nebenkosten.git"
        return 0
    fi

    # Prompt for token
    msg_info "Repository requires authentication"
    echo -e "${YW}Please enter your GitHub Personal Access Token:${CL}"
    echo -e "${BL}(Create one at: https://github.com/settings/tokens)${CL}"
    read -s GITHUB_TOKEN
    echo ""

    if [ -z "$GITHUB_TOKEN" ]; then
        msg_error "GitHub token is required for private repositories"
        exit 1
    fi

    GITHUB_CLONE_URL="https://${GITHUB_TOKEN}@github.com/overlandla/nebenkosten.git"
}

# Set up GitHub authentication
setup_github_auth

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

# Clone the repository (fresh installation)
msg_info "Cloning repository"
$STD git clone "$GITHUB_CLONE_URL"
cd nebenkosten

# Save GitHub clone URL for future updates
echo "$GITHUB_CLONE_URL" > /root/.github_clone_url
chmod 600 /root/.github_clone_url

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
msg_info "Starting Dagster services"
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
