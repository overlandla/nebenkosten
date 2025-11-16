"""
InfluxDB Resource for Dagster
Provides InfluxDB client access with configuration
"""

import os
from typing import Optional

from dagster import ConfigurableResource
from influxdb_client import InfluxDBClient
from pydantic import Field


class InfluxDBResource(ConfigurableResource):
    """
    Resource for InfluxDB client connections

    Provides access to InfluxDB for reading and writing time-series data
    """

    url: str = Field(default="http://localhost:8086", description="InfluxDB server URL")

    bucket_raw: str = Field(
        default="lampfi", description="Bucket name for raw meter data"
    )

    bucket_processed: str = Field(
        default="lampfi_processed", description="Bucket name for processed data"
    )

    timeout: int = Field(default=30000, description="Request timeout in milliseconds")

    retry_attempts: int = Field(
        default=3, description="Number of retry attempts for failed requests"
    )

    def get_client(self) -> InfluxDBClient:
        """
        Create and return an InfluxDB client

        Returns:
            Configured InfluxDBClient instance
        """
        token = os.environ.get("INFLUX_TOKEN")
        org = os.environ.get("INFLUX_ORG")

        if not token:
            raise ValueError("INFLUX_TOKEN environment variable not set")
        if not org:
            raise ValueError("INFLUX_ORG environment variable not set")

        return InfluxDBClient(url=self.url, token=token, org=org, timeout=self.timeout)

    @property
    def org(self) -> str:
        """Get InfluxDB organization from environment"""
        org = os.environ.get("INFLUX_ORG")
        if not org:
            raise ValueError("INFLUX_ORG environment variable not set")
        return org
