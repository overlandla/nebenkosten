#!/bin/bash

# Configuration Wizard for Utility Meter Dashboard
# This script helps configure the InfluxDB connection and other settings

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Installation directory
INSTALL_DIR="/opt/utility-meter-dashboard"
ENV_FILE="$INSTALL_DIR/.env.local"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root or with sudo${NC}"
    exit 1
fi

# Check if installation directory exists
if [ ! -d "$INSTALL_DIR" ]; then
    echo -e "${RED}Error: Installation directory not found at $INSTALL_DIR${NC}"
    echo -e "${YELLOW}Please run the installation script first${NC}"
    exit 1
fi

echo -e "${GREEN}=================================${NC}"
echo -e "${GREEN}Utility Meter Dashboard${NC}"
echo -e "${GREEN}Configuration Wizard${NC}"
echo -e "${GREEN}=================================${NC}"
echo ""

# Function to read input with default value
read_with_default() {
    local prompt="$1"
    local default="$2"
    local varname="$3"

    if [ -n "$default" ]; then
        echo -e "${BLUE}$prompt${NC} ${YELLOW}[$default]${NC}: "
    else
        echo -e "${BLUE}$prompt${NC}: "
    fi

    read -r input
    if [ -z "$input" ]; then
        eval "$varname='$default'"
    else
        eval "$varname='$input'"
    fi
}

# Load existing configuration if it exists
if [ -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}Existing configuration found. Current values will be shown as defaults.${NC}"
    echo ""

    # Source the existing env file to get current values
    source <(grep -E '^[A-Z_]+=' "$ENV_FILE" | sed 's/^/export /')
fi

# InfluxDB Configuration
echo -e "${GREEN}=== InfluxDB Configuration ===${NC}"
echo ""

read_with_default "InfluxDB URL (e.g., http://192.168.1.100:8086)" "${INFLUX_URL:-http://localhost:8086}" INFLUX_URL
read_with_default "InfluxDB Token" "${INFLUX_TOKEN:-}" INFLUX_TOKEN
read_with_default "InfluxDB Organization" "${INFLUX_ORG:-}" INFLUX_ORG
read_with_default "InfluxDB Raw Data Bucket" "${INFLUX_BUCKET_RAW:-homeassistant_raw}" INFLUX_BUCKET_RAW
read_with_default "InfluxDB Processed Data Bucket" "${INFLUX_BUCKET_PROCESSED:-homeassistant_processed}" INFLUX_BUCKET_PROCESSED

echo ""
echo -e "${GREEN}=== Gas Conversion Parameters ===${NC}"
echo -e "${YELLOW}(Used for converting between m³ and kWh for gas meters)${NC}"
echo ""

read_with_default "Gas Energy Content (kWh/m³)" "${GAS_ENERGY_CONTENT:-10.3}" GAS_ENERGY_CONTENT
read_with_default "Gas Z-Factor" "${GAS_Z_FACTOR:-0.95}" GAS_Z_FACTOR

echo ""
echo -e "${GREEN}=== Configuration Summary ===${NC}"
echo ""
echo -e "${BLUE}InfluxDB URL:${NC} $INFLUX_URL"
echo -e "${BLUE}InfluxDB Token:${NC} ${INFLUX_TOKEN:0:10}..." # Show only first 10 chars
echo -e "${BLUE}InfluxDB Org:${NC} $INFLUX_ORG"
echo -e "${BLUE}Raw Bucket:${NC} $INFLUX_BUCKET_RAW"
echo -e "${BLUE}Processed Bucket:${NC} $INFLUX_BUCKET_PROCESSED"
echo -e "${BLUE}Gas Energy Content:${NC} $GAS_ENERGY_CONTENT kWh/m³"
echo -e "${BLUE}Gas Z-Factor:${NC} $GAS_Z_FACTOR"
echo ""

# Confirm before writing
echo -e "${YELLOW}Do you want to save this configuration? (y/n)${NC}: "
read -r confirm

if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo -e "${RED}Configuration cancelled${NC}"
    exit 0
fi

# Write configuration file
echo ""
echo -e "${GREEN}Writing configuration to $ENV_FILE...${NC}"

cat > "$ENV_FILE" <<EOF
# InfluxDB Configuration
INFLUX_URL=$INFLUX_URL
INFLUX_TOKEN=$INFLUX_TOKEN
INFLUX_ORG=$INFLUX_ORG
INFLUX_BUCKET_RAW=$INFLUX_BUCKET_RAW
INFLUX_BUCKET_PROCESSED=$INFLUX_BUCKET_PROCESSED

# Gas Conversion Parameters
GAS_ENERGY_CONTENT=$GAS_ENERGY_CONTENT
GAS_Z_FACTOR=$GAS_Z_FACTOR
EOF

chmod 600 "$ENV_FILE"

echo -e "${GREEN}Configuration saved successfully!${NC}"
echo ""

# Test InfluxDB connection
echo -e "${YELLOW}Testing InfluxDB connection...${NC}"

if command -v curl &> /dev/null; then
    if curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Token $INFLUX_TOKEN" "$INFLUX_URL/health" | grep -q "200"; then
        echo -e "${GREEN}✓ InfluxDB connection successful!${NC}"
    else
        echo -e "${RED}✗ Could not connect to InfluxDB${NC}"
        echo -e "${YELLOW}Please verify your URL and token are correct${NC}"
        echo -e "${YELLOW}You can test manually with: curl -H 'Authorization: Token YOUR_TOKEN' $INFLUX_URL/health${NC}"
    fi
else
    echo -e "${YELLOW}curl not found, skipping connection test${NC}"
fi

echo ""

# Ask if user wants to restart the service
echo -e "${YELLOW}Do you want to restart the dashboard service now? (y/n)${NC}: "
read -r restart_confirm

if [[ "$restart_confirm" =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}Restarting utility-dashboard.service...${NC}"
    systemctl restart utility-dashboard.service

    sleep 2

    if systemctl is-active --quiet utility-dashboard.service; then
        echo -e "${GREEN}✓ Service restarted successfully!${NC}"
        echo ""

        # Get the IP address
        IP_ADDR=$(hostname -I | awk '{print $1}')

        echo -e "${GREEN}==================================${NC}"
        echo -e "${GREEN}Dashboard is now running!${NC}"
        echo -e "${GREEN}==================================${NC}"
        echo ""
        echo -e "${BLUE}Access URL:${NC} http://$IP_ADDR:3000"
        echo ""
        echo -e "${YELLOW}Useful commands:${NC}"
        echo -e "  View status: ${BLUE}systemctl status utility-dashboard.service${NC}"
        echo -e "  View logs:   ${BLUE}journalctl -u utility-dashboard.service -f${NC}"
        echo -e "  Restart:     ${BLUE}systemctl restart utility-dashboard.service${NC}"
        echo ""
    else
        echo -e "${RED}✗ Service failed to start${NC}"
        echo -e "${YELLOW}Check logs with: journalctl -u utility-dashboard.service -n 50${NC}"
    fi
else
    echo -e "${YELLOW}Service not restarted. To apply changes, run:${NC}"
    echo -e "${BLUE}systemctl restart utility-dashboard.service${NC}"
fi

echo ""
echo -e "${GREEN}Configuration complete!${NC}"
