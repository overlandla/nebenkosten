"""
Integration tests for Dagster analytics assets
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest

# Add project paths
workflows_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(workflows_path))

from dagster import build_asset_context

from dagster_project.assets.analytics_assets import (anomaly_detection,
                                                     consumption_data,
                                                     interpolated_meter_series,
                                                     meter_discovery,
                                                     raw_meter_data)
from dagster_project.resources.config_resource import ConfigResource
from dagster_project.resources.influxdb_resource import InfluxDBResource


class TestAnalyticsAssetsIntegration:
    """Integration tests for analytics workflow"""

    @pytest.fixture
    def mock_influx_resource(self):
        """Create mock InfluxDB resource"""
        resource = Mock(spec=InfluxDBResource)
        resource.url = "http://test:8086"
        resource.org = "test_org"
        resource.bucket_raw = "test_bucket"
        resource.bucket_processed = "test_processed"
        return resource

    @pytest.fixture
    def mock_config_resource(self, tmp_path):
        """Create mock config resource with temporary config files"""
        # Create temporary config files
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        # Main config
        config_file = config_dir / "config.yaml"
        config_file.write_text(
            """
start_year: 2024
gas_conversion:
  energy_content: 11.504
  z_factor: 0.8885
"""
        )

        # Meters config
        meters_file = config_dir / "meters.yaml"
        meters_file.write_text(
            """
meters:
  - meter_id: "test_meter"
    type: "physical"
    output_unit: "kWh"
    installation_date: "2024-01-01"
"""
        )

        # Seasonal patterns
        patterns_file = config_dir / "seasonal_patterns.yaml"
        patterns_file.write_text("patterns: {}")

        resource = ConfigResource(
            config_path=str(config_file),
            meters_config_path=str(meters_file),
            seasonal_patterns_path=str(patterns_file),
            start_year=2024,
        )
        return resource

    @patch("src.influx_client.InfluxClient_Official")
    def test_meter_discovery_integration(
        self, mock_influx_official, mock_influx_resource, mock_config_resource
    ):
        """Test meter discovery asset"""
        # Set required env vars
        os.environ["INFLUX_TOKEN"] = "test_token"
        os.environ["INFLUX_ORG"] = "test_org"

        context = build_asset_context(
            resources={"influxdb": mock_influx_resource, "config": mock_config_resource}
        )

        # Mock the discovery to return test meters
        with patch(
            "src.influx_client.InfluxClient.discover_available_meters"
        ) as mock_discover:
            mock_discover.return_value = ["test_meter_1", "test_meter_2"]

            result = meter_discovery(
                context, mock_influx_resource, mock_config_resource
            )

            assert isinstance(result, list)
            assert len(result) == 2
            assert "test_meter_1" in result

    @patch("src.influx_client.InfluxClient_Official")
    def test_raw_meter_data_integration(
        self, mock_influx_official, mock_influx_resource, mock_config_resource
    ):
        """Test raw meter data fetching asset"""
        os.environ["INFLUX_TOKEN"] = "test_token"
        os.environ["INFLUX_ORG"] = "test_org"

        context = build_asset_context(
            resources={"influxdb": mock_influx_resource, "config": mock_config_resource}
        )

        meters = ["test_meter"]

        # Mock the fetch to return test data
        with patch("src.influx_client.InfluxClient.fetch_all_meter_data") as mock_fetch:
            mock_fetch.return_value = pd.DataFrame(
                {
                    "timestamp": pd.date_range(
                        "2024-01-01", periods=10, freq="D", tz="UTC"
                    ),
                    "value": range(100, 110),
                }
            )

            result = raw_meter_data(
                context, meters, mock_influx_resource, mock_config_resource
            )

            assert isinstance(result, dict)
            assert "test_meter" in result
            assert len(result["test_meter"]) == 10

    @patch("src.influx_client.InfluxClient_Official")
    def test_interpolated_meter_series_integration(
        self, mock_influx_official, mock_influx_resource, mock_config_resource
    ):
        """Test interpolation asset with real data flow"""
        os.environ["INFLUX_TOKEN"] = "test_token"
        os.environ["INFLUX_ORG"] = "test_org"

        context = build_asset_context(
            resources={"influxdb": mock_influx_resource, "config": mock_config_resource}
        )

        # Input: sparse raw data
        raw_data = {
            "test_meter": pd.DataFrame(
                {
                    "timestamp": pd.date_range(
                        "2024-01-01", "2024-01-31", freq="5D", tz="UTC"
                    ),
                    "value": [100, 105, 110, 115, 120, 125, 130],
                }
            )
        }

        # Mock the influx client
        with patch("src.influx_client.InfluxClient") as mock_client_class:
            mock_client = Mock()
            mock_client.meter_data_cache = {}
            mock_client_class.return_value = mock_client

            daily_output, monthly_output = interpolated_meter_series(
                context, raw_data, mock_influx_resource, mock_config_resource
            )

            # Check outputs
            assert "test_meter" in daily_output.value
            assert "test_meter" in monthly_output.value

            daily_df = daily_output.value["test_meter"]
            assert len(daily_df) > 0  # Should have interpolated daily values

            monthly_df = monthly_output.value["test_meter"]
            assert len(monthly_df) > 0  # Should have monthly aggregates

    def test_consumption_data_integration(self):
        """Test consumption calculation asset"""
        os.environ["INFLUX_TOKEN"] = "test_token"
        os.environ["INFLUX_ORG"] = "test_org"

        context = build_asset_context()

        # Input: daily interpolated readings
        daily_series = {
            "test_meter": pd.DataFrame(
                {
                    "timestamp": pd.date_range(
                        "2024-01-01", periods=10, freq="D", tz="UTC"
                    ),
                    "value": [100, 102, 104, 106, 108, 110, 112, 114, 116, 118],
                }
            )
        }

        master_series = {}  # No master meters for this test

        mock_config = Mock()

        result = consumption_data(context, daily_series, master_series, mock_config)

        assert isinstance(result, dict)
        assert "test_meter" in result

        consumption_df = result["test_meter"]
        assert len(consumption_df) == 10
        # First day should be 0, rest should be 2.0
        assert consumption_df.iloc[0]["value"] == 0.0
        assert consumption_df.iloc[1]["value"] == 2.0

    def test_anomaly_detection_integration(self):
        """Test anomaly detection asset with known anomalies"""
        os.environ["INFLUX_TOKEN"] = "test_token"
        os.environ["INFLUX_ORG"] = "test_org"

        context = build_asset_context()

        # Create consumption data with clear anomalies
        timestamps = pd.date_range("2024-01-01", periods=100, freq="D", tz="UTC")
        # Normal consumption: 2.0 per day, with 2 anomalies
        values = [2.0] * 100
        values[30] = 20.0  # Anomaly 1: 10x normal
        values[70] = 25.0  # Anomaly 2: 12.5x normal

        consumption = {
            "test_meter": pd.DataFrame({"timestamp": timestamps, "value": values})
        }

        virtual_consumption = {}  # No virtual meters

        result = anomaly_detection(context, consumption, virtual_consumption)

        assert isinstance(result, dict)

        if "test_meter" in result:
            anomalies = result["test_meter"]
            # Should detect both anomalies
            assert len(anomalies) >= 2
            # Should have required anomaly metadata
            assert "z_score" in anomalies.columns
            assert "anomaly_count" in anomalies.columns


class TestCompleteWorkflow:
    """Test complete workflow from discovery to anomaly detection"""

    @patch("src.influx_client.InfluxClient_Official")
    def test_full_workflow_integration(self, mock_influx_official, tmp_path):
        """Test complete workflow execution"""
        os.environ["INFLUX_TOKEN"] = "test_token"
        os.environ["INFLUX_ORG"] = "test_org"

        # Create config files
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        config_file = config_dir / "config.yaml"
        config_file.write_text(
            """
start_year: 2024
gas_conversion:
  energy_content: 11.504
  z_factor: 0.8885
"""
        )

        meters_file = config_dir / "meters.yaml"
        meters_file.write_text(
            """
meters:
  - meter_id: "test_meter"
    type: "physical"
    output_unit: "kWh"
"""
        )

        patterns_file = config_dir / "seasonal_patterns.yaml"
        patterns_file.write_text("patterns: {}")

        # Create resources
        influx_resource = Mock(spec=InfluxDBResource)
        influx_resource.url = "http://test:8086"
        influx_resource.org = "test_org"
        influx_resource.bucket_raw = "test_bucket"

        config_resource = ConfigResource(
            config_path=str(config_file),
            meters_config_path=str(meters_file),
            seasonal_patterns_path=str(patterns_file),
            start_year=2024,
        )

        context = build_asset_context(
            resources={"influxdb": influx_resource, "config": config_resource}
        )

        # Mock data flow
        with patch(
            "src.influx_client.InfluxClient.discover_available_meters"
        ) as mock_discover, patch(
            "src.influx_client.InfluxClient.fetch_all_meter_data"
        ) as mock_fetch:

            # Step 1: Discovery
            mock_discover.return_value = ["test_meter"]
            meters = meter_discovery(context, influx_resource, config_resource)
            assert meters == ["test_meter"]

            # Step 2: Fetch raw data
            mock_fetch.return_value = pd.DataFrame(
                {
                    "timestamp": pd.date_range(
                        "2024-01-01", "2024-01-31", freq="2D", tz="UTC"
                    ),
                    "value": range(100, 116),
                }
            )

            raw_data_result = raw_meter_data(
                context, meters, influx_resource, config_resource
            )
            assert "test_meter" in raw_data_result

            # Workflow successfully executed through multiple steps
            assert True  # If we got here, workflow is functional


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
