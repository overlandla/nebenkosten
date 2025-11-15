"""
Unit tests for Dagster resources
"""
import os
import pytest
from unittest.mock import MagicMock, patch
from workflows_dagster.dagster_project.resources.influxdb_resource import InfluxDBResource
from workflows_dagster.dagster_project.resources.tibber_resource import TibberResource
from workflows_dagster.dagster_project.resources.config_resource import ConfigResource


class TestInfluxDBResource:
    """Unit tests for InfluxDBResource"""

    @pytest.mark.unit
    def test_resource_initialization(self, mock_influxdb_resource):
        """Test InfluxDB resource initializes with correct config"""
        assert mock_influxdb_resource.url == "http://localhost:8086"
        assert mock_influxdb_resource.bucket_raw == "test_raw"
        assert mock_influxdb_resource.bucket_processed == "test_processed"
        assert mock_influxdb_resource.timeout == 10000
        assert mock_influxdb_resource.retry_attempts == 2

    @pytest.mark.unit
    def test_get_client_requires_token(self):
        """Test get_client raises error without INFLUX_TOKEN"""
        resource = InfluxDBResource(
            url="http://localhost:8086",
            bucket_raw="test",
            bucket_processed="test"
        )

        # Temporarily remove token
        token = os.environ.pop("INFLUX_TOKEN", None)
        try:
            with pytest.raises(ValueError, match="INFLUX_TOKEN"):
                resource.get_client()
        finally:
            if token:
                os.environ["INFLUX_TOKEN"] = token

    @pytest.mark.unit
    def test_get_client_requires_org(self):
        """Test get_client raises error without INFLUX_ORG"""
        resource = InfluxDBResource(
            url="http://localhost:8086",
            bucket_raw="test",
            bucket_processed="test"
        )

        # Temporarily remove org
        org = os.environ.pop("INFLUX_ORG", None)
        try:
            with pytest.raises(ValueError, match="INFLUX_ORG"):
                resource.get_client()
        finally:
            if org:
                os.environ["INFLUX_ORG"] = org

    @pytest.mark.unit
    @patch('workflows_dagster.dagster_project.resources.influxdb_resource.InfluxDBClient')
    def test_get_client_creates_client(self, mock_client_class, mock_influxdb_resource):
        """Test get_client creates InfluxDBClient with correct params"""
        mock_influxdb_resource.get_client()

        mock_client_class.assert_called_once_with(
            url="http://localhost:8086",
            token="test-token-123",
            org="test-org",
            timeout=10000
        )

    @pytest.mark.unit
    def test_org_property(self, mock_influxdb_resource):
        """Test org property returns environment variable"""
        assert mock_influxdb_resource.org == "test-org"


class TestTibberResource:
    """Unit tests for TibberResource"""

    @pytest.mark.unit
    def test_resource_initialization(self, mock_tibber_resource):
        """Test Tibber resource initializes with correct config"""
        assert mock_tibber_resource.api_url == "https://api.tibber.com/v1-beta/gql"
        assert mock_tibber_resource.timeout == 30

    @pytest.mark.unit
    @pytest.mark.tibber
    @patch('workflows_dagster.dagster_project.resources.tibber_resource.requests.post')
    def test_fetch_consumption_success(self, mock_post, mock_tibber_resource, sample_tibber_response):
        """Test successful Tibber API consumption fetch"""
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "viewer": {
                    "homes": [{
                        "consumption": {
                            "nodes": sample_tibber_response
                        }
                    }]
                }
            }
        }
        mock_post.return_value = mock_response

        result = mock_tibber_resource.fetch_consumption(lookback_hours=48)

        assert len(result) == 48
        assert result[0]["consumption"] == sample_tibber_response[0]["consumption"]
        mock_post.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.tibber
    def test_fetch_consumption_missing_token(self, mock_tibber_resource):
        """Test fetch_consumption raises error without token"""
        # Temporarily remove token
        token = os.environ.pop("TIBBER_API_TOKEN", None)
        try:
            with pytest.raises(ValueError, match="TIBBER_API_TOKEN"):
                mock_tibber_resource.fetch_consumption()
        finally:
            if token:
                os.environ["TIBBER_API_TOKEN"] = token

    @pytest.mark.unit
    @pytest.mark.tibber
    @patch('workflows_dagster.dagster_project.resources.tibber_resource.requests.post')
    def test_fetch_consumption_graphql_error(self, mock_post, mock_tibber_resource):
        """Test fetch_consumption handles GraphQL errors"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "errors": [{"message": "Invalid token"}]
        }
        mock_post.return_value = mock_response

        with pytest.raises(ValueError, match="Tibber API error"):
            mock_tibber_resource.fetch_consumption()

    @pytest.mark.unit
    @pytest.mark.tibber
    @patch('workflows_dagster.dagster_project.resources.tibber_resource.requests.post')
    def test_fetch_consumption_network_error(self, mock_post, mock_tibber_resource):
        """Test fetch_consumption handles network errors"""
        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")

        with pytest.raises(requests.exceptions.ConnectionError):
            mock_tibber_resource.fetch_consumption()


class TestConfigResource:
    """Unit tests for ConfigResource"""

    @pytest.mark.unit
    def test_resource_initialization(self, mock_config_resource):
        """Test Config resource initializes with correct paths"""
        assert mock_config_resource.start_year == 2020
        assert "config.yaml" in mock_config_resource.config_path

    @pytest.mark.unit
    def test_load_config_success(self, mock_config_resource):
        """Test successful config loading"""
        config = mock_config_resource.load_config()

        assert "influxdb" in config
        assert "gas_conversion" in config
        assert "meters" in config
        assert "seasonal_patterns" in config
        assert config["start_year"] == 2020

    @pytest.mark.unit
    def test_get_meters_by_type(self, mock_config_resource):
        """Test filtering meters by type"""
        config = mock_config_resource.load_config()

        physical = mock_config_resource.get_meters_by_type(config, "physical")
        assert len(physical) == 1
        assert physical[0]["meter_id"] == "strom_total"

        master = mock_config_resource.get_meters_by_type(config, "master")
        assert len(master) == 1
        assert master[0]["meter_id"] == "gas_total"

        virtual = mock_config_resource.get_meters_by_type(config, "virtual")
        assert len(virtual) == 1
        assert virtual[0]["meter_id"] == "eg_kalfire"

    @pytest.mark.unit
    def test_get_meter_config(self, mock_config_resource):
        """Test getting specific meter config"""
        config = mock_config_resource.load_config()

        meter = mock_config_resource.get_meter_config(config, "strom_total")
        assert meter is not None
        assert meter["type"] == "physical"
        assert meter["output_unit"] == "kWh"

        missing = mock_config_resource.get_meter_config(config, "nonexistent")
        assert missing is None

    @pytest.mark.unit
    def test_get_seasonal_pattern(self, mock_config_resource):
        """Test getting seasonal patterns"""
        config = mock_config_resource.load_config()

        pattern = mock_config_resource.get_seasonal_pattern(config, "strom_total")
        assert pattern is not None
        assert len(pattern) == 12  # 12 months
        assert all(isinstance(p, float) for p in pattern)

        missing = mock_config_resource.get_seasonal_pattern(config, "nonexistent")
        assert missing is None

    @pytest.mark.unit
    def test_get_gas_conversion_params(self, mock_config_resource):
        """Test getting gas conversion parameters"""
        config = mock_config_resource.load_config()

        params = mock_config_resource.get_gas_conversion_params(config)
        assert "energy_content" in params
        assert "z_factor" in params
        assert params["energy_content"] == 11.504
        assert params["z_factor"] == 0.8885

    @pytest.mark.unit
    def test_load_config_missing_file(self, tmp_path):
        """Test load_config raises error for missing file"""
        resource = ConfigResource(
            config_path=str(tmp_path / "nonexistent.yaml"),
            meters_config_path=str(tmp_path / "meters.yaml"),
            seasonal_patterns_path=str(tmp_path / "patterns.yaml")
        )

        with pytest.raises(FileNotFoundError):
            resource.load_config()
