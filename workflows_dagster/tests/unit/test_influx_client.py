"""
Unit tests for InfluxClient
"""
import pytest
import pandas as pd
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock, patch
import sys
from pathlib import Path

# Add src to path
workflows_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(workflows_path))

from src.influx_client import InfluxClient


class TestInfluxClient:
    """Test suite for InfluxClient"""

    @pytest.fixture
    def mock_client(self):
        """Create InfluxClient with mocked dependencies"""
        with patch('src.influx_client.InfluxClient_Official'):
            client = InfluxClient(
                url="http://test:8086",
                token="test_token",
                org="test_org",
                bucket="test_bucket"
            )
            client.query_api = Mock()
            return client

    def test_initialization(self, mock_client):
        """Test InfluxClient initializes correctly"""
        assert mock_client.url == "http://test:8086"
        assert mock_client.token == "test_token"
        assert mock_client.org == "test_org"
        assert mock_client.bucket == "test_bucket"
        assert isinstance(mock_client.meter_data_cache, dict)

    def test_discover_available_meters_success(self, mock_client):
        """Test successful meter discovery"""
        # Mock successful query result
        mock_df = pd.DataFrame({'entity_id': ['gas_zahler', 'haupt_strom', 'haupt_wasser']})
        mock_client.query_api.query_data_frame = Mock(return_value=mock_df)

        meters = mock_client.discover_available_meters()

        assert len(meters) == 3
        assert 'gas_zahler' in meters
        assert 'haupt_strom' in meters
        assert meters == sorted(meters)  # Should be sorted

    def test_discover_available_meters_empty(self, mock_client):
        """Test meter discovery with no results"""
        mock_client.query_api.query_data_frame = Mock(return_value=pd.DataFrame())

        meters = mock_client.discover_available_meters()

        assert meters == []

    def test_discover_available_meters_list_result(self, mock_client):
        """Test meter discovery with list result (InfluxDB behavior)"""
        mock_df1 = pd.DataFrame({'entity_id': ['gas_zahler']})
        mock_df2 = pd.DataFrame({'entity_id': ['haupt_strom']})
        mock_client.query_api.query_data_frame = Mock(return_value=[mock_df1, mock_df2])

        meters = mock_client.discover_available_meters()

        assert len(meters) == 2
        assert 'gas_zahler' in meters
        assert 'haupt_strom' in meters

    def test_discover_available_meters_filters_none(self, mock_client):
        """Test meter discovery filters out None values"""
        mock_df = pd.DataFrame({'entity_id': ['gas_zahler', None, 'haupt_strom', '']})
        mock_client.query_api.query_data_frame = Mock(return_value=mock_df)

        meters = mock_client.discover_available_meters()

        assert len(meters) == 2
        assert None not in meters
        assert '' not in meters

    def test_fetch_all_meter_data_success(self, mock_client):
        """Test successful meter data fetch"""
        # Mock data
        timestamps = pd.date_range('2024-01-01', periods=5, freq='D', tz='UTC')
        mock_df = pd.DataFrame({
            '_time': timestamps,
            '_value': [100.0, 102.5, 105.0, 108.0, 110.5]
        })
        mock_client.query_api.query_data_frame = Mock(return_value=mock_df)

        result = mock_client.fetch_all_meter_data('gas_zahler')

        assert len(result) == 5
        assert 'timestamp' in result.columns
        assert 'value' in result.columns
        assert result['timestamp'].iloc[0] == timestamps[0]
        assert result['value'].iloc[0] == 100.0

    def test_fetch_all_meter_data_caching(self, mock_client):
        """Test that fetched data is cached"""
        mock_df = pd.DataFrame({
            '_time': pd.date_range('2024-01-01', periods=3, tz='UTC'),
            '_value': [100, 101, 102]
        })
        mock_client.query_api.query_data_frame = Mock(return_value=mock_df)

        # First call
        result1 = mock_client.fetch_all_meter_data('gas_zahler')
        
        # Second call should use cache
        result2 = mock_client.fetch_all_meter_data('gas_zahler')

        # Query should only be called once
        assert mock_client.query_api.query_data_frame.call_count == 1
        
        # Results should be equal
        pd.testing.assert_frame_equal(result1, result2)

    def test_fetch_all_meter_data_empty(self, mock_client):
        """Test fetching data for meter with no data"""
        mock_client.query_api.query_data_frame = Mock(return_value=pd.DataFrame())

        result = mock_client.fetch_all_meter_data('nonexistent_meter')

        assert result.empty
        assert list(result.columns) == ['timestamp', 'value']

    def test_fetch_all_meter_data_removes_duplicates(self, mock_client):
        """Test that duplicate timestamps are removed"""
        timestamps = ['2024-01-01', '2024-01-01', '2024-01-02']
        mock_df = pd.DataFrame({
            '_time': pd.to_datetime(timestamps, utc=True),
            '_value': [100.0, 100.5, 102.0]  # Second value should win
        })
        mock_client.query_api.query_data_frame = Mock(return_value=mock_df)

        result = mock_client.fetch_all_meter_data('gas_zahler')

        assert len(result) == 2  # Duplicate removed
        # Should keep last value for duplicate timestamp
        assert result.iloc[0]['value'] == 100.5

    def test_fetch_all_meter_data_with_start_date(self, mock_client):
        """Test fetching data with start date parameter"""
        mock_df = pd.DataFrame({
            '_time': pd.date_range('2024-01-01', periods=3, tz='UTC'),
            '_value': [100, 101, 102]
        })
        mock_client.query_api.query_data_frame = Mock(return_value=mock_df)

        start_date = datetime(2024, 1, 1)
        result = mock_client.fetch_all_meter_data('gas_zahler', start_date=start_date)

        # Verify query was called with date parameter
        assert mock_client.query_api.query_data_frame.called
        assert len(result) == 3


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
