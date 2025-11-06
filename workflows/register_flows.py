"""
Flow Registration Script
Registers Prefect flows and creates schedules
"""
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from prefect import serve
from prefect.deployments import Deployment
from prefect.server.schemas.schedules import CronSchedule
from config_loader import get_config_loader
from logging_config import setup_logging
from tibber_sync_flow import tibber_sync_flow
from analytics_flow import analytics_flow
import logging

logger = logging.getLogger(__name__)


def main():
    """Register and deploy flows with Prefect server"""

    # Load configuration
    config_loader = get_config_loader()
    config = config_loader.get_full_config()

    # Setup logging
    setup_logging(config)

    logger.info("=" * 60)
    logger.info("Registering Prefect Flows")
    logger.info("=" * 60)

    # Get schedules from config
    tibber_schedule = config["workflows"]["tibber_sync"]["schedule"]
    analytics_schedule = config["workflows"]["analytics"]["schedule"]

    logger.info(f"Tibber sync schedule: {tibber_schedule}")
    logger.info(f"Analytics schedule: {analytics_schedule}")

    # Create deployments
    deployments = []

    # Tibber Sync Deployment
    if config.get("tibber_token"):
        tibber_deployment = Deployment.build_from_flow(
            flow=tibber_sync_flow,
            name="tibber-sync-scheduled",
            parameters={"config": config},
            schedule=CronSchedule(cron=tibber_schedule, timezone="UTC"),
            work_pool_name="default-pool",
            tags=["tibber", "data-ingestion", "hourly"]
        )
        deployments.append(tibber_deployment)
        logger.info("✅ Tibber sync deployment configured")
    else:
        logger.warning("⚠️ Tibber token not configured - skipping Tibber sync deployment")

    # Analytics Deployment
    analytics_deployment = Deployment.build_from_flow(
        flow=analytics_flow,
        name="analytics-scheduled",
        parameters={"config": config},
        schedule=CronSchedule(cron=analytics_schedule, timezone="UTC"),
        work_pool_name="default-pool",
        tags=["analytics", "data-processing", "daily"]
    )
    deployments.append(analytics_deployment)
    logger.info("✅ Analytics deployment configured")

    # Apply deployments
    for deployment in deployments:
        deployment.apply()
        logger.info(f"✅ Applied deployment: {deployment.name}")

    logger.info("=" * 60)
    logger.info(f"Successfully registered {len(deployments)} deployments")
    logger.info("Flows are now scheduled and ready to run")
    logger.info("=" * 60)

    # Print summary
    print("\n" + "=" * 60)
    print("DEPLOYMENT SUMMARY")
    print("=" * 60)
    for deployment in deployments:
        print(f"  {deployment.name}")
        print(f"    Flow: {deployment.flow_name}")
        print(f"    Schedule: {deployment.schedule}")
        print(f"    Tags: {deployment.tags}")
        print()
    print("=" * 60)
    print("Access Prefect UI at: http://localhost:4200")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Failed to register flows: {e}", exc_info=True)
        sys.exit(1)
