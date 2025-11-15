# Testing Guide for Dagster Utility Workflows

Comprehensive testing suite with unit, integration, and system tests for the Dagster implementation.

## Table of Contents

- [Test Structure](#test-structure)
- [Quick Start](#quick-start)
- [Test Types](#test-types)
- [Running Tests](#running-tests)
- [Writing Tests](#writing-tests)
- [Continuous Integration](#continuous-integration)
- [Troubleshooting](#troubleshooting)

## Test Structure

```
workflows-dagster/tests/
├── conftest.py                    # Shared pytest fixtures
├── fixtures/
│   ├── mock_data.py              # Mock data generators
│   └── __init__.py
├── unit/                         # Fast, isolated tests
│   ├── test_resources.py        # Resource unit tests
│   ├── test_tibber_assets.py    # Tibber asset tests
│   └── test_analytics_assets.py # Analytics asset tests
├── integration/                  # Component integration tests
│   └── test_asset_integration.py
└── system/                       # End-to-end tests
    └── test_end_to_end.py
```

## Quick Start

### Local Testing (Fastest)

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests
cd workflows-dagster
./run-tests.sh

# Run only unit tests (fast)
./run-tests.sh unit

# Run with coverage
./run-tests.sh all coverage
```

### Docker Testing

```bash
# Run tests in Docker container (isolated)
./test-dagster-docker.sh

# Run specific test type
./test-dagster-docker.sh -m unit
```

## Test Types

### Unit Tests (`tests/unit/`)

**Purpose:** Test individual components in isolation with mocked dependencies

**Characteristics:**
- Fast (< 1 second per test)
- No external dependencies
- Mocked InfluxDB, Tibber API, file I/O
- High code coverage target (>80%)

**Examples:**
```bash
# Run all unit tests
pytest tests/unit/ -m unit

# Run specific test file
pytest tests/unit/test_resources.py

# Run specific test
pytest tests/unit/test_resources.py::TestInfluxDBResource::test_resource_initialization

# Run unit tests excluding slow ones
pytest tests/unit/ -m "unit and not slow"
```

**Markers:**
- `@pytest.mark.unit` - Standard unit test
- `@pytest.mark.tibber` - Requires Tibber-related mocks
- `@pytest.mark.influxdb` - Requires InfluxDB-related mocks

### Integration Tests (`tests/integration/`)

**Purpose:** Test how multiple components work together

**Characteristics:**
- Moderate speed (1-5 seconds per test)
- May use test databases or containers
- Tests asset dependencies and job execution
- Validates data flow between components

**Examples:**
```bash
# Run all integration tests
pytest tests/integration/ -m integration

# Run with verbose output
pytest tests/integration/ -m integration -v -s
```

**Markers:**
- `@pytest.mark.integration` - Integration test
- `@pytest.mark.slow` - Takes longer to run (>5 seconds)

### System Tests (`tests/system/`)

**Purpose:** End-to-end validation of complete workflows

**Characteristics:**
- Slowest (5-30 seconds per test)
- Tests complete pipelines
- Validates data quality and business logic
- May require more setup/teardown

**Examples:**
```bash
# Run all system tests
pytest tests/system/ -m system

# Run specific E2E test
pytest tests/system/test_end_to_end.py::TestAnalyticsE2E
```

**Markers:**
- `@pytest.mark.system` - System/E2E test
- `@pytest.mark.slow` - Expected to take time

## Running Tests

### Test Runner Script

The `run-tests.sh` script provides convenient test execution:

```bash
# Syntax
./run-tests.sh [test_type] [coverage]

# Examples
./run-tests.sh unit           # Unit tests only
./run-tests.sh integration    # Integration tests only
./run-tests.sh system          # System tests only
./run-tests.sh fast            # Quick unit tests
./run-tests.sh all             # All tests (default)
./run-tests.sh all coverage    # All tests with coverage report
```

### Direct Pytest Usage

For more control, use pytest directly:

```bash
# Run by marker
pytest -m unit                 # Unit tests only
pytest -m "unit or integration" # Unit + integration
pytest -m "not slow"           # Skip slow tests

# Run by path
pytest tests/unit/             # All unit tests
pytest tests/                  # All tests

# Run specific tests
pytest tests/unit/test_resources.py::TestConfigResource
pytest -k "tibber"             # Tests matching "tibber"

# Verbose output
pytest -v                      # Verbose
pytest -vv                     # Extra verbose
pytest -s                      # Show print statements

# Parallel execution (requires pytest-xdist)
pytest -n auto                 # Auto-detect CPU count
pytest -n 4                    # Use 4 workers

# Stop on first failure
pytest -x

# Show slowest tests
pytest --durations=10
```

### Coverage Reports

```bash
# Generate HTML coverage report
pytest --cov=dagster_project --cov-report=html

# View report
open htmlcov/index.html

# Terminal coverage report
pytest --cov=dagster_project --cov-report=term-missing

# Fail if coverage below threshold
pytest --cov=dagster_project --cov-fail-under=80
```

### Docker Testing

```bash
# Run in Docker (isolated environment)
./test-dagster-docker.sh

# With specific pytest args
./test-dagster-docker.sh -m unit -v

# With coverage
./test-dagster-docker.sh --cov=dagster_project --cov-report=term
```

## Writing Tests

### Test Structure

Follow this pattern for new tests:

```python
import pytest
from unittest.mock import MagicMock, patch

class TestYourComponent:
    """Test suite for YourComponent"""

    @pytest.mark.unit
    def test_basic_functionality(self, fixture_name):
        """Test description"""
        # Arrange
        component = YourComponent()

        # Act
        result = component.do_something()

        # Assert
        assert result == expected_value
```

### Using Fixtures

Common fixtures available in `conftest.py`:

```python
def test_with_resources(
    mock_influxdb_resource,
    mock_tibber_resource,
    mock_config_resource,
    sample_meter_data,
    sample_consumption_data
):
    """Fixtures are automatically injected"""
    # Use fixtures in your test
    config = mock_config_resource.load_config()
    assert config is not None
```

### Mocking External Dependencies

```python
from unittest.mock import patch, MagicMock

@patch('module.path.InfluxDBClient')
def test_with_mocked_client(mock_client_class):
    """Mock external dependencies"""
    # Setup mock
    mock_instance = MagicMock()
    mock_instance.query.return_value = []
    mock_client_class.return_value = mock_instance

    # Test code that uses InfluxDBClient
    # ...
```

### Testing Dagster Assets

```python
from dagster import build_asset_context, materialize

def test_asset_execution():
    """Test asset can be materialized"""
    context = build_asset_context()

    result = your_asset(context, resource1, resource2)

    assert result is not None
```

### Testing Dagster Jobs

```python
def test_job_execution():
    """Test job runs successfully"""
    result = your_job.execute_in_process(
        resources={
            "influxdb": mock_influxdb_resource,
            "config": mock_config_resource
        }
    )

    assert result.success
```

### Test Data Generation

Use helper functions from `tests/fixtures/mock_data.py`:

```python
from tests.fixtures.mock_data import (
    generate_meter_readings,
    generate_consumption_data,
    generate_tibber_api_response
)

def test_with_generated_data():
    """Use generated test data"""
    readings = generate_meter_readings(
        start_date="2024-01-01",
        days=31,
        initial_value=100.0,
        daily_increment=10.5
    )

    assert len(readings) == 31
```

## Pytest Configuration

Configuration in `pytest.ini`:

```ini
[pytest]
# Markers
markers =
    unit: Unit tests
    integration: Integration tests
    system: System/E2E tests
    slow: Slow tests
    tibber: Tibber-related tests
    influxdb: InfluxDB-related tests

# Test discovery
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

## Continuous Integration

### GitHub Actions Example

Create `.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements-dagster.txt
          pip install -r requirements-test.txt

      - name: Run tests
        run: |
          cd workflows-dagster
          pytest tests/ --cov=dagster_project --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### Pre-commit Hooks

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: pytest-unit
        name: pytest unit tests
        entry: bash -c 'cd workflows-dagster && pytest tests/unit/ -m unit'
        language: system
        pass_filenames: false
        always_run: true
```

## Troubleshooting

### Common Issues

**1. Import Errors**

```bash
# Problem: Can't import dagster_project
# Solution: Ensure PYTHONPATH is set
export PYTHONPATH=/path/to/nebenkosten:/path/to/nebenkosten/Nebenkosten
pytest
```

**2. Environment Variables Not Set**

```bash
# Problem: Tests fail due to missing env vars
# Solution: conftest.py sets test values, but you can override
export INFLUX_TOKEN=test-token
export INFLUX_ORG=test-org
export TIBBER_API_TOKEN=test-token
pytest
```

**3. Fixture Not Found**

```bash
# Problem: pytest can't find fixture
# Solution: Ensure conftest.py is in parent directory
# Fixtures in tests/conftest.py are available to all tests
```

**4. Slow Tests**

```bash
# Skip slow tests during development
pytest -m "not slow"

# Run slow tests in parallel
pytest -n auto -m slow
```

**5. Coverage Not Accurate**

```bash
# Ensure you're measuring the right package
pytest --cov=dagster_project --cov-report=term-missing

# Check what's being covered
pytest --cov=dagster_project --cov-report=html
open htmlcov/index.html
```

### Debugging Tests

```bash
# Drop into debugger on failure
pytest --pdb

# Drop into debugger on first failure
pytest -x --pdb

# Show local variables on failure
pytest -l

# Increase verbosity
pytest -vv -s
```

## Best Practices

1. **Test Organization**
   - One test class per component
   - Group related tests in classes
   - Use descriptive test names

2. **Test Independence**
   - Each test should run independently
   - Don't rely on test execution order
   - Clean up in fixtures

3. **Mocking**
   - Mock external services (InfluxDB, Tibber API)
   - Don't mock code under test
   - Use realistic mock data

4. **Coverage**
   - Aim for >80% coverage
   - Focus on critical paths
   - Don't test framework code

5. **Speed**
   - Keep unit tests fast (< 1s)
   - Use markers for slow tests
   - Run fast tests frequently

## Coverage Goals

| Test Type | Target Coverage | Speed |
|-----------|----------------|-------|
| Unit | >90% | Fast |
| Integration | >70% | Medium |
| System | Critical paths | Slow |

## Next Steps

- Run tests locally: `./run-tests.sh`
- Add tests for new features
- Set up CI/CD pipeline
- Monitor coverage trends
- Write tests first (TDD)

## Support

For issues with tests:
1. Check this documentation
2. Review test output carefully
3. Check fixture definitions in `conftest.py`
4. Consult Dagster testing docs: https://docs.dagster.io/concepts/testing
