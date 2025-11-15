"""
System/End-to-end tests
Tests full workflow execution with real-ish conditions
"""
import pytest
from unittest.mock import patch, MagicMock
from dagster import materialize_to_memory
import pandas as pd

from workflows_dagster.dagster_project import utility_repository
from workflows_dagster.dagster_project.jobs import tibber_sync_job, analytics_job
from tests.fixtures.mock_data import (
    generate_tibber_api_response,
    generate_multi_meter_data
)


class TestTibberSyncE2E:
    """End-to-end tests for Tibber sync workflow"""

    @pytest.mark.system
    @pytest.mark.slow
    @pytest.mark.tibber
    @patch('workflows_dagster.dagster_project.resources.tibber_resource.requests.post')
    @patch('workflows_dagster.dagster_project.assets.tibber_assets._get_last_influxdb_timestamp')
    @patch('workflows_dagster.dagster_project.assets.tibber_assets._write_to_influxdb')
    def test_complete_tibber_sync_flow(
        self,
        mock_write,
        mock_get_timestamp,
        mock_requests
    ):
        """Test complete Tibber sync from API to InfluxDB"""
        # Mock Tibber API response
        tibber_data = generate_tibber_api_response(hours=48)
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "viewer": {
                    "homes": [{
                        "consumption": {"nodes": tibber_data}
                    }]
                }
            }
        }
        mock_requests.return_value = mock_response

        # No existing data in InfluxDB
        mock_get_timestamp.return_value = None

        # Mock write success
        mock_write.return_value = len(tibber_data)

        # Execute job
        result = tibber_sync_job.execute_in_process()

        assert result.success
        # Verify Tibber API was called
        mock_requests.assert_called_once()
        # Verify data was written to InfluxDB
        mock_write.assert_called_once()


class TestAnalyticsE2E:
    """End-to-end tests for analytics workflow"""

    @pytest.mark.system
    @pytest.mark.slow
    @patch('workflows_dagster.dagster_project.assets.analytics_assets.InfluxClient')
    @patch('workflows_dagster.dagster_project.assets.analytics_assets.DataProcessor')
    @patch('workflows_dagster.dagster_project.assets.analytics_assets.ConsumptionCalculator')
    @patch('workflows_dagster.dagster_project.assets.influxdb_writer_assets.InfluxDBResource.get_client')
    def test_complete_analytics_pipeline(
        self,
        mock_get_client,
        mock_calc_class,
        mock_processor_class,
        mock_influx_class
    ):
        """Test complete analytics pipeline from discovery to storage"""
        # Setup mocks for full pipeline

        # 1. InfluxClient - discovery and fetch
        mock_influx = MagicMock()
        mock_influx.discover_available_meters.return_value = ["strom_total", "gas_total"]
        mock_influx.fetch_all_meter_data.side_effect = lambda meter_id, start: \
            generate_multi_meter_data([meter_id], days=31)[meter_id]
        mock_influx.meter_data_cache = {}
        mock_influx_class.return_value = mock_influx

        # 2. DataProcessor - interpolation
        mock_processor = MagicMock()
        from tests.fixtures.mock_data import generate_meter_readings
        mock_processor.create_standardized_daily_series.return_value = generate_meter_readings(days=31)
        mock_processor.aggregate_daily_to_frequency.return_value = generate_meter_readings(days=2)
        mock_processor_class.return_value = mock_processor

        # 3. ConsumptionCalculator - consumption calc
        mock_calc = MagicMock()
        from tests.fixtures.mock_data import generate_consumption_data
        mock_calc.calculate_consumption_from_readings.return_value = generate_consumption_data(days=30)
        mock_calc_class.return_value = mock_calc

        # 4. InfluxDB client for writing
        mock_client = MagicMock()
        mock_write_api = MagicMock()
        mock_client.write_api.return_value = mock_write_api
        mock_get_client.return_value.__enter__.return_value = mock_client

        # Execute analytics job
        result = analytics_job.execute_in_process()

        assert result.success

        # Verify key operations occurred
        mock_influx.discover_available_meters.assert_called()
        mock_influx.fetch_all_meter_data.assert_called()
        mock_processor.create_standardized_daily_series.assert_called()
        mock_calc.calculate_consumption_from_readings.assert_called()
        # Write API should have been called to write results
        assert mock_write_api.write.called


class TestFullSystemWithConfig:
    """System tests using actual config files"""

    @pytest.mark.system
    @pytest.mark.slow
    def test_load_and_validate_repository(self):
        """Test repository loads successfully with all definitions"""
        from workflows_dagster.dagster_project import utility_repository

        # Should load without errors
        assert utility_repository is not None

        # Check assets are defined
        assets = list(utility_repository.get_all_asset_specs())
        assert len(assets) >= 9  # We have 9 main assets

        # Check jobs are defined
        jobs = list(utility_repository.get_all_job_defs())
        assert len(jobs) >= 2  # tibber_sync and analytics_processing

        # Check schedules are defined
        schedules = list(utility_repository.get_all_schedule_defs())
        assert len(schedules) >= 2  # tibber_sync_hourly and analytics_daily

    @pytest.mark.system
    def test_asset_groups_defined(self):
        """Test assets are organized into proper groups"""
        from workflows_dagster.dagster_project import utility_repository

        assets = list(utility_repository.get_all_asset_specs())
        groups = set()
        for asset in assets:
            if hasattr(asset, 'group_name') and asset.group_name:
                groups.add(asset.group_name)

        # Should have expected groups
        expected_groups = {"ingestion", "discovery", "processing", "analysis", "storage"}
        assert groups.intersection(expected_groups), f"Found groups: {groups}"


class TestDataQuality:
    """System tests for data quality and validation"""

    @pytest.mark.system
    @patch('workflows_dagster.dagster_project.assets.analytics_assets.InfluxClient')
    @patch('workflows_dagster.dagster_project.assets.analytics_assets.DataProcessor')
    def test_interpolation_produces_valid_data(
        self,
        mock_processor_class,
        mock_influx_class,
        mock_influxdb_resource,
        mock_config_resource
    ):
        """Test interpolation produces valid, non-null data"""
        from dagster_project.assets.analytics_assets import (
            fetch_meter_data,
            interpolated_meter_series
        )
        from dagster import build_asset_context
        from tests.fixtures.mock_data import generate_meter_readings

        # Setup mocks
        mock_influx = MagicMock()
        mock_influx.fetch_all_meter_data.return_value = generate_meter_readings(days=31)
        mock_influx.meter_data_cache = {}
        mock_influx_class.return_value = mock_influx

        mock_processor = MagicMock()
        daily_data = generate_meter_readings(days=31)
        monthly_data = generate_meter_readings(days=2)
        mock_processor.create_standardized_daily_series.return_value = daily_data
        mock_processor.aggregate_daily_to_frequency.return_value = monthly_data
        mock_processor_class.return_value = mock_processor

        # Fetch data
        context = build_asset_context()
        raw_data_output = fetch_meter_data(
            context,
            ["meter1"],
            mock_influxdb_resource,
            mock_config_resource
        )

        # Interpolate
        daily, monthly = interpolated_meter_series(
            context,
            raw_data_output.value,
            mock_influxdb_resource,
            mock_config_resource
        )

        # Validate daily data
        assert "meter1" in daily.value
        daily_df = daily.value["meter1"]
        assert not daily_df.empty
        assert not daily_df["value"].isna().any()
        assert (daily_df["value"] >= 0).all()  # No negative meter readings

        # Validate monthly data
        assert "meter1" in monthly.value
        monthly_df = monthly.value["meter1"]
        assert not monthly_df.empty
        assert not monthly_df["value"].isna().any()

    @pytest.mark.system
    def test_consumption_never_exceeds_reasonable_bounds(self):
        """Test consumption calculations stay within reasonable bounds"""
        from dagster_project.assets.analytics_assets import consumption_data
        from dagster import build_asset_context
        from tests.fixtures.mock_data import generate_meter_readings
        from unittest.mock import patch

        context = build_asset_context()
        daily_series = {"meter1": generate_meter_readings(days=31, daily_increment=10.0)}
        master_series = {}

        with patch('dagster_project.assets.analytics_assets.ConsumptionCalculator') as mock_calc_class:
            from tests.fixtures.mock_data import generate_consumption_data
            mock_calc = MagicMock()
            mock_calc.calculate_consumption_from_readings.return_value = generate_consumption_data(days=30)
            mock_calc_class.return_value = mock_calc

            result = consumption_data(context, daily_series, master_series, None)

            # Verify consumption values are reasonable
            for meter_id, consumption_df in result.items():
                # Consumption should be positive
                assert (consumption_df["value"] >= 0).all()
                # Consumption shouldn't be astronomically high (< 1000 kWh/day)
                assert (consumption_df["value"] < 1000).all()
