"""
Dagster Jobs for Utility Analysis
"""
from dagster import define_asset_job, AssetSelection

# Tibber sync job - runs hourly
tibber_sync_job = define_asset_job(
    name="tibber_sync",
    description="Fetch and store Tibber electricity consumption data",
    selection=AssetSelection.keys("tibber_consumption_raw"),
    tags={"type": "ingestion", "source": "tibber"}
)

# Analytics job - runs daily
analytics_job = define_asset_job(
    name="analytics_processing",
    description="Process utility meter data - interpolation, master/virtual meters, consumption, anomalies",
    selection=AssetSelection.groups("discovery", "processing", "analysis", "storage"),
    tags={"type": "analytics", "frequency": "daily"}
)

__all__ = ["tibber_sync_job", "analytics_job"]
