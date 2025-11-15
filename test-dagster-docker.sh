#!/bin/bash
# Run Dagster tests inside Docker container

set -e

echo "🐳 Running Dagster tests in Docker container..."
echo ""

# Build test image
docker build -f Dockerfile.dagster -t dagster-test .

# Run tests
docker run --rm \
    -v $(pwd)/workflows-dagster:/app/workflows-dagster:ro \
    -v $(pwd)/config:/app/config:ro \
    -v $(pwd)/Nebenkosten/src:/app/Nebenkosten/src:ro \
    -e INFLUX_TOKEN=test-token \
    -e INFLUX_ORG=test-org \
    -e TIBBER_API_TOKEN=test-tibber-token \
    dagster-test \
    bash -c "
        cd /app/workflows-dagster && \
        pip install -q -r /app/requirements-test.txt && \
        pytest tests/ -v ${@}
    "

echo ""
echo "✅ Docker tests complete!"
