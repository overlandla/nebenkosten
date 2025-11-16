#!/bin/bash
# Stop script for Dagster workflows (systemd native deployment)

set -e

echo "🛑 Stopping Dagster Utility Analysis Workflows..."

# Stop services in reverse order
sudo systemctl stop dagster-webserver.service
sudo systemctl stop dagster-daemon.service
sudo systemctl stop dagster-user-code.service

echo "✅ Dagster services stopped"
echo ""
echo "Note: All data is preserved in /opt/dagster-workflows/nebenkosten/"
echo ""
echo "To restart services, run:"
echo "  ./start-dagster.sh"
echo "  or: systemctl start dagster-*"
