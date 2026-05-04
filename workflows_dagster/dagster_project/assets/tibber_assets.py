"""
Tibber Data Ingestion Assets
Fetches electricity consumption from Tibber API and writes to InfluxDB
"""

from datetime import datetime, timezone
from math import ceil
from typing import Dict, List, Optional

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
    configured_lookback_hours = tibber_config.get("lookback_hours", 48)
    max_lookback_hours = tibber_config.get("max_lookback_hours", 720)

    logger.info(f"Starting Tibber sync for meter: {meter_id}")

    # Get last timestamps from InfluxDB for both Tibber-derived schemas:
    # - energy: hourly consumption/cost used by dashboard cost views
    # - kWh/value: cumulative Home Assistant-style meter used by analytics
    last_energy_timestamp = _get_last_influxdb_timestamp(influxdb, meter_id)
    if last_energy_timestamp:
        logger.info(f"Last energy timestamp in InfluxDB: {last_energy_timestamp}")
    else:
        logger.info("No existing energy data in InfluxDB")

    cumulative_reading = _get_last_cumulative_meter_reading(influxdb, meter_id)
    if cumulative_reading:
        logger.info(
            "Last cumulative meter reading in InfluxDB: "
            f"{cumulative_reading['timestamp']} = {cumulative_reading['value']} kWh"
        )
    else:
        logger.warning(
            "No cumulative kWh meter reading found. The energy schema can still be "
            "written, but cumulative kWh/value writes will be skipped unless a "
            "fallback start value is configured."
        )

    lookback_hours = _determine_lookback_hours(
        configured_lookback_hours,
        max_lookback_hours,
        last_energy_timestamp,
        cumulative_reading,
    )
    logger.info(f"Using Tibber lookback window: {lookback_hours} hours")

    # Fetch data from Tibber
    try:
        consumption_data = tibber.fetch_consumption(lookback_hours=lookback_hours)
        logger.info(f"Fetched {len(consumption_data)} points from Tibber")
    except Exception as e:
        logger.error(f"Failed to fetch data from Tibber: {str(e)}")
        raise

    normalized_data = _normalize_consumption_points(consumption_data, logger)

    energy_data = _filter_points_after_timestamp(normalized_data, last_energy_timestamp)
    cumulative_data = _build_cumulative_meter_points(
        normalized_data, cumulative_reading, logger
    )

    logger.info(f"Found {len(energy_data)} new energy data points to write")
    logger.info(f"Found {len(cumulative_data)} new cumulative kWh points to write")

    energy_points_written = 0
    cumulative_points_written = 0

    if energy_data:
        energy_points_written = _write_to_influxdb(influxdb, meter_id, energy_data)
        logger.info(f"Successfully wrote {energy_points_written} energy points")

    if cumulative_data:
        cumulative_points_written = _write_cumulative_meter_readings(
            influxdb, meter_id, cumulative_data
        )
        logger.info(
            f"Successfully wrote {cumulative_points_written} cumulative kWh points"
        )

    if energy_data or cumulative_data:
        latest_written = (
            cumulative_data[-1]["timestamp"].isoformat()
            if cumulative_data
            else energy_data[-1]["to"]
        )

        return MaterializeResult(
            metadata={
                "records_fetched": len(consumption_data),
                "records_written": energy_points_written,
                "energy_records_written": energy_points_written,
                "cumulative_records_written": cumulative_points_written,
                "meter_id": meter_id,
                "last_timestamp": MetadataValue.text(latest_written),
            }
        )
    else:
        logger.info("No new data to write")
        return MaterializeResult(
            metadata={
                "records_fetched": len(consumption_data),
                "records_written": 0,
                "energy_records_written": 0,
                "cumulative_records_written": 0,
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
          |> range(start: -365d)
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


def _get_last_cumulative_meter_reading(
    influxdb: InfluxDBResource, meter_id: str
) -> Optional[Dict[str, object]]:
    """
    Get the latest cumulative kWh reading for a Tibber-backed physical meter.

    This is the Home Assistant-style input_number schema consumed by the analytics
    pipeline. It is separate from the hourly Tibber `energy` measurement.
    """
    with influxdb.get_client() as client:
        query_api = client.query_api()

        query = f"""
        from(bucket: "{influxdb.bucket_raw}")
          |> range(start: -30d)
          |> filter(fn: (r) => r["_measurement"] == "kWh")
          |> filter(fn: (r) => r["entity_id"] == "{meter_id}")
          |> filter(fn: (r) => r["domain"] == "input_number")
          |> filter(fn: (r) => r["_field"] == "value")
          |> last()
        """

        try:
            tables = query_api.query(query, org=influxdb.org)

            if tables and len(tables) > 0:
                for record in tables[0].records:
                    return {
                        "timestamp": _ensure_utc(record.get_time()),
                        "value": float(record.get_value()),
                    }

            return None
        except Exception:
            return None


def _ensure_utc(timestamp: datetime) -> datetime:
    """Return a timezone-aware UTC datetime."""
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def _parse_tibber_timestamp(timestamp: str) -> datetime:
    """Parse a Tibber timestamp and normalize it to UTC."""
    return _ensure_utc(datetime.fromisoformat(timestamp.replace("Z", "+00:00")))


def _normalize_consumption_points(consumption_data: List[Dict], logger) -> List[Dict]:
    """Parse and sort Tibber points, skipping malformed rows."""
    normalized = []

    for point in consumption_data:
        try:
            point_time = _parse_tibber_timestamp(point["from"])
            normalized_point = dict(point)
            normalized_point["_timestamp"] = point_time
            normalized.append(normalized_point)
        except Exception as e:
            logger.warning(f"Skipping invalid Tibber data point: {str(e)}")

    normalized.sort(key=lambda item: item["_timestamp"])
    return normalized


def _filter_points_after_timestamp(
    points: List[Dict], last_timestamp: Optional[datetime]
) -> List[Dict]:
    """Return points whose Tibber start timestamp is newer than last_timestamp."""
    if last_timestamp is None:
        return points

    last_timestamp = _ensure_utc(last_timestamp)
    return [point for point in points if point["_timestamp"] > last_timestamp]


def _determine_lookback_hours(
    configured_lookback_hours: int,
    max_lookback_hours: int,
    last_energy_timestamp: Optional[datetime],
    cumulative_reading: Optional[Dict[str, object]],
) -> int:
    """
    Pick a Tibber fetch window large enough to recover from scheduler downtime.

    Normal operation uses the configured window. If either target schema has not
    advanced beyond that window, fetch enough extra history to catch up, capped
    by max_lookback_hours.
    """
    candidate_timestamps = []
    if last_energy_timestamp:
        candidate_timestamps.append(_ensure_utc(last_energy_timestamp))
    if cumulative_reading:
        candidate_timestamps.append(_ensure_utc(cumulative_reading["timestamp"]))

    if not candidate_timestamps:
        return configured_lookback_hours

    oldest_target_timestamp = min(candidate_timestamps)
    hours_since_oldest = (
        datetime.now(timezone.utc) - oldest_target_timestamp
    ).total_seconds() / 3600

    if hours_since_oldest <= configured_lookback_hours:
        return configured_lookback_hours

    catchup_hours = ceil(hours_since_oldest) + 48
    return min(max(catchup_hours, configured_lookback_hours), max_lookback_hours)


def _build_cumulative_meter_points(
    points: List[Dict], last_reading: Optional[Dict[str, object]], logger
) -> List[Dict]:
    """
    Convert hourly Tibber consumption into cumulative kWh meter readings.

    The cumulative series is append-only and anchored from the latest existing
    kWh/value reading. If no anchor exists, this deliberately returns no rows.
    """
    if not last_reading:
        return []

    last_timestamp = _ensure_utc(last_reading["timestamp"])
    cumulative_value = float(last_reading["value"])

    new_points = _filter_points_after_timestamp(points, last_timestamp)
    cumulative_points = []

    for point in new_points:
        consumption = point.get("consumption")
        if consumption is None:
            logger.warning(
                f"Skipping cumulative write for {point.get('from')}: no consumption"
            )
            continue

        hourly_consumption = float(consumption)
        cumulative_value += hourly_consumption

        cumulative_points.append(
            {
                "timestamp": point["_timestamp"],
                "value": cumulative_value,
                "hourly_consumption": hourly_consumption,
                "cost": float(point["cost"]) if point.get("cost") is not None else None,
                "unit_price": (
                    float(point["unitPrice"])
                    if point.get("unitPrice") is not None
                    else None
                ),
            }
        )

    return cumulative_points


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
            timestamp = data_point.get("_timestamp") or _parse_tibber_timestamp(
                data_point["from"]
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


def _write_cumulative_meter_readings(
    influxdb: InfluxDBResource, meter_id: str, meter_readings: List[Dict]
) -> int:
    """
    Write Home Assistant-style cumulative kWh meter readings.

    This preserves the legacy schema used by analytics meter discovery while
    moving ownership from cron to Dagster.
    """
    if not meter_readings:
        return 0

    with influxdb.get_client() as client:
        write_api = client.write_api(write_options=SYNCHRONOUS)

        points = []
        for reading in meter_readings:
            point = (
                Point("kWh")
                .tag("entity_id", meter_id)
                .tag("domain", "input_number")
                .tag("unit_of_measurement", "kWh")
                .tag("device_class", "energy")
                .tag("state_class", "total_increasing")
                .field("value", float(reading["value"]))
                .field("hourly_consumption", float(reading["hourly_consumption"]))
                .time(reading["timestamp"], WritePrecision.NS)
            )

            if reading.get("cost") is not None:
                point = point.field("cost", float(reading["cost"]))
            if reading.get("unit_price") is not None:
                point = point.field("unit_price", float(reading["unit_price"]))

            points.append(point)

        write_api.write(bucket=influxdb.bucket_raw, org=influxdb.org, record=points)

        return len(points)
