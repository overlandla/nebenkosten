#!/bin/bash
# Quick start script for Dagster workflows

set -e

echo "🚀 Starting Dagster Utility Analysis Workflows..."
echo ""

# Validate environment files exist
echo "🔍 Validating environment configuration..."
./validate-env.sh
echo ""

# Check if network exists, create if not
if ! docker network inspect utility-network >/dev/null 2>&1; then
    echo "📡 Creating utility-network..."
    docker network create utility-network
fi

# Start services
echo "🐳 Starting Dagster services..."
docker-compose -f docker-compose.dagster.yml up -d --build

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check health
if docker ps | grep -q dagster-webserver; then
    echo "✅ Dagster services are running!"
    echo ""
    echo "🌐 Dagster UI: http://localhost:3000"
    echo ""
    echo "📊 Available services:"
    docker-compose -f docker-compose.dagster.yml ps
    echo ""
    echo "📝 Next steps:"
    echo "  1. Open http://localhost:3000 in your browser"
    echo "  2. Navigate to Assets to see the pipeline"
    echo "  3. Go to Automation → Schedules to enable schedules"
    echo "  4. Or manually trigger jobs from the Jobs tab"
else
    echo "❌ Failed to start Dagster services"
    echo "Check logs with: docker-compose -f docker-compose.dagster.yml logs"
    exit 1
fi
