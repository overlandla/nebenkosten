#!/bin/bash
# Stop script for Dagster workflows

set -e

echo "🛑 Stopping Dagster Utility Analysis Workflows..."
docker-compose -f docker-compose.dagster.yml down

echo "✅ Dagster services stopped"
echo ""
echo "Note: Data is preserved in Docker volumes"
echo "To completely remove including data, run:"
echo "  docker-compose -f docker-compose.dagster.yml down -v"
