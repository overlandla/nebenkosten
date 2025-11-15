#!/bin/bash
set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Dagster Local Integration Test Runner               ║${NC}"
echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo ""

# Configuration
DAGSTER_PORT=3001
DAGSTER_URL="http://localhost:${DAGSTER_PORT}"
DAGSTER_PID_FILE=".dagster_test.pid"
WAIT_TIME=15

# Parse arguments
RUN_TESTS=true
CLEANUP=true

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-cleanup)
            CLEANUP=false
            shift
            ;;
        --skip-tests)
            RUN_TESTS=false
            shift
            ;;
        --port)
            DAGSTER_PORT="$2"
            DAGSTER_URL="http://localhost:${DAGSTER_PORT}"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --no-cleanup    Keep Dagster running after tests"
            echo "  --skip-tests    Just start Dagster, don't run tests"
            echo "  --port N        Use port N instead of 3001"
            echo "  --help          Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  INFLUX_TOKEN, INFLUX_ORG, TIBBER_API_TOKEN - Used by Dagster"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Function to check if port is in use
check_port() {
    if lsof -Pi :$DAGSTER_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to wait for Dagster to be ready
wait_for_dagster() {
    echo -e "${YELLOW}Waiting for Dagster to be ready at ${DAGSTER_URL}...${NC}"
    local max_attempts=30
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if curl -s -f "${DAGSTER_URL}" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Dagster is ready!${NC}"
            return 0
        fi
        attempt=$((attempt + 1))
        echo -n "."
        sleep 1
    done

    echo -e "${RED}✗ Dagster failed to start${NC}"
    return 1
}

# Function to start Dagster
start_dagster() {
    echo -e "${YELLOW}Starting local Dagster instance on port ${DAGSTER_PORT}...${NC}"

    # Check if port is already in use
    if check_port; then
        echo -e "${YELLOW}⚠ Port ${DAGSTER_PORT} is already in use${NC}"
        echo -e "${YELLOW}Testing if it's a working Dagster instance...${NC}"
        if curl -s -f "${DAGSTER_URL}" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Using existing Dagster instance${NC}"
            return 0
        else
            echo -e "${RED}✗ Port in use but not responding. Please free port ${DAGSTER_PORT}${NC}"
            exit 1
        fi
    fi

    # Set environment variables for testing
    export DAGSTER_HOME="${PWD}/.dagster_test_home"
    mkdir -p "$DAGSTER_HOME"

    # Create minimal dagster.yaml
    cat > "$DAGSTER_HOME/dagster.yaml" <<EOF
run_storage:
  module: dagster.core.storage.runs
  class: SqliteRunStorage
  config:
    base_dir: ${DAGSTER_HOME}/runs

event_log_storage:
  module: dagster.core.storage.event_log
  class: SqliteEventLogStorage
  config:
    base_dir: ${DAGSTER_HOME}/event_logs

schedule_storage:
  module: dagster.core.storage.schedules
  class: SqliteScheduleStorage
  config:
    base_dir: ${DAGSTER_HOME}/schedules
EOF

    # Start Dagster in background
    echo -e "${BLUE}Starting: dagster dev -m dagster_project -h 0.0.0.0 -p ${DAGSTER_PORT}${NC}"

    nohup python3 -m dagster dev \
        -m dagster_project \
        -h 0.0.0.0 \
        -p ${DAGSTER_PORT} \
        > .dagster_test.log 2>&1 &

    DAGSTER_PID=$!
    echo $DAGSTER_PID > "$DAGSTER_PID_FILE"

    echo -e "${GREEN}✓ Dagster started with PID ${DAGSTER_PID}${NC}"

    # Wait for it to be ready
    if ! wait_for_dagster; then
        echo -e "${RED}Dagster startup failed. Showing last 50 lines of log:${NC}"
        tail -50 .dagster_test.log
        cleanup_dagster
        exit 1
    fi

    echo -e "${BLUE}Dagster UI available at: ${DAGSTER_URL}${NC}"
}

# Function to run tests
run_tests() {
    echo -e "${BLUE}Running live integration tests...${NC}"

    export DAGSTER_TEST_URL="${DAGSTER_URL}"

    # Run live tests
    python3 -m pytest tests/integration/test_live_dagster.py \
        -v \
        --tb=short \
        --color=yes \
        -m live

    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✓ All live integration tests passed!${NC}"
    else
        echo -e "${RED}✗ Some tests failed${NC}"
    fi

    return $exit_code
}

# Function to cleanup Dagster
cleanup_dagster() {
    if [ "$CLEANUP" = false ]; then
        echo -e "${YELLOW}Skipping cleanup (--no-cleanup flag used)${NC}"
        echo -e "${BLUE}Dagster is still running at ${DAGSTER_URL}${NC}"
        echo -e "${BLUE}To stop manually:${NC}"
        if [ -f "$DAGSTER_PID_FILE" ]; then
            echo -e "  kill \$(cat $DAGSTER_PID_FILE)"
            echo -e "  rm $DAGSTER_PID_FILE"
        fi
        return 0
    fi

    echo -e "${YELLOW}Stopping Dagster...${NC}"

    if [ -f "$DAGSTER_PID_FILE" ]; then
        DAGSTER_PID=$(cat "$DAGSTER_PID_FILE")
        if ps -p $DAGSTER_PID > /dev/null 2>&1; then
            kill $DAGSTER_PID
            echo -e "${GREEN}✓ Dagster stopped (PID ${DAGSTER_PID})${NC}"
        fi
        rm "$DAGSTER_PID_FILE"
    fi

    # Cleanup test home
    if [ -d ".dagster_test_home" ]; then
        rm -rf .dagster_test_home
    fi

    echo -e "${GREEN}✓ Cleanup complete${NC}"
}

# Trap to ensure cleanup on exit
trap cleanup_dagster EXIT INT TERM

# Main execution
start_dagster

if [ "$RUN_TESTS" = true ]; then
    run_tests
    TEST_EXIT_CODE=$?
else
    echo -e "${BLUE}Skipping tests (--skip-tests flag used)${NC}"
    echo -e "${BLUE}Dagster is running at ${DAGSTER_URL}${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop${NC}"

    # Wait indefinitely
    while true; do
        sleep 1
    done
fi

exit ${TEST_EXIT_CODE:-0}
