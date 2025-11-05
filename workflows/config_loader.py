"""
Configuration Loader
Loads configuration from YAML files and environment variables
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Loads and validates configuration from YAML files and environment variables"""

    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self._validate_secrets()

    def _load_config(self) -> Dict[str, Any]:
        """Load main configuration from YAML"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        logger.info(f"Loading configuration from {self.config_path}")
        with self.config_path.open() as f:
            config = yaml.safe_load(f)

        # Load meters configuration
        meters_path = Path(config.get("meters_config", "config/meters.yaml"))
        if meters_path.exists():
            with meters_path.open() as f:
                meters_config = yaml.safe_load(f)
                config["meters"] = meters_config.get("meters", [])
                logger.info(f"Loaded {len(config['meters'])} meter definitions")
        else:
            logger.warning(f"Meters configuration file not found: {meters_path}")
            config["meters"] = []

        # Load seasonal patterns configuration
        patterns_path = Path(config.get("seasonal_patterns_config", "config/seasonal_patterns.yaml"))
        if patterns_path.exists():
            with patterns_path.open() as f:
                patterns_config = yaml.safe_load(f)
                config["seasonal_patterns"] = patterns_config.get("patterns", {})
                logger.info(f"Loaded seasonal patterns for {len(config['seasonal_patterns'])} meters")
        else:
            logger.warning(f"Seasonal patterns file not found: {patterns_path}")
            config["seasonal_patterns"] = {}

        return config

    def _validate_secrets(self):
        """Validate that required secrets are present in environment"""
        required_secrets = ["INFLUX_TOKEN", "INFLUX_ORG"]

        missing_secrets = [s for s in required_secrets if not os.environ.get(s)]

        if missing_secrets:
            raise ValueError(
                f"Missing required secrets: {', '.join(missing_secrets)}. "
                "Please ensure secrets/*.env files are loaded."
            )

        # Tibber token is optional (only needed if Tibber sync is enabled)
        if not os.environ.get("TIBBER_API_TOKEN"):
            logger.warning("TIBBER_API_TOKEN not set - Tibber sync will be disabled")

        logger.info("All required secrets validated successfully")

    def get_full_config(self) -> Dict[str, Any]:
        """Get complete configuration with secrets merged"""
        full_config = dict(self.config)

        # Add secrets from environment
        full_config["influx_token"] = os.environ.get("INFLUX_TOKEN")
        full_config["influx_org"] = os.environ.get("INFLUX_ORG")
        full_config["tibber_token"] = os.environ.get("TIBBER_API_TOKEN")

        return full_config

    def get_meters_by_type(self, meter_type: str) -> list:
        """Get all meters of a specific type (physical, master, virtual)"""
        return [m for m in self.config.get("meters", []) if m.get("type") == meter_type]

    def get_meter_config(self, meter_id: str) -> Dict[str, Any]:
        """Get configuration for a specific meter"""
        for meter in self.config.get("meters", []):
            if meter.get("meter_id") == meter_id:
                return meter
        return None

    def get_seasonal_pattern(self, meter_id: str) -> list:
        """Get seasonal pattern for a meter (monthly percentages)"""
        pattern = self.config.get("seasonal_patterns", {}).get(meter_id)
        if pattern:
            return pattern.get("monthly_percentages", [])
        return None


# Singleton instance
_config_loader_instance = None


def get_config_loader(config_path: str = "config/config.yaml") -> ConfigLoader:
    """Get or create the singleton ConfigLoader instance"""
    global _config_loader_instance
    if _config_loader_instance is None:
        _config_loader_instance = ConfigLoader(config_path)
    return _config_loader_instance
