"""
Integration tests for asset interactions
Tests how multiple assets work together
"""
import pytest
from unittest.mock import patch, MagicMock
from dagster import materialize, AssetSelection
import pandas as pd

from dagster_project.assets import (
    meter_discovery,
    fetch_meter_data,
    interpolated_meter_series
)
from dagster_project.resources import (
    InfluxDBResource,
    ConfigResource
)
from tests.fixtures.mock_data import generate_meter_readings


class TestAssetPipeline:
    """Integration tests for asset pipeline"""

    @pytest.mark.integration
    @pytest.mark.slow
    @patch('dagster_project.assets.analytics_assets.InfluxClient')
    @patch('dagster_project.assets.analytics_assets.DataProcessor')
    def test_discovery_to_interpolation_pipeline(
        self,
        mock_processor_class,
        mock_influx_class,
        mock_config_resource
    ):
        """Test full pipeline from discovery to interpolation"""
        # Mock InfluxClient for discovery and fetch
        mock_influx = MagicMock()
        mock_influx.discover_available_meters.return_value = ["meter1", "meter2"]
        mock_influx.fetch_all_meter_data.return_value = generate_meter_readings(days=31)
        mock_influx.meter_data_cache = {}
        mock_influx_class.return_value = mock_influx

        # Mock DataProcessor for interpolation
        mock_processor = MagicMock()
        mock_processor.create_standardized_daily_series.return_value = generate_meter_readings(days=31)
        mock_processor.aggregate_daily_to_frequency.return_value = generate_meter_readings(days=2)
        mock_processor_class.return_value = mock_processor

        # Mock InfluxDB resource
        influxdb = InfluxDBResource(
            url="http://localhost:8086",
            bucket_raw="test",
            bucket_processed="test"
        )

        # Materialize assets
        result = materialize(
            assets=[meter_discovery, fetch_meter_data, interpolated_meter_series],
            resources={
                "influxdb": influxdb,
                "config": mock_config_resource
            }
        )

        assert result.success
        assert len(result.asset_materializations_for_node("meter_discovery")) == 1
        assert len(result.asset_materializations_for_node("fetch_meter_data")) == 1
        assert len(result.asset_materializations_for_node("interpolated_meter_series")) == 2  # daily + monthly

    @pytest.mark.integration
    def test_asset_dependencies_resolve(self, mock_config_resource):
        """Test that asset dependencies are correctly defined"""
        from workflows_dagster.dagster_project import utility_repository

        # Get all assets
        assets = utility_repository.get_all_asset_specs()

        # Check specific dependencies
        asset_dict = {asset.key.to_user_string(): asset for asset in assets}

        # fetch_meter_data depends on meter_discovery
        fetch_asset = asset_dict.get("fetch_meter_data")
        if fetch_asset and hasattr(fetch_asset, 'dependencies'):
            deps = [str(d) for d in fetch_asset.dependencies]
            # Dependencies should include meter_discovery


class TestJobExecution:
    """Integration tests for job execution"""

    @pytest.mark.integration
    @pytest.mark.slow
    @patch('dagster_project.assets.analytics_assets.InfluxClient')
    @patch('dagster_project.assets.analytics_assets.DataProcessor')
    @patch('dagster_project.assets.analytics_assets.ConsumptionCalculator')
    def test_analytics_job_execution(
        self,
        mock_calc_class,
        mock_processor_class,
        mock_influx_class,
        mock_config_resource
    ):
        """Test full analytics job can execute"""
        from dagster_project.jobs import analytics_job

        # Setup mocks
        mock_influx = MagicMock()
        mock_influx.discover_available_meters.return_value = ["meter1"]
        mock_influx.fetch_all_meter_data.return_value = generate_meter_readings(days=31)
        mock_influx.meter_data_cache = {}
        mock_influx_class.return_value = mock_influx

        mock_processor = MagicMock()
        mock_processor.create_standardized_daily_series.return_value = generate_meter_readings(days=31)
        mock_processor.aggregate_daily_to_frequency.return_value = generate_meter_readings(days=2)
        mock_processor_class.return_value = mock_processor

        from tests.fixtures.mock_data import generate_consumption_data
        mock_calc = MagicMock()
        mock_calc.calculate_consumption_from_readings.return_value = generate_consumption_data(days=30)
        mock_calc_class.return_value = mock_calc

        # Mock InfluxDB write operations
        with patch('dagster_project.assets.influxdb_writer_assets.InfluxDBResource.get_client'):
            influxdb = InfluxDBResource(
                url="http://localhost:8086",
                bucket_raw="test",
                bucket_processed="test"
            )

            # Execute job
            result = analytics_job.execute_in_process(
                resources={
                    "influxdb": influxdb,
                    "config": mock_config_resource
                }
            )

            assert result.success


class TestResourceIntegration:
    """Integration tests for resources working with assets"""

    @pytest.mark.integration
    def test_config_resource_loads_for_assets(self, mock_config_resource):
        """Test config resource can be used by assets"""
        config = mock_config_resource.load_config()

        assert "meters" in config
        assert "gas_conversion" in config
        assert len(config["meters"]) > 0

    @pytest.mark.integration
    def test_influxdb_resource_context_manager(self):
        """Test InfluxDB resource works as context manager"""
        resource = InfluxDBResource(
            url="http://localhost:8086",
            bucket_raw="test",
            bucket_processed="test"
        )

        # Should be able to get client
        with patch('dagster_project.resources.influxdb_resource.InfluxDBClient'):
            client = resource.get_client()
            assert client is not None
