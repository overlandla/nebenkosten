#!/bin/bash
# Quick start script for Dagster workflows (systemd native deployment)

set -e

echo "🚀 Starting Dagster Utility Analysis Workflows..."
echo ""

# Validate environment files exist
echo "🔍 Validating environment configuration..."
./validate-env.sh
echo ""

# Start services in order
echo "📡 Starting Dagster services..."
sudo systemctl start dagster-user-code.service
sleep 2
sudo systemctl start dagster-daemon.service
sleep 2
sudo systemctl start dagster-webserver.service

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check health
if systemctl is-active --quiet dagster-webserver.service; then
    echo "✅ Dagster services are running!"
    echo ""
    echo "🌐 Dagster UI: http://localhost:3000"
    echo ""
    echo "📊 Service status:"
    systemctl status dagster-user-code.service --no-pager -l | head -n 3
    systemctl status dagster-daemon.service --no-pager -l | head -n 3
    systemctl status dagster-webserver.service --no-pager -l | head -n 3
    echo ""
    echo "📝 Next steps:"
    echo "  1. Open http://localhost:3000 in your browser"
    echo "  2. Navigate to Assets to see the pipeline"
    echo "  3. Go to Automation → Schedules to enable schedules"
    echo "  4. Or manually trigger jobs from the Jobs tab"
    echo ""
    echo "📋 Useful commands:"
    echo "  journalctl -u dagster-webserver -f  # View webserver logs"
    echo "  journalctl -u dagster-daemon -f     # View daemon logs"
    echo "  systemctl status dagster-*          # Check all services"
else
    echo "❌ Failed to start Dagster services"
    echo "Check logs with: journalctl -u dagster-webserver -n 50"
    exit 1
fi
