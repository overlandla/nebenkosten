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

  # Override build_container to use our custom install script
  function build_container() {
    # Call the original container creation logic
    msg_info "Allocating disk space"
    DISK_REF="$STORAGE:$DISK_SIZE"
    if [ "$STORAGE_TYPE" = "dir" ] || [ "$STORAGE_TYPE" = "nfs" ]; then
      DISK_REF="$STORAGE:0"
    fi

    msg_info "Creating LXC Container"
    DISK_PARAM="${STORAGE}:${DISK_SIZE}"
    if [ "$STORAGE_TYPE" = "dir" ] || [ "$STORAGE_TYPE" = "nfs" ]; then
      DISK_PARAM="${STORAGE}:0"
    fi

    # Run pct create in a subshell to isolate from error trap
    (
      set +eE
      trap - ERR
      pct create $CTID $TEMPLATE_STOR \
        -arch $(dpkg --print-architecture) \
        -cmode shell \
        -cores $CORE_COUNT \
        -description "# ${APP} LXC
## Created using https://github.com/overlandla/nebenkosten
" \
        -features $FEATURES \
        -hostname $NSAPP \
        -memory $RAM_SIZE \
        -net0 name=eth0,bridge=$BRG,ip=$NET \
        -onboot $START_ON_BOOT \
        -ostype debian \
        -rootfs $DISK_PARAM \
        -swap $SWAP_SIZE \
        -tags proxmox \
        -unprivileged $UNPRIV
    )
    PCT_CREATE_EXIT=$?

    if [ $PCT_CREATE_EXIT -ne 0 ]; then
      msg_error "Failed to create LXC container (exit code: $PCT_CREATE_EXIT)"
      exit $PCT_CREATE_EXIT
    fi
    msg_ok "LXC Container $CTID was successfully created"

    msg_info "Starting LXC Container"
    pct start $CTID
    msg_ok "Started LXC Container"

    msg_info "Checking network connectivity"
    pct exec $CTID -- bash -c "for i in {1..30}; do ping -c1 1.1.1.1 &>/dev/null && break; sleep 1; done"
    msg_ok "Network in LXC is reachable (ping)"

    # Export the install helper functions for the install script
    if [ "$var_os" = "alpine" ]; then
      export FUNCTIONS_FILE_PATH="$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/misc/alpine-install.func)"
    else
      export FUNCTIONS_FILE_PATH="$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/misc/install.func)"
    fi

    # Use our custom install script from our repository
    msg_info "Installing ${APP}"
    pct exec $CTID -- bash -c "FUNCTIONS_FILE_PATH='$FUNCTIONS_FILE_PATH' bash <(curl -fsSL https://raw.githubusercontent.com/overlandla/nebenkosten/main/dashboard/install/utility-meter-dashboard-install.sh)"
    msg_ok "Installed ${APP}"

    # Run customization if function exists
    if command -v customize &> /dev/null; then
      msg_info "Customizing Container"
      customize
      msg_ok "Customized Container"
    fi
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
# UPDATE CODE (Runs inside LXC when executed directly)
# ============================================================================

# If we're inside an LXC and being run directly, run the install/update script
msg_info "Downloading and running install/update script"
bash <(curl -fsSL https://raw.githubusercontent.com/overlandla/nebenkosten/main/dashboard/install/utility-meter-dashboard-install.sh)
