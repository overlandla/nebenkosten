"""
Tests for Tibber Sync Flow
"""
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from workflows.tibber_sync_flow import (
    fetch_tibber_data,
    get_last_influxdb_timestamp,
    write_to_influxdb,
    tibber_sync_flow
)


def test_fetch_tibber_data_success(mock_requests_post, tibber_api_response):
    """Test successful Tibber API fetch"""
    result = fetch_tibber_data("test_token", lookback_hours=48)

    assert len(result) == 2
    assert result[0]["consumption"] == 1.5
    assert result[1]["consumption"] == 1.2
    assert "cost" in result[0]


def test_fetch_tibber_data_api_error(mock_requests_post):
    """Test handling of API errors"""
    mock_requests_post.return_value.json.return_value = {
        "errors": [{"message": "Invalid token"}]
    }

    with pytest.raises(ValueError, match="Tibber API error"):
        fetch_tibber_data("invalid_token")


def test_fetch_tibber_data_network_error():
    """Test handling of network errors"""
    with patch('requests.post', side_effect=ConnectionError("Network error")):
        with pytest.raises(ConnectionError):
            fetch_tibber_data("test_token")


def test_get_last_influxdb_timestamp_with_data(mock_influxdb_client):
    """Test getting last timestamp when data exists"""
    result = get_last_influxdb_timestamp(
        "http://test:8086",
        "test_token",
        "test_org",
        "test_bucket",
        "test_meter"
    )

    assert result is not None
    assert isinstance(result, datetime)


def test_get_last_influxdb_timestamp_no_data():
    """Test getting last timestamp when no data exists"""
    with patch('influxdb_client.InfluxDBClient') as mock_client:
        mock_query_api = MagicMock()
        mock_query_api.query.return_value = []
        mock_client.return_value.__enter__.return_value.query_api.return_value = mock_query_api

        result = get_last_influxdb_timestamp(
            "http://test:8086",
            "test_token",
            "test_org",
            "test_bucket",
            "test_meter"
        )

        assert result is None


def test_write_to_influxdb_new_data(mock_influxdb_client, tibber_api_response):
    """Test writing new data points to InfluxDB"""
    data_points = tibber_api_response["data"]["viewer"]["homes"][0]["consumption"]["nodes"]

    result = write_to_influxdb(
        "http://test:8086",
        "test_token",
        "test_org",
        "test_bucket",
        "test_meter",
        data_points,
        last_timestamp=None
    )

    assert result == 2


def test_write_to_influxdb_no_new_data(mock_influxdb_client, tibber_api_response):
    """Test that no data is written when all points are old"""
    data_points = tibber_api_response["data"]["viewer"]["homes"][0]["consumption"]["nodes"]
    last_timestamp = datetime(2023, 12, 1, 2, 0, 0)  # After all test data

    result = write_to_influxdb(
        "http://test:8086",
        "test_token",
        "test_org",
        "test_bucket",
        "test_meter",
        data_points,
        last_timestamp=last_timestamp
    )

    assert result == 0


def test_tibber_sync_flow_success(test_config, mock_requests_post, mock_influxdb_client):
    """Test complete Tibber sync flow"""
    result = tibber_sync_flow(test_config)

    assert isinstance(result, int)
    assert result >= 0


def test_tibber_sync_flow_no_token(test_config):
    """Test flow skips when Tibber token is not configured"""
    config_without_token = test_config.copy()
    config_without_token["tibber_token"] = None

    result = tibber_sync_flow(config_without_token)

    assert result == 0


def test_tibber_sync_flow_empty_response(test_config, mock_requests_post, mock_influxdb_client):
    """Test flow handles empty API response"""
    mock_requests_post.return_value.json.return_value = {
        "data": {
            "viewer": {
                "homes": [{
                    "consumption": {
                        "nodes": []
                    }
                }]
            }
        }
    }

    result = tibber_sync_flow(test_config)

    assert result == 0
