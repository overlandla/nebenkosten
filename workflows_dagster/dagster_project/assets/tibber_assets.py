"""
Tibber Data Ingestion Assets
Fetches electricity consumption from Tibber API and writes to InfluxDB
"""

from datetime import datetime, timezone
from typing import Optional

from dagster import (
    AssetExecutionContext,
    MaterializeResult,
    MetadataValue,
    OpExecutionContext,
    asset,
)
from influxdb_client import Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from ..resources.config_resource import ConfigResource
from ..resources.influxdb_resource import InfluxDBResource
from ..resources.tibber_resource import TibberResource


@asset(
    group_name="ingestion",
    compute_kind="api",
    description="Fetch and store Tibber electricity consumption data",
)
def tibber_consumption_raw(
    context: AssetExecutionContext,
    influxdb: InfluxDBResource,
    tibber: TibberResource,
    config: ConfigResource,
) -> MaterializeResult:
    """
    Fetch consumption data from Tibber API and write to InfluxDB

    This asset:
    1. Checks the last timestamp in InfluxDB to avoid duplicates
    2. Fetches new data from Tibber API (last 48 hours)
    3. Writes only new data points to InfluxDB

    Returns:
        MaterializeResult with metadata about records written
    """
    logger = context.log
    cfg = config.load_config()

    # Get Tibber meter ID from config
    tibber_config = cfg.get("tibber", {})
    meter_id = tibber_config.get("meter_id", "haupt_strom")
    lookback_hours = tibber_config.get("lookback_hours", 48)

    logger.info(f"Starting Tibber sync for meter: {meter_id}")

    # Get last timestamp from InfluxDB
    last_timestamp = _get_last_influxdb_timestamp(influxdb, meter_id)
    if last_timestamp:
        logger.info(f"Last timestamp in InfluxDB: {last_timestamp}")
    else:
        logger.info("No existing data in InfluxDB")

    # Fetch data from Tibber
    try:
        consumption_data = tibber.fetch_consumption(lookback_hours=lookback_hours)
        logger.info(f"Fetched {len(consumption_data)} points from Tibber")
    except Exception as e:
        logger.error(f"Failed to fetch data from Tibber: {str(e)}")
        raise

    # Filter out data that already exists in InfluxDB
    new_data = []
    for point in consumption_data:
        try:
            # Parse timestamp and ensure it's timezone-aware (UTC)
            point_time = datetime.fromisoformat(point["from"].replace("Z", "+00:00"))
            if point_time.tzinfo is None:
                point_time = point_time.replace(tzinfo=timezone.utc)
            else:
                point_time = point_time.astimezone(timezone.utc)

            # Ensure last_timestamp is timezone-aware if it exists
            if last_timestamp and last_timestamp.tzinfo is None:
                last_timestamp = last_timestamp.replace(tzinfo=timezone.utc)
            elif last_timestamp and last_timestamp.tzinfo != timezone.utc:
                last_timestamp = last_timestamp.astimezone(timezone.utc)

            # Compare timestamps
            if last_timestamp is None or point_time > last_timestamp:
                new_data.append(point)

        except Exception as e:
            logger.warning(f"Skipping invalid data point: {str(e)}")
            continue

    logger.info(f"Found {len(new_data)} new data points to write")

    if new_data:
        # Write to InfluxDB
        points_written = _write_to_influxdb(influxdb, meter_id, new_data)
        logger.info(f"Successfully wrote {points_written} points to InfluxDB")

        return MaterializeResult(
            metadata={
                "records_fetched": len(consumption_data),
                "records_written": points_written,
                "meter_id": meter_id,
                "last_timestamp": MetadataValue.text(
                    new_data[-1]["to"] if new_data else "N/A"
                ),
            }
        )
    else:
        logger.info("No new data to write")
        return MaterializeResult(
            metadata={
                "records_fetched": len(consumption_data),
                "records_written": 0,
                "meter_id": meter_id,
                "status": "up_to_date",
            }
        )


def _get_last_influxdb_timestamp(
    influxdb: InfluxDBResource, meter_id: str
) -> Optional[datetime]:
    """
    Get the most recent timestamp from InfluxDB for a specific meter

    Args:
        influxdb: InfluxDB resource
        meter_id: Meter entity ID

    Returns:
        Most recent timestamp or None if no data exists
    """
    with influxdb.get_client() as client:
        query_api = client.query_api()

        query = f"""
        from(bucket: "{influxdb.bucket_raw}")
          |> range(start: -30d)
          |> filter(fn: (r) => r["entity_id"] == "{meter_id}")
          |> filter(fn: (r) => r["_field"] == "consumption")
          |> last()
        """

        try:
            tables = query_api.query(query, org=influxdb.org)

            if tables and len(tables) > 0:
                for record in tables[0].records:
                    return record.get_time()

            return None
        except Exception as e:
            # If query fails (e.g., no data), return None
            return None


def _write_to_influxdb(
    influxdb: InfluxDBResource, meter_id: str, consumption_data: list
) -> int:
    """
    Write consumption data points to InfluxDB

    Args:
        influxdb: InfluxDB resource
        meter_id: Meter entity ID
        consumption_data: List of consumption data points

    Returns:
        Number of points written
    """
    with influxdb.get_client() as client:
        write_api = client.write_api(write_options=SYNCHRONOUS)

        points = []
        for data_point in consumption_data:
            # Parse timestamp
            timestamp = datetime.fromisoformat(
                data_point["from"].replace("Z", "+00:00")
            )

            # Create InfluxDB point
            point = (
                Point("energy")
                .tag("entity_id", meter_id)
                .tag("domain", "sensor")
                .field("consumption", float(data_point.get("consumption") or 0))
                .field("cost", float(data_point.get("cost") or 0))
                .field("unit_price", float(data_point.get("unitPrice") or 0))
                .field("unit_price_vat", float(data_point.get("unitPriceVAT") or 0))
                .time(timestamp, WritePrecision.NS)
            )
            points.append(point)

        # Write all points
        write_api.write(bucket=influxdb.bucket_raw, org=influxdb.org, record=points)

        return len(points)
