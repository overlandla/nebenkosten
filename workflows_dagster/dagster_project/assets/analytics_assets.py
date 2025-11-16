"""
Analytics Assets for Utility Meter Processing
Main data processing pipeline for meter data interpolation and calculations

IMPROVEMENTS:
- Fixed imports to use properly created src modules
- Fixed multi_asset return types
- Improved anomaly detection with statistical methods
- Added unit conversion validation
- Added offset reasonability checks for master meters
- Better error handling and logging
- Comprehensive documentation
"""

import os
# Import utility analysis modules from src
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from dagster import (AssetExecutionContext, AssetOut, MaterializeResult,
                     MetadataValue, Output, asset, multi_asset)

# Add workflows_dagster to path to access src modules
workflows_dagster_path = Path(__file__).parent.parent.parent
if str(workflows_dagster_path) not in sys.path:
    sys.path.insert(0, str(workflows_dagster_path))

from src.calculator import ConsumptionCalculator
from src.data_processor import DataProcessor
from src.influx_client import InfluxClient

from ..resources.config_resource import ConfigResource
from ..resources.influxdb_resource import InfluxDBResource

# =============================================================================
# DISCOVERY ASSETS
# =============================================================================


@asset(
    group_name="discovery",
    compute_kind="influxdb",
    description="Discover all available physical meters in InfluxDB",
)
def meter_discovery(
    context: AssetExecutionContext, influxdb: InfluxDBResource, config: ConfigResource
) -> List[str]:
    """
    Discover all available meters in InfluxDB

    Queries the raw data bucket for all input_number entities (physical meters)
    and returns a sorted list of entity IDs.

    Returns:
        List of meter entity IDs found in the database

    Example:
        ['gas_zahler', 'haupt_strom', 'haupt_wasser', 'og1_strom', ...]
    """
    logger = context.log

    try:
        cfg = config.load_config()
        logger.info("Discovering available meters from InfluxDB...")

        influx_client = InfluxClient(
            url=influxdb.url,
            token=os.environ.get("INFLUX_TOKEN"),
            org=influxdb.org,
            bucket=influxdb.bucket_raw,
        )

        meters = influx_client.discover_available_meters()

        if not meters:
            logger.warning("No meters found in InfluxDB!")
            return []

        logger.info(f"Found {len(meters)} physical meters: {meters}")
        return meters

    except Exception as e:
        logger.error(f"Failed to discover meters: {str(e)}")
        raise


# =============================================================================
# RAW DATA FETCHING
# =============================================================================


@asset(
    group_name="processing",
    compute_kind="influxdb",
    description="Fetch raw meter data for all discovered meters",
)
def raw_meter_data(
    context: AssetExecutionContext,
    meter_discovery: List[str],
    influxdb: InfluxDBResource,
    config: ConfigResource,
) -> Dict[str, pd.DataFrame]:
    """
    Fetch raw data for all discovered meters

    For each meter found in discovery, fetches all historical readings from
    the configured start year to present.

    Args:
        meter_discovery: List of meter IDs from discovery asset
        influxdb: InfluxDB connection resource
        config: Configuration resource

    Returns:
        Dictionary mapping meter_id to DataFrame of raw readings
        {
            'gas_zahler': DataFrame(timestamp, value),
            'haupt_strom': DataFrame(timestamp, value),
            ...
        }

    Notes:
        - Empty DataFrames are returned for meters with no data
        - Errors for individual meters don't fail the entire asset
    """
    logger = context.log

    try:
        if not meter_discovery:
            logger.warning("No meters to fetch data for")
            return {}

        cfg = config.load_config()
        start_year = cfg.get("start_year", 2020)
        start_date = datetime(start_year, 1, 1)

        logger.info(
            f"Fetching raw data for {len(meter_discovery)} meters " f"from {start_date}"
        )

        influx_client = InfluxClient(
            url=influxdb.url,
            token=os.environ.get("INFLUX_TOKEN"),
            org=influxdb.org,
            bucket=influxdb.bucket_raw,
        )

        raw_data = {}
        total_points = 0
        meters_with_no_data = []

        for meter_id in meter_discovery:
            try:
                logger.info(f"Fetching raw data for {meter_id}")
                data = influx_client.fetch_all_meter_data(meter_id, start_date)

                if data.empty:
                    logger.warning(f"No data found for {meter_id}")
                    meters_with_no_data.append(meter_id)

                raw_data[meter_id] = data
                total_points += len(data)
                logger.info(f"Fetched {len(data)} points for {meter_id}")

            except Exception as e:
                logger.error(f"Failed to fetch data for {meter_id}: {str(e)}")
                # Add empty DataFrame to avoid breaking downstream assets
                raw_data[meter_id] = pd.DataFrame(columns=["timestamp", "value"])

        if meters_with_no_data:
            logger.warning(f"Meters with no data: {', '.join(meters_with_no_data)}")

        logger.info(f"Total raw data points fetched: {total_points}")
        return raw_data

    except Exception as e:
        logger.error(f"Failed to fetch meter data: {str(e)}")
        raise


# =============================================================================
# INTERPOLATION & AGGREGATION
# =============================================================================


@multi_asset(
    outs={
        "daily_interpolated_series": AssetOut(
            description="Interpolated daily meter readings for all meters"
        ),
        "monthly_interpolated_series": AssetOut(
            description="Aggregated monthly meter readings for all meters"
        ),
    },
    group_name="processing",
    compute_kind="python",
    description="Create interpolated daily and monthly series for all meters",
)
def interpolated_meter_series(
    context: AssetExecutionContext,
    raw_meter_data: Dict[str, pd.DataFrame],
    influxdb: InfluxDBResource,
    config: ConfigResource,
) -> Tuple[Output, Output]:
    """
    Create interpolated daily and monthly series for all meters

    Takes sparse raw meter readings and creates standardized time series with
    exactly one reading per day (or per month for monthly series).

    Process:
    1. For each meter, get installation/deinstallation dates from config
    2. Create daily series using DataProcessor (handles interpolation/extrapolation)
    3. Aggregate daily series to monthly

    Args:
        raw_meter_data: Dictionary of raw meter readings
        influxdb: InfluxDB connection resource
        config: Configuration resource

    Returns:
        Tuple of two Output objects:
        - daily_interpolated_series: Daily readings for all meters
        - monthly_interpolated_series: Monthly aggregated readings

    Notes:
        - Uses linear interpolation for gaps in data
        - Applies regression-based extrapolation when needed
        - Installation/deinstallation dates limit the time range
    """
    logger = context.log
    cfg = config.load_config()
    start_year = cfg.get("start_year", 2020)

    start_date_str = f"{start_year}-01-01"
    end_date_str = datetime.now().strftime("%Y-%m-%d")

    logger.info(f"Creating interpolated series from {start_date_str} to {end_date_str}")

    influx_client = InfluxClient(
        url=influxdb.url,
        token=os.environ.get("INFLUX_TOKEN"),
        org=influxdb.org,
        bucket=influxdb.bucket_raw,
    )

    # Pre-populate cache with raw data
    influx_client.meter_data_cache = raw_meter_data.copy()

    data_processor = DataProcessor(influx_client)

    daily_readings = {}
    monthly_readings = {}
    total_daily_points = 0
    total_monthly_points = 0

    # Get meters configuration for installation/deinstallation dates
    meters_config = cfg.get("meters", [])
    meter_config_map = {m["meter_id"]: m for m in meters_config if "meter_id" in m}

    for meter_id, raw_data in raw_meter_data.items():
        try:
            logger.info(f"Processing {meter_id}")

            if raw_data.empty:
                logger.warning(f"Skipping {meter_id}: no raw data")
                daily_readings[meter_id] = pd.DataFrame(columns=["timestamp", "value"])
                monthly_readings[meter_id] = pd.DataFrame(
                    columns=["timestamp", "value"]
                )
                continue

            # Get installation/deinstallation dates from config
            meter_config = meter_config_map.get(meter_id, {})
            installation_date = meter_config.get("installation_date")
            deinstallation_date = meter_config.get("deinstallation_date")

            # Create daily series
            daily_series = data_processor.create_standardized_daily_series(
                meter_id,
                start_date_str,
                end_date_str,
                installation_date=installation_date,
                deinstallation_date=deinstallation_date,
            )
            daily_readings[meter_id] = daily_series
            total_daily_points += len(daily_series)

            # Aggregate to monthly
            monthly_series = data_processor.aggregate_daily_to_frequency(
                daily_series, "M"
            )
            monthly_readings[meter_id] = monthly_series
            total_monthly_points += len(monthly_series)

            logger.info(
                f"Created {len(daily_series)} daily and {len(monthly_series)} "
                f"monthly points for {meter_id}"
            )

        except Exception as e:
            logger.error(f"Failed to process {meter_id}: {str(e)}")
            # Add empty DataFrames to avoid breaking downstream
            daily_readings[meter_id] = pd.DataFrame(columns=["timestamp", "value"])
            monthly_readings[meter_id] = pd.DataFrame(columns=["timestamp", "value"])

    logger.info(
        f"Total daily points: {total_daily_points}, "
        f"monthly points: {total_monthly_points}"
    )

    return (
        Output(
            value=daily_readings,
            metadata={
                "meter_count": len(daily_readings),
                "total_points": total_daily_points,
                "date_range": f"{start_date_str} to {end_date_str}",
            },
        ),
        Output(
            value=monthly_readings,
            metadata={
                "meter_count": len(monthly_readings),
                "total_points": total_monthly_points,
                "date_range": f"{start_date_str} to {end_date_str}",
            },
        ),
    )


# =============================================================================
# MASTER METER PROCESSING
# =============================================================================


def _validate_unit_conversion(from_unit: str, to_unit: str, logger) -> bool:
    """
    Validate that unit conversion is supported

    Prevents mixing incompatible units (e.g., L with kWh)

    Args:
        from_unit: Source unit
        to_unit: Target unit
        logger: Dagster logger

    Returns:
        True if conversion is valid, False otherwise
    """
    from_unit_lower = from_unit.lower()
    to_unit_lower = to_unit.lower()

    if from_unit_lower == to_unit_lower:
        return True

    # Valid conversion pairs
    valid_conversions = [
        {"m³", "kwh"},  # Gas volume to energy
        {"kwh", "m³"},  # Gas energy to volume
    ]

    conversion_pair = {from_unit_lower, to_unit_lower}

    for valid_pair in valid_conversions:
        if conversion_pair == valid_pair:
            return True

    logger.error(
        f"Invalid unit conversion: {from_unit} → {to_unit}. "
        f"Valid conversions: m³↔kWh"
    )
    return False


def _convert_series(
    series: pd.DataFrame,
    from_unit: str,
    to_unit: str,
    gas_conversion_factor: float,
    logger,
) -> pd.DataFrame:
    """
    Convert meter reading series between units

    Handles gas volume (m³) to energy (kWh) conversion and reverse.

    Args:
        series: DataFrame with 'value' column
        from_unit: Source unit (e.g., 'm³')
        to_unit: Target unit (e.g., 'kWh')
        gas_conversion_factor: Conversion factor (energy_content * z_factor)
        logger: Dagster logger

    Returns:
        Converted DataFrame with same structure

    Notes:
        - Returns copy of original series if from_unit == to_unit
        - Validates conversion is supported before proceeding
    """
    if from_unit == to_unit or series.empty:
        return series.copy()

    # Validate conversion is supported
    if not _validate_unit_conversion(from_unit, to_unit, logger):
        logger.warning(
            f"Skipping unsupported conversion: {from_unit} → {to_unit}, "
            f"returning original series"
        )
        return series.copy()

    converted = series.copy()

    if from_unit.lower() == "m³" and to_unit.lower() == "kwh":
        converted["value"] = converted["value"] * gas_conversion_factor
        logger.debug(
            f"Converted {from_unit} → {to_unit} "
            f"using factor {gas_conversion_factor:.4f}"
        )
    elif from_unit.lower() == "kwh" and to_unit.lower() == "m³":
        if gas_conversion_factor > 0:
            converted["value"] = converted["value"] / gas_conversion_factor
            logger.debug(
                f"Converted {from_unit} → {to_unit} "
                f"using factor 1/{gas_conversion_factor:.4f}"
            )
        else:
            logger.error(
                f"Cannot convert {from_unit} → {to_unit}: "
                f"invalid conversion factor {gas_conversion_factor}"
            )

    return converted


@asset(
    group_name="processing",
    compute_kind="python",
    description="Process master meters by combining physical meters across time periods",
)
def master_meter_series(
    context: AssetExecutionContext,
    daily_interpolated_series: Dict[str, pd.DataFrame],
    monthly_interpolated_series: Dict[str, pd.DataFrame],
    config: ConfigResource,
) -> Dict[str, Dict[str, pd.DataFrame]]:
    """
    Process master meters by combining source meters across periods

    Master meters represent logical meters that may be composed of multiple
    physical meters over time (e.g., due to meter replacements or combining
    multiple sources).

    Configuration Example:
        {
          "meter_id": "gas_total",
          "type": "master",
          "output_unit": "kWh",
          "periods": [
            {
              "start_date": "2020-01-01",
              "end_date": "2023-06-15",
              "source_meters": ["gas_zahler_alt"],
              "source_unit": "m³",
              "composition_type": "single"
            },
            {
              "start_date": "2023-06-15",
              "end_date": "2025-12-31",
              "source_meters": ["gas_zahler"],
              "source_unit": "m³",
              "composition_type": "single",
              "apply_offset_from_previous_period": true
            }
          ]
        }

    Process:
    1. For each master meter in config
    2. For each period, get source meter data
    3. Convert units if needed (e.g., m³ → kWh)
    4. Apply composition (single meter or sum of multiple)
    5. Apply offset if continuing from previous period
    6. Combine all periods into continuous series

    Args:
        daily_interpolated_series: Daily readings for physical meters
        monthly_interpolated_series: Monthly readings for physical meters
        config: Configuration resource

    Returns:
        Dictionary with master meter data:
        {
            'gas_total': {
                'daily': DataFrame(timestamp, value),
                'monthly': DataFrame(timestamp, value)
            },
            ...
        }

    Notes:
        - Offsets are validated for reasonability (warn if >20% of previous value)
        - Unit conversions are validated before application
        - Missing source meters log warnings but don't fail the asset
    """
    logger = context.log
    cfg = config.load_config()

    master_meters = config.get_meters_by_type(cfg, "master")
    logger.info(f"Processing {len(master_meters)} master meters")

    gas_conversion_params = config.get_gas_conversion_params(cfg)
    gas_conversion_factor = (
        gas_conversion_params["energy_content"] * gas_conversion_params["z_factor"]
    )

    master_results = {}

    for master_config in master_meters:
        master_id = master_config["meter_id"]
        output_unit = master_config.get("output_unit", "kWh")
        periods = master_config.get("periods", [])

        logger.info(f"Processing master meter: {master_id} with {len(periods)} periods")

        result = {"daily": pd.DataFrame(), "monthly": pd.DataFrame()}

        for freq, readings_dict in [
            ("daily", daily_interpolated_series),
            ("monthly", monthly_interpolated_series),
        ]:
            combined_parts = []
            previous_period_last_value = 0.0

            for period_idx, period in enumerate(periods):
                start_date = pd.to_datetime(period["start_date"])
                end_date = pd.to_datetime(period["end_date"])
                composition_type = period.get("composition_type", "single")
                source_meters = period.get("source_meters", [])
                source_unit = period.get("source_unit", output_unit)
                apply_offset = period.get("apply_offset_from_previous_period", False)

                logger.debug(
                    f"Period {period_idx + 1}: {start_date.date()} to {end_date.date()}, "
                    f"sources: {source_meters}"
                )

                # Get data from source meters
                source_data_list = []
                for source_id in source_meters:
                    if source_id in readings_dict:
                        source_df = readings_dict[source_id].copy()

                        # Ensure timestamp column exists
                        if "timestamp" not in source_df.columns:
                            if isinstance(source_df.index, pd.DatetimeIndex):
                                source_df = source_df.reset_index()
                                source_df = source_df.rename(
                                    columns={source_df.columns[0]: "timestamp"}
                                )

                        # Filter to period date range
                        source_df = source_df[
                            (source_df["timestamp"] >= start_date)
                            & (source_df["timestamp"] <= end_date)
                        ]

                        # Convert units if needed
                        source_df = _convert_series(
                            source_df,
                            source_unit,
                            output_unit,
                            gas_conversion_factor,
                            logger,
                        )

                        source_data_list.append(source_df)
                    else:
                        logger.warning(
                            f"Source meter {source_id} not found for "
                            f"master meter {master_id}"
                        )

                if not source_data_list:
                    logger.warning(
                        f"No source data found for period {period_idx + 1} "
                        f"of {master_id}"
                    )
                    continue

                # Combine source meters based on composition type
                if composition_type == "sum":
                    # Sum all source meters (for parallel meters)
                    period_data = source_data_list[0].copy()
                    for other_df in source_data_list[1:]:
                        # Align on timestamp and sum values
                        merged = period_data.merge(
                            other_df,
                            on="timestamp",
                            how="outer",
                            suffixes=("", "_other"),
                        )
                        merged["value"] = merged["value"].fillna(0) + merged[
                            "value_other"
                        ].fillna(0)
                        period_data = merged[["timestamp", "value"]]
                else:  # single
                    period_data = source_data_list[0].copy()

                # Apply offset if requested (for meter continuity)
                if apply_offset and previous_period_last_value > 0:
                    if not period_data.empty:
                        period_first_value = period_data.iloc[0]["value"]
                        offset = previous_period_last_value - period_first_value

                        # IMPROVEMENT: Validate offset reasonability
                        if abs(offset) > 0.2 * previous_period_last_value:
                            logger.warning(
                                f"Large offset detected for {master_id} period {period_idx + 1}: "
                                f"{offset:.2f} ({abs(offset)/previous_period_last_value*100:.1f}% "
                                f"of previous value). This may indicate a configuration error."
                            )

                        period_data["value"] = period_data["value"] + offset
                        logger.debug(
                            f"Applied offset {offset:.2f} to period {period_idx + 1}"
                        )

                combined_parts.append(period_data)

                # Track last value for next period
                if not period_data.empty:
                    previous_period_last_value = period_data.iloc[-1]["value"]

            # Concatenate all periods
            if combined_parts:
                result[freq] = pd.concat(combined_parts).sort_values("timestamp")
                result[freq] = result[freq].drop_duplicates(subset=["timestamp"])
                result[freq] = result[freq].reset_index(drop=True)
                logger.info(f"Master {master_id} {freq}: {len(result[freq])} points")

        master_results[master_id] = result

    logger.info(f"Completed processing {len(master_results)} master meters")

    return master_results


# =============================================================================
# CONSUMPTION CALCULATION
# =============================================================================


@asset(
    group_name="processing",
    compute_kind="python",
    description="Calculate consumption values from meter readings",
)
def consumption_data(
    context: AssetExecutionContext,
    daily_interpolated_series: Dict[str, pd.DataFrame],
    master_meter_series: Dict[str, Dict[str, pd.DataFrame]],
    config: ConfigResource,
) -> Dict[str, pd.DataFrame]:
    """
    Calculate daily consumption values from cumulative meter readings

    Converts cumulative meter readings (monotonically increasing values) to
    daily consumption (difference between consecutive days).

    Process:
    1. Combine physical and master meter readings
    2. For each meter, calculate consumption = reading[day] - reading[day-1]
    3. Clip negative values to 0 (handles meter resets)

    Args:
        daily_interpolated_series: Daily readings for physical meters
        master_meter_series: Daily/monthly readings for master meters
        config: Configuration resource

    Returns:
        Dictionary mapping meter_id to consumption DataFrame
        {
            'gas_zahler': DataFrame(timestamp, value),  # value = daily consumption
            'haupt_strom': DataFrame(timestamp, value),
            ...
        }

    Notes:
        - First day for each meter has 0 consumption (no previous value)
        - Negative consumption is clipped to 0 (meter resets or errors)
        - Empty DataFrames for meters with no readings
    """
    logger = context.log

    # Combine physical and master meters
    all_meters = {}
    all_meters.update({k: v for k, v in daily_interpolated_series.items()})
    all_meters.update({k: v["daily"] for k, v in master_meter_series.items()})

    logger.info(f"Calculating consumption for {len(all_meters)} meters")

    calculator = ConsumptionCalculator()
    consumption_results = {}
    total_points = 0
    skipped_meters = []

    for meter_id, readings in all_meters.items():
        try:
            if readings.empty:
                logger.warning(f"Skipping {meter_id}: no readings data")
                skipped_meters.append(meter_id)
                consumption_results[meter_id] = pd.DataFrame(
                    columns=["timestamp", "value"]
                )
                continue

            consumption = calculator.calculate_consumption_from_readings(readings)
            consumption_results[meter_id] = consumption
            total_points += len(consumption)

            # Log summary statistics
            if len(consumption) > 0:
                total_consumption = consumption["value"].sum()
                avg_daily = consumption["value"].mean()
                max_daily = consumption["value"].max()
                logger.debug(
                    f"{meter_id}: {len(consumption)} days, "
                    f"total={total_consumption:.2f}, "
                    f"avg_daily={avg_daily:.2f}, "
                    f"max_daily={max_daily:.2f}"
                )

        except Exception as e:
            logger.error(f"Failed to calculate consumption for {meter_id}: {str(e)}")
            skipped_meters.append(meter_id)
            consumption_results[meter_id] = pd.DataFrame(columns=["timestamp", "value"])

    if skipped_meters:
        logger.warning(
            f"Skipped {len(skipped_meters)} meters: {', '.join(skipped_meters)}"
        )

    logger.info(f"Total consumption points calculated: {total_points}")

    return consumption_results


# =============================================================================
# VIRTUAL METER PROCESSING
# =============================================================================


@asset(
    group_name="processing",
    compute_kind="python",
    description="Calculate virtual meters using subtraction logic",
)
def virtual_meter_data(
    context: AssetExecutionContext,
    consumption_data: Dict[str, pd.DataFrame],
    config: ConfigResource,
) -> Dict[str, pd.DataFrame]:
    """
    Calculate virtual meters from consumption data

    Virtual meters represent derived consumption values calculated by
    subtracting sub-meters from a base meter.

    Example:
        strom_allgemein = haupt_strom - eg_strom - og1_strom - og2_strom
        (general electricity = total - apartment 1 - apartment 2 - apartment 3)

    Configuration Example:
        {
          "meter_id": "eg_kalfire",
          "type": "virtual",
          "base_meter": "gas_total",
          "subtract_meters": ["gastherme_gesamt"],
          "subtract_meter_conversions": {
            "gastherme_gesamt": {
              "from_unit": "kWh",
              "to_unit": "m³"
            }
          }
        }

    Process:
    1. Start with base meter consumption
    2. For each subtract meter:
       a. Convert units if needed
       b. Subtract from base (only where both have data)
    3. Clip negative values to 0
    4. Return resulting virtual consumption

    Args:
        consumption_data: Daily consumption for all meters
        config: Configuration resource

    Returns:
        Dictionary with virtual meter consumption data
        {
            'eg_kalfire': DataFrame(timestamp, value),
            'strom_allgemein': DataFrame(timestamp, value),
            ...
        }

    Notes:
        - Unit conversions are validated before application
        - Subtraction only occurs for dates where both meters have data
        - Negative values are clipped to 0 (prevents negative consumption)
        - Missing base or subtract meters log warnings but don't fail
    """
    logger = context.log
    cfg = config.load_config()

    virtual_meters = config.get_meters_by_type(cfg, "virtual")
    logger.info(f"Processing {len(virtual_meters)} virtual meters")

    gas_conversion_params = config.get_gas_conversion_params(cfg)
    gas_conversion_factor = (
        gas_conversion_params["energy_content"] * gas_conversion_params["z_factor"]
    )

    virtual_results = {}

    for virtual_config in virtual_meters:
        meter_id = virtual_config["meter_id"]
        base_meter = virtual_config.get("base_meter")
        subtract_meters = virtual_config.get("subtract_meters", [])
        subtract_conversions = virtual_config.get("subtract_meter_conversions", {})

        logger.info(
            f"Processing virtual meter: {meter_id} = "
            f"{base_meter} - {subtract_meters}"
        )

        if base_meter not in consumption_data:
            logger.warning(
                f"Base meter {base_meter} not found for virtual meter {meter_id}"
            )
            continue

        base_consumption = consumption_data[base_meter].copy()

        # Ensure timestamp column
        if "timestamp" not in base_consumption.columns:
            if isinstance(base_consumption.index, pd.DatetimeIndex):
                base_consumption = base_consumption.reset_index()
                base_consumption = base_consumption.rename(
                    columns={base_consumption.columns[0]: "timestamp"}
                )

        for subtract_meter in subtract_meters:
            if subtract_meter not in consumption_data:
                logger.warning(
                    f"Subtract meter {subtract_meter} not found for "
                    f"virtual meter {meter_id}"
                )
                continue

            subtract_consumption = consumption_data[subtract_meter].copy()

            # Ensure timestamp column
            if "timestamp" not in subtract_consumption.columns:
                if isinstance(subtract_consumption.index, pd.DatetimeIndex):
                    subtract_consumption = subtract_consumption.reset_index()
                    subtract_consumption = subtract_consumption.rename(
                        columns={subtract_consumption.columns[0]: "timestamp"}
                    )

            # Apply unit conversion if specified
            if subtract_meter in subtract_conversions:
                conversion = subtract_conversions[subtract_meter]
                from_unit = conversion.get("from_unit", "")
                to_unit = conversion.get("to_unit", "")

                logger.debug(
                    f"Converting {subtract_meter} from {from_unit} to {to_unit}"
                )

                if not _validate_unit_conversion(from_unit, to_unit, logger):
                    logger.warning(
                        f"Skipping {subtract_meter} due to invalid conversion"
                    )
                    continue

                if from_unit.lower() == "kwh" and to_unit.lower() == "m³":
                    if gas_conversion_factor > 0:
                        subtract_consumption["value"] = (
                            subtract_consumption["value"] / gas_conversion_factor
                        )
                    else:
                        logger.error(
                            f"Cannot convert: invalid conversion factor "
                            f"{gas_conversion_factor}"
                        )
                        continue
                elif from_unit.lower() == "m³" and to_unit.lower() == "kwh":
                    subtract_consumption["value"] = (
                        subtract_consumption["value"] * gas_conversion_factor
                    )

            # Merge and subtract - align on timestamp
            merged = base_consumption.merge(
                subtract_consumption[["timestamp", "value"]],
                on="timestamp",
                how="left",
                suffixes=("", "_subtract"),
            )

            # Subtract where both have data
            merged["value_subtract"] = merged["value_subtract"].fillna(0)
            merged["value"] = merged["value"] - merged["value_subtract"]

            base_consumption = merged[["timestamp", "value"]]

        # Clip negative values to zero
        base_consumption["value"] = base_consumption["value"].clip(lower=0)

        virtual_results[meter_id] = base_consumption

        if len(base_consumption) > 0:
            total = base_consumption["value"].sum()
            logger.info(
                f"Created virtual meter {meter_id} with {len(base_consumption)} "
                f"points (total consumption: {total:.2f})"
            )

    logger.info(f"Completed processing {len(virtual_results)} virtual meters")

    return virtual_results


# =============================================================================
# ANOMALY DETECTION
# =============================================================================


@asset(
    group_name="analysis",
    compute_kind="python",
    description="Detect consumption anomalies using statistical methods",
)
def anomaly_detection(
    context: AssetExecutionContext,
    consumption_data: Dict[str, pd.DataFrame],
    virtual_meter_data: Dict[str, pd.DataFrame],
) -> Dict[str, pd.DataFrame]:
    """
    Detect anomalies in consumption data using statistical methods

    IMPROVED ALGORITHM:
    Uses multi-method anomaly detection:
    1. Z-score method: Detects outliers >3 standard deviations from mean
    2. IQR method: Detects outliers beyond 1.5 * IQR from quartiles
    3. Rolling Z-score: Detects local anomalies using 30-day window

    An anomaly is flagged if detected by at least 2 of the 3 methods,
    reducing false positives while maintaining sensitivity.

    Args:
        consumption_data: Daily consumption for physical/master meters
        virtual_meter_data: Daily consumption for virtual meters

    Returns:
        Dictionary with anomaly DataFrames per meter
        {
            'gas_zahler': DataFrame(timestamp, value, z_score, iqr_bounds, ...),
            ...
        }

    Notes:
        - Requires at least 60 days of data for meaningful statistics
        - Seasonal patterns are NOT yet accounted for (future improvement)
        - Anomalies include the detection method flags for analysis
    """
    logger = context.log

    # Combine all consumption data
    all_consumption = {}
    all_consumption.update(consumption_data)
    all_consumption.update(virtual_meter_data)

    logger.info(f"Detecting anomalies for {len(all_consumption)} meters")

    anomalies = {}
    total_anomalies = 0

    for meter_id, consumption in all_consumption.items():
        if consumption.empty or len(consumption) < 60:
            logger.debug(
                f"Skipping {meter_id}: insufficient data "
                f"({len(consumption)} days, need 60+)"
            )
            continue

        try:
            # Ensure we have a proper DataFrame with value column
            if "value" not in consumption.columns:
                logger.warning(f"No 'value' column in {meter_id}")
                continue

            df = consumption.copy()

            # Ensure timestamp is in columns (not index)
            if "timestamp" not in df.columns:
                if isinstance(df.index, pd.DatetimeIndex):
                    df = df.reset_index()
                    df = df.rename(columns={df.columns[0]: "timestamp"})

            # Remove zero-consumption days for better statistics
            df_nonzero = df[df["value"] > 0].copy()

            if len(df_nonzero) < 30:
                logger.debug(
                    f"Skipping {meter_id}: insufficient non-zero data "
                    f"({len(df_nonzero)} days)"
                )
                continue

            # Method 1: Global Z-score
            mean_consumption = df_nonzero["value"].mean()
            std_consumption = df_nonzero["value"].std()

            if std_consumption > 0:
                df["z_score"] = (df["value"] - mean_consumption) / std_consumption
                df["anomaly_zscore"] = df["z_score"].abs() > 3
            else:
                df["z_score"] = 0
                df["anomaly_zscore"] = False

            # Method 2: IQR method
            q1 = df_nonzero["value"].quantile(0.25)
            q3 = df_nonzero["value"].quantile(0.75)
            iqr = q3 - q1

            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            df["iqr_lower"] = lower_bound
            df["iqr_upper"] = upper_bound
            df["anomaly_iqr"] = (df["value"] < lower_bound) | (
                df["value"] > upper_bound
            )

            # Method 3: Rolling Z-score (local anomalies)
            rolling_mean = (
                df["value"].rolling(window=30, min_periods=10, center=True).mean()
            )
            rolling_std = (
                df["value"].rolling(window=30, min_periods=10, center=True).std()
            )

            df["rolling_z_score"] = (df["value"] - rolling_mean) / rolling_std
            df["anomaly_rolling"] = df["rolling_z_score"].abs() > 2.5

            # Combine methods: flag as anomaly if detected by 2+ methods
            df["anomaly_count"] = (
                df["anomaly_zscore"].astype(int)
                + df["anomaly_iqr"].astype(int)
                + df["anomaly_rolling"].astype(int)
            )
            df["is_anomaly"] = df["anomaly_count"] >= 2

            # Filter to anomalies only
            anomaly_points = df[df["is_anomaly"]].copy()

            if len(anomaly_points) > 0:
                anomalies[meter_id] = anomaly_points
                total_anomalies += len(anomaly_points)

                logger.info(
                    f"Found {len(anomaly_points)} anomalies for {meter_id} "
                    f"({len(anomaly_points)/len(df)*100:.1f}% of data)"
                )

                # Log some details about the anomalies
                logger.debug(
                    f"{meter_id} anomaly summary: "
                    f"mean={mean_consumption:.2f}, "
                    f"std={std_consumption:.2f}, "
                    f"IQR=[{lower_bound:.2f}, {upper_bound:.2f}]"
                )

        except Exception as e:
            logger.error(
                f"Error detecting anomalies for {meter_id}: {str(e)}", exc_info=True
            )
            continue

    logger.info(
        f"Total anomalies detected: {total_anomalies} across "
        f"{len(anomalies)} meters"
    )

    return anomalies
