"""
InfluxDB Client for Dagster Workflows
Fetches and caches meter data from InfluxDB
"""

import logging
from datetime import datetime
from typing import List, Optional

import pandas as pd
from influxdb_client import InfluxDBClient as InfluxClient_Official
from influxdb_client import Point
from influxdb_client.client.write_api import SYNCHRONOUS


class InfluxClient:
    """
    Client for interacting with InfluxDB to fetch and write meter data.

    This class provides methods to:
    - Discover available meters in the database
    - Fetch historical meter readings
    - Cache meter data for performance
    - Write new data points to InfluxDB
    """

    def __init__(self, url: str, token: str, org: str, bucket: str):
        """
        Initialize InfluxDB connection

        Args:
            url: InfluxDB server URL (e.g., 'http://192.168.1.75:8086')
            token: Authentication token
            org: Organization name
            bucket: Bucket name for raw data
        """
        self.url = url
        self.token = token
        self.org = org
        self.bucket = bucket

        # Initialize InfluxDB client
        self.client = InfluxClient_Official(
            url=self.url, token=self.token, org=self.org
        )
        self.query_api = self.client.query_api()

        # Cache for meter data to avoid repeated queries
        self.meter_data_cache = {}

    def discover_available_meters(self) -> List[str]:
        """
        Discover all available physical meters (input_number entities) in the database

        Returns:
            List of meter entity IDs sorted alphabetically

        Example:
            ['gas_zahler', 'haupt_strom', 'haupt_wasser']
        """
        query = f"""
        from(bucket: "{self.bucket}")
        |> range(start: 1970-01-01T00:00:00Z)
        |> filter(fn: (r) => r["domain"] == "input_number")
        |> filter(fn: (r) => r["_field"] == "value")
        |> group(columns: ["entity_id"])
        |> distinct(column: "entity_id")
        |> yield()
        """

        try:
            result = self.query_api.query_data_frame(query)

            # Handle case where result is a list
            if isinstance(result, list):
                if len(result) == 0:
                    return []
                result = pd.concat(result, ignore_index=True)

            if result.empty:
                return []

            # Filter out None values and empty strings
            entity_ids = result["entity_id"].dropna().unique().tolist()
            entity_ids = [eid for eid in entity_ids if eid and str(eid).strip()]

            return sorted(entity_ids)

        except Exception as e:
            logging.error(f"Error discovering meters: {e}")
            return []

    def fetch_all_meter_data(
        self, entity_id: str, start_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Fetch all available data for a specific input_number meter

        Args:
            entity_id: Meter identifier (e.g., 'gas_zahler')
            start_date: Optional start date for data fetch (default: fetch all data from 1970)

        Returns:
            DataFrame with columns ['timestamp', 'value']
            - timestamp: UTC datetime of the reading
            - value: Meter reading value

        Notes:
            - Results are cached in memory to avoid repeated queries
            - Duplicates at the same timestamp are removed (last value kept)
            - Data is sorted by timestamp
        """
        # Check cache first
        cache_key = f"{entity_id}_{start_date.isoformat() if start_date else 'all'}"
        if cache_key in self.meter_data_cache:
            logging.debug(f"Using cached data for {entity_id}")
            return self.meter_data_cache[cache_key]

        start_str = (
            start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
            if start_date
            else "1970-01-01T00:00:00Z"
        )

        query = f"""
        from(bucket: "{self.bucket}")
        |> range(start: {start_str})
        |> filter(fn: (r) => r["entity_id"] == "{entity_id}")
        |> filter(fn: (r) => r["domain"] == "input_number")
        |> filter(fn: (r) => r["_field"] == "value")
        |> sort(columns: ["_time"])
        |> yield()
        """

        try:
            result = self.query_api.query_data_frame(query)

            # Handle case where result is a list
            if isinstance(result, list):
                if len(result) == 0:
                    logging.warning(f"No data found for {entity_id}")
                    return pd.DataFrame(columns=["timestamp", "value"])
                result = pd.concat(result, ignore_index=True)

            if result.empty:
                logging.warning(f"No data found for {entity_id}")
                return pd.DataFrame(columns=["timestamp", "value"])

            # Clean and prepare data
            df = result[["_time", "_value"]].copy()
            df["_time"] = pd.to_datetime(df["_time"], utc=True)
            df = df.sort_values("_time").reset_index(drop=True)
            df.columns = ["timestamp", "value"]

            # Remove duplicates (keep last value for same timestamp)
            df = df.drop_duplicates(subset=["timestamp"], keep="last")

            # Cache the result
            self.meter_data_cache[cache_key] = df

            logging.info(
                f"Fetched {len(df)} data points for {entity_id} "
                f"(range: {df['timestamp'].min()} to {df['timestamp'].max()})"
            )

            return df

        except Exception as e:
            logging.error(f"Error fetching data for {entity_id}: {e}")
            return pd.DataFrame(columns=["timestamp", "value"])

    def write_data_to_influx(
        self,
        entity_id: str,
        value: float,
        timestamp: datetime,
        measurement: str,
        domain: str = "input_number",
        source: str = "dagster",
    ) -> bool:
        """
        Write a single data point to InfluxDB

        Args:
            entity_id: Meter identifier
            value: Meter reading value
            timestamp: Timestamp of the reading
            measurement: InfluxDB measurement name
            domain: Home Assistant domain (default: 'input_number')
            source: Data source identifier (default: 'dagster')

        Returns:
            True if write successful, False otherwise

        Example:
            client.write_data_to_influx(
                entity_id='gas_zahler',
                value=1234.56,
                timestamp=datetime.now(timezone.utc),
                measurement='m³'
            )
        """
        try:
            point = (
                Point(measurement)
                .tag("entity_id", entity_id)
                .tag("domain", domain)
                .tag("source", source)
                .field("value", float(value))
                .time(timestamp)
            )
            write_api = self.client.write_api(write_options=SYNCHRONOUS)
            write_api.write(bucket=self.bucket, org=self.org, record=point)

            logging.debug(
                f"Wrote data to InfluxDB: {entity_id}={value} "
                f"at {timestamp} ({measurement})"
            )
            return True

        except Exception as e:
            logging.error(f"Failed to write data to InfluxDB for {entity_id}: {e}")
            return False

    def close(self):
        """Close the InfluxDB client connection"""
        if hasattr(self, "client"):
            self.client.close()

    def __del__(self):
        """Cleanup: close connection when object is destroyed"""
        self.close()
