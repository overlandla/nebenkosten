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

set -e

# Detect if we're running on Proxmox host (not inside container)
if [ -f /etc/pve/.version ] && [ ! -f /.dockerenv ] && [ ! -f /run/.containerenv ]; then
  # Running on Proxmox host - create LXC container

  echo "Creating Dagster Workflows LXC Container..."

  # Get next available CT ID
  CTID=$(pvesh get /cluster/nextid)

  # Configuration
  STORAGE="local-lvm"
  TEMPLATE_STORAGE="local"
  TEMPLATE="debian-12-standard_12.7-1_amd64.tar.zst"
  HOSTNAME="dagster-workflows"
  CORES="2"
  MEMORY="4096"
  DISK="8"

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
  sleep 10

  # Install base packages
  echo "Installing base packages (curl, etc)..."
  pct exec $CTID -- bash -c "apt-get update -qq && apt-get install -y -qq curl sudo"

  # Install
  echo "Running installation..."
  pct exec $CTID -- bash -c "curl -fsSL https://raw.githubusercontent.com/overlandla/nebenkosten/main/workflows_dagster/install/dagster-workflows-install.sh | bash"

  # Get IP
  IP=$(pct exec $CTID -- hostname -I | awk '{print $1}')

  echo ""
  echo "✓ Installation complete!"
  echo "  Container ID: $CTID"
  echo "  IP Address: $IP"
  echo "  Dagster: http://${IP}:3000"
  echo ""
  echo "To access container shell: pct enter $CTID"
  echo ""

  exit 0
fi

# ============================================================================
# UPDATE CODE (Runs inside LXC when executed directly)
# ============================================================================

# If we're inside an LXC and being run directly, run the install/update script
echo "Running install/update script..."
bash <(curl -fsSL https://raw.githubusercontent.com/overlandla/nebenkosten/main/workflows_dagster/install/dagster-workflows-install.sh)
