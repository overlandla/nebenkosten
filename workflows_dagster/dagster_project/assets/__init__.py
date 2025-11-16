"""
Dagster Assets for Utility Analysis
"""
from .tibber_assets import tibber_consumption_raw
from .water_temp_assets import water_temperature_raw
from .analytics_assets import (
    meter_discovery,
    raw_meter_data,
    interpolated_meter_series,
    master_meter_series,
    consumption_data,
    virtual_meter_data,
    anomaly_detection
)
from .influxdb_writer_assets import write_processed_data_to_influxdb

__all__ = [
    # Tibber ingestion
    "tibber_consumption_raw",
    # Water temperature ingestion
    "water_temperature_raw",
    # Analytics pipeline
    "meter_discovery",
    "raw_meter_data",
    "interpolated_meter_series",
    "master_meter_series",
    "consumption_data",
    "virtual_meter_data",
    "anomaly_detection",
    # Storage
    "write_processed_data_to_influxdb"
]
