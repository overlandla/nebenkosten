"""
Tibber API Resource for Dagster
Provides access to Tibber electricity consumption data
"""
import os
from typing import List, Dict
import requests
from dagster import ConfigurableResource, get_dagster_logger
from pydantic import Field


class TibberResource(ConfigurableResource):
    """
    Resource for Tibber API access

    Fetches electricity consumption data from Tibber's GraphQL API
    """

    api_url: str = Field(
        default="https://api.tibber.com/v1-beta/gql",
        description="Tibber GraphQL API URL"
    )

    timeout: int = Field(
        default=30,
        description="Request timeout in seconds"
    )

    def fetch_consumption(self, lookback_hours: int = 48) -> List[Dict]:
        """
        Fetch consumption data from Tibber API

        Args:
            lookback_hours: Number of hours to fetch (max 744 = 31 days)

        Returns:
            List of consumption data points with fields:
            - from: Start timestamp (ISO format)
            - to: End timestamp (ISO format)
            - consumption: Consumption in kWh
            - cost: Cost in currency
            - unitPrice: Price per kWh
            - unitPriceVAT: VAT included price
        """
        logger = get_dagster_logger()
        api_token = os.environ.get("TIBBER_API_TOKEN")

        if not api_token:
            raise ValueError("TIBBER_API_TOKEN environment variable not set")

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
                self.api_url,
                json={"query": query},
                headers={"Authorization": f"Bearer {api_token}"},
                timeout=self.timeout
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
