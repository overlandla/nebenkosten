"""
Environment variable validation for Dagster workflows
Validates all required environment variables at startup
"""

import os
from typing import List, Tuple

from dagster import get_dagster_logger


def validate_environment() -> None:
    """
    Validate all required environment variables are set.

    Raises:
        ValueError: If any required environment variables are missing
    """
    # Skip validation in testing mode
    if os.environ.get("TESTING", "").lower() in ("true", "1", "yes"):
        return

    logger = get_dagster_logger()

    # Required environment variables
    required_vars = [
        "INFLUX_TOKEN",
        "INFLUX_ORG",
    ]

    # Optional but recommended variables
    recommended_vars = [
        "TIBBER_API_TOKEN",
    ]

    # Check required variables
    missing_required = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_required.append(var)

    if missing_required:
        error_msg = (
            f"Missing required environment variables: {', '.join(missing_required)}\n"
            f"Please set these variables before starting Dagster."
        )
        logger.error(error_msg)
        raise ValueError(error_msg)

    # Check recommended variables
    missing_recommended = []
    for var in recommended_vars:
        if not os.environ.get(var):
            missing_recommended.append(var)

    if missing_recommended:
        logger.warning(
            f"Missing recommended environment variables: {', '.join(missing_recommended)}\n"
            f"Some features may not work correctly."
        )

    # Validate Dagster PostgreSQL configuration if present
    postgres_vars = [
        "DAGSTER_POSTGRES_USER",
        "DAGSTER_POSTGRES_PASSWORD",
        "DAGSTER_POSTGRES_DB",
        "DAGSTER_POSTGRES_HOST",
        "DAGSTER_POSTGRES_PORT",
    ]

    postgres_set = [var for var in postgres_vars if os.environ.get(var)]
    if postgres_set and len(postgres_set) != len(postgres_vars):
        missing_postgres = [var for var in postgres_vars if var not in postgres_set]
        logger.warning(
            f"Partial PostgreSQL configuration detected. Missing: {', '.join(missing_postgres)}\n"
            f"Dagster may fall back to SQLite storage."
        )

    logger.info("Environment variable validation completed successfully")


def get_missing_env_vars(required: List[str]) -> List[str]:
    """
    Get list of missing environment variables.

    Args:
        required: List of required environment variable names

    Returns:
        List of missing variable names
    """
    return [var for var in required if not os.environ.get(var)]


def validate_config_files() -> Tuple[bool, List[str]]:
    """
    Validate that required configuration files exist.

    Returns:
        Tuple of (all_present, missing_files)
    """
    from pathlib import Path

    required_files = [
        "config/config.yaml",
        "config/meters.yaml",
    ]

    missing = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing.append(file_path)

    return (len(missing) == 0, missing)
