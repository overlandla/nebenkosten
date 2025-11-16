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

    if [[ ! -d /opt/dagster-workflows/nebenkosten/.git ]]; then
      msg_error "No ${APP} Installation Found!"
      exit
    fi

    msg_info "Downloading update script"
    bash <(curl -fsSL https://raw.githubusercontent.com/overlandla/nebenkosten/main/workflows_dagster/install/dagster-workflows-install.sh)
    exit
  }

  # Set custom description for the container
  export PCT_OPTIONS="-description \"# ${APP} LXC
## Created using https://github.com/overlandla/nebenkosten
\""

  # Override build_container to use framework creation with our custom install
  function build_container() {
    # Source (not execute in subshell) the framework's container creation script
    # This preserves variables like CTID in the current shell
    source <(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/misc/create_lxc.sh)

    # Now CTID is set, continue with setup
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
    pct exec "$CTID" -- bash <(curl -fsSL https://raw.githubusercontent.com/overlandla/nebenkosten/main/workflows_dagster/install/dagster-workflows-install.sh)
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
bash <(curl -fsSL https://raw.githubusercontent.com/overlandla/nebenkosten/main/workflows_dagster/install/dagster-workflows-install.sh)
