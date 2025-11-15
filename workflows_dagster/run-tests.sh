#!/bin/bash
# Test runner script for Dagster workflows

set -e

cd "$(dirname "$0")"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🧪 Dagster Utility Analysis Test Suite${NC}"
echo ""

# Parse command line arguments
TEST_TYPE="${1:-all}"
COVERAGE="${2:-false}"

# Install test dependencies if needed
if ! python -c "import pytest" 2>/dev/null; then
    echo -e "${YELLOW}Installing test dependencies...${NC}"
    pip install -q -r requirements-test.txt
fi

# Run tests based on type
case "$TEST_TYPE" in
    unit)
        echo -e "${GREEN}Running unit tests...${NC}"
        if [ "$COVERAGE" == "coverage" ]; then
            pytest tests/unit/ -m unit --cov=dagster_project --cov-report=html --cov-report=term
        else
            pytest tests/unit/ -m unit -v
        fi
        ;;

    integration)
        echo -e "${GREEN}Running integration tests...${NC}"
        pytest tests/integration/ -m integration -v
        ;;

    system)
        echo -e "${GREEN}Running system/E2E tests...${NC}"
        pytest tests/system/ -m system -v
        ;;

    fast)
        echo -e "${GREEN}Running fast tests (unit only)...${NC}"
        pytest tests/unit/ -m "unit and not slow" -v
        ;;

    all)
        echo -e "${GREEN}Running all tests...${NC}"
        if [ "$COVERAGE" == "coverage" ]; then
            pytest tests/ --cov=dagster_project --cov-report=html --cov-report=term-missing
        else
            pytest tests/ -v
        fi
        ;;

    *)
        echo -e "${RED}Unknown test type: $TEST_TYPE${NC}"
        echo ""
        echo "Usage: ./run-tests.sh [test_type] [coverage]"
        echo ""
        echo "Test types:"
        echo "  unit        - Run unit tests only (fast)"
        echo "  integration - Run integration tests"
        echo "  system      - Run system/E2E tests"
        echo "  fast        - Run quick unit tests only"
        echo "  all         - Run all tests (default)"
        echo ""
        echo "Coverage:"
        echo "  coverage    - Generate coverage report"
        echo ""
        echo "Examples:"
        echo "  ./run-tests.sh unit"
        echo "  ./run-tests.sh all coverage"
        exit 1
        ;;
esac

TEST_EXIT_CODE=$?

echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
else
    echo -e "${RED}❌ Some tests failed${NC}"
fi

exit $TEST_EXIT_CODE
