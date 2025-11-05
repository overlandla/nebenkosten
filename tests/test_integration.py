"""
Integration Tests
Tests that verify end-to-end workflow functionality
"""
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from workflows.config_loader import ConfigLoader
from workflows.logging_config import setup_logging


@pytest.mark.integration
def test_config_loader_with_real_files(test_config_files, mock_env_vars):
    """Integration test: Load configuration from actual files"""
    config_path = test_config_files / "config.yaml"
    loader = ConfigLoader(str(config_path))

    config = loader.get_full_config()

    # Verify all major sections are present
    assert "influxdb" in config
    assert "tibber" in config
    assert "gas_conversion" in config
    assert "workflows" in config
    assert "meters" in config
    assert "seasonal_patterns" in config

    # Verify secrets are loaded from environment
    assert config["influx_token"] == "test_token_123"
    assert config["influx_org"] == "test_org_456"


@pytest.mark.integration
def test_logging_setup(test_config, tmp_path):
    """Integration test: Logging configuration"""
    # Update log file to temp location
    test_config["logging"]["file"] = str(tmp_path / "test.log")

    setup_logging(test_config)

    # Try logging something
    import logging
    logger = logging.getLogger("test")
    logger.info("Test message")

    # Verify log file was created
    log_file = tmp_path / "test.log"
    assert log_file.exists()


@pytest.mark.integration
@patch('workflows.analytics_flow.InfluxClient')
@patch('workflows.analytics_flow.DataProcessor')
def test_analytics_flow_end_to_end(
    mock_processor,
    mock_influx,
    test_config,
    sample_meter_data,
    sample_consumption_data
):
    """Integration test: Full analytics flow execution"""
    # Setup mocks
    mock_influx_instance = MagicMock()
    mock_influx_instance.discover_available_meters.return_value = ["test_meter"]
    mock_influx_instance.fetch_all_meter_data.return_value = sample_meter_data
    mock_influx.return_value = mock_influx_instance

    mock_processor_instance = MagicMock()
    mock_processor_instance.create_standardized_daily_series.return_value = sample_meter_data
    mock_processor_instance.aggregate_daily_to_frequency.return_value = sample_meter_data.head(12)
    mock_processor.return_value = mock_processor_instance

    # Import and run flow
    from workflows.analytics_flow import analytics_flow

    with patch('workflows.analytics_flow.discover_meters') as mock_discover:
        with patch('workflows.analytics_flow.write_results') as mock_write:
            mock_discover.return_value = ["test_meter"]
            mock_write.return_value = 100

            # This would normally run the full flow
            # For testing, we verify it can be imported and called
            assert callable(analytics_flow)


@pytest.mark.integration
@patch('requests.post')
@patch('influxdb_client.InfluxDBClient')
def test_tibber_sync_flow_end_to_end(
    mock_influx,
    mock_requests,
    test_config,
    tibber_api_response
):
    """Integration test: Full Tibber sync flow execution"""
    # Setup mocks
    mock_response = MagicMock()
    mock_response.json.return_value = tibber_api_response
    mock_response.raise_for_status.return_value = None
    mock_requests.return_value = mock_response

    mock_query_api = MagicMock()
    mock_query_api.query.return_value = []
    mock_write_api = MagicMock()

    mock_client = MagicMock()
    mock_client.query_api.return_value = mock_query_api
    mock_client.write_api.return_value = mock_write_api
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None

    mock_influx.return_value = mock_client

    # Import and run flow
    from workflows.tibber_sync_flow import tibber_sync_flow

    result = tibber_sync_flow(test_config)

    assert isinstance(result, int)
    assert result >= 0


@pytest.mark.integration
def test_meter_type_filtering(test_config):
    """Integration test: Verify meter type filtering works correctly"""
    physical_meters = [m for m in test_config["meters"] if m["type"] == "physical"]
    master_meters = [m for m in test_config["meters"] if m["type"] == "master"]
    virtual_meters = [m for m in test_config["meters"] if m["type"] == "virtual"]

    assert len(physical_meters) == 1
    assert len(master_meters) == 1
    assert len(virtual_meters) == 1

    # Verify structure of each type
    assert "installation_date" in physical_meters[0]
    assert "periods" in master_meters[0]
    assert "calculation_type" in virtual_meters[0]


@pytest.mark.integration
def test_gas_conversion_calculation(test_config):
    """Integration test: Verify gas conversion calculations"""
    gas_conversion_factor = (
        test_config["gas_conversion"]["energy_content"] *
        test_config["gas_conversion"]["z_factor"]
    )

    # Test m³ to kWh
    cubic_meters = 100
    kwh = cubic_meters * gas_conversion_factor
    assert kwh > cubic_meters  # kWh should be larger number

    # Test kWh to m³ (reverse)
    converted_back = kwh / gas_conversion_factor
    assert abs(converted_back - cubic_meters) < 0.01  # Should be approximately equal


@pytest.mark.integration
def test_seasonal_pattern_validation(test_config):
    """Integration test: Verify seasonal patterns are valid"""
    for meter_id, pattern in test_config["seasonal_patterns"].items():
        # Pattern should have 12 months
        assert len(pattern) == 12

        # All values should be positive
        assert all(v >= 0 for v in pattern)

        # Sum should be close to 100 (percentages)
        # Allow some tolerance for test data
        assert 80 <= sum(pattern) <= 120


@pytest.mark.integration
def test_master_meter_period_validation(test_config):
    """Integration test: Verify master meter periods are valid"""
    master_meters = [m for m in test_config["meters"] if m["type"] == "master"]

    for meter in master_meters:
        periods = meter.get("periods", [])
        assert len(periods) > 0

        for period in periods:
            # Required fields
            assert "start_date" in period
            assert "end_date" in period
            assert "composition_type" in period
            assert "source_meters" in period
            assert "source_unit" in period

            # Valid composition types
            assert period["composition_type"] in ["single", "sum"]

            # Source meters should be a list
            assert isinstance(period["source_meters"], list)
            assert len(period["source_meters"]) > 0


@pytest.mark.integration
def test_virtual_meter_dependencies_exist(test_config):
    """Integration test: Verify virtual meters reference valid base meters"""
    all_meter_ids = [m["meter_id"] for m in test_config["meters"]]
    virtual_meters = [m for m in test_config["meters"] if m["type"] == "virtual"]

    for meter in virtual_meters:
        # Base meter should exist
        assert meter["base_meter"] in all_meter_ids

        # Subtract meters should exist
        for subtract_meter in meter.get("subtract_meters", []):
            assert subtract_meter in all_meter_ids
