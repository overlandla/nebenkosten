"""
Configuration Resource for Dagster
Provides access to meter configurations and settings
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dagster import ConfigurableResource, get_dagster_logger
from pydantic import Field


class ConfigResource(ConfigurableResource):
    """
    Resource for loading and accessing configuration

    Loads meter definitions, seasonal patterns, and workflow settings
    from YAML configuration files
    """

    config_path: str = Field(
        default="config/config.yaml", description="Path to main configuration file"
    )

    meters_config_path: str = Field(
        default="config/meters.yaml", description="Path to meters configuration file"
    )

    seasonal_patterns_path: str = Field(
        default="config/seasonal_patterns.yaml",
        description="Path to seasonal patterns configuration file",
    )

    start_year: int = Field(
        default=2020, description="Starting year for historical data processing"
    )

    def load_config(self) -> Dict[str, Any]:
        """
        Load complete configuration from files

        Returns:
            Dictionary containing all configuration data
        """
        logger = get_dagster_logger()
        config_file = Path(self.config_path)

        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")

        logger.info(f"Loading configuration from {config_file}")
        with config_file.open() as f:
            config = yaml.safe_load(f)

        # Load meters configuration
        meters_file = Path(self.meters_config_path)
        if meters_file.exists():
            with meters_file.open() as f:
                meters_config = yaml.safe_load(f)
                config["meters"] = meters_config.get("meters", [])
                logger.info(f"Loaded {len(config['meters'])} meter definitions")
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
