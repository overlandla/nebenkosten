"""
Unit tests for Tibber ingestion assets
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
import pandas as pd
from dagster import build_asset_context

from workflows_dagster.dagster_project.assets.tibber_assets import (
    tibber_consumption_raw,
    _get_last_influxdb_timestamp,
    _write_to_influxdb
)


class TestTibberConsumptionRawAsset:
    """Unit tests for tibber_consumption_raw asset"""

    @pytest.mark.unit
    @pytest.mark.tibber
    @patch('workflows_dagster.dagster_project.assets.tibber_assets._get_last_influxdb_timestamp')
    @patch('workflows_dagster.dagster_project.assets.tibber_assets._write_to_influxdb')
    def test_asset_with_new_data(
        self,
        mock_write,
        mock_get_timestamp,
        sample_tibber_response
    ):
        """Test asset processes new data correctly"""
        context = build_asset_context()
        mock_get_timestamp.return_value = None  # No existing data
        mock_write.return_value = len(sample_tibber_response)

        # Create mock resources
        mock_influxdb = MagicMock()
        mock_influxdb.url = "http://localhost:8086"
        mock_influxdb.bucket_raw = "test_raw"
        mock_influxdb.org = "test-org"

        mock_tibber = MagicMock()
        mock_tibber.fetch_consumption.return_value = sample_tibber_response

        mock_config = MagicMock()
        mock_config.load_config.return_value = {
            "tibber": {"meter_id": "haupt_strom", "lookback_hours": 48}
        }

        result = tibber_consumption_raw(
            context,
            mock_influxdb,
            mock_tibber,
            mock_config
        )

        assert result.metadata["records_fetched"] == 48
        assert result.metadata["records_written"] == 48
        mock_write.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.tibber
    @patch('workflows_dagster.dagster_project.assets.tibber_assets._get_last_influxdb_timestamp')
    @patch('workflows_dagster.dagster_project.assets.tibber_assets._write_to_influxdb')
    def test_asset_with_no_new_data(
        self,
        mock_write,
        mock_get_timestamp,
        sample_tibber_response
    ):
        """Test asset handles case with no new data"""
        context = build_asset_context()
        # Set last timestamp to future (all data already exists)
        mock_get_timestamp.return_value = datetime.now(timezone.utc)

        # Create mock resources
        mock_influxdb = MagicMock()
        mock_influxdb.url = "http://localhost:8086"
        mock_influxdb.bucket_raw = "test_raw"
        mock_influxdb.org = "test-org"

        mock_tibber = MagicMock()
        mock_tibber.fetch_consumption.return_value = sample_tibber_response

        mock_config = MagicMock()
        mock_config.load_config.return_value = {
            "tibber": {"meter_id": "haupt_strom", "lookback_hours": 48}
        }

        result = tibber_consumption_raw(
            context,
            mock_influxdb,
            mock_tibber,
            mock_config
        )

        assert result.metadata["records_written"] == 0
        assert result.metadata["status"] == "up_to_date"
        mock_write.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.tibber
    def test_get_last_influxdb_timestamp_with_data(self):
        """Test getting last timestamp when data exists"""
        # Mock InfluxDB client and query response
        mock_client = MagicMock()
        mock_query_api = MagicMock()
        mock_client.query_api.return_value = mock_query_api
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        # Mock query result with a record
        mock_record = MagicMock()
        test_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        mock_record.get_time.return_value = test_time

        mock_table = MagicMock()
        mock_table.records = [mock_record]
        mock_query_api.query.return_value = [mock_table]

        # Create mock resource
        mock_influxdb = MagicMock()
        mock_influxdb.get_client.return_value = mock_client
        mock_influxdb.bucket_raw = "test_raw"
        mock_influxdb.org = "test-org"

        timestamp = _get_last_influxdb_timestamp(mock_influxdb, "haupt_strom")

        assert timestamp == test_time

    @pytest.mark.unit
    @pytest.mark.tibber
    def test_get_last_influxdb_timestamp_no_data(self):
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

        timestamp = _get_last_influxdb_timestamp(mock_influxdb, "haupt_strom")

        assert timestamp is None

    @pytest.mark.unit
    @pytest.mark.tibber
    def test_write_to_influxdb(self, sample_tibber_response):
        """Test writing data to InfluxDB"""
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

        count = _write_to_influxdb(
            mock_influxdb,
            "haupt_strom",
            sample_tibber_response
        )

        assert count == len(sample_tibber_response)
        mock_write_api.write.assert_called_once()

        # Check that write was called with correct bucket and org
        call_kwargs = mock_write_api.write.call_args.kwargs
        assert call_kwargs["bucket"] == "test_raw"
        assert call_kwargs["org"] == "test-org"

    @pytest.mark.unit
    @pytest.mark.tibber
    def test_write_to_influxdb_creates_correct_points(self):
        """Test that write creates properly formatted InfluxDB points"""
        mock_client = MagicMock()
        mock_write_api = MagicMock()
        mock_client.write_api.return_value = mock_write_api
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        test_data = [
            {
                "from": "2024-01-15T10:00:00Z",
                "to": "2024-01-15T11:00:00Z",
                "consumption": 1.5,
                "cost": 0.30,
                "unitPrice": 0.20,
                "unitPriceVAT": 0.04
            }
        ]

        # Create mock resource
        mock_influxdb = MagicMock()
        mock_influxdb.get_client.return_value = mock_client
        mock_influxdb.bucket_raw = "test_raw"
        mock_influxdb.org = "test-org"

        _write_to_influxdb(mock_influxdb, "test_meter", test_data)

        # Verify write was called with points
        call_args = mock_write_api.write.call_args
        points = call_args.kwargs["record"]
        assert len(points) == 1
