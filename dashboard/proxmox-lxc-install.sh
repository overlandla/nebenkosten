#!/usr/bin/env bash

# Copyright (c) 2024
# Author: Your Name
# License: MIT
# https://github.com/overlandla/nebenkosten
#
# Source: https://github.com/overlandla/nebenkosten/tree/main/dashboard
# This script installs the Utility Meter Dashboard as a Proxmox LXC container
#
# Usage:
#   - Run on Proxmox host: Creates LXC and installs dashboard
#   - Run inside LXC: Updates existing installation
#
# Documentation: https://github.com/overlandla/nebenkosten/blob/main/dashboard/PROXMOX_INSTALLATION.md

# Detect if we're running on Proxmox host (not inside container)
if [ -f /etc/pve/.version ] && [ ! -f /.dockerenv ] && [ ! -f /run/.containerenv ]; then
  # Running on Proxmox host - create LXC container
  source <(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/misc/build.func)

  # Application metadata
  APP="Utility Meter Dashboard"
  var_tags="utilities;monitoring;dashboard;nextjs"
  var_cpu="2"
  var_ram="2048"
  var_disk="4"
  var_os="debian"
  var_version="12"
  var_unprivileged="1"
  var_install=""  # Disable framework's default install script

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

    if [[ ! -f /opt/utility-meter-dashboard/package.json ]]; then
      msg_error "No ${APP} Installation Found!"
      exit
    fi

    msg_info "Downloading update script"
    bash <(curl -fsSL https://raw.githubusercontent.com/overlandla/nebenkosten/main/dashboard/install/utility-meter-dashboard-install.sh)
    exit
  }

  # Set custom description for the container
  export PCT_OPTIONS="-description \"# ${APP} LXC
## Created using https://github.com/overlandla/nebenkosten
\""

  # Override build_container to use framework creation with our custom install
  function build_container() {
    # Use framework's container creation
    bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/misc/create_lxc.sh)"

    # Framework handles starting and network check automatically
    msg_info "Starting LXC Container"
    pct start "$CTID"
    msg_ok "Started LXC Container"

    msg_info "Waiting for LXC network to be reachable"
    pct exec "$CTID" -- bash -c "for i in {1..30}; do ping -c1 1.1.1.1 &>/dev/null && break; sleep 1; done"
    msg_ok "Network in LXC is reachable (ping)"

    # Set up locale and install base packages
    msg_info "Setting up Container OS"
    pct exec "$CTID" -- bash -c "
      apt-get update &>/dev/null
      apt-get install -y curl sudo mc &>/dev/null
    "
    msg_ok "Set up Container OS"

    # Run our custom install script
    msg_info "Installing ${APP}"
    pct exec "$CTID" -- bash <(curl -fsSL https://raw.githubusercontent.com/overlandla/nebenkosten/main/dashboard/install/utility-meter-dashboard-install.sh)
    msg_ok "Installed ${APP}"
  }

  # Build the container (this creates LXC and runs install portion inside it)
  start
  description

  # Show completion message
  msg_ok "Completed Successfully!\n"
  echo -e "${CREATING}${GN}${APP} setup has been successfully initialized!${CL}"
  echo -e "${INFO}${YW} Access it using the following URL:${CL}"
  echo -e "${TAB}${GATEWAY}${BGN}http://${IP}:3000${CL}"
  exit 0
fi

# ============================================================================
# UPDATE CODE (Runs inside LXC when executed directly)
# ============================================================================

# If we're inside an LXC and being run directly, run the install/update script
msg_info "Downloading and running install/update script"
bash <(curl -fsSL https://raw.githubusercontent.com/overlandla/nebenkosten/main/dashboard/install/utility-meter-dashboard-install.sh)
