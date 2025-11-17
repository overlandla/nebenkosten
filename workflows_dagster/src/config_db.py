"""
Configuration Database Client

Provides access to the PostgreSQL configuration database for reading
meters, households, and settings that can be edited via the Next.js UI.

This module serves as a bridge between the database and Dagster assets,
with YAML fallback support for backwards compatibility.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, date
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class ConfigDatabaseClient:
    """Client for accessing the configuration database"""

    def __init__(
        self,
        host: str = None,
        port: int = None,
        dbname: str = None,
        user: str = None,
        password: str = None,
    ):
        """
        Initialize the configuration database client

        Args:
            host: Database host (defaults to CONFIG_DB_HOST env var or 'localhost')
            port: Database port (defaults to CONFIG_DB_PORT env var or 5432)
            dbname: Database name (defaults to CONFIG_DB_NAME env var or 'nebenkosten_config')
            user: Database user (defaults to CONFIG_DB_USER env var or 'dagster')
            password: Database password (defaults to CONFIG_DB_PASSWORD env var or 'dagster')
        """
        self.host = host or os.environ.get("CONFIG_DB_HOST", "localhost")
        self.port = port or int(os.environ.get("CONFIG_DB_PORT", "5432"))
        self.dbname = dbname or os.environ.get("CONFIG_DB_NAME", "nebenkosten_config")
        self.user = user or os.environ.get("CONFIG_DB_USER", "dagster")
        self.password = password or os.environ.get("CONFIG_DB_PASSWORD", "dagster")

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                dbname=self.dbname,
                user=self.user,
                password=self.password,
                cursor_factory=RealDictCursor,
            )
            yield conn
        except Exception as e:
            logger.error(f"Failed to connect to config database: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def get_meters(
        self, active_only: bool = True, meter_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all meters from the database

        Args:
            active_only: If True, only return active meters (default: True)
            meter_type: Filter by meter type (electricity, gas, water, heat, solar)

        Returns:
            List of meter dictionaries
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM meters WHERE 1=1"
            params = []

            if active_only:
                query += " AND active = %s"
                params.append(True)

            if meter_type:
                query += " AND meter_type = %s"
                params.append(meter_type)

            query += " ORDER BY id"

            cursor.execute(query, params)
            meters = cursor.fetchall()

            return [dict(meter) for meter in meters]

    def get_meter(self, meter_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific meter by ID

        Args:
            meter_id: Meter identifier

        Returns:
            Meter dictionary or None if not found
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM meters WHERE id = %s", (meter_id,))
            meter = cursor.fetchone()
            return dict(meter) if meter else None

    def get_households(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get all households from the database

        Args:
            active_only: If True, only return active households (default: True)

        Returns:
            List of household dictionaries
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM households WHERE 1=1"
            params = []

            if active_only:
                query += " AND active = %s"
                params.append(True)

            query += " ORDER BY id"

            cursor.execute(query, params)
            households = cursor.fetchall()

            return [dict(household) for household in households]

    def get_household(self, household_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific household by ID

        Args:
            household_id: Household identifier

        Returns:
            Household dictionary or None if not found
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM households WHERE id = %s", (household_id,))
            household = cursor.fetchone()
            return dict(household) if household else None

    def get_household_meters(self, household_id: str) -> List[Dict[str, Any]]:
        """
        Get all meters assigned to a household

        Args:
            household_id: Household identifier

        Returns:
            List of household-meter assignment dictionaries
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT hm.*, m.name, m.meter_type, m.unit
                FROM household_meters hm
                JOIN meters m ON hm.meter_id = m.id
                WHERE hm.household_id = %s
                ORDER BY m.meter_type, m.id
            """,
                (household_id,),
            )
            assignments = cursor.fetchall()
            return [dict(assignment) for assignment in assignments]

    def get_setting(self, key: str) -> Optional[Any]:
        """
        Get a specific setting value

        Args:
            key: Setting key

        Returns:
            Setting value (parsed from JSON) or None if not found
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = %s", (key,))
            result = cursor.fetchone()
            return result["value"] if result else None

    def get_all_settings(self) -> Dict[str, Any]:
        """
        Get all settings as a dictionary

        Returns:
            Dictionary of all settings (key -> value)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM settings ORDER BY key")
            settings = cursor.fetchall()
            return {setting["key"]: setting["value"] for setting in settings}

    def update_setting(
        self, key: str, value: Any, description: Optional[str] = None
    ) -> bool:
        """
        Update or insert a setting

        Args:
            key: Setting key
            value: Setting value (will be JSON-encoded)
            description: Optional description

        Returns:
            True if successful
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            value_json = json.dumps(value) if not isinstance(value, str) else value

            if description:
                cursor.execute(
                    """
                    INSERT INTO settings (key, value, description)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (key) DO UPDATE SET
                        value = EXCLUDED.value,
                        description = EXCLUDED.description,
                        updated_at = NOW()
                """,
                    (key, value_json, description),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO settings (key, value)
                    VALUES (%s, %s)
                    ON CONFLICT (key) DO UPDATE SET
                        value = EXCLUDED.value,
                        updated_at = NOW()
                """,
                    (key, value_json),
                )

            conn.commit()
            return True

    def get_meters_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        Get meters filtered by category

        Args:
            category: Meter category (physical, master, virtual)

        Returns:
            List of meter dictionaries
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM meters WHERE category = %s AND active = true ORDER BY id",
                (category,),
            )
            meters = cursor.fetchall()
            return [dict(meter) for meter in meters]

    def check_connection(self) -> bool:
        """
        Check if the database connection is working

        Returns:
            True if connection successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False


# Global instance for convenience (can be overridden)
_default_client: Optional[ConfigDatabaseClient] = None


def get_config_db_client() -> ConfigDatabaseClient:
    """Get or create the default config database client"""
    global _default_client
    if _default_client is None:
        _default_client = ConfigDatabaseClient()
    return _default_client
