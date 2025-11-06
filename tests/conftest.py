"""
Pytest Configuration and Fixtures
Provides common test fixtures and mocks for the test suite
"""
import pytest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
import tempfile
import yaml


@pytest.fixture
def test_config():
    """Provide a test configuration dictionary"""
    return {
        "influxdb": {
            "url": "http://test-influxdb:8086",
            "bucket_raw": "test_lampfi",
            "bucket_processed": "test_lampfi_processed",
            "timeout": 30,
            "retry_attempts": 3
        },
        "tibber": {
            "polling_interval": 3600,
            "lookback_hours": 48,
            "meter_id": "test_haupt_strom"
        },
        "gas_conversion": {
            "energy_content": 11.504,
            "z_factor": 0.8885
        },
        "workflows": {
            "analytics": {
                "schedule": "0 2 * * *",
                "start_year": 2023
            },
            "tibber_sync": {
                "schedule": "5 * * * *"
            }
        },
        "logging": {
            "level": "INFO",
            "format": "json",
            "file": "/tmp/test_utility_analyzer.log"
        },
        "influx_token": "test_token_123",
        "influx_org": "test_org_456",
        "tibber_token": "test_tibber_789",
        "meters": [
            {
                "meter_id": "test_physical_meter",
                "type": "physical",
                "output_unit": "kWh",
                "installation_date": "2023-01-01",
                "description": "Test physical meter"
            },
            {
                "meter_id": "test_master_meter",
                "type": "master",
                "output_unit": "kWh",
                "description": "Test master meter",
                "periods": [
                    {
                        "start_date": "2023-01-01",
                        "end_date": "2023-06-30",
                        "composition_type": "single",
                        "source_meters": ["old_meter"],
                        "source_unit": "kWh"
                    },
                    {
                        "start_date": "2023-07-01",
                        "end_date": "9999-12-31",
                        "composition_type": "single",
                        "source_meters": ["test_physical_meter"],
                        "source_unit": "kWh",
                        "apply_offset_from_previous_period": True
                    }
                ]
            },
            {
                "meter_id": "test_virtual_meter",
                "type": "virtual",
                "output_unit": "kWh",
                "description": "Test virtual meter",
                "calculation_type": "subtraction",
                "base_meter": "test_master_meter",
                "subtract_meters": ["test_physical_meter"]
            }
        ],
        "seasonal_patterns": {
            "test_physical_meter": [10, 9, 8, 7, 6, 5, 5, 6, 7, 8, 9, 10]
        }
    }


@pytest.fixture
def test_config_files(tmp_path, test_config):
    """Create temporary config files for testing"""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    # Main config
    main_config = {
        "influxdb": test_config["influxdb"],
        "tibber": test_config["tibber"],
        "gas_conversion": test_config["gas_conversion"],
        "workflows": test_config["workflows"],
        "logging": test_config["logging"],
        "meters_config": str(config_dir / "meters.yaml"),
        "seasonal_patterns_config": str(config_dir / "seasonal_patterns.yaml")
    }

    config_file = config_dir / "config.yaml"
    with config_file.open('w') as f:
        yaml.dump(main_config, f)

    # Meters config
    meters_config = {"meters": test_config["meters"]}
    meters_file = config_dir / "meters.yaml"
    with meters_file.open('w') as f:
        yaml.dump(meters_config, f)

    # Seasonal patterns
    patterns_config = {"patterns": {
        "test_physical_meter": {
            "monthly_percentages": test_config["seasonal_patterns"]["test_physical_meter"]
        }
    }}
    patterns_file = config_dir / "seasonal_patterns.yaml"
    with patterns_file.open('w') as f:
        yaml.dump(patterns_config, f)

    return config_dir


@pytest.fixture
def sample_meter_data():
    """Generate sample meter reading data"""
    timestamps = pd.date_range(
        start='2023-01-01',
        end='2023-12-31',
        freq='D',
        tz='UTC'
    )

    data = pd.DataFrame({
        'timestamp': timestamps,
        'value': range(100, 100 + len(timestamps))
    })

    return data


@pytest.fixture
def sample_consumption_data():
    """Generate sample consumption data"""
    timestamps = pd.date_range(
        start='2023-01-31',
        end='2023-12-31',
        freq='M',
        tz='UTC'
    )

    data = pd.DataFrame({
        'timestamp': timestamps,
        'consumption': [100, 95, 90, 85, 70, 60, 55, 65, 75, 85, 95, 105]
    })

    return data


@pytest.fixture
def tibber_api_response():
    """Mock Tibber API response"""
    return {
        "data": {
            "viewer": {
                "homes": [{
                    "consumption": {
                        "nodes": [
                            {
                                "from": "2023-12-01T00:00:00.000Z",
                                "to": "2023-12-01T01:00:00.000Z",
                                "consumption": 1.5,
                                "cost": 0.45,
                                "unitPrice": 0.30,
                                "unitPriceVAT": 0.06
                            },
                            {
                                "from": "2023-12-01T01:00:00.000Z",
                                "to": "2023-12-01T02:00:00.000Z",
                                "consumption": 1.2,
                                "cost": 0.36,
                                "unitPrice": 0.30,
                                "unitPriceVAT": 0.06
                            }
                        ]
                    }
                }]
            }
        }
    }


@pytest.fixture
def mock_influx_client():
    """Mock InfluxDB client"""
    mock_client = MagicMock()
    mock_client.discover_available_meters.return_value = [
        "test_physical_meter",
        "old_meter"
    ]
    mock_client.fetch_all_meter_data.return_value = pd.DataFrame({
        'timestamp': pd.date_range('2023-01-01', '2023-12-31', freq='D', tz='UTC'),
        'value': range(100, 465)
    })

    return mock_client


@pytest.fixture
def mock_requests_post(tibber_api_response):
    """Mock requests.post for API calls"""
    mock_response = Mock()
    mock_response.json.return_value = tibber_api_response
    mock_response.raise_for_status.return_value = None
    mock_response.status_code = 200

    with patch('requests.post', return_value=mock_response) as mock:
        yield mock


@pytest.fixture
def mock_influxdb_client():
    """Mock InfluxDB client context manager"""
    mock_client = MagicMock()
    mock_query_api = MagicMock()
    mock_write_api = MagicMock()

    mock_client.query_api.return_value = mock_query_api
    mock_client.write_api.return_value = mock_write_api

    # Mock query results
    mock_record = Mock()
    mock_record.get_time.return_value = datetime(2023, 12, 1, 0, 0, 0)
    mock_table = Mock()
    mock_table.records = [mock_record]
    mock_query_api.query.return_value = [mock_table]

    with patch('influxdb_client.InfluxDBClient', return_value=mock_client) as mock:
        yield mock


@pytest.fixture
def mock_env_vars(monkeypatch, test_config):
    """Set environment variables for testing"""
    monkeypatch.setenv("INFLUX_TOKEN", test_config["influx_token"])
    monkeypatch.setenv("INFLUX_ORG", test_config["influx_org"])
    monkeypatch.setenv("TIBBER_API_TOKEN", test_config["tibber_token"])


@pytest.fixture
def sample_anomalies():
    """Generate sample anomaly data"""
    return [
        {
            "timestamp": pd.Timestamp("2023-06-15", tz='UTC'),
            "consumption": 250.5,
            "meter_id": "test_physical_meter"
        },
        {
            "timestamp": pd.Timestamp("2023-08-20", tz='UTC'),
            "consumption": 300.2,
            "meter_id": "test_physical_meter"
        }
    ]


@pytest.fixture(autouse=True)
def cleanup_logs():
    """Clean up test log files after each test"""
    yield
    # Cleanup code runs after test
    log_file = Path("/tmp/test_utility_analyzer.log")
    if log_file.exists():
        log_file.unlink()
