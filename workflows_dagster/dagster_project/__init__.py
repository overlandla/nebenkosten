"""
Dagster Project for Utility Analysis
Main repository definition
"""

from dagster import Definitions

# Validate environment before importing anything else
from .utils import validate_environment

validate_environment()

# Import assets
from .assets import (anomaly_detection, consumption_data,
                     interpolated_meter_series, master_meter_series,
                     meter_discovery, raw_meter_data, tibber_consumption_raw,
                     virtual_meter_data, water_temperature_raw,
                     write_processed_data_to_influxdb)
# Import jobs
from .jobs import analytics_job, tibber_sync_job, water_temp_sync_job
# Import resources
from .resources import ConfigResource, InfluxDBResource, TibberResource
# Import schedules
from .schedules import (analytics_schedule, tibber_sync_schedule,
                        water_temp_sync_schedule)
# Import sensors
from .sensors import analytics_failure_sensor, anomaly_alert_sensor

# Define the repository
utility_repository = Definitions(
    assets=[
        # Tibber ingestion
        tibber_consumption_raw,
        # Water temperature ingestion
        water_temperature_raw,
        # Analytics pipeline
        meter_discovery,
        raw_meter_data,
        interpolated_meter_series,
        master_meter_series,
        consumption_data,
        virtual_meter_data,
        anomaly_detection,
        # Storage
        write_processed_data_to_influxdb,
    ],
    jobs=[tibber_sync_job, water_temp_sync_job, analytics_job],
    schedules=[tibber_sync_schedule, water_temp_sync_schedule, analytics_schedule],
    sensors=[analytics_failure_sensor, anomaly_alert_sensor],
    resources={
        "influxdb": InfluxDBResource(
            url="http://192.168.1.75:8086",
            bucket_raw="lampfi",
            bucket_processed="lampfi_processed",
            timeout=30000,
            retry_attempts=3,
        ),
        "tibber": TibberResource(
            api_url="https://api.tibber.com/v1-beta/gql", timeout=30
        ),
        "config": ConfigResource(
            config_path="config/config.yaml",
            meters_config_path="config/meters.yaml",
            seasonal_patterns_path="config/seasonal_patterns.yaml",
            start_year=2020,
        ),
    },
)

__all__ = ["utility_repository"]
