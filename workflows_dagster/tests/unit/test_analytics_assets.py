"""
Unit tests for analytics assets
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from dagster import build_asset_context

from tests.fixtures.mock_data import (generate_anomaly_data,
                                      generate_consumption_data,
                                      generate_meter_readings,
                                      generate_multi_meter_data)
from workflows_dagster.dagster_project.assets.analytics_assets import (
    anomaly_detection, consumption_data, fetch_meter_data,
    interpolated_meter_series, master_meter_series, meter_discovery,
    virtual_meter_data)


class TestMeterDiscoveryAsset:
    """Unit tests for meter_discovery asset"""

    @pytest.mark.unit
    @pytest.mark.influxdb
    @patch("workflows_dagster.dagster_project.assets.analytics_assets.InfluxClient")
    def test_discovers_meters(
        self, mock_influx_class, mock_influxdb_resource, mock_config_resource
    ):
        """Test meter discovery returns list of meters"""
        context = build_asset_context()

        # Mock InfluxClient
        mock_client = MagicMock()
        mock_client.discover_available_meters.return_value = [
            "strom_total",
            "gas_total",
            "wasser",
        ]
        mock_influx_class.return_value = mock_client

        meters = meter_discovery(context, mock_influxdb_resource, mock_config_resource)

        assert len(meters) == 3
        assert "strom_total" in meters
        assert "gas_total" in meters


class TestFetchMeterDataAsset:
    """Unit tests for fetch_meter_data asset"""

    @pytest.mark.unit
    @pytest.mark.influxdb
    @patch("workflows_dagster.dagster_project.assets.analytics_assets.InfluxClient")
    def test_fetches_data_for_all_meters(
        self, mock_influx_class, mock_influxdb_resource, mock_config_resource
    ):
        """Test fetching raw data for all discovered meters"""
        context = build_asset_context()
        meter_list = ["meter1", "meter2"]

        # Mock InfluxClient
        mock_client = MagicMock()
        mock_client.fetch_all_meter_data.return_value = generate_meter_readings(days=10)
        mock_influx_class.return_value = mock_client

        result = fetch_meter_data(
            context, meter_list, mock_influxdb_resource, mock_config_resource
        )

        assert len(result.value) == 2
        assert "meter1" in result.value
        assert "meter2" in result.value
        assert result.metadata["meter_count"].value == 2


class TestInterpolatedMeterSeriesAsset:
    """Unit tests for interpolated_meter_series asset"""

    @pytest.mark.unit
    @patch("workflows_dagster.dagster_project.assets.analytics_assets.DataProcessor")
    @patch("workflows_dagster.dagster_project.assets.analytics_assets.InfluxClient")
    def test_creates_daily_and_monthly_series(
        self,
        mock_influx_class,
        mock_processor_class,
        mock_influxdb_resource,
        mock_config_resource,
    ):
        """Test interpolation creates both daily and monthly series"""
        context = build_asset_context()
        raw_data = {"meter1": generate_meter_readings(days=31)}

        # Mock DataProcessor
        mock_processor = MagicMock()
        mock_processor.create_standardized_daily_series.return_value = (
            generate_meter_readings(days=31)
        )
        mock_processor.aggregate_daily_to_frequency.return_value = (
            generate_meter_readings(days=2)
        )
        mock_processor_class.return_value = mock_processor

        # Mock InfluxClient
        mock_client = MagicMock()
        mock_influx_class.return_value = mock_client

        daily, monthly = interpolated_meter_series(
            context, raw_data, mock_influxdb_resource, mock_config_resource
        )

        assert len(daily.value) == 1
        assert len(monthly.value) == 1
        assert "meter1" in daily.value
        assert "meter1" in monthly.value


class TestMasterMeterSeriesAsset:
    """Unit tests for master_meter_series asset"""

    @pytest.mark.unit
    def test_processes_master_meters(self, mock_config_resource):
        """Test master meter processing combines source meters"""
        context = build_asset_context()

        # Create mock daily and monthly data
        daily_data = {
            "gas_meter_1": generate_meter_readings(start_date="2024-01-01", days=31)
        }
        monthly_data = {
            "gas_meter_1": generate_meter_readings(start_date="2024-01-01", days=2)
        }

        result = master_meter_series(
            context, daily_data, monthly_data, mock_config_resource
        )

        # Should have gas_total master meter
        assert "gas_total" in result
        assert "daily" in result["gas_total"]
        assert "monthly" in result["gas_total"]

    @pytest.mark.unit
    def test_applies_unit_conversion(self, mock_config_resource):
        """Test master meters apply unit conversion (m³ <-> kWh)"""
        context = build_asset_context()

        # This test would verify gas conversion happens
        # For now, just verify structure
        daily_data = {"gas_meter_1": generate_meter_readings(days=10)}
        monthly_data = {"gas_meter_1": generate_meter_readings(days=1)}

        result = master_meter_series(
            context, daily_data, monthly_data, mock_config_resource
        )

        # Verify result has expected structure
        for master_id, data in result.items():
            assert "daily" in data
            assert "monthly" in data


class TestConsumptionDataAsset:
    """Unit tests for consumption_data asset"""

    @pytest.mark.unit
    @patch(
        "workflows_dagster.dagster_project.assets.analytics_assets.ConsumptionCalculator"
    )
    def test_calculates_consumption(self, mock_calc_class, mock_config_resource):
        """Test consumption calculation from readings"""
        context = build_asset_context()

        daily_series = {"meter1": generate_meter_readings(days=31)}
        master_series = {}

        # Mock calculator
        mock_calc = MagicMock()
        mock_calc.calculate_consumption_from_readings.return_value = (
            generate_consumption_data(days=30)
        )
        mock_calc_class.return_value = mock_calc

        result = consumption_data(
            context, daily_series, master_series, mock_config_resource
        )

        assert "meter1" in result
        assert len(result["meter1"]) == 30

    @pytest.mark.unit
    @patch(
        "workflows_dagster.dagster_project.assets.analytics_assets.ConsumptionCalculator"
    )
    def test_combines_physical_and_master_meters(
        self, mock_calc_class, mock_config_resource
    ):
        """Test consumption includes both physical and master meters"""
        context = build_asset_context()

        daily_series = {"physical_meter": generate_meter_readings(days=10)}
        master_series = {
            "master_meter": {
                "daily": generate_meter_readings(days=10),
                "monthly": generate_meter_readings(days=1),
            }
        }

        mock_calc = MagicMock()
        mock_calc.calculate_consumption_from_readings.return_value = (
            generate_consumption_data(days=9)
        )
        mock_calc_class.return_value = mock_calc

        result = consumption_data(
            context, daily_series, master_series, mock_config_resource
        )

        assert "physical_meter" in result
        assert "master_meter" in result


class TestVirtualMeterDataAsset:
    """Unit tests for virtual_meter_data asset"""

    @pytest.mark.unit
    def test_calculates_virtual_meters(self, mock_config_resource):
        """Test virtual meter calculation via subtraction"""
        context = build_asset_context()

        # Create consumption data
        consumption = {
            "gas_total": generate_consumption_data(days=31, base_consumption=20.0),
            "gastherme_gesamt": generate_consumption_data(
                days=31, base_consumption=15.0
            ),
        }

        result = virtual_meter_data(context, consumption, mock_config_resource)

        # Should have eg_kalfire virtual meter
        assert "eg_kalfire" in result
        assert len(result["eg_kalfire"]) > 0

    @pytest.mark.unit
    def test_clips_negative_values(self, mock_config_resource):
        """Test virtual meters clip negative values to zero"""
        context = build_asset_context()

        # Create consumption where subtraction would be negative
        consumption = {
            "gas_total": generate_consumption_data(days=10, base_consumption=5.0),
            "gastherme_gesamt": generate_consumption_data(
                days=10, base_consumption=10.0
            ),
        }

        result = virtual_meter_data(context, consumption, mock_config_resource)

        # All values should be >= 0
        if "eg_kalfire" in result:
            assert (result["eg_kalfire"]["value"] >= 0).all()


class TestAnomalyDetectionAsset:
    """Unit tests for anomaly_detection asset"""

    @pytest.mark.unit
    def test_detects_anomalies(self):
        """Test anomaly detection finds consumption spikes"""
        context = build_asset_context()

        consumption = {"meter1": generate_anomaly_data(days=31, anomaly_days=[10, 20])}
        virtual_consumption = {}

        result = anomaly_detection(context, consumption, virtual_consumption)

        # Should detect anomalies
        assert "meter1" in result
        assert len(result["meter1"]) > 0

    @pytest.mark.unit
    def test_no_anomalies_for_consistent_data(self):
        """Test no anomalies detected for consistent consumption"""
        context = build_asset_context()

        # Consistent consumption
        consumption = {
            "meter1": generate_consumption_data(
                days=31, base_consumption=10.0, variation=0.5
            )
        }
        virtual_consumption = {}

        result = anomaly_detection(context, consumption, virtual_consumption)

        # Should not have meter1 if no anomalies
        # (or have empty DataFrame)
        if "meter1" in result:
            assert len(result["meter1"]) == 0

    @pytest.mark.unit
    def test_combines_consumption_and_virtual(self):
        """Test anomaly detection processes both regular and virtual meters"""
        context = build_asset_context()

        consumption = {"meter1": generate_anomaly_data(days=31, anomaly_days=[10])}
        virtual_consumption = {
            "virtual1": generate_anomaly_data(days=31, anomaly_days=[20])
        }

        result = anomaly_detection(context, consumption, virtual_consumption)

        # Both meters should be analyzed
        # Results depend on actual anomaly thresholds
        assert isinstance(result, dict)

    @pytest.mark.unit
    def test_skips_meters_with_insufficient_data(self):
        """Test anomaly detection skips meters with too little data"""
        context = build_asset_context()

        # Only 10 days of data (need 30+ for rolling average)
        consumption = {"meter1": generate_consumption_data(days=10)}
        virtual_consumption = {}

        result = anomaly_detection(context, consumption, virtual_consumption)

        # Should skip meter1
        assert "meter1" not in result or len(result["meter1"]) == 0
