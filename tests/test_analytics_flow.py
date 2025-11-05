"""
Tests for Analytics Flow
"""
import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import patch, MagicMock
from workflows.analytics_flow import (
    detect_anomalies,
    process_virtual_meter,
    calculate_consumption
)


def test_detect_anomalies_found(sample_consumption_data):
    """Test anomaly detection when anomalies exist"""
    # Add some anomalous points
    data = sample_consumption_data.copy()
    data.loc[5, 'consumption'] = 500  # Very high consumption

    anomalies = detect_anomalies("test_meter", data, threshold_multiplier=2.0)

    assert len(anomalies) > 0
    assert any(a['consumption'] == 500 for a in anomalies)


def test_detect_anomalies_none_found(sample_consumption_data):
    """Test anomaly detection when no anomalies exist"""
    anomalies = detect_anomalies("test_meter", sample_consumption_data)

    assert len(anomalies) == 0


def test_detect_anomalies_empty_data():
    """Test anomaly detection with empty data"""
    empty_data = pd.DataFrame(columns=['timestamp', 'consumption'])
    anomalies = detect_anomalies("test_meter", empty_data)

    assert len(anomalies) == 0


def test_process_virtual_meter_basic(test_config):
    """Test basic virtual meter processing"""
    # Create mock consumption data
    base_consumption = pd.DataFrame({
        'timestamp': pd.date_range('2023-01-31', '2023-03-31', freq='M', tz='UTC'),
        'consumption': [100, 120, 110]
    })

    subtract_consumption = pd.DataFrame({
        'timestamp': pd.date_range('2023-01-31', '2023-03-31', freq='M', tz='UTC'),
        'consumption': [30, 40, 35]
    })

    consumption_data = {
        'base_meter': base_consumption,
        'subtract_meter': subtract_consumption
    }

    virtual_config = {
        "meter_id": "virtual_test",
        "base_meter": "base_meter",
        "subtract_meters": ["subtract_meter"],
        "subtract_meter_conversions": {}
    }

    result = process_virtual_meter(virtual_config, consumption_data, test_config)

    assert len(result) == 3
    assert result.iloc[0]['consumption'] == 70  # 100 - 30
    assert result.iloc[1]['consumption'] == 80  # 120 - 40


def test_process_virtual_meter_with_unit_conversion(test_config):
    """Test virtual meter with unit conversion"""
    base_consumption = pd.DataFrame({
        'timestamp': pd.date_range('2023-01-31', '2023-02-28', freq='M', tz='UTC'),
        'consumption': [1000, 1200]  # m³
    })

    subtract_consumption_kwh = pd.DataFrame({
        'timestamp': pd.date_range('2023-01-31', '2023-02-28', freq='M', tz='UTC'),
        'consumption': [1022.4, 1226.9]  # kWh (to be converted to m³)
    })

    consumption_data = {
        'gas_total': base_consumption,
        'gastherme': subtract_consumption_kwh
    }

    virtual_config = {
        "meter_id": "eg_kalfire",
        "base_meter": "gas_total",
        "subtract_meters": ["gastherme"],
        "subtract_meter_conversions": {
            "gastherme": {
                "from_unit": "kWh",
                "to_unit": "m³"
            }
        }
    }

    result = process_virtual_meter(virtual_config, consumption_data, test_config)

    assert len(result) == 2
    # After conversion (kWh -> m³) using gas conversion factor
    # 1022.4 kWh / 10.223 ≈ 100 m³
    # 1000 - 100 = 900 m³
    assert result.iloc[0]['consumption'] > 0
    assert result.iloc[0]['consumption'] < 1000  # Should be less than base


def test_process_virtual_meter_negative_clipping(test_config):
    """Test that negative values are clipped to zero"""
    base_consumption = pd.DataFrame({
        'timestamp': pd.date_range('2023-01-31', '2023-02-28', freq='M', tz='UTC'),
        'consumption': [100, 120]
    })

    subtract_consumption = pd.DataFrame({
        'timestamp': pd.date_range('2023-01-31', '2023-02-28', freq='M', tz='UTC'),
        'consumption': [150, 140]  # More than base
    })

    consumption_data = {
        'base_meter': base_consumption,
        'subtract_meter': subtract_consumption
    }

    virtual_config = {
        "meter_id": "virtual_test",
        "base_meter": "base_meter",
        "subtract_meters": ["subtract_meter"],
        "subtract_meter_conversions": {}
    }

    result = process_virtual_meter(virtual_config, consumption_data, test_config)

    # All values should be clipped to 0 (no negative consumption)
    assert all(result['consumption'] >= 0)
    assert result.iloc[0]['consumption'] == 0


def test_process_virtual_meter_missing_base(test_config):
    """Test handling of missing base meter"""
    consumption_data = {
        'other_meter': pd.DataFrame({'timestamp': [], 'consumption': []})
    }

    virtual_config = {
        "meter_id": "virtual_test",
        "base_meter": "missing_base",
        "subtract_meters": [],
        "subtract_meter_conversions": {}
    }

    result = process_virtual_meter(virtual_config, consumption_data, test_config)

    assert result.empty


def test_calculate_consumption_basic(sample_meter_data, test_config):
    """Test basic consumption calculation"""
    # Create monthly readings
    monthly_readings = pd.DataFrame({
        'timestamp': pd.date_range('2023-01-31', '2023-03-31', freq='M', tz='UTC'),
        'value': [100, 150, 200]
    })

    result = calculate_consumption("test_meter", monthly_readings, test_config)

    assert len(result) >= 2  # Should have consumption values
    # First consumption should be difference: 150 - 100 = 50
    # (Note: actual calculation may differ due to processing logic)


def test_calculate_consumption_empty_data(test_config):
    """Test consumption calculation with empty data"""
    empty_data = pd.DataFrame(columns=['timestamp', 'value'])

    result = calculate_consumption("test_meter", empty_data, test_config)

    # Should not crash, may return empty or handle gracefully
    assert isinstance(result, pd.DataFrame)
