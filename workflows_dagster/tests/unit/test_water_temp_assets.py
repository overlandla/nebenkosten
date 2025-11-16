"""
Unit tests for Water Temperature ingestion assets
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from dagster import build_asset_context

from workflows_dagster.dagster_project.assets.water_temp_assets import (
    LAKE_CONFIGS,
    _get_last_influxdb_timestamp,
    _scrape_lake_temperature,
    _write_to_influxdb,
    water_temperature_raw,
)


class TestWaterTemperatureRawAsset:
    """Unit tests for water_temperature_raw partitioned asset"""

    @pytest.mark.unit
    @pytest.mark.water_temp
    @patch(
        "workflows_dagster.dagster_project.assets.water_temp_assets._scrape_lake_temperature"
    )
    @patch(
        "workflows_dagster.dagster_project.assets.water_temp_assets._get_last_influxdb_timestamp"
    )
    @patch(
        "workflows_dagster.dagster_project.assets.water_temp_assets._write_to_influxdb"
    )
    def test_asset_partition_with_new_data(
        self, mock_write, mock_get_timestamp, mock_scrape
    ):
        """Test asset partition processes new data correctly"""
        # Test with schliersee partition
        context = build_asset_context(partition_key="schliersee")
        mock_get_timestamp.return_value = None  # No existing data

        # Mock scraping to return temperature data
        test_time = datetime(2024, 11, 15, 10, 0, 0, tzinfo=timezone.utc)
        mock_scrape.return_value = {"temperature": 12.5, "timestamp": test_time}

        # Create mock resource
        mock_influxdb = MagicMock()
        mock_influxdb.url = "http://localhost:8086"
        mock_influxdb.bucket_raw = "test_raw"
        mock_influxdb.org = "test-org"

        result = water_temperature_raw(context, mock_influxdb)

        # Should have written data for this partition
        assert result.metadata["lake"] == "Schliersee"
        assert result.metadata["status"] == "written"
        assert result.metadata["temperature_celsius"] == 12.5
        mock_write.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.water_temp
    @patch(
        "workflows_dagster.dagster_project.assets.water_temp_assets._scrape_lake_temperature"
    )
    @patch(
        "workflows_dagster.dagster_project.assets.water_temp_assets._get_last_influxdb_timestamp"
    )
    @patch(
        "workflows_dagster.dagster_project.assets.water_temp_assets._write_to_influxdb"
    )
    def test_asset_partition_with_existing_data(
        self, mock_write, mock_get_timestamp, mock_scrape
    ):
        """Test asset partition handles case with existing data (no write)"""
        context = build_asset_context(partition_key="tegernsee")

        # Mock that data already exists
        test_time = datetime(2024, 11, 15, 10, 0, 0, tzinfo=timezone.utc)
        mock_get_timestamp.return_value = test_time

        # Mock scraping returns same timestamp
        mock_scrape.return_value = {"temperature": 12.5, "timestamp": test_time}

        # Create mock resource
        mock_influxdb = MagicMock()
        mock_influxdb.url = "http://localhost:8086"
        mock_influxdb.bucket_raw = "test_raw"
        mock_influxdb.org = "test-org"

        result = water_temperature_raw(context, mock_influxdb)

        # Should not have written anything
        assert result.metadata["status"] == "up_to_date"
        assert result.metadata["lake"] == "Tegernsee"
        mock_write.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.water_temp
    @patch(
        "workflows_dagster.dagster_project.assets.water_temp_assets._scrape_lake_temperature"
    )
    @patch(
        "workflows_dagster.dagster_project.assets.water_temp_assets._get_last_influxdb_timestamp"
    )
    @patch(
        "workflows_dagster.dagster_project.assets.water_temp_assets._write_to_influxdb"
    )
    def test_asset_partition_with_scraping_failure(
        self, mock_write, mock_get_timestamp, mock_scrape
    ):
        """Test asset partition handles scraping failures gracefully"""
        context = build_asset_context(partition_key="isar")
        mock_get_timestamp.return_value = None

        # Mock scraping failure
        mock_scrape.return_value = None

        # Create mock resource
        mock_influxdb = MagicMock()
        mock_influxdb.url = "http://localhost:8086"
        mock_influxdb.bucket_raw = "test_raw"
        mock_influxdb.org = "test-org"

        result = water_temperature_raw(context, mock_influxdb)

        # Should have error status
        assert result.metadata["status"] == "error"
        assert result.metadata["lake"] == "Isar"
        assert result.metadata["error"] == "scraping_failed"
        mock_write.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.water_temp
    @patch(
        "workflows_dagster.dagster_project.assets.water_temp_assets._scrape_lake_temperature"
    )
    @patch(
        "workflows_dagster.dagster_project.assets.water_temp_assets._get_last_influxdb_timestamp"
    )
    @patch(
        "workflows_dagster.dagster_project.assets.water_temp_assets._write_to_influxdb"
    )
    def test_all_lake_partitions(self, mock_write, mock_get_timestamp, mock_scrape):
        """Test that all lake partitions can be processed"""
        test_time = datetime(2024, 11, 15, 10, 0, 0, tzinfo=timezone.utc)
        mock_get_timestamp.return_value = None
        mock_scrape.return_value = {"temperature": 12.5, "timestamp": test_time}

        mock_influxdb = MagicMock()
        mock_influxdb.url = "http://localhost:8086"
        mock_influxdb.bucket_raw = "test_raw"
        mock_influxdb.org = "test-org"

        # Test each partition
        for lake_id in LAKE_CONFIGS.keys():
            context = build_asset_context(partition_key=lake_id)
            result = water_temperature_raw(context, mock_influxdb)

            assert result.metadata["status"] == "written"
            assert result.metadata["lake"] == LAKE_CONFIGS[lake_id]["lake_name"]


class TestScrapeLakeTemperature:
    """Unit tests for _scrape_lake_temperature helper"""

    @pytest.mark.unit
    @pytest.mark.water_temp
    @patch("workflows_dagster.dagster_project.assets.water_temp_assets.requests.get")
    def test_scrape_success(self, mock_get):
        """Test successful temperature scraping"""
        # Mock HTML response
        html = """
        <table>
            <tbody>
                <tr>
                    <td>15.11.2024 10:00</td>
                    <td>12.5°C</td>
                </tr>
            </tbody>
        </table>
        """
        mock_response = MagicMock()
        mock_response.text = html
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        logger = MagicMock()
        lake_config = LAKE_CONFIGS["schliersee"]

        result = _scrape_lake_temperature(lake_config, logger)

        assert result is not None
        assert result["temperature"] == 12.5
        assert isinstance(result["timestamp"], datetime)
        # Should be in UTC
        assert result["timestamp"].tzinfo == timezone.utc

    @pytest.mark.unit
    @pytest.mark.water_temp
    @patch("workflows_dagster.dagster_project.assets.water_temp_assets.requests.get")
    def test_scrape_http_error(self, mock_get):
        """Test scraping with HTTP error"""
        mock_get.side_effect = Exception("Connection error")

        logger = MagicMock()
        lake_config = LAKE_CONFIGS["schliersee"]

        result = _scrape_lake_temperature(lake_config, logger)

        assert result is None
        logger.error.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.water_temp
    @patch("workflows_dagster.dagster_project.assets.water_temp_assets.requests.get")
    def test_scrape_invalid_html(self, mock_get):
        """Test scraping with invalid HTML structure"""
        # Mock HTML without proper table structure
        html = "<div>No table here</div>"
        mock_response = MagicMock()
        mock_response.text = html
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        logger = MagicMock()
        lake_config = LAKE_CONFIGS["tegernsee"]

        result = _scrape_lake_temperature(lake_config, logger)

        assert result is None
        logger.warning.assert_called()

    @pytest.mark.unit
    @pytest.mark.water_temp
    @patch("workflows_dagster.dagster_project.assets.water_temp_assets.requests.get")
    def test_scrape_invalid_temperature_format(self, mock_get):
        """Test scraping with invalid temperature format"""
        html = """
        <table>
            <tbody>
                <tr>
                    <td>15.11.2024 10:00</td>
                    <td>Not a number</td>
                </tr>
            </tbody>
        </table>
        """
        mock_response = MagicMock()
        mock_response.text = html
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        logger = MagicMock()
        lake_config = LAKE_CONFIGS["isar"]

        result = _scrape_lake_temperature(lake_config, logger)

        assert result is None
        logger.warning.assert_called()


class TestGetLastInfluxDBTimestamp:
    """Unit tests for _get_last_influxdb_timestamp helper"""

    @pytest.mark.unit
    @pytest.mark.water_temp
    def test_get_timestamp_with_data(self):
        """Test getting last timestamp when data exists"""
        # Mock InfluxDB client and query response
        mock_client = MagicMock()
        mock_query_api = MagicMock()
        mock_client.query_api.return_value = mock_query_api
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        # Mock query result with a record
        mock_record = MagicMock()
        test_time = datetime(2024, 11, 15, 12, 0, 0, tzinfo=timezone.utc)
        mock_record.get_time.return_value = test_time

        mock_table = MagicMock()
        mock_table.records = [mock_record]
        mock_query_api.query.return_value = [mock_table]

        # Create mock resource
        mock_influxdb = MagicMock()
        mock_influxdb.get_client.return_value = mock_client
        mock_influxdb.bucket_raw = "test_raw"
        mock_influxdb.org = "test-org"

        logger = MagicMock()

        timestamp = _get_last_influxdb_timestamp(
            mock_influxdb, "temp_schliersee_water", logger
        )

        assert timestamp == test_time

    @pytest.mark.unit
    @pytest.mark.water_temp
    def test_get_timestamp_no_data(self):
        """Test getting last timestamp when no data exists"""
        mock_client = MagicMock()
        mock_query_api = MagicMock()
        mock_client.query_api.return_value = mock_query_api
        mock_query_api.query.return_value = []  # No results
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        # Create mock resource
        mock_influxdb = MagicMock()
        mock_influxdb.get_client.return_value = mock_client
        mock_influxdb.bucket_raw = "test_raw"
        mock_influxdb.org = "test-org"

        logger = MagicMock()

        timestamp = _get_last_influxdb_timestamp(
            mock_influxdb, "temp_tegernsee_water", logger
        )

        assert timestamp is None


class TestWriteToInfluxDB:
    """Unit tests for _write_to_influxdb helper"""

    @pytest.mark.unit
    @pytest.mark.water_temp
    def test_write_to_influxdb(self):
        """Test writing temperature data to InfluxDB"""
        mock_client = MagicMock()
        mock_write_api = MagicMock()
        mock_client.write_api.return_value = mock_write_api
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        # Create mock resource
        mock_influxdb = MagicMock()
        mock_influxdb.get_client.return_value = mock_client
        mock_influxdb.bucket_raw = "test_raw"
        mock_influxdb.org = "test-org"

        lake_config = LAKE_CONFIGS["schliersee"]
        temp_data = {
            "temperature": 12.5,
            "timestamp": datetime(2024, 11, 15, 10, 0, 0, tzinfo=timezone.utc),
        }

        logger = MagicMock()

        _write_to_influxdb(mock_influxdb, lake_config, temp_data, logger)

        # Verify write was called
        mock_write_api.write.assert_called_once()

        # Check that write was called with correct bucket and org
        call_kwargs = mock_write_api.write.call_args.kwargs
        assert call_kwargs["bucket"] == "test_raw"
        assert call_kwargs["org"] == "test-org"

    @pytest.mark.unit
    @pytest.mark.water_temp
    def test_write_creates_correct_point_structure(self):
        """Test that write creates properly formatted InfluxDB point"""
        mock_client = MagicMock()
        mock_write_api = MagicMock()
        mock_client.write_api.return_value = mock_write_api
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        # Create mock resource
        mock_influxdb = MagicMock()
        mock_influxdb.get_client.return_value = mock_client
        mock_influxdb.bucket_raw = "test_raw"
        mock_influxdb.org = "test-org"

        lake_config = LAKE_CONFIGS["tegernsee"]
        temp_data = {
            "temperature": 10.0,
            "timestamp": datetime(2024, 11, 15, 10, 0, 0, tzinfo=timezone.utc),
        }

        logger = MagicMock()

        _write_to_influxdb(mock_influxdb, lake_config, temp_data, logger)

        # Verify write was called with a Point
        call_args = mock_write_api.write.call_args
        point = call_args.kwargs["record"]
        assert point is not None
