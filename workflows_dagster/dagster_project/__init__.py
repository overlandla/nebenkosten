"""
Dagster Project for Utility Analysis
Main repository definition
"""
from dagster import Definitions

# Validate environment before importing anything else
from .utils import validate_environment
validate_environment()

# Import resources
from .resources import InfluxDBResource, TibberResource, ConfigResource

# Import assets
from .assets import (
    tibber_consumption_raw,
    water_temperature_raw,
    meter_discovery,
    fetch_meter_data,
    interpolated_meter_series,
    master_meter_series,
    consumption_data,
    virtual_meter_data,
    anomaly_detection,
    write_processed_data_to_influxdb
)

# Import jobs
from .jobs import tibber_sync_job, water_temp_sync_job, analytics_job

# Import schedules
from .schedules import tibber_sync_schedule, water_temp_sync_schedule, analytics_schedule

# Define the repository
utility_repository = Definitions(
    assets=[
        # Tibber ingestion
        tibber_consumption_raw,
        # Water temperature ingestion
        water_temperature_raw,
        # Analytics pipeline
        meter_discovery,
        fetch_meter_data,
        interpolated_meter_series,
        master_meter_series,
        consumption_data,
        virtual_meter_data,
        anomaly_detection,
        # Storage
        write_processed_data_to_influxdb
    ],
    jobs=[
        tibber_sync_job,
        water_temp_sync_job,
        analytics_job
    ],
    schedules=[
        tibber_sync_schedule,
        water_temp_sync_schedule,
        analytics_schedule
    ],
    resources={
        "influxdb": InfluxDBResource(
            url="http://192.168.1.75:8086",
            bucket_raw="lampfi",
            bucket_processed="lampfi_processed",
            timeout=30000,
            retry_attempts=3
        ),
        "tibber": TibberResource(
            api_url="https://api.tibber.com/v1-beta/gql",
            timeout=30
        ),
        "config": ConfigResource(
            config_path="config/config.yaml",
            meters_config_path="config/meters.yaml",
            seasonal_patterns_path="config/seasonal_patterns.yaml",
            start_year=2020
        )
    }
)

__all__ = ["utility_repository"]
