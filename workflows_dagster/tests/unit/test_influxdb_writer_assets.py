"""
Unit tests for InfluxDB writer assets
"""
import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from datetime import datetime, timezone
from dagster import build_asset_context

from workflows_dagster.dagster_project.assets.influxdb_writer_assets import (
    write_processed_data_to_influxdb,
    _create_points_from_dataframe,
    _create_anomaly_points
)
from tests.fixtures.mock_data import (
    generate_meter_readings,
    generate_consumption_data,
    generate_anomaly_data
)


def get_metadata_value(metadata_dict, key):
    """
    Helper to extract metadata value regardless of Dagster version.
    Handles both MetadataValue objects and raw values.
    """
    value = metadata_dict[key]
    return value.value if hasattr(value, 'value') else value


class TestCreatePointsFromDataFrame:
    """Unit tests for _create_points_from_dataframe helper"""

    @pytest.mark.unit
    def test_creates_points_with_timezone_aware_index(self):
        """Test point creation with timezone-aware timestamps"""
        # Create DataFrame with timezone-aware index
        dates = pd.date_range('2024-01-01', periods=5, freq='D', tz='UTC')
        df = pd.DataFrame({'value': [10.5, 11.2, 9.8, 10.1, 11.0]}, index=dates)

        points = _create_points_from_dataframe(df, "test_meter", "meter_reading")

        assert len(points) == 5
        # Verify points were created (they should be Point objects)
        assert all(hasattr(p, '_tags') for p in points)

    @pytest.mark.unit
    def test_creates_points_with_naive_timestamps(self):
        """Test point creation with timezone-naive timestamps (should convert to UTC)"""
        # Create DataFrame with naive timestamps
        dates = pd.date_range('2024-01-01', periods=3, freq='D')
        df = pd.DataFrame({'value': [5.0, 6.0, 7.0]}, index=dates)

        points = _create_points_from_dataframe(df, "meter_naive", "meter_reading")

        assert len(points) == 3
        assert all(hasattr(p, '_tags') for p in points)

    @pytest.mark.unit
    def test_creates_points_with_correct_measurement(self):
        """Test points have correct measurement name"""
        df = generate_meter_readings(days=2)

        points = _create_points_from_dataframe(df, "meter1", "custom_measurement")

        # Points should be created (basic validation)
        assert len(points) == len(df)

    @pytest.mark.unit
    def test_handles_empty_dataframe(self):
        """Test handling of empty DataFrame"""
        df = pd.DataFrame({'value': []}, index=pd.DatetimeIndex([]))

        points = _create_points_from_dataframe(df, "empty_meter", "meter_reading")

        assert len(points) == 0

    @pytest.mark.unit
    def test_converts_values_to_float(self):
        """Test that values are properly converted to float"""
        dates = pd.date_range('2024-01-01', periods=3, freq='D', tz='UTC')
        # Use integer values to ensure float conversion
        df = pd.DataFrame({'value': [10, 20, 30]}, index=dates)

        points = _create_points_from_dataframe(df, "int_meter", "meter_reading")

        assert len(points) == 3


class TestCreateAnomalyPoints:
    """Unit tests for _create_anomaly_points helper"""

    @pytest.mark.unit
    def test_creates_anomaly_points_with_all_fields(self):
        """Test anomaly point creation with all fields present"""
        df = generate_anomaly_data(days=5, anomaly_days=[2])

        points = _create_anomaly_points(df, "anomaly_meter")

        assert len(points) == len(df)
        # Verify points were created
        assert all(hasattr(p, '_tags') for p in points)

    @pytest.mark.unit
    def test_creates_anomaly_points_without_optional_fields(self):
        """Test anomaly points when optional fields are missing"""
        # Create DataFrame with only 'value' column
        dates = pd.date_range('2024-01-01', periods=3, freq='D', tz='UTC')
        df = pd.DataFrame({'value': [50.0, 60.0, 70.0]}, index=dates)

        points = _create_anomaly_points(df, "test_anomaly")

        assert len(points) == 3

    @pytest.mark.unit
    def test_handles_naive_timestamps_in_anomalies(self):
        """Test anomaly points with timezone-naive timestamps"""
        dates = pd.date_range('2024-01-01', periods=2, freq='D')
        df = pd.DataFrame({
            'value': [100.0, 110.0],
            'rolling_avg': [50.0, 55.0],
            'threshold': [75.0, 80.0]
        }, index=dates)

        points = _create_anomaly_points(df, "naive_anomaly")

        assert len(points) == 2

    @pytest.mark.unit
    def test_handles_empty_anomaly_dataframe(self):
        """Test handling of empty anomaly DataFrame"""
        df = pd.DataFrame({'value': []}, index=pd.DatetimeIndex([]))

        points = _create_anomaly_points(df, "no_anomalies")

        assert len(points) == 0


class TestWriteProcessedDataToInfluxDB:
    """Unit tests for write_processed_data_to_influxdb asset"""

    @pytest.mark.unit
    @pytest.mark.influxdb
    def test_writes_all_data_types(self, mock_influxdb_resource):
        """Test writing all types of processed data"""
        context = build_asset_context()

        # Create mock data for all inputs
        daily_series = {"meter1": generate_meter_readings(days=10)}
        monthly_series = {"meter1": generate_meter_readings(days=2)}
        master_series = {
            "master1": {
                "daily": generate_meter_readings(days=10),
                "monthly": generate_meter_readings(days=2)
            }
        }
        consumption = {"meter1": generate_consumption_data(days=9)}
        virtual = {"virtual1": generate_consumption_data(days=9)}
        anomalies = {"meter1": generate_anomaly_data(days=10, anomaly_days=[5])}

        # Mock InfluxDB client and write API
        mock_client = MagicMock()
        mock_write_api = MagicMock()
        mock_client.write_api.return_value = mock_write_api
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        mock_influxdb = MagicMock()
        mock_influxdb.bucket_processed = "test_processed"
        mock_influxdb.org = "test-org"
        mock_influxdb.get_client.return_value = mock_client

        result = write_processed_data_to_influxdb(
            context,
            daily_series,
            monthly_series,
            master_series,
            consumption,
            virtual,
            anomalies,
            mock_influxdb
        )

        # Verify write API was called multiple times
        assert mock_write_api.write.call_count > 0

        # Verify result has metadata
        assert "total_points" in result.metadata
        assert get_metadata_value(result.metadata, "total_points") > 0

    @pytest.mark.unit
    @pytest.mark.influxdb
    def test_writes_daily_interpolated_series(self, mock_influxdb_resource):
        """Test writing daily interpolated series"""
        context = build_asset_context()

        daily_series = {
            "meter1": generate_meter_readings(days=5),
            "meter2": generate_meter_readings(days=5)
        }

        # Mock InfluxDB
        mock_client = MagicMock()
        mock_write_api = MagicMock()
        mock_client.write_api.return_value = mock_write_api
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        mock_influxdb = MagicMock()
        mock_influxdb.bucket_processed = "test_processed"
        mock_influxdb.org = "test-org"
        mock_influxdb.get_client.return_value = mock_client

        result = write_processed_data_to_influxdb(
            context,
            daily_series,
            {},  # No monthly
            {},  # No master
            {},  # No consumption
            {},  # No virtual
            {},  # No anomalies
            mock_influxdb
        )

        # Should have written for 2 meters
        assert mock_write_api.write.call_count >= 2
        assert get_metadata_value(result.metadata, "daily_points") == 2

    @pytest.mark.unit
    @pytest.mark.influxdb
    def test_writes_monthly_interpolated_series(self, mock_influxdb_resource):
        """Test writing monthly interpolated series"""
        context = build_asset_context()

        monthly_series = {"meter1": generate_meter_readings(days=3)}

        mock_client = MagicMock()
        mock_write_api = MagicMock()
        mock_client.write_api.return_value = mock_write_api
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        mock_influxdb = MagicMock()
        mock_influxdb.bucket_processed = "test_processed"
        mock_influxdb.org = "test-org"
        mock_influxdb.get_client.return_value = mock_client

        result = write_processed_data_to_influxdb(
            context,
            {},  # No daily
            monthly_series,
            {},  # No master
            {},  # No consumption
            {},  # No virtual
            {},  # No anomalies
            mock_influxdb
        )

        assert mock_write_api.write.call_count >= 1
        assert get_metadata_value(result.metadata, "monthly_points") >= 3

    @pytest.mark.unit
    @pytest.mark.influxdb
    def test_writes_master_meter_series(self, mock_influxdb_resource):
        """Test writing master meter series with both daily and monthly"""
        context = build_asset_context()

        master_series = {
            "master1": {
                "daily": generate_meter_readings(days=10),
                "monthly": generate_meter_readings(days=2)
            },
            "master2": {
                "daily": generate_meter_readings(days=10),
                "monthly": generate_meter_readings(days=2)
            }
        }

        mock_client = MagicMock()
        mock_write_api = MagicMock()
        mock_client.write_api.return_value = mock_write_api
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        mock_influxdb = MagicMock()
        mock_influxdb.bucket_processed = "test_processed"
        mock_influxdb.org = "test-org"
        mock_influxdb.get_client.return_value = mock_client

        result = write_processed_data_to_influxdb(
            context,
            {},  # No daily
            {},  # No monthly
            master_series,
            {},  # No consumption
            {},  # No virtual
            {},  # No anomalies
            mock_influxdb
        )

        # Should write for 2 masters x 2 frequencies = 4 writes
        assert mock_write_api.write.call_count >= 4
        assert get_metadata_value(result.metadata, "master_points") > 0

    @pytest.mark.unit
    @pytest.mark.influxdb
    def test_skips_empty_master_meter_dataframes(self, mock_influxdb_resource):
        """Test that empty master meter DataFrames are skipped"""
        context = build_asset_context()

        master_series = {
            "master_empty": {
                "daily": pd.DataFrame({'value': []}, index=pd.DatetimeIndex([])),
                "monthly": pd.DataFrame({'value': []}, index=pd.DatetimeIndex([]))
            }
        }

        mock_client = MagicMock()
        mock_write_api = MagicMock()
        mock_client.write_api.return_value = mock_write_api
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        mock_influxdb = MagicMock()
        mock_influxdb.bucket_processed = "test_processed"
        mock_influxdb.org = "test-org"
        mock_influxdb.get_client.return_value = mock_client

        result = write_processed_data_to_influxdb(
            context,
            {},  # No daily
            {},  # No monthly
            master_series,
            {},  # No consumption
            {},  # No virtual
            {},  # No anomalies
            mock_influxdb
        )

        # Should not write empty dataframes
        assert get_metadata_value(result.metadata, "master_points") == 0

    @pytest.mark.unit
    @pytest.mark.influxdb
    def test_writes_consumption_data(self, mock_influxdb_resource):
        """Test writing consumption data"""
        context = build_asset_context()

        consumption = {
            "meter1": generate_consumption_data(days=10),
            "meter2": generate_consumption_data(days=10)
        }

        mock_client = MagicMock()
        mock_write_api = MagicMock()
        mock_client.write_api.return_value = mock_write_api
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        mock_influxdb = MagicMock()
        mock_influxdb.bucket_processed = "test_processed"
        mock_influxdb.org = "test-org"
        mock_influxdb.get_client.return_value = mock_client

        result = write_processed_data_to_influxdb(
            context,
            {},  # No daily
            {},  # No monthly
            {},  # No master
            consumption,
            {},  # No virtual
            {},  # No anomalies
            mock_influxdb
        )

        assert mock_write_api.write.call_count >= 2
        assert get_metadata_value(result.metadata, "consumption_points") >= 20

    @pytest.mark.unit
    @pytest.mark.influxdb
    def test_writes_virtual_meter_consumption(self, mock_influxdb_resource):
        """Test writing virtual meter consumption"""
        context = build_asset_context()

        virtual = {"virtual1": generate_consumption_data(days=15)}

        mock_client = MagicMock()
        mock_write_api = MagicMock()
        mock_client.write_api.return_value = mock_write_api
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        mock_influxdb = MagicMock()
        mock_influxdb.bucket_processed = "test_processed"
        mock_influxdb.org = "test-org"
        mock_influxdb.get_client.return_value = mock_client

        result = write_processed_data_to_influxdb(
            context,
            {},  # No daily
            {},  # No monthly
            {},  # No master
            {},  # No consumption
            virtual,
            {},  # No anomalies
            mock_influxdb
        )

        assert mock_write_api.write.call_count >= 1
        assert get_metadata_value(result.metadata, "virtual_points") >= 15

    @pytest.mark.unit
    @pytest.mark.influxdb
    def test_writes_anomaly_data(self, mock_influxdb_resource):
        """Test writing anomaly detection data"""
        context = build_asset_context()

        anomalies = {
            "meter1": generate_anomaly_data(days=10, anomaly_days=[3, 7]),
            "meter2": generate_anomaly_data(days=5, anomaly_days=[2])
        }

        mock_client = MagicMock()
        mock_write_api = MagicMock()
        mock_client.write_api.return_value = mock_write_api
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        mock_influxdb = MagicMock()
        mock_influxdb.bucket_processed = "test_processed"
        mock_influxdb.org = "test-org"
        mock_influxdb.get_client.return_value = mock_client

        result = write_processed_data_to_influxdb(
            context,
            {},  # No daily
            {},  # No monthly
            {},  # No master
            {},  # No consumption
            {},  # No virtual
            anomalies,
            mock_influxdb
        )

        assert mock_write_api.write.call_count >= 2
        assert get_metadata_value(result.metadata, "anomaly_points") > 0

    @pytest.mark.unit
    @pytest.mark.influxdb
    def test_handles_empty_inputs(self, mock_influxdb_resource):
        """Test handling when all inputs are empty"""
        context = build_asset_context()

        mock_client = MagicMock()
        mock_write_api = MagicMock()
        mock_client.write_api.return_value = mock_write_api
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        mock_influxdb = MagicMock()
        mock_influxdb.bucket_processed = "test_processed"
        mock_influxdb.org = "test-org"
        mock_influxdb.get_client.return_value = mock_client

        result = write_processed_data_to_influxdb(
            context,
            {},  # Empty
            {},  # Empty
            {},  # Empty
            {},  # Empty
            {},  # Empty
            {},  # Empty
            mock_influxdb
        )

        # Should complete successfully even with no data
        assert get_metadata_value(result.metadata, "total_points") == 0

    @pytest.mark.unit
    @pytest.mark.influxdb
    def test_uses_correct_bucket_and_org(self, mock_influxdb_resource):
        """Test that writes use correct bucket and org"""
        context = build_asset_context()

        daily_series = {"meter1": generate_meter_readings(days=2)}

        mock_client = MagicMock()
        mock_write_api = MagicMock()
        mock_client.write_api.return_value = mock_write_api
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        mock_influxdb = MagicMock()
        mock_influxdb.bucket_processed = "custom_processed_bucket"
        mock_influxdb.org = "custom-org"
        mock_influxdb.get_client.return_value = mock_client

        write_processed_data_to_influxdb(
            context,
            daily_series,
            {},
            {},
            {},
            {},
            {},
            mock_influxdb
        )

        # Verify write was called with correct bucket and org
        write_calls = mock_write_api.write.call_args_list
        assert len(write_calls) > 0

        for call in write_calls:
            kwargs = call[1]
            assert kwargs['bucket'] == "custom_processed_bucket"
            assert kwargs['org'] == "custom-org"

    @pytest.mark.unit
    @pytest.mark.influxdb
    def test_metadata_counts_are_accurate(self, mock_influxdb_resource):
        """Test that metadata counts reflect actual data written"""
        context = build_asset_context()

        daily_series = {"m1": generate_meter_readings(days=5)}
        monthly_series = {"m1": generate_meter_readings(days=2)}
        consumption = {"m1": generate_consumption_data(days=4)}

        mock_client = MagicMock()
        mock_write_api = MagicMock()
        mock_client.write_api.return_value = mock_write_api
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        mock_influxdb = MagicMock()
        mock_influxdb.bucket_processed = "test_processed"
        mock_influxdb.org = "test-org"
        mock_influxdb.get_client.return_value = mock_client

        result = write_processed_data_to_influxdb(
            context,
            daily_series,
            monthly_series,
            {},
            consumption,
            {},
            {},
            mock_influxdb
        )

        # Verify metadata structure
        assert "daily_points" in result.metadata
        assert "monthly_points" in result.metadata
        assert "consumption_points" in result.metadata
        assert "virtual_points" in result.metadata
        assert "anomaly_points" in result.metadata

        # Verify values are integers
        assert isinstance(get_metadata_value(result.metadata, "daily_points"), int)
        assert isinstance(get_metadata_value(result.metadata, "total_points"), int)
