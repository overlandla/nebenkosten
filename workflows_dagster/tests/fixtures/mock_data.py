"""
Mock data generators for testing
"""

from datetime import datetime, timedelta
from typing import Dict, List

import pandas as pd


def generate_meter_readings(
    start_date: str = "2024-01-01",
    days: int = 31,
    initial_value: float = 100.0,
    daily_increment: float = 10.5,
) -> pd.DataFrame:
    """
    Generate mock meter reading data

    Args:
        start_date: Start date (YYYY-MM-DD)
        days: Number of days to generate
        initial_value: Starting meter value
        daily_increment: Daily consumption amount

    Returns:
        DataFrame with meter readings
    """
    dates = pd.date_range(start=start_date, periods=days, freq="D")
    values = [initial_value + (i * daily_increment) for i in range(days)]

    return pd.DataFrame({"value": values}, index=dates)


def generate_consumption_data(
    start_date: str = "2024-01-01",
    days: int = 31,
    base_consumption: float = 10.5,
    variation: float = 2.0,
) -> pd.DataFrame:
    """
    Generate mock consumption data with variation

    Args:
        start_date: Start date
        days: Number of days
        base_consumption: Base daily consumption
        variation: Random variation range

    Returns:
        DataFrame with consumption values
    """
    import random

    random.seed(42)  # Reproducible

    dates = pd.date_range(start=start_date, periods=days, freq="D")
    values = [
        base_consumption + random.uniform(-variation, variation) for _ in range(days)
    ]

    return pd.DataFrame({"value": values}, index=dates)


def generate_tibber_api_response(hours: int = 48) -> List[Dict]:
    """
    Generate mock Tibber API response

    Args:
        hours: Number of hours of data

    Returns:
        List of consumption data points
    """
    now = datetime.now()
    return [
        {
            "from": (now - timedelta(hours=i)).isoformat() + "Z",
            "to": (now - timedelta(hours=i - 1)).isoformat() + "Z",
            "consumption": round(1.0 + (i % 10) * 0.1, 2),
            "cost": round(0.20 + (i % 10) * 0.02, 3),
            "unitPrice": 0.21,
            "unitPriceVAT": 0.04,
        }
        for i in range(hours, 0, -1)
    ]


def generate_multi_meter_data(
    meter_ids: List[str], start_date: str = "2024-01-01", days: int = 31
) -> Dict[str, pd.DataFrame]:
    """
    Generate mock data for multiple meters

    Args:
        meter_ids: List of meter identifiers
        start_date: Start date
        days: Number of days

    Returns:
        Dictionary mapping meter_id to DataFrame
    """
    data = {}
    for i, meter_id in enumerate(meter_ids):
        data[meter_id] = generate_meter_readings(
            start_date=start_date,
            days=days,
            initial_value=100.0 + (i * 50),
            daily_increment=5.0 + (i * 2),
        )
    return data


def generate_anomaly_data(
    start_date: str = "2024-01-01", days: int = 31, anomaly_days: List[int] = None
) -> pd.DataFrame:
    """
    Generate consumption data with anomalies

    Args:
        start_date: Start date
        days: Number of days
        anomaly_days: List of day indices (0-based) to make anomalous

    Returns:
        DataFrame with consumption including anomalies
    """
    if anomaly_days is None:
        anomaly_days = [10, 20]

    dates = pd.date_range(start=start_date, periods=days, freq="D")
    values = []

    for i in range(days):
        if i in anomaly_days:
            values.append(50.0)  # Anomalously high
        else:
            values.append(10.0)  # Normal

    return pd.DataFrame({"value": values}, index=dates)


def generate_master_meter_config() -> Dict:
    """
    Generate mock master meter configuration

    Returns:
        Master meter configuration dictionary
    """
    return {
        "meter_id": "gas_total",
        "type": "master",
        "output_unit": "m³",
        "description": "Total gas across meter replacements",
        "periods": [
            {
                "start_date": "2020-01-01",
                "end_date": "2023-12-31",
                "composition_type": "single",
                "source_meters": ["gas_meter_old"],
                "source_unit": "m³",
            },
            {
                "start_date": "2024-01-01",
                "end_date": "9999-12-31",
                "composition_type": "single",
                "source_meters": ["gas_meter_new"],
                "source_unit": "m³",
                "apply_offset_from_previous_period": True,
            },
        ],
    }


def generate_virtual_meter_config() -> Dict:
    """
    Generate mock virtual meter configuration

    Returns:
        Virtual meter configuration dictionary
    """
    return {
        "meter_id": "eg_kalfire",
        "type": "virtual",
        "output_unit": "m³",
        "description": "Fireplace gas consumption",
        "calculation_type": "subtraction",
        "base_meter": "gas_total",
        "subtract_meters": ["gastherme_gesamt"],
        "subtract_meter_conversions": {
            "gastherme_gesamt": {"from_unit": "kWh", "to_unit": "m³"}
        },
    }
