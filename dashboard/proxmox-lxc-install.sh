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

set -e

# Detect if we're running on Proxmox host (not inside container)
if [ -f /etc/pve/.version ] && [ ! -f /.dockerenv ] && [ ! -f /run/.containerenv ]; then
  # Running on Proxmox host - create LXC container

  echo "Creating Utility Meter Dashboard LXC Container..."

  # Get next available CT ID
  CTID=$(pvesh get /cluster/nextid)

  # Configuration
  STORAGE="local-lvm"
  TEMPLATE_STORAGE="local"
  TEMPLATE="debian-12-standard_12.7-1_amd64.tar.zst"
  HOSTNAME="utility-dashboard"
  CORES="2"
  MEMORY="2048"
  DISK="4"

  # Download template if needed
  if ! pveam list $TEMPLATE_STORAGE | grep -q $TEMPLATE; then
    echo "Downloading Debian 12 template..."
    pveam download $TEMPLATE_STORAGE $TEMPLATE
  fi

  # Create container
  echo "Creating container $CTID..."
  pct create $CTID $TEMPLATE_STORAGE:vztmpl/$TEMPLATE \
    --hostname $HOSTNAME \
    --cores $CORES \
    --memory $MEMORY \
    --rootfs $STORAGE:$DISK \
    --net0 name=eth0,bridge=vmbr0,ip=dhcp \
    --unprivileged 1 \
    --features nesting=1 \
    --onboot 0

  # Start container
  echo "Starting container..."
  pct start $CTID

  # Wait for network
  echo "Waiting for network..."
  sleep 5

  # Install
  echo "Running installation..."
  pct exec $CTID -- bash -c "curl -fsSL https://raw.githubusercontent.com/overlandla/nebenkosten/main/dashboard/install/utility-meter-dashboard-install.sh | bash"

  # Get IP
  IP=$(pct exec $CTID -- hostname -I | awk '{print $1}')

  echo ""
  echo "✓ Installation complete!"
  echo "  Container ID: $CTID"
  echo "  Access at: http://${IP}:3000"
  echo ""

  exit 0
fi

# ============================================================================
# UPDATE CODE (Runs inside LXC when executed directly)
# ============================================================================

# If we're inside an LXC and being run directly, run the install/update script
echo "Running install/update script..."
bash <(curl -fsSL https://raw.githubusercontent.com/overlandla/nebenkosten/main/dashboard/install/utility-meter-dashboard-install.sh)
