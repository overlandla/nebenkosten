"""
Dagster Schedules for Utility Analysis
"""
from dagster import ScheduleDefinition
from ..jobs import tibber_sync_job, analytics_job

# Tibber sync schedule - runs hourly at :05 minutes
tibber_sync_schedule = ScheduleDefinition(
    name="tibber_sync_hourly",
    job=tibber_sync_job,
    cron_schedule="5 * * * *",  # Every hour at :05
    execution_timezone="UTC",
    description="Fetch Tibber consumption data every hour"
)

# Analytics schedule - runs daily at 2:00 AM
analytics_schedule = ScheduleDefinition(
    name="analytics_daily",
    job=analytics_job,
    cron_schedule="0 2 * * *",  # Daily at 2:00 AM
    execution_timezone="UTC",
    description="Process utility meter data daily"
)

__all__ = ["tibber_sync_schedule", "analytics_schedule"]
