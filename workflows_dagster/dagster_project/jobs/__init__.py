"""
Dagster Jobs for Utility Analysis
"""

from dagster import AssetSelection, define_asset_job

# Tibber sync job - runs hourly
tibber_sync_job = define_asset_job(
    name="tibber_sync",
    description="Fetch and store Tibber electricity consumption data",
    selection=AssetSelection.keys("tibber_consumption_raw"),
    tags={"type": "ingestion", "source": "tibber"},
)

# Water temperature sync job - runs every 6 hours
water_temp_sync_job = define_asset_job(
    name="water_temp_sync",
    description="Fetch and store water temperature data from Bavarian lakes",
    selection=AssetSelection.keys("water_temperature_raw"),
    tags={"type": "ingestion", "source": "bayern_nid"},
)

# Analytics job - runs daily
analytics_job = define_asset_job(
    name="analytics_processing",
    description="Process utility meter data - interpolation, master/virtual meters, consumption, anomalies",
    selection=AssetSelection.groups("discovery", "processing", "analysis", "storage"),
    tags={"type": "analytics", "frequency": "daily"},
)

__all__ = ["tibber_sync_job", "water_temp_sync_job", "analytics_job"]
