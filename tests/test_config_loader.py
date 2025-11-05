"""
Tests for Configuration Loader
"""
import pytest
import os
from workflows.config_loader import ConfigLoader, get_config_loader


def test_config_loader_basic(test_config_files, mock_env_vars):
    """Test basic configuration loading"""
    config_path = test_config_files / "config.yaml"
    loader = ConfigLoader(str(config_path))

    config = loader.get_full_config()

    assert config["influxdb"]["url"] == "http://test-influxdb:8086"
    assert config["influxdb"]["bucket_raw"] == "test_lampfi"
    assert config["influx_token"] == "test_token_123"
    assert config["influx_org"] == "test_org_456"


def test_config_loader_loads_meters(test_config_files, mock_env_vars):
    """Test that meters are loaded correctly"""
    config_path = test_config_files / "config.yaml"
    loader = ConfigLoader(str(config_path))

    assert len(loader.config["meters"]) == 3

    # Check physical meter
    physical = [m for m in loader.config["meters"] if m["type"] == "physical"][0]
    assert physical["meter_id"] == "test_physical_meter"
    assert physical["output_unit"] == "kWh"


def test_config_loader_loads_seasonal_patterns(test_config_files, mock_env_vars):
    """Test that seasonal patterns are loaded"""
    config_path = test_config_files / "config.yaml"
    loader = ConfigLoader(str(config_path))

    patterns = loader.config.get("seasonal_patterns", {})
    assert "test_physical_meter" in patterns
    assert len(patterns["test_physical_meter"]["monthly_percentages"]) == 12


def test_config_loader_validates_secrets(test_config_files):
    """Test that missing secrets are detected"""
    config_path = test_config_files / "config.yaml"

    with pytest.raises(ValueError, match="Missing required secrets"):
        ConfigLoader(str(config_path))


def test_config_loader_missing_file():
    """Test error handling for missing config file"""
    with pytest.raises(FileNotFoundError):
        ConfigLoader("nonexistent.yaml")


def test_get_meters_by_type(test_config_files, mock_env_vars):
    """Test filtering meters by type"""
    config_path = test_config_files / "config.yaml"
    loader = ConfigLoader(str(config_path))

    physical = loader.get_meters_by_type("physical")
    assert len(physical) == 1
    assert physical[0]["meter_id"] == "test_physical_meter"

    master = loader.get_meters_by_type("master")
    assert len(master) == 1
    assert master[0]["meter_id"] == "test_master_meter"

    virtual = loader.get_meters_by_type("virtual")
    assert len(virtual) == 1
    assert virtual[0]["meter_id"] == "test_virtual_meter"


def test_get_meter_config(test_config_files, mock_env_vars):
    """Test getting specific meter configuration"""
    config_path = test_config_files / "config.yaml"
    loader = ConfigLoader(str(config_path))

    meter = loader.get_meter_config("test_physical_meter")
    assert meter is not None
    assert meter["type"] == "physical"

    non_existent = loader.get_meter_config("nonexistent_meter")
    assert non_existent is None


def test_get_seasonal_pattern(test_config_files, mock_env_vars):
    """Test getting seasonal pattern for a meter"""
    config_path = test_config_files / "config.yaml"
    loader = ConfigLoader(str(config_path))

    pattern = loader.get_seasonal_pattern("test_physical_meter")
    assert pattern is not None
    assert len(pattern) == 12
    assert sum(pattern) == 90  # Sum of test pattern

    no_pattern = loader.get_seasonal_pattern("nonexistent_meter")
    assert no_pattern is None


def test_tibber_token_optional(test_config_files, monkeypatch):
    """Test that Tibber token is optional"""
    monkeypatch.setenv("INFLUX_TOKEN", "test_token")
    monkeypatch.setenv("INFLUX_ORG", "test_org")
    # Don't set TIBBER_API_TOKEN

    config_path = test_config_files / "config.yaml"
    loader = ConfigLoader(str(config_path))

    config = loader.get_full_config()
    assert config["tibber_token"] is None
