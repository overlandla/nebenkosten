# Testing Guide

Comprehensive test suite for the Utility Meter Analytics System.

---

## Test Suite Overview

**Total Tests:** 37 tests across 4 test modules
- ✅ **9 tests** - Configuration loader
- ✅ **9 tests** - Analytics flow tasks
- ✅ **10 tests** - Tibber sync flow
- ✅ **9 tests** - Integration tests

**Test Coverage:** Targets 80%+ coverage of workflows/ directory

---

## Test Organization

```
tests/
├── conftest.py                   # Shared fixtures and mocks
├── test_config_loader.py         # Configuration loading tests
├── test_analytics_flow.py        # Analytics workflow task tests
├── test_tibber_sync_flow.py      # Tibber sync workflow tests
└── test_integration.py           # End-to-end integration tests
```

---

## Running Tests

### Prerequisites

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Or install test tools only
pip install pytest pytest-cov pytest-mock
```

### Basic Test Execution

```bash
# Run all tests
pytest

# Run specific test module
pytest tests/test_config_loader.py

# Run specific test
pytest tests/test_config_loader.py::test_config_loader_basic

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=workflows --cov-report=term-missing
```

### Test Categories

Tests are marked for easy filtering:

```bash
# Run only unit tests (fast)
pytest -m unit

# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"

# Run tests related to Tibber
pytest -m tibber

# Run tests related to InfluxDB
pytest -m influxdb
```

### Docker Testing (Recommended)

Run tests in the same environment as production:

```bash
# Build worker image
docker-compose build prefect-worker

# Run tests in container
docker-compose run --rm prefect-worker pytest tests/ -v

# With coverage
docker-compose run --rm prefect-worker pytest tests/ -v --cov=workflows --cov-report=html

# View coverage report (generated in htmlcov/)
open htmlcov/index.html
```

---

## Test Modules

### 1. Configuration Loader Tests (`test_config_loader.py`)

Tests for `workflows/config_loader.py`

**Tests:**
- ✅ `test_config_loader_basic` - Load configuration from YAML
- ✅ `test_config_loader_loads_meters` - Verify meters are loaded
- ✅ `test_config_loader_loads_seasonal_patterns` - Verify patterns loaded
- ✅ `test_config_loader_validates_secrets` - Check secret validation
- ✅ `test_config_loader_missing_file` - Handle missing config file
- ✅ `test_get_meters_by_type` - Filter meters by type
- ✅ `test_get_meter_config` - Get specific meter configuration
- ✅ `test_get_seasonal_pattern` - Get seasonal pattern for meter
- ✅ `test_tibber_token_optional` - Tibber token is optional

**Example:**
```bash
pytest tests/test_config_loader.py -v

# Expected output:
# ✓ test_config_loader_basic PASSED
# ✓ test_config_loader_loads_meters PASSED
# ... 9 tests passed in 0.5s
```

### 2. Analytics Flow Tests (`test_analytics_flow.py`)

Tests for `workflows/analytics_flow.py` task functions

**Tests:**
- ✅ `test_detect_anomalies_found` - Detect consumption anomalies
- ✅ `test_detect_anomalies_none_found` - No anomalies case
- ✅ `test_detect_anomalies_empty_data` - Handle empty data
- ✅ `test_process_virtual_meter_basic` - Basic virtual meter calculation
- ✅ `test_process_virtual_meter_with_unit_conversion` - With unit conversion
- ✅ `test_process_virtual_meter_negative_clipping` - Clip negative values
- ✅ `test_process_virtual_meter_missing_base` - Handle missing base meter
- ✅ `test_calculate_consumption_basic` - Basic consumption calculation
- ✅ `test_calculate_consumption_empty_data` - Handle empty data

**Example:**
```bash
pytest tests/test_analytics_flow.py::test_detect_anomalies_found -v

# Expected output:
# ✓ test_detect_anomalies_found PASSED
```

### 3. Tibber Sync Flow Tests (`test_tibber_sync_flow.py`)

Tests for `workflows/tibber_sync_flow.py` workflow

**Tests:**
- ✅ `test_fetch_tibber_data_success` - Successful API fetch
- ✅ `test_fetch_tibber_data_api_error` - Handle API errors
- ✅ `test_fetch_tibber_data_network_error` - Handle network errors
- ✅ `test_get_last_influxdb_timestamp_with_data` - Get last timestamp
- ✅ `test_get_last_influxdb_timestamp_no_data` - No existing data case
- ✅ `test_write_to_influxdb_new_data` - Write new data points
- ✅ `test_write_to_influxdb_no_new_data` - Idempotent writes
- ✅ `test_tibber_sync_flow_success` - Complete workflow
- ✅ `test_tibber_sync_flow_no_token` - Skip when token missing
- ✅ `test_tibber_sync_flow_empty_response` - Handle empty response

**Example:**
```bash
pytest tests/test_tibber_sync_flow.py -v
```

### 4. Integration Tests (`test_integration.py`)

End-to-end tests verifying system behavior

**Tests:**
- ✅ `test_config_loader_with_real_files` - Load from actual files
- ✅ `test_logging_setup` - Logging configuration
- ✅ `test_analytics_flow_end_to_end` - Full analytics workflow
- ✅ `test_tibber_sync_flow_end_to_end` - Full Tibber sync workflow
- ✅ `test_meter_type_filtering` - Meter type filtering
- ✅ `test_gas_conversion_calculation` - Gas unit conversions
- ✅ `test_seasonal_pattern_validation` - Seasonal patterns are valid
- ✅ `test_master_meter_period_validation` - Master meter periods valid
- ✅ `test_virtual_meter_dependencies_exist` - Virtual meter dependencies

**Example:**
```bash
pytest tests/test_integration.py -v -m integration
```

---

## Test Fixtures

Located in `tests/conftest.py`, these fixtures provide reusable test data:

### Configuration Fixtures

- **`test_config`** - Complete test configuration dictionary
- **`test_config_files`** - Temporary config files (config.yaml, meters.yaml, patterns.yaml)
- **`mock_env_vars`** - Mock environment variables (INFLUX_TOKEN, etc.)

### Data Fixtures

- **`sample_meter_data`** - Sample meter reading DataFrame (daily data for 1 year)
- **`sample_consumption_data`** - Sample consumption DataFrame (monthly data)
- **`sample_anomalies`** - Sample anomaly records

### Mock Fixtures

- **`tibber_api_response`** - Mock Tibber GraphQL API response
- **`mock_influx_client`** - Mock InfluxDB client
- **`mock_requests_post`** - Mock requests.post for API calls
- **`mock_influxdb_client`** - Mock InfluxDB client context manager

### Example Usage

```python
def test_my_feature(test_config, sample_meter_data):
    """Test using fixtures"""
    # test_config and sample_meter_data are automatically provided
    assert test_config["influxdb"]["url"] == "http://test-influxdb:8086"
    assert len(sample_meter_data) == 365
```

---

## Writing New Tests

### Test Template

```python
"""
Tests for New Feature
"""
import pytest
from workflows.new_feature import new_function


def test_new_function_basic(test_config):
    """Test basic functionality of new_function"""
    result = new_function(test_config)

    assert result is not None
    assert result.some_property == expected_value


def test_new_function_error_handling():
    """Test error handling"""
    with pytest.raises(ValueError, match="Expected error message"):
        new_function(invalid_input)


@pytest.mark.slow
def test_new_function_performance(sample_meter_data):
    """Test performance with large dataset"""
    import time

    start = time.time()
    result = new_function(sample_meter_data)
    elapsed = time.time() - start

    assert elapsed < 5.0  # Should complete in under 5 seconds
```

### Best Practices

1. **Use descriptive test names** - `test_function_name_expected_behavior`
2. **One assertion focus per test** - Test one thing well
3. **Use fixtures** - Reuse test data and mocks
4. **Mark tests appropriately** - Use `@pytest.mark.unit`, `@pytest.mark.integration`, etc.
5. **Mock external dependencies** - Don't make real API or database calls
6. **Test edge cases** - Empty data, None values, errors
7. **Keep tests fast** - Unit tests should run in milliseconds

---

## Test Coverage

### Generating Coverage Reports

```bash
# Terminal report
pytest --cov=workflows --cov-report=term-missing

# HTML report (opens in browser)
pytest --cov=workflows --cov-report=html
open htmlcov/index.html

# XML report (for CI/CD)
pytest --cov=workflows --cov-report=xml
```

### Coverage Goals

| Module | Target Coverage | Current |
|--------|----------------|---------|
| `config_loader.py` | 90% | 89% |
| `logging_config.py` | 80% | 0% * |
| `tibber_sync_flow.py` | 85% | 0% * |
| `analytics_flow.py` | 80% | 0% * |
| `register_flows.py` | 70% | 0% * |

*Note: 0% coverage indicates tests exist but require proper environment (Docker) to run.

### Improving Coverage

```bash
# Find uncovered lines
pytest --cov=workflows --cov-report=term-missing | grep "MISS"

# Generate detailed report
pytest --cov=workflows --cov-report=html

# View in browser to see which lines need tests
open htmlcov/workflows_config_loader_py.html
```

---

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt

      - name: Run tests
        run: |
          pytest tests/ --cov=workflows --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

### Pre-commit Hook

Add to `.git/hooks/pre-commit`:

```bash
#!/bin/bash

# Run tests before commit
pytest tests/ -x

if [ $? -ne 0 ]; then
    echo "Tests failed! Commit aborted."
    exit 1
fi
```

---

## Troubleshooting

### Tests fail with "ModuleNotFoundError"

**Solution:** Install dependencies
```bash
pip install -r requirements-worker.txt
pip install -r requirements-dev.txt
```

### Tests fail with import errors

**Solution:** Set PYTHONPATH
```bash
export PYTHONPATH=/path/to/nebenkosten:/path/to/nebenkosten/Nebenkosten
pytest tests/
```

### Tests pass locally but fail in Docker

**Solution:** Check environment variables
```bash
# Ensure secrets are available in container
docker-compose run --rm prefect-worker env | grep INFLUX
```

### Coverage report shows 0% for all modules

**Solution:** Run tests with coverage enabled
```bash
pytest --cov=workflows --cov-report=term
```

### Fixtures not found

**Solution:** Ensure conftest.py is in tests/ directory
```bash
ls tests/conftest.py
# Should exist
```

---

## Test Summary

| Category | Tests | Status |
|----------|-------|--------|
| Configuration | 9 | ✅ All passing |
| Analytics Tasks | 9 | ✅ Created |
| Tibber Sync | 10 | ✅ Created |
| Integration | 9 | ✅ Created |
| **Total** | **37** | **✅ Ready** |

---

## Next Steps

1. **Run tests in Docker** for full validation:
   ```bash
   docker-compose run --rm prefect-worker pytest tests/ -v
   ```

2. **Add more tests** as new features are developed

3. **Set up CI/CD** to run tests automatically on commits

4. **Monitor coverage** and aim for 80%+ across all modules

5. **Document test failures** and create issues for fixes

---

## Resources

- **Pytest Documentation:** https://docs.pytest.org/
- **Pytest Fixtures:** https://docs.pytest.org/en/latest/how-to/fixtures.html
- **Coverage.py:** https://coverage.readthedocs.io/
- **Testing Best Practices:** https://docs.pytest.org/en/latest/goodpractices.html

---

**Test Suite Complete!** 🎉

All 37 tests are created and ready to run in the Docker environment.
