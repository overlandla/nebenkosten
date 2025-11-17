#!/usr/bin/env bash

# Quick fix script for common installation issues
# Run this on your LXC if the diagnostic script found errors

set -e

# Colors
BL="\033[36m"
GN="\033[1;92m"
CL="\033[m"
YW="\033[1;33m"
RD="\033[01;31m"

msg_info() { echo -e "${BL}[INFO]${CL} $1"; }
msg_ok() { echo -e "${GN}[OK]${CL} $1"; }
msg_error() { echo -e "${RD}[ERROR]${CL} $1"; }

echo -e "${BL}═══════════════════════════════════════════════════════${CL}"
echo -e "${BL}  Dagster Installation Fix Script${CL}"
echo -e "${BL}═══════════════════════════════════════════════════════${CL}\n"

BASE_DIR="/opt/dagster-workflows/nebenkosten"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    msg_error "Please run as root (use sudo)"
    exit 1
fi

# Check if base directory exists
if [ ! -d "$BASE_DIR" ]; then
    msg_error "Base directory not found: $BASE_DIR"
    msg_error "Please run the full installation script first"
    exit 1
fi

msg_info "Creating missing directories"
mkdir -p "$BASE_DIR/logs"
mkdir -p "$BASE_DIR/storage"
msg_ok "Created logs and storage directories"

msg_info "Creating missing secrets file"
if [ ! -f "$BASE_DIR/secrets/influxdb.env" ]; then
    cat > "$BASE_DIR/secrets/influxdb.env" <<'EOF'
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
    chmod 600 "$BASE_DIR/secrets/influxdb.env"
    msg_ok "Created influxdb.env"
else
    msg_ok "influxdb.env already exists"
fi

msg_info "Creating optional secrets file"
if [ ! -f "$BASE_DIR/secrets/tibber.env" ]; then
    cat > "$BASE_DIR/secrets/tibber.env" <<'EOF'
# Tibber API Configuration
# Edit this file with your actual values (optional - only needed for Tibber sync)

# Tibber API Token
TIBBER_API_TOKEN=your-tibber-api-token-here

# Optional: Tibber API URL (override default)
# TIBBER_API_URL=https://api.tibber.com/v1-beta/gql
EOF
    chmod 600 "$BASE_DIR/secrets/tibber.env"
    msg_ok "Created tibber.env"
else
    msg_ok "tibber.env already exists"
fi

msg_info "Fixing ownership"
chown -R dagster:dagster /opt/dagster-workflows
msg_ok "Set ownership to dagster:dagster"

msg_info "Copying systemd service files"
cp "$BASE_DIR/workflows_dagster/systemd/dagster-webserver.service" /etc/systemd/system/
cp "$BASE_DIR/workflows_dagster/systemd/dagster-daemon.service" /etc/systemd/system/
cp "$BASE_DIR/workflows_dagster/systemd/dagster-user-code.service" /etc/systemd/system/
msg_ok "Copied service files"

msg_info "Reloading systemd"
systemctl daemon-reload
msg_ok "Systemd reloaded"

msg_info "Enabling services"
systemctl enable dagster-user-code.service
systemctl enable dagster-daemon.service
systemctl enable dagster-webserver.service
msg_ok "Services enabled"

msg_info "Starting services"
systemctl start dagster-user-code.service
sleep 3
systemctl start dagster-daemon.service
sleep 2
systemctl start dagster-webserver.service
msg_ok "Services started"

echo -e "\n${BL}Checking service status...${CL}\n"
systemctl status dagster-user-code.service --no-pager -l || true
echo ""
systemctl status dagster-daemon.service --no-pager -l || true
echo ""
systemctl status dagster-webserver.service --no-pager -l || true

echo -e "\n${GN}═══════════════════════════════════════════════════════${CL}"
echo -e "${GN}  Fix Complete!${CL}"
echo -e "${GN}═══════════════════════════════════════════════════════${CL}\n"

IP_ADDR=$(hostname -I | awk '{print $1}')
echo -e "${BL}Dagster UI:${CL} ${GN}http://$IP_ADDR:3000${CL}\n"

echo -e "${YW}⚠️  IMPORTANT:${CL}"
echo -e "Edit the secrets file with your actual InfluxDB credentials:"
echo -e "${BL}$BASE_DIR/secrets/influxdb.env${CL}\n"

echo -e "Then restart services:"
echo -e "${GN}systemctl restart dagster-user-code dagster-daemon dagster-webserver${CL}\n"
