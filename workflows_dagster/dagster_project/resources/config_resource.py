"""
Configuration Resource for Dagster
Provides access to meter configurations and settings

This resource uses PostgreSQL as the primary source for configuration,
with YAML files as a fallback for backwards compatibility.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dagster import ConfigurableResource, get_dagster_logger
from pydantic import Field

# Import the config database client
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from config_db import ConfigDatabaseClient


class ConfigResource(ConfigurableResource):
    """
    Resource for loading and accessing configuration

    Loads meter definitions, seasonal patterns, and workflow settings
    from PostgreSQL database (primary) or YAML configuration files (fallback)
    """

    config_path: str = Field(
        default="config/config.yaml",
        description="Path to main configuration file (fallback)",
    )

    meters_config_path: str = Field(
        default="config/meters.yaml",
        description="Path to meters configuration file (fallback)",
    )

    seasonal_patterns_path: str = Field(
        default="config/seasonal_patterns.yaml",
        description="Path to seasonal patterns configuration file (fallback)",
    )

    start_year: int = Field(
        default=2020, description="Starting year for historical data processing"
    )

    use_database: bool = Field(
        default=True,
        description="Use PostgreSQL database for configuration (fallback to YAML if false or unavailable)",
    )

    def _load_from_database(self) -> Optional[Dict[str, Any]]:
        """
        Load configuration from PostgreSQL database

        Returns:
            Configuration dictionary or None if database unavailable
        """
        logger = get_dagster_logger()

        try:
            db_client = ConfigDatabaseClient()

            # Check database connection
            if not db_client.check_connection():
                logger.warning(
                    "Config database connection failed, falling back to YAML"
                )
                return None

            logger.info("Loading configuration from PostgreSQL database")

            config = {}

            # Load all settings
            settings = db_client.get_all_settings()
            logger.info(f"Loaded {len(settings)} settings from database")

            # Extract specific settings
            config["gas_conversion"] = settings.get(
                "gas_conversion", {"energy_content": 11.504, "z_factor": 0.8885}
            )

            config["influxdb"] = settings.get("influxdb", {})
            config["tibber"] = settings.get("tibber", {})
            config["workflows"] = settings.get("workflows", {})

            # Load meters from database and convert to YAML-compatible format
            db_meters = db_client.get_meters(active_only=False)
            logger.info(f"Loaded {len(db_meters)} meters from database")

            # Convert database meters to YAML format for compatibility
            config["meters"] = []
            for meter in db_meters:
                meter_config = {
                    "meter_id": meter["id"],
                    "type": meter["category"],  # physical, master, virtual
                    "output_unit": meter["unit"],
                    "description": meter["name"],
                }

                if meter.get("installation_date"):
                    meter_config["installation_date"] = meter[
                        "installation_date"
                    ].strftime("%Y-%m-%d")

                if meter.get("deinstallation_date"):
                    meter_config["deinstallation_date"] = meter[
                        "deinstallation_date"
                    ].strftime("%Y-%m-%d")

                # Add calculation config for master/virtual meters
                if meter.get("calculation_config"):
                    calc_config = meter["calculation_config"]

                    if meter["category"] == "master" and "periods" in calc_config:
                        meter_config["periods"] = calc_config["periods"]

                    elif meter["category"] == "virtual":
                        meter_config["calculation_type"] = calc_config.get(
                            "calculation_type", "subtraction"
                        )
                        meter_config["base_meter"] = calc_config.get("base_meter")
                        meter_config["subtract_meters"] = calc_config.get(
                            "subtract_meters", []
                        )
                        if "conversions" in calc_config:
                            meter_config["subtract_meter_conversions"] = calc_config[
                                "conversions"
                            ]

                config["meters"].append(meter_config)

            # Load seasonal patterns (still from YAML for now)
            patterns_file = Path(self.seasonal_patterns_path)
            if patterns_file.exists():
                with patterns_file.open() as f:
                    patterns_config = yaml.safe_load(f)
                    config["seasonal_patterns"] = patterns_config.get("patterns", {})
                    logger.info(
                        f"Loaded seasonal patterns for {len(config['seasonal_patterns'])} meters"
                    )
            else:
                config["seasonal_patterns"] = {}

            # Load households from database
            households = db_client.get_households()
            config["households"] = households
            logger.info(f"Loaded {len(households)} households from database")

            # Add start year
            config["start_year"] = self.start_year

            return config

        except Exception as e:
            logger.warning(
                f"Failed to load config from database: {e}, falling back to YAML"
            )
            return None

    def _load_from_yaml(self) -> Dict[str, Any]:
        """
        Load configuration from YAML files (fallback)

        Returns:
            Configuration dictionary
        """
        logger = get_dagster_logger()
        logger.info("Loading configuration from YAML files")

        config_file = Path(self.config_path)

        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")

        with config_file.open() as f:
            config = yaml.safe_load(f)

        # Load meters configuration
        meters_file = Path(self.meters_config_path)
        if meters_file.exists():
            with meters_file.open() as f:
                meters_config = yaml.safe_load(f)
                config["meters"] = meters_config.get("meters", [])
                logger.info(
                    f"Loaded {len(config['meters'])} meter definitions from YAML"
                )
        else:
            logger.warning(f"Meters configuration file not found: {meters_file}")
            config["meters"] = []

        # Load seasonal patterns
        patterns_file = Path(self.seasonal_patterns_path)
        if patterns_file.exists():
            with patterns_file.open() as f:
                patterns_config = yaml.safe_load(f)
                config["seasonal_patterns"] = patterns_config.get("patterns", {})
                logger.info(
                    f"Loaded seasonal patterns for {len(config['seasonal_patterns'])} meters"
                )
        else:
            logger.warning(f"Seasonal patterns file not found: {patterns_file}")
            config["seasonal_patterns"] = {}

        # Add start year from resource config
        config["start_year"] = self.start_year

        return config

    def load_config(self) -> Dict[str, Any]:
        """
        Load complete configuration from database or YAML files

        Tries PostgreSQL database first, falls back to YAML if unavailable

        Returns:
            Dictionary containing all configuration data
        """
        logger = get_dagster_logger()

        # Try database first if enabled
        if self.use_database:
            config = self._load_from_database()
            if config is not None:
                return config

        # Fallback to YAML
        return self._load_from_yaml()

    def get_meters_by_type(self, config: Dict[str, Any], meter_type: str) -> List[Dict]:
        """
        Get all meters of a specific type

        Args:
            config: Configuration dictionary from load_config()
            meter_type: Type of meter (physical, master, virtual)

        Returns:
            List of meter configurations
        """
        return [m for m in config.get("meters", []) if m.get("type") == meter_type]

    def get_meter_config(
        self, config: Dict[str, Any], meter_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific meter

        Args:
            config: Configuration dictionary from load_config()
            meter_id: Meter identifier

        Returns:
            Meter configuration dictionary or None if not found
        """
        for meter in config.get("meters", []):
            if meter.get("meter_id") == meter_id:
                return meter
        return None

    def get_seasonal_pattern(
        self, config: Dict[str, Any], meter_id: str
    ) -> Optional[List[float]]:
        """
        Get seasonal pattern for a meter

        Args:
            config: Configuration dictionary from load_config()
            meter_id: Meter identifier

        Returns:
            List of monthly percentages or None if not found
        """
        pattern = config.get("seasonal_patterns", {}).get(meter_id)
        if pattern:
            return pattern.get("monthly_percentages", [])
        return None

    def get_gas_conversion_params(self, config: Dict[str, Any]) -> Dict[str, float]:
        """
        Get gas conversion parameters

        Args:
            config: Configuration dictionary from load_config()

        Returns:
            Dictionary with energy_content and z_factor
        """
        gas_config = config.get("gas_conversion", {})
        return {
            "energy_content": gas_config.get("energy_content", 11.504),
            "z_factor": gas_config.get("z_factor", 0.8885),
        }
