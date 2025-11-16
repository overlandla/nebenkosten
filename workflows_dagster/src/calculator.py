"""
Consumption Calculator for Utility Meter Data
Calculates consumption from meter readings
"""

import logging
from typing import Optional

import pandas as pd


class ConsumptionCalculator:
    """
    Calculator for consumption values from cumulative meter readings.

    Provides methods to:
    - Calculate period consumption from cumulative readings
    - Calculate annual consumption
    - Handle meter resets and edge cases
    """

    def calculate_consumption_from_readings(
        self, readings: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Calculate daily consumption from cumulative meter readings

        Args:
            readings: DataFrame with DatetimeIndex and 'value' column containing
                     cumulative meter readings

        Returns:
            DataFrame with DatetimeIndex and 'value' column containing daily consumption

        Example:
            Input (cumulative readings):
                2024-01-01: 100.0
                2024-01-02: 102.5
                2024-01-03: 106.0

            Output (daily consumption):
                2024-01-01: 0.0     (no previous reading)
                2024-01-02: 2.5
                2024-01-03: 3.5

        Notes:
            - Negative consumption values are clipped to 0 (handles meter resets)
            - First day has 0 consumption (no previous value to diff against)
        """
        if readings.empty:
            return pd.DataFrame()

        # Ensure we have a DatetimeIndex
        if "timestamp" in readings.columns:
            consumption = readings.set_index("timestamp").copy()
        else:
            consumption = readings.copy()

        # Calculate difference between consecutive readings
        consumption["value"] = consumption["value"].diff()

        # Fill first NaN with 0 (no consumption on first day)
        consumption["value"] = consumption["value"].fillna(0)

        # Clip negative values to 0 (meter resets or errors)
        consumption["value"] = consumption["value"].clip(lower=0)

        return consumption.reset_index()

    def calculate_annual_consumption(self, readings: pd.DataFrame, year: int) -> float:
        """
        Calculate total consumption for a specific year

        Args:
            readings: DataFrame with timestamp and value columns (cumulative readings)
            year: Year to calculate consumption for

        Returns:
            Total consumption for the year (non-negative)

        Example:
            readings:
                2023-12-31: 1000.0
                2024-12-31: 1500.0

            calculate_annual_consumption(readings, 2024) -> 500.0

        Notes:
            - Uses nearest values to year boundaries if exact dates not present
            - Returns 0 if data insufficient for the year
        """
        if readings.empty:
            return 0.0

        # Ensure we have timestamp column
        if "timestamp" not in readings.columns:
            if isinstance(readings.index, pd.DatetimeIndex):
                df = readings.reset_index()
            else:
                logging.error("Cannot find timestamp in readings")
                return 0.0
        else:
            df = readings.copy()

        # Define year boundaries
        year_start = pd.Timestamp(f"{year}-01-01", tz="UTC")
        year_end = pd.Timestamp(f"{year}-12-31 23:59:59", tz="UTC")

        try:
            # Set timestamp as index for nearest lookup
            series = df.set_index("timestamp")

            # Get value at start of year (or closest)
            start_idx = series.index.get_indexer([year_start], method="nearest")[0]
            start_value = series.iloc[start_idx]["value"]

            # Get value at end of year (or closest)
            end_idx = series.index.get_indexer([year_end], method="nearest")[0]
            end_value = series.iloc[end_idx]["value"]

            # Calculate consumption
            consumption = end_value - start_value

            # Ensure non-negative
            return max(0.0, consumption)

        except Exception as e:
            logging.error(f"Error calculating annual consumption for {year}: {e}")
            return 0.0

    def combine_meter_readings(
        self,
        old_readings: pd.DataFrame,
        new_readings: pd.DataFrame,
        replacement_date: str,
    ) -> tuple[Optional[pd.DataFrame], float]:
        """
        Combine readings from an old and new meter at a replacement date

        When a physical meter is replaced, the new meter starts at a different
        value (often 0). This method combines the two series by offsetting the
        new meter's values to continue from where the old meter ended.

        Args:
            old_readings: DataFrame with readings from the old meter
            new_readings: DataFrame with readings from the new meter
            replacement_date: ISO format date string when meter was replaced

        Returns:
            Tuple of (combined_dataframe, offset_applied)
            - combined_dataframe: Continuous series combining both meters
            - offset_applied: The value added to new meter readings

        Example:
            old_readings:
                2024-01-01: 1000.0
                2024-06-01: 1500.0  (last reading before replacement)

            new_readings:
                2024-06-01: 0.0     (new meter starts at 0)
                2024-12-31: 250.0

            Result:
                2024-01-01: 1000.0
                2024-06-01: 1500.0
                2024-12-31: 1750.0  (250 + 1500 offset)

            offset_applied: 1500.0
        """
        if old_readings is None or old_readings.empty:
            logging.warning("Old meter readings not found or empty")
            return None, 0.0

        if new_readings is None or new_readings.empty:
            logging.warning("New meter readings not found or empty")
            return None, 0.0

        replacement_ts = pd.Timestamp(replacement_date, tz="UTC")

        # Ensure timestamp column exists
        for df_name, df in [("old", old_readings), ("new", new_readings)]:
            if "timestamp" not in df.columns:
                logging.error(f"{df_name} readings missing timestamp column")
                return None, 0.0

        # Filter old series up to replacement date
        old_filtered = old_readings[old_readings["timestamp"] <= replacement_ts].copy()

        # Get last value from old meter
        last_old_value = (
            old_filtered["value"].iloc[-1] if not old_filtered.empty else 0.0
        )

        # Filter new series from replacement date onwards
        new_filtered = new_readings[new_readings["timestamp"] >= replacement_ts].copy()

        if new_filtered.empty:
            logging.warning("New meter has no data after replacement date")
            return old_filtered, 0.0

        # Calculate offset to align new meter with old meter's last value
        first_new_value = new_filtered["value"].iloc[0]
        offset = last_old_value - first_new_value

        # Apply offset to new meter values
        new_filtered["value"] = new_filtered["value"] + offset

        # Combine series
        combined = pd.concat([old_filtered, new_filtered])
        combined = combined.drop_duplicates(subset=["timestamp"])
        combined = combined.sort_values("timestamp").reset_index(drop=True)

        logging.info(
            f"Combined meter series: {len(combined)} points total, "
            f"offset applied: {offset:.2f}"
        )

        return combined, offset
