"""
Integration tests for asset interactions
Tests how multiple assets work together
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from dagster import AssetSelection, materialize

from tests.fixtures.mock_data import generate_meter_readings
from workflows_dagster.dagster_project.assets import (
    fetch_meter_data,
    interpolated_meter_series,
    meter_discovery,
)
from workflows_dagster.dagster_project.resources import ConfigResource, InfluxDBResource


class TestAssetPipeline:
    """Integration tests for asset pipeline"""

    @pytest.mark.integration
    @pytest.mark.slow
    @patch("workflows_dagster.dagster_project.assets.analytics_assets.InfluxClient")
    @patch("workflows_dagster.dagster_project.assets.analytics_assets.DataProcessor")
    def test_discovery_to_interpolation_pipeline(
        self, mock_processor_class, mock_influx_class, mock_config_resource
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
        mock_processor.create_standardized_daily_series.return_value = (
            generate_meter_readings(days=31)
        )
        mock_processor.aggregate_daily_to_frequency.return_value = (
            generate_meter_readings(days=2)
        )
        mock_processor_class.return_value = mock_processor

        # Mock InfluxDB resource
        influxdb = InfluxDBResource(
            url="http://localhost:8086", bucket_raw="test", bucket_processed="test"
        )

        # Materialize assets
        result = materialize(
            assets=[meter_discovery, fetch_meter_data, interpolated_meter_series],
            resources={"influxdb": influxdb, "config": mock_config_resource},
        )

        assert result.success
        assert len(result.asset_materializations_for_node("meter_discovery")) == 1
        assert len(result.asset_materializations_for_node("fetch_meter_data")) == 1
        assert (
            len(result.asset_materializations_for_node("interpolated_meter_series"))
            == 2
        )  # daily + monthly

    @pytest.mark.integration
    def test_asset_dependencies_resolve(self, mock_config_resource):
        """Test that asset dependencies are correctly defined"""
        from dagster_project import (
            consumption_data,
            fetch_meter_data,
            interpolated_meter_series,
            meter_discovery,
            tibber_consumption_raw,
            virtual_meter_data,
        )

        # Verify assets are importable and have correct structure
        assert tibber_consumption_raw is not None
        assert meter_discovery is not None
        assert fetch_meter_data is not None
        assert interpolated_meter_series is not None
        assert consumption_data is not None
        assert virtual_meter_data is not None

        # Check that assets have keys
        assert hasattr(meter_discovery, "key")
        assert hasattr(fetch_meter_data, "key")


class TestJobExecution:
    """Integration tests for job execution"""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_analytics_job_exists(self, mock_config_resource):
        """Test analytics job is properly defined"""
        from dagster_project.jobs import analytics_job, tibber_sync_job

        # Verify jobs are importable
        assert analytics_job is not None
        assert tibber_sync_job is not None

        # Verify jobs have correct names
        assert hasattr(analytics_job, "name")
        assert analytics_job.name == "analytics_processing"

        assert hasattr(tibber_sync_job, "name")
        assert tibber_sync_job.name == "tibber_sync"


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
            url="http://localhost:8086", bucket_raw="test", bucket_processed="test"
        )

        # Should be able to get client
        with patch("dagster_project.resources.influxdb_resource.InfluxDBClient"):
            client = resource.get_client()
            assert client is not None
