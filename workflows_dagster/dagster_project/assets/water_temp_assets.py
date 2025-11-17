"""
Water Temperature Data Ingestion Assets
Fetches water temperature from Bavarian lakes and writes to InfluxDB
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import requests
from bs4 import BeautifulSoup
from dagster import (
    AssetExecutionContext,
    MaterializeResult,
    MetadataValue,
    asset,
)
from influxdb_client import Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from ..resources.influxdb_resource import InfluxDBResource

# Lake configuration
LAKE_CONFIGS = {
    "schliersee": {
        "url": "https://www.nid.bayern.de/wassertemperatur/inn/schliersee-18222008",
        "entity_id": "temp_schliersee_water",
        "friendly_name": "Temp Schliersee Water",
        "lake_name": "Schliersee",
    },
    "tegernsee": {
        "url": "https://www.nid.bayern.de/wassertemperatur/inn/gmund_tegernsee-18201303",
        "entity_id": "temp_tegernsee_water",
        "friendly_name": "Temp Tegernsee Water",
        "lake_name": "Tegernsee",
    },
    "isar": {
        "url": "https://www.nid.bayern.de/wassertemperatur/isar/muenchen-16005701",
        "entity_id": "temp_isar_water",
        "friendly_name": "Temp Isar Munchen",
        "lake_name": "Isar",
    },
}


@asset(
    group_name="ingestion",
    compute_kind="web_scraping",
    description="Fetch and store water temperature data from Bavarian lakes",
)
def water_temperature_raw(
    context: AssetExecutionContext, influxdb: InfluxDBResource
) -> MaterializeResult:
    """
    Fetch water temperature data from all Bavarian lakes and write to InfluxDB

    Process:
    1. Iterates through all configured lakes
    2. Scrapes water temperature data from nid.bayern.de for each lake
    3. Parses temperature values and timestamps
    4. Checks for duplicates by comparing with last timestamp in InfluxDB
    5. Writes new data points to InfluxDB

    Returns:
        MaterializeResult with metadata about the operation for all lakes
    """
    logger = context.log
    results = {}

    for lake_id, lake_config in LAKE_CONFIGS.items():
        logger.info(f"Processing water temperature for {lake_config['lake_name']}")

        try:
            # Check last timestamp in InfluxDB
            last_timestamp = _get_last_influxdb_timestamp(
                influxdb, lake_config["entity_id"], logger
            )

            if last_timestamp:
                logger.info(f"Last timestamp in InfluxDB: {last_timestamp}")
            else:
                logger.info("No existing data in InfluxDB")

            # Scrape current temperature
            temp_data = _scrape_lake_temperature(lake_config, logger)

            if not temp_data:
                logger.error(
                    f"Failed to scrape temperature data for {lake_config['lake_name']}"
                )
                results[lake_id] = {
                    "status": "error",
                    "error": "scraping_failed",
                }
                continue

            # Check if this is new data
            if last_timestamp and temp_data["timestamp"] <= last_timestamp:
                logger.info(
                    f"Data already exists (scraped: {temp_data['timestamp']}, "
                    f"last: {last_timestamp})"
                )
                results[lake_id] = {
                    "status": "up_to_date",
                    "temperature_celsius": temp_data["temperature"],
                    "timestamp": temp_data["timestamp"].isoformat(),
                }
                continue

            # Write new data to InfluxDB
            _write_to_influxdb(influxdb, lake_config, temp_data, logger)
            logger.info(
                f"Successfully wrote {temp_data['temperature']}°C at {temp_data['timestamp']}"
            )

            results[lake_id] = {
                "status": "written",
                "temperature_celsius": temp_data["temperature"],
                "timestamp": temp_data["timestamp"].isoformat(),
            }

        except Exception as e:
            logger.error(f"Error processing {lake_config['lake_name']}: {str(e)}")
            results[lake_id] = {
                "status": "error",
                "error": str(e),
            }

    # Create summary metadata
    total_lakes = len(LAKE_CONFIGS)
    written = sum(1 for r in results.values() if r["status"] == "written")
    up_to_date = sum(1 for r in results.values() if r["status"] == "up_to_date")
    errors = sum(1 for r in results.values() if r["status"] == "error")

    return MaterializeResult(
        metadata={
            "total_lakes": total_lakes,
            "written": written,
            "up_to_date": up_to_date,
            "errors": errors,
            "details": MetadataValue.json(results),
        }
    )


def _scrape_lake_temperature(lake_config: Dict, logger) -> Optional[Dict]:
    """
    Scrape temperature data for a specific lake

    Args:
        lake_config: Lake configuration dictionary
        logger: Dagster logger

    Returns:
        Dictionary with 'temperature' and 'timestamp' or None if scraping fails
    """
    lake_name = lake_config["lake_name"]
    url = lake_config["url"]

    try:
        # Send GET request
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.text, "html.parser")

        # Find table with temperature data
        tables = soup.find_all("table")
        target_table = None

        for table in tables:
            tbody = table.find("tbody")
            if tbody and tbody.find("tr"):
                target_table = table
                break

        if not target_table:
            logger.warning(f"{lake_name}: No suitable table found")
            return None

        # Get first row (most recent entry)
        first_row = target_table.find("tbody").find("tr")
        if not first_row:
            logger.warning(f"{lake_name}: No data rows found")
            return None

        cells = first_row.find_all("td")
        if len(cells) < 2:
            logger.warning(f"{lake_name}: Insufficient columns in table")
            return None

        # Extract timestamp and temperature
        timestamp_str = cells[0].text.strip()
        temperature_str = cells[1].text.strip()

        # Parse temperature (format: "15.2°C" or "15.2 °C")
        temp_match = re.search(r"(\d+(?:\.\d+)?)", temperature_str)
        if not temp_match:
            logger.warning(
                f"{lake_name}: Could not extract numeric temperature from '{temperature_str}'"
            )
            return None

        temperature_value = float(temp_match.group(1))

        # Parse timestamp (format: DD.MM.YYYY HH:MM)
        try:
            # Parse as naive datetime
            naive_timestamp = datetime.strptime(timestamp_str, "%d.%m.%Y %H:%M")

            # Source data is in CEST (UTC+2)
            cest_offset = timedelta(hours=2)
            cest_timezone = timezone(cest_offset)

            # Make timezone-aware and convert to UTC
            timestamp_cest = naive_timestamp.replace(tzinfo=cest_timezone)
            timestamp_utc = timestamp_cest.astimezone(timezone.utc)

            return {"temperature": temperature_value, "timestamp": timestamp_utc}

        except ValueError as e:
            logger.warning(
                f"{lake_name}: Error parsing timestamp '{timestamp_str}': {e}"
            )
            return None

    except requests.exceptions.RequestException as e:
        logger.warning(f"{lake_name}: HTTP request failed - {e}")
        return None
    except Exception as e:
        logger.error(f"{lake_name}: Unexpected error during scraping - {e}")
        return None


def _get_last_influxdb_timestamp(
    influxdb: InfluxDBResource, entity_id: str, logger
) -> Optional[datetime]:
    """
    Get the most recent timestamp from InfluxDB for a specific water temp sensor

    Args:
        influxdb: InfluxDB resource
        entity_id: Entity ID for the lake temperature sensor
        logger: Dagster logger

    Returns:
        Most recent timestamp or None if no data exists
    """
    with influxdb.get_client() as client:
        query_api = client.query_api()

        query = f"""
        from(bucket: "{influxdb.bucket_raw}")
          |> range(start: -30d)
          |> filter(fn: (r) => r["entity_id"] == "{entity_id}")
          |> filter(fn: (r) => r["_field"] == "value")
          |> filter(fn: (r) => r["_measurement"] == "°C")
          |> last()
        """

        try:
            tables = query_api.query(query, org=influxdb.org)

            if tables and len(tables) > 0:
                for record in tables[0].records:
                    return record.get_time()

            return None
        except Exception as e:
            logger.debug(f"Query failed (likely no data): {e}")
            return None


def _write_to_influxdb(
    influxdb: InfluxDBResource, lake_config: Dict, temp_data: Dict, logger
) -> None:
    """
    Write temperature data point to InfluxDB

    Args:
        influxdb: InfluxDB resource
        lake_config: Lake configuration
        temp_data: Temperature data with 'temperature' and 'timestamp'
        logger: Dagster logger
    """
    with influxdb.get_client() as client:
        write_api = client.write_api(write_options=SYNCHRONOUS)

        # Create InfluxDB point with Home Assistant compatible tags
        point = (
            Point("°C")
            .tag("domain", "sensor")
            .tag("entity_id", lake_config["entity_id"])
            .tag("friendly_name", lake_config["friendly_name"])
            .tag("lake", lake_config["lake_name"])
            .tag("source", "bayern_nid")
            .tag("unit_of_measurement", "°C")
            .tag("device_class", "temperature")
            .tag("state_class", "measurement")
            .field("value", float(temp_data["temperature"]))
            .time(temp_data["timestamp"], WritePrecision.NS)
        )

        # Write to InfluxDB
        write_api.write(bucket=influxdb.bucket_raw, org=influxdb.org, record=point)

        logger.debug(
            f"Wrote point: {lake_config['lake_name']} = "
            f"{temp_data['temperature']}°C at {temp_data['timestamp']}"
        )
