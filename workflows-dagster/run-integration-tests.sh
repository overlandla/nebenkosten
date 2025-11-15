#!/bin/bash
set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Dagster Integration Test Runner                     ║${NC}"
echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo ""

# Default values
MODE="local"
CLEAN_UP=true
WAIT_TIME=30
SKIP_BUILD=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --docker)
            MODE="docker"
            shift
            ;;
        --no-cleanup)
            CLEAN_UP=false
            shift
            ;;
        --wait)
            WAIT_TIME="$2"
            shift 2
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --docker        Run tests against Docker Compose Dagster instance"
            echo "  --no-cleanup    Don't stop Docker containers after tests"
            echo "  --wait N        Wait N seconds for services to be ready (default: 30)"
            echo "  --skip-build    Skip Docker image building"
            echo "  --help          Show this help message"
            echo ""
            echo "Modes:"
            echo "  local (default) - Run tests against locally running Dagster"
            echo "  docker          - Spin up test Docker environment and run tests"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Function to check if Dagster is ready
check_dagster_ready() {
    local url=$1
    local max_attempts=20
    local attempt=0

    echo -e "${YELLOW}Waiting for Dagster to be ready at $url...${NC}"

    while [ $attempt -lt $max_attempts ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Dagster is ready!${NC}"
            return 0
        fi
        attempt=$((attempt + 1))
        echo -n "."
        sleep 2
    done

    echo -e "${RED}✗ Dagster failed to become ready${NC}"
    return 1
}

# Function to run tests
run_tests() {
    local dagster_url=$1

    echo -e "${BLUE}Running integration tests...${NC}"

    # Set environment variables for tests
    export DAGSTER_TEST_URL="$dagster_url"
    export INFLUX_URL="http://localhost:8086"
    export INFLUX_TOKEN="test-token-12345"
    export INFLUX_ORG="test-org"
    export INFLUX_BUCKET="test-bucket"
    export TIBBER_API_TOKEN="test-tibber-token"

    # Run integration tests
    python3 -m pytest tests/integration/ \
        -m integration \
        -v \
        --tb=short \
        --color=yes

    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✓ All integration tests passed!${NC}"
    else
        echo -e "${RED}✗ Some integration tests failed${NC}"
    fi

    return $exit_code
}

# Function to cleanup Docker
cleanup_docker() {
    if [ "$CLEAN_UP" = true ]; then
        echo -e "${YELLOW}Cleaning up Docker containers...${NC}"
        docker-compose -f ../docker-compose.dagster-test.yml down -v
        echo -e "${GREEN}✓ Cleanup complete${NC}"
    else
        echo -e "${YELLOW}Skipping cleanup (containers still running)${NC}"
        echo -e "${BLUE}To access Dagster UI: http://localhost:3001${NC}"
        echo -e "${BLUE}To stop manually: docker-compose -f docker-compose.dagster-test.yml down -v${NC}"
    fi
}

# Main execution
if [ "$MODE" = "docker" ]; then
    echo -e "${BLUE}Mode: Docker${NC}"
    echo -e "${YELLOW}This will start a test Dagster environment...${NC}"

    # Navigate to parent directory for docker-compose
    cd ..

    # Build Docker images if needed
    if [ "$SKIP_BUILD" = false ]; then
        echo -e "${YELLOW}Building Docker images...${NC}"
        docker-compose -f docker-compose.dagster-test.yml build --quiet
        echo -e "${GREEN}✓ Build complete${NC}"
    fi

    # Start services
    echo -e "${YELLOW}Starting Dagster test services...${NC}"
    docker-compose -f docker-compose.dagster-test.yml up -d

    # Wait for services to be ready
    echo -e "${YELLOW}Waiting ${WAIT_TIME} seconds for services to initialize...${NC}"
    sleep "$WAIT_TIME"

    # Check if Dagster is ready
    if ! check_dagster_ready "http://localhost:3001"; then
        echo -e "${RED}Failed to connect to Dagster${NC}"
        echo -e "${YELLOW}Showing logs:${NC}"
        docker-compose -f docker-compose.dagster-test.yml logs --tail=50
        cleanup_docker
        exit 1
    fi

    # Run tests
    cd workflows-dagster
    run_tests "http://localhost:3001"
    TEST_EXIT_CODE=$?

    # Cleanup
    cd ..
    cleanup_docker

    exit $TEST_EXIT_CODE

elif [ "$MODE" = "local" ]; then
    echo -e "${BLUE}Mode: Local${NC}"
    echo -e "${YELLOW}Assuming Dagster is running on http://localhost:3000${NC}"

    # Check if Dagster is running
    if ! curl -s -f "http://localhost:3000" > /dev/null 2>&1; then
        echo -e "${RED}✗ Dagster is not running on http://localhost:3000${NC}"
        echo -e "${YELLOW}Please start Dagster first:${NC}"
        echo -e "  docker-compose -f docker-compose.dagster.yml up -d"
        echo -e "  OR run with --docker flag to auto-start test environment"
        exit 1
    fi

    echo -e "${GREEN}✓ Dagster is running${NC}"

    # Run tests
    run_tests "http://localhost:3000"
    exit $?
fi
