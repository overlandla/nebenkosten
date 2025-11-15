"""
Shared pytest fixtures for Dagster tests
"""
import os
import pytest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from dagster import build_asset_context, build_op_context

# Set test environment variables
os.environ["INFLUX_TOKEN"] = "test-token-123"
os.environ["INFLUX_ORG"] = "test-org"
os.environ["TIBBER_API_TOKEN"] = "test-tibber-token-456"


@pytest.fixture
def mock_influxdb_resource():
    """Mock InfluxDB resource for testing"""
    from dagster_project.resources.influxdb_resource import InfluxDBResource

    resource = InfluxDBResource(
        url="http://localhost:8086",
        bucket_raw="test_raw",
        bucket_processed="test_processed",
        timeout=10000,
        retry_attempts=2
    )
    return resource


@pytest.fixture
def mock_tibber_resource():
    """Mock Tibber resource for testing"""
    from dagster_project.resources.tibber_resource import TibberResource

    resource = TibberResource(
        api_url="https://api.tibber.com/v1-beta/gql",
        timeout=30
    )
    return resource


@pytest.fixture
def mock_config_resource(tmp_path):
    """Mock configuration resource with test config files"""
    from dagster_project.resources.config_resource import ConfigResource

    # Create test config files
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
influxdb:
  url: "http://localhost:8086"
  bucket_raw: "test_raw"
  bucket_processed: "test_processed"
  timeout: 30

gas_conversion:
  energy_content: 11.504
  z_factor: 0.8885

tibber:
  meter_id: "haupt_strom"
  lookback_hours: 48
""")

    meters_file = tmp_path / "meters.yaml"
    meters_file.write_text("""
meters:
  - meter_id: "strom_total"
    type: "physical"
    output_unit: "kWh"
    description: "Total electricity"

  - meter_id: "gas_total"
    type: "master"
    output_unit: "m³"
    description: "Total gas consumption"
    periods:
      - start_date: "2020-01-01"
        end_date: "2024-12-31"
        composition_type: "single"
        source_meters: ["gas_meter_1"]
        source_unit: "m³"

  - meter_id: "eg_kalfire"
    type: "virtual"
    output_unit: "m³"
    description: "Fireplace gas consumption"
    calculation_type: "subtraction"
    base_meter: "gas_total"
    subtract_meters: ["gastherme_gesamt"]
    subtract_meter_conversions:
      gastherme_gesamt:
        from_unit: "kWh"
        to_unit: "m³"
""")

    patterns_file = tmp_path / "patterns.yaml"
    patterns_file.write_text("""
patterns:
  strom_total:
    monthly_percentages: [0.09, 0.09, 0.08, 0.08, 0.07, 0.07, 0.08, 0.08, 0.09, 0.09, 0.09, 0.09]
""")

    resource = ConfigResource(
        config_path=str(config_file),
        meters_config_path=str(meters_file),
        seasonal_patterns_path=str(patterns_file),
        start_year=2020
    )
    return resource


@pytest.fixture
def sample_meter_data():
    """Sample meter reading data"""
    dates = pd.date_range(start="2024-01-01", end="2024-01-31", freq="D")
    data = pd.DataFrame({
        "value": range(100, 100 + len(dates))
    }, index=dates)
    return data


@pytest.fixture
def sample_consumption_data():
    """Sample consumption data"""
    dates = pd.date_range(start="2024-01-01", end="2024-01-31", freq="D")
    data = pd.DataFrame({
        "value": [10.5, 12.3, 11.8, 9.5, 10.2] * 6 + [10.5]  # 31 days
    }, index=dates[:31])
    return data


@pytest.fixture
def sample_tibber_response():
    """Sample Tibber API response"""
    now = datetime.now()
    return [
        {
            "from": (now - timedelta(hours=i)).isoformat() + "Z",
            "to": (now - timedelta(hours=i-1)).isoformat() + "Z",
            "consumption": 1.2 + (i * 0.1),
            "cost": 0.25 + (i * 0.02),
            "unitPrice": 0.21,
            "unitPriceVAT": 0.04
        }
        for i in range(48, 0, -1)
    ]


@pytest.fixture
def mock_influx_client():
    """Mock InfluxClient from Nebenkosten/src"""
    with patch('src.influx_client.InfluxClient') as mock:
        instance = MagicMock()
        instance.discover_available_meters.return_value = ["strom_total", "gas_total"]
        instance.fetch_all_meter_data.return_value = pd.DataFrame({
            "value": range(100, 150)
        }, index=pd.date_range("2024-01-01", periods=50, freq="D"))
        instance.meter_data_cache = {}
        mock.return_value = instance
        yield instance


@pytest.fixture
def mock_data_processor():
    """Mock DataProcessor from Nebenkosten/src"""
    with patch('src.data_processor.DataProcessor') as mock:
        instance = MagicMock()
        instance.create_standardized_daily_series.return_value = pd.DataFrame({
            "value": range(100, 131)
        }, index=pd.date_range("2024-01-01", periods=31, freq="D"))
        instance.aggregate_daily_to_frequency.return_value = pd.DataFrame({
            "value": [100, 130]
        }, index=pd.date_range("2024-01-01", periods=2, freq="M"))
        mock.return_value = instance
        yield instance


@pytest.fixture
def mock_consumption_calculator():
    """Mock ConsumptionCalculator from Nebenkosten/src"""
    with patch('src.calculator.ConsumptionCalculator') as mock:
        instance = MagicMock()
        instance.calculate_consumption_from_readings.return_value = pd.DataFrame({
            "value": [10.5] * 30
        }, index=pd.date_range("2024-01-01", periods=30, freq="D"))
        mock.return_value = instance
        yield instance


@pytest.fixture
def dagster_context():
    """Build a Dagster asset execution context for testing"""
    return build_asset_context()


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment variables after each test"""
    yield
    # Cleanup happens here if needed
