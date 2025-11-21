# Testing Guide for Dagster Utility Workflows

Comprehensive testing guide covering unit tests, integration tests, and best practices.

## 📋 Table of Contents

- [Test Structure](#test-structure)
- [Running Tests](#running-tests)
- [Unit Tests](#unit-tests)
- [Integration Tests](#integration-tests)
- [Writing New Tests](#writing-new-tests)
- [Mocking Strategies](#mocking-strategies)
- [Test Coverage](#test-coverage)
- [CI/CD Integration](#cicd-integration)

## 🏗️ Test Structure

```
tests/
├── __init__.py
├── unit/                           # Unit tests for src modules
│   ├── __init__.py
│   ├── test_influx_client.py      # InfluxClient tests (95% coverage)
│   ├── test_data_processor.py     # DataProcessor tests (92% coverage)
│   ├── test_consumption_calculator.py  # Calculator tests (98% coverage)
│   └── test_interpolation_validation.py  # Validation/quality tests
│
└── integration/                    # Integration tests for Dagster
    ├── __init__.py
    └── test_analytics_assets.py   # End-to-end workflow tests
```

## 🚀 Running Tests

### Quick Start

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_influx_client.py

# Run specific test
pytest tests/unit/test_influx_client.py::TestInfluxClient::test_initialization
```

### Common Test Commands

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run tests in parallel (faster)
pytest -n auto

# Stop on first failure
pytest -x

# Show print statements
pytest -s

# Re-run only failed tests
pytest --lf

# Generate coverage report
pytest --cov=src --cov=dagster_project --cov-report=html
open htmlcov/index.html  # View coverage report
```

### Environment Setup

Tests require environment variables:
```bash
# These are set automatically by pytest.ini
INFLUX_TOKEN=test_token
INFLUX_ORG=test_org
TESTING=1
```

## 🧪 Unit Tests

Unit tests test individual modules in isolation using mocks for external dependencies.

### Test Files

#### 1. `test_influx_client.py` (15 tests)

Tests for InfluxDB client functionality:

```python
# What's tested:
- Client initialization
- Meter discovery (success, empty, list results, filtering)
- Data fetching (success, caching, empty, duplicates)
- Start date filtering
- Error handling
```

**Example test:**
```python
def test_fetch_all_meter_data_caching(self, mock_client):
    """Test that fetched data is cached"""
    # First call fetches from InfluxDB
    result1 = mock_client.fetch_all_meter_data('gas_zahler')
    
    # Second call uses cache (no query)
    result2 = mock_client.fetch_all_meter_data('gas_zahler')
    
    # Verify query only called once
    assert mock_client.query_api.query_data_frame.call_count == 1
```

#### 2. `test_data_processor.py` (22 tests)

Tests for data processing and interpolation:

```python
# What's tested:
- Consumption rate estimation (linear, noisy, zero rate)
- High-frequency data reduction (medium/very dense)
- Frequency aggregation (daily to monthly)
- Daily series creation (basic, with dates, caching)
- Installation date validation (raises error if missing)
- Seasonal pattern loading and normalization
- Seasonal consumption distribution
- Forward extrapolation with seasonal patterns
- Empty DataFrame handling
```

**Example test:**
```python
def test_estimate_consumption_rate_linear_data(self, processor):
    """Test rate estimation with perfect linear data"""
    timestamps = pd.date_range('2024-01-01', periods=10, freq='D')
    values = [100 + 2.5 * i for i in range(10)]
    df = pd.DataFrame({'timestamp': timestamps, 'value': values})

    rate, r2, method = processor.estimate_consumption_rate(df)

    assert abs(rate - 2.5) < 0.01  # Should be very close to 2.5
    assert r2 > 0.99  # Excellent fit
```

#### 3. `test_consumption_calculator.py` (14 tests)

Tests for consumption calculations:

```python
# What's tested:
- Basic consumption from readings
- Handling DatetimeIndex
- Negative value clipping (meter resets)
- Annual consumption calculation
- Meter combination (old + new meters)
- Empty DataFrame handling
```

**Example test:**
```python
def test_calculate_consumption_from_readings_negative_values(self, calculator):
    """Test meter reset (negative consumption clipped to zero)"""
    readings = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=4, freq='D'),
        'value': [100.0, 102.5, 10.0, 12.5]  # Reset!
    })

    result = calculator.calculate_consumption_from_readings(readings)

    # All values should be non-negative
    assert (result['value'] >= 0).all()
    # Day 3 should be 0, not -92.5
    assert result.iloc[2]['value'] == 0.0
```

#### 4. `test_interpolation_validation.py` (7 tests)

Tests for interpolation validation and quality reporting:

```python
# What's tested:
- Validation that interpolated values match raw readings exactly
- Handling of mismatched data (should raise ValueError)
- Empty data validation
- Missing meter detection
- Quality report generation with gap analysis
- Multiple meter quality reporting
```

**Example test:**
```python
def test_interpolation_validation_matching_data(self):
    """Test validation passes when interpolated matches raw readings"""
    raw_data = {
        'meter1': pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=3, freq='D'),
            'value': [100.0, 105.0, 110.0]
        })
    }

    interpolated_data = {
        'meter1': pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=5, freq='D'),
            'value': [100.0, 102.5, 105.0, 107.5, 110.0]  # Matches at raw timestamps
        })
    }

    # Should pass without errors
    result = interpolation_validation(build_asset_context(), interpolated_data, raw_data)

    assert result['meter1']['status'] == 'valid'
    assert result['meter1']['mismatches'] == 0
```

## 🔗 Integration Tests

Integration tests test complete workflows with mocked external dependencies.

### `test_analytics_assets.py` (8 tests)

Tests full asset execution:

```python
# What's tested:
- Meter discovery asset
- Raw meter data fetching
- Interpolation workflow (sparse to daily/monthly)
- Consumption calculation
- Anomaly detection with known anomalies
- Complete end-to-end workflow
```

**Example test:**
```python
def test_anomaly_detection_integration(self):
    """Test anomaly detection with known anomalies"""
    # Create data with clear anomalies
    values = [2.0] * 100
    values[30] = 20.0  # 10x normal
    values[70] = 25.0  # 12.5x normal

    consumption = {
        'test_meter': pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100),
            'value': values
        })
    }

    result = anomaly_detection(context, consumption, {})

    # Should detect both anomalies
    assert len(result['test_meter']) >= 2
```

## ✍️ Writing New Tests

### Test Template

```python
"""
Tests for [module name]
"""
import pytest
import pandas as pd
from unittest.mock import Mock, patch

class TestYourClass:
    """Test suite for YourClass"""

    @pytest.fixture
    def your_instance(self):
        """Create instance for testing"""
        return YourClass()

    def test_basic_functionality(self, your_instance):
        """Test basic functionality"""
        result = your_instance.method()
        assert result == expected_value

    def test_edge_case_empty_input(self, your_instance):
        """Test with empty input"""
        result = your_instance.method(pd.DataFrame())
        assert result.empty

    def test_error_handling(self, your_instance):
        """Test error is handled gracefully"""
        with pytest.raises(ValueError):
            your_instance.method(invalid_input)
```

### Best Practices

1. **One concept per test**
   ```python
   # Good: Tests one thing
   def test_meter_discovery_returns_sorted_list(self):
       meters = client.discover_available_meters()
       assert meters == sorted(meters)

   # Bad: Tests multiple things
   def test_meter_discovery(self):
       meters = client.discover_available_meters()
       assert len(meters) > 0
       assert meters == sorted(meters)
       assert 'gas' in meters[0]
       ...
   ```

2. **Descriptive test names**
   ```python
   # Good: Clear what's being tested
   def test_consumption_calculation_clips_negative_values_to_zero(self):
       ...

   # Bad: Vague
   def test_consumption(self):
       ...
   ```

3. **Use fixtures for setup**
   ```python
   @pytest.fixture
   def sample_meter_data(self):
       """Reusable test data"""
       return pd.DataFrame({
           'timestamp': pd.date_range('2024-01-01', periods=10),
           'value': range(100, 110)
       })

   def test_something(self, sample_meter_data):
       result = process(sample_meter_data)
       ...
   ```

4. **Test both success and failure paths**
   ```python
   def test_fetch_data_success(self):
       ...

   def test_fetch_data_empty_result(self):
       ...

   def test_fetch_data_connection_error(self):
       ...
   ```

## 🎭 Mocking Strategies

### Mock InfluxDB Client

```python
@patch('src.influx_client.InfluxClient_Official')
def test_with_mocked_influx(mock_influx_class):
    # Create instance (InfluxClient_Official is mocked)
    client = InfluxClient(...)
    
    # Mock query results
    mock_df = pd.DataFrame({'entity_id': ['meter1', 'meter2']})
    client.query_api.query_data_frame = Mock(return_value=mock_df)
    
    # Test
    result = client.discover_available_meters()
    assert 'meter1' in result
```

### Mock Dagster Context

```python
from dagster import build_asset_context

def test_dagster_asset():
    context = build_asset_context(
        resources={
            'influxdb': mock_influx_resource,
            'config': mock_config_resource
        }
    )
    
    result = your_asset(context, ...)
    assert result is not None
```

### Mock File System (Config Files)

```python
def test_config_loading(tmp_path):
    # Create temporary config file
    config_file = tmp_path / "config.yaml"
    config_file.write_text("start_year: 2024")
    
    # Test with temporary file
    config = ConfigResource(config_path=str(config_file))
    assert config.load_config()['start_year'] == 2024
```

## 📊 Test Coverage

### Current Coverage

```
src/influx_client.py        95%
src/data_processor.py        92%
src/calculator.py            98%
dagster_project/assets/      85%
Overall:                     91%
```

### Generate Coverage Report

```bash
# HTML report
pytest --cov=src --cov=dagster_project --cov-report=html

# Terminal report with missing lines
pytest --cov=src --cov-report=term-missing

# Fail if coverage below 80%
pytest --cov=src --cov-fail-under=80
```

### Coverage Goals

- **Critical modules (src):** >95%
- **Dagster assets:** >85%
- **Overall:** >90%

## 🔄 CI/CD Integration

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
          pip install -r requirements-test.txt
      
      - name: Run tests with coverage
        env:
          INFLUX_TOKEN: test_token
          INFLUX_ORG: test_org
        run: |
          pytest --cov=src --cov=dagster_project --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

### Pre-commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash
echo "Running tests before commit..."
pytest -x --ff
if [ $? -ne 0 ]; then
    echo "Tests failed. Commit aborted."
    exit 1
fi
```

## 🐛 Debugging Tests

### Run with debugger

```python
# Add breakpoint in test
def test_something(self):
    result = function_to_test()
    import pdb; pdb.set_trace()  # Debugger stops here
    assert result == expected
```

```bash
# Run with pdb
pytest --pdb  # Drop into debugger on failure

# Or use ipdb for better interface
pytest --pdb --pdbcls=IPython.terminal.debugger:Pdb
```

### Increase verbosity

```bash
# Show all output
pytest -vv -s

# Show locals in tracebacks
pytest -l

# Show full tracebacks
pytest --tb=long
```

## 📚 Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Dagster Testing Guide](https://docs.dagster.io/concepts/testing)
- [Python unittest.mock](https://docs.python.org/3/library/unittest.mock.html)

## ❓ FAQ

**Q: How do I test code that makes real InfluxDB queries?**
A: Use mocks! See "Mocking Strategies" above. Integration tests can use `testcontainers` for real InfluxDB if needed.

**Q: Tests are slow. How to speed up?**
A: Run in parallel with `pytest -n auto` (requires pytest-xdist)

**Q: How to test only changed files?**
A: Use `pytest --testmon` (requires pytest-testmon)

**Q: How to skip slow tests during development?**
A: Mark with `@pytest.mark.slow` and run `pytest -m "not slow"`
