"""
Tibber Sync Flow
Fetches electricity consumption data from Tibber API and writes to InfluxDB
"""
from prefect import flow, task, get_run_logger
from prefect.task_runners import SequentialTaskRunner
import requests
from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from typing import List, Dict, Optional
import time


@task(retries=3, retry_delay_seconds=60)
def fetch_tibber_data(api_token: str, lookback_hours: int = 48) -> List[Dict]:
    """
    Fetch consumption data from Tibber GraphQL API

    Args:
        api_token: Tibber API token
        lookback_hours: Number of hours to fetch (max 744 = 31 days)

    Returns:
        List of consumption data points
    """
    logger = get_run_logger()
    logger.info(f"Fetching Tibber data for last {lookback_hours} hours")

    query = """
    {
      viewer {
        homes {
          consumption(resolution: HOURLY, last: %d) {
            nodes {
              from
              to
              consumption
              cost
              unitPrice
              unitPriceVAT
            }
          }
        }
      }
    }
    """ % lookback_hours

    try:
        response = requests.post(
            "https://api.tibber.com/v1-beta/gql",
            json={"query": query},
            headers={"Authorization": f"Bearer {api_token}"},
            timeout=30
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch Tibber data: {e}")
        raise

    data = response.json()

    # Check for GraphQL errors
    if "errors" in data:
        error_msg = data["errors"][0].get("message", "Unknown GraphQL error")
        logger.error(f"Tibber GraphQL error: {error_msg}")
        raise ValueError(f"Tibber API error: {error_msg}")

    consumptions = data["data"]["viewer"]["homes"][0]["consumption"]["nodes"]
    logger.info(f"Fetched {len(consumptions)} data points from Tibber")

    return consumptions


@task(retries=3, retry_delay_seconds=30)
def get_last_influxdb_timestamp(
    influx_url: str,
    influx_token: str,
    influx_org: str,
    bucket: str,
    meter_id: str
) -> Optional[datetime]:
    """
    Get the most recent timestamp from InfluxDB for a specific meter

    Args:
        influx_url: InfluxDB URL
        influx_token: InfluxDB API token
        influx_org: InfluxDB organization
        bucket: InfluxDB bucket name
        meter_id: Meter entity ID

    Returns:
        Most recent timestamp or None if no data exists
    """
    logger = get_run_logger()

    try:
        with InfluxDBClient(url=influx_url, token=influx_token, org=influx_org) as client:
            query_api = client.query_api()

            query = f'''
            from(bucket: "{bucket}")
                |> range(start: -30d)
                |> filter(fn: (r) => r["entity_id"] == "{meter_id}")
                |> filter(fn: (r) => r["_field"] == "value")
                |> last()
            '''

            result = query_api.query(query)

            if result and len(result) > 0 and len(result[0].records) > 0:
                last_time = result[0].records[0].get_time()
                logger.info(f"Last InfluxDB timestamp for {meter_id}: {last_time}")
                return last_time

            logger.info(f"No existing data found in InfluxDB for {meter_id}")
            return None

    except Exception as e:
        logger.error(f"Failed to query InfluxDB: {e}")
        raise


@task(retries=3, retry_delay_seconds=30)
def write_to_influxdb(
    influx_url: str,
    influx_token: str,
    influx_org: str,
    bucket: str,
    meter_id: str,
    data_points: List[Dict],
    last_timestamp: Optional[datetime]
) -> int:
    """
    Write new data points to InfluxDB

    Args:
        influx_url: InfluxDB URL
        influx_token: InfluxDB API token
        influx_org: InfluxDB organization
        bucket: InfluxDB bucket name
        meter_id: Meter entity ID to write to
        data_points: List of Tibber data points
        last_timestamp: Last timestamp in InfluxDB (to avoid duplicates)

    Returns:
        Number of points written
    """
    logger = get_run_logger()

    # Filter for new data only
    new_points = []
    for point in data_points:
        point_time = datetime.fromisoformat(point["from"].replace("Z", "+00:00"))

        if last_timestamp is None or point_time > last_timestamp:
            new_points.append(point)

    if not new_points:
        logger.info("No new data points to write")
        return 0

    logger.info(f"Writing {len(new_points)} new data points to InfluxDB")

    try:
        with InfluxDBClient(url=influx_url, token=influx_token, org=influx_org) as client:
            write_api = client.write_api(write_options=SYNCHRONOUS)

            points = []
            for point in new_points:
                timestamp = datetime.fromisoformat(point["from"].replace("Z", "+00:00"))

                p = (
                    Point("kWh")
                    .tag("entity_id", meter_id)
                    .tag("domain", "input_number")
                    .field("value", float(point["consumption"]))
                    .time(timestamp, WritePrecision.NS)
                )

                # Add optional fields if available
                if point.get("cost") is not None:
                    p.field("cost", float(point["cost"]))
                if point.get("unitPrice") is not None:
                    p.field("unit_price", float(point["unitPrice"]))

                points.append(p)

            write_api.write(bucket=bucket, record=points)
            logger.info(f"Successfully wrote {len(points)} points to bucket '{bucket}'")

    except Exception as e:
        logger.error(f"Failed to write to InfluxDB: {e}")
        raise

    return len(new_points)


@flow(name="Tibber Sync", task_runner=SequentialTaskRunner(), log_prints=True)
def tibber_sync_flow(config: Dict) -> int:
    """
    Main flow for syncing Tibber data to InfluxDB

    Args:
        config: Configuration dictionary with:
            - tibber_token: Tibber API token
            - influx_token: InfluxDB API token
            - influx_org: InfluxDB organization
            - influxdb: Dict with url, bucket_raw
            - tibber: Dict with lookback_hours, meter_id

    Returns:
        Number of data points written
    """
    logger = get_run_logger()
    logger.info("=" * 60)
    logger.info("Starting Tibber Sync Flow")
    logger.info("=" * 60)

    # Validate Tibber token
    if not config.get("tibber_token"):
        logger.warning("Tibber API token not configured - skipping sync")
        return 0

    # Fetch Tibber data
    start_time = time.time()
    tibber_data = fetch_tibber_data(
        api_token=config["tibber_token"],
        lookback_hours=config["tibber"]["lookback_hours"]
    )

    if not tibber_data:
        logger.warning("No data returned from Tibber API")
        return 0

    # Get last InfluxDB timestamp
    last_timestamp = get_last_influxdb_timestamp(
        influx_url=config["influxdb"]["url"],
        influx_token=config["influx_token"],
        influx_org=config["influx_org"],
        bucket=config["influxdb"]["bucket_raw"],
        meter_id=config["tibber"]["meter_id"]
    )

    # Write new data
    points_written = write_to_influxdb(
        influx_url=config["influxdb"]["url"],
        influx_token=config["influx_token"],
        influx_org=config["influx_org"],
        bucket=config["influxdb"]["bucket_raw"],
        meter_id=config["tibber"]["meter_id"],
        data_points=tibber_data,
        last_timestamp=last_timestamp
    )

    elapsed_time = time.time() - start_time
    logger.info("=" * 60)
    logger.info(f"Tibber sync completed in {elapsed_time:.2f}s")
    logger.info(f"Points written: {points_written}")
    logger.info("=" * 60)

    return points_written


if __name__ == "__main__":
    # For local testing
    from config_loader import get_config_loader
    from logging_config import setup_logging
    import os

    # Load configuration
    config_loader = get_config_loader()
    config = config_loader.get_full_config()

    # Setup logging
    setup_logging(config)

    # Run flow
    result = tibber_sync_flow(config)
    print(f"Result: {result} points written")
