"""
Analytics Assets for Utility Meter Processing
Main data processing pipeline for meter data interpolation and calculations
"""
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any
import pandas as pd
from dagster import (
    asset,
    multi_asset,
    AssetOut,
    AssetExecutionContext,
    MaterializeResult,
    MetadataValue,
    Output
)
import sys
from pathlib import Path

# Import existing utility analysis modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "Nebenkosten"))
from src.influx_client import InfluxClient
from src.data_processor import DataProcessor
from src.calculator import ConsumptionCalculator

from ..resources.influxdb_resource import InfluxDBResource
from ..resources.config_resource import ConfigResource


@asset(
    group_name="discovery",
    compute_kind="influxdb",
    description="Discover all available physical meters in InfluxDB"
)
def meter_discovery(
    context: AssetExecutionContext,
    influxdb: InfluxDBResource,
    config: ConfigResource
) -> List[str]:
    """
    Discover all available meters in InfluxDB

    Returns:
        List of meter entity IDs found in the database
    """
    logger = context.log
    cfg = config.load_config()

    logger.info("Discovering available meters from InfluxDB...")

    influx_client = InfluxClient(
        url=influxdb.url,
        token=os.environ.get("INFLUX_TOKEN"),
        org=influxdb.org,
        bucket=influxdb.bucket_raw
    )

    meters = influx_client.discover_available_meters()
    logger.info(f"Found {len(meters)} physical meters: {meters}")

    return meters


@multi_asset(
    outs={
        "raw_meter_data": AssetOut(
            description="Raw meter data fetched from InfluxDB for all meters"
        ),
    },
    group_name="processing",
    compute_kind="influxdb",
    description="Fetch raw meter data for all discovered meters"
)
def fetch_meter_data(
    context: AssetExecutionContext,
    meter_discovery: List[str],
    influxdb: InfluxDBResource,
    config: ConfigResource
) -> Output:
    """
    Fetch raw data for all discovered meters

    Returns:
        Dictionary mapping meter_id to DataFrame of raw readings
    """
    logger = context.log
    cfg = config.load_config()
    start_year = cfg.get("start_year", 2020)
    start_date = datetime(start_year, 1, 1)

    logger.info(f"Fetching raw data for {len(meter_discovery)} meters from {start_date}")

    influx_client = InfluxClient(
        url=influxdb.url,
        token=os.environ.get("INFLUX_TOKEN"),
        org=influxdb.org,
        bucket=influxdb.bucket_raw
    )

    raw_data = {}
    total_points = 0

    for meter_id in meter_discovery:
        logger.info(f"Fetching raw data for {meter_id}")
        data = influx_client.fetch_all_meter_data(meter_id, start_date)
        raw_data[meter_id] = data
        total_points += len(data)
        logger.info(f"Fetched {len(data)} points for {meter_id}")

    logger.info(f"Total raw data points fetched: {total_points}")

    return Output(
        value=raw_data,
        metadata={
            "meter_count": len(raw_data),
            "total_points": total_points,
            "meters": MetadataValue.text(", ".join(meter_discovery))
        }
    )


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
    description="Create interpolated daily and monthly series for all meters"
)
def interpolated_meter_series(
    context: AssetExecutionContext,
    raw_meter_data: Dict[str, pd.DataFrame],
    influxdb: InfluxDBResource,
    config: ConfigResource
):
    """
    Create interpolated daily and monthly series for all meters

    Returns:
        Tuple of (daily_readings_dict, monthly_readings_dict)
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
        bucket=influxdb.bucket_raw
    )

    # Pre-populate cache with raw data
    influx_client.meter_data_cache = raw_meter_data.copy()

    data_processor = DataProcessor(influx_client)

    daily_readings = {}
    monthly_readings = {}
    total_daily_points = 0
    total_monthly_points = 0

    for meter_id, raw_data in raw_meter_data.items():
        logger.info(f"Processing {meter_id}")

        # Create daily series
        daily_series = data_processor.create_standardized_daily_series(
            meter_id,
            start_date_str,
            end_date_str
        )
        daily_readings[meter_id] = daily_series
        total_daily_points += len(daily_series)

        # Aggregate to monthly
        monthly_series = data_processor.aggregate_daily_to_frequency(daily_series, 'M')
        monthly_readings[meter_id] = monthly_series
        total_monthly_points += len(monthly_series)

        logger.info(f"Created {len(daily_series)} daily and {len(monthly_series)} monthly points for {meter_id}")

    logger.info(f"Total daily points: {total_daily_points}, monthly points: {total_monthly_points}")

    return (
        Output(
            value=daily_readings,
            metadata={
                "meter_count": len(daily_readings),
                "total_points": total_daily_points
            }
        ),
        Output(
            value=monthly_readings,
            metadata={
                "meter_count": len(monthly_readings),
                "total_points": total_monthly_points
            }
        )
    )


@asset(
    group_name="processing",
    compute_kind="python",
    description="Process master meters by combining physical meters across time periods"
)
def master_meter_series(
    context: AssetExecutionContext,
    daily_interpolated_series: Dict[str, pd.DataFrame],
    monthly_interpolated_series: Dict[str, pd.DataFrame],
    config: ConfigResource
) -> Dict[str, Dict[str, pd.DataFrame]]:
    """
    Process master meters by combining source meters across periods

    Returns:
        Dictionary with master meter data: {master_id: {"daily": df, "monthly": df}}
    """
    logger = context.log
    cfg = config.load_config()

    master_meters = config.get_meters_by_type(cfg, "master")
    logger.info(f"Processing {len(master_meters)} master meters")

    gas_conversion_params = config.get_gas_conversion_params(cfg)
    gas_conversion_factor = (
        gas_conversion_params["energy_content"] *
        gas_conversion_params["z_factor"]
    )

    def convert_series(series: pd.DataFrame, from_unit: str, to_unit: str) -> pd.DataFrame:
        """Convert meter reading series between units"""
        if from_unit == to_unit or series.empty:
            return series.copy()

        converted = series.copy()
        if from_unit.lower() == 'm³' and to_unit.lower() == 'kwh':
            converted['value'] = converted['value'] * gas_conversion_factor
        elif from_unit.lower() == 'kwh' and to_unit.lower() == 'm³':
            if gas_conversion_factor > 0:
                converted['value'] = converted['value'] / gas_conversion_factor
        else:
            logger.warning(f"Unsupported conversion: {from_unit} to {to_unit}")

        return converted

    master_results = {}

    for master_config in master_meters:
        master_id = master_config["meter_id"]
        output_unit = master_config.get("output_unit", "kWh")
        periods = master_config.get("periods", [])

        logger.info(f"Processing master meter: {master_id} with {len(periods)} periods")

        result = {"daily": pd.DataFrame(), "monthly": pd.DataFrame()}

        for freq, readings_dict in [("daily", daily_interpolated_series), ("monthly", monthly_interpolated_series)]:
            combined_parts = []
            previous_period_last_value = 0.0

            for period in periods:
                start_date = pd.to_datetime(period["start_date"])
                end_date = pd.to_datetime(period["end_date"])
                composition_type = period.get("composition_type", "single")
                source_meters = period.get("source_meters", [])
                source_unit = period.get("source_unit", output_unit)
                apply_offset = period.get("apply_offset_from_previous_period", False)

                # Get data from source meters
                source_data_list = []
                for source_id in source_meters:
                    if source_id in readings_dict:
                        source_df = readings_dict[source_id].copy()
                        # Filter to period date range
                        source_df = source_df[
                            (source_df.index >= start_date) &
                            (source_df.index <= end_date)
                        ]
                        # Convert units if needed
                        source_df = convert_series(source_df, source_unit, output_unit)
                        source_data_list.append(source_df)

                if not source_data_list:
                    continue

                # Combine source meters based on composition type
                if composition_type == "sum":
                    # Sum all source meters
                    period_data = source_data_list[0].copy()
                    for other_df in source_data_list[1:]:
                        period_data = period_data.add(other_df, fill_value=0)
                else:  # single
                    period_data = source_data_list[0].copy()

                # Apply offset if requested
                if apply_offset and previous_period_last_value > 0:
                    if not period_data.empty:
                        period_first_value = period_data.iloc[0]['value']
                        offset = previous_period_last_value - period_first_value
                        period_data['value'] = period_data['value'] + offset

                combined_parts.append(period_data)

                # Track last value for next period
                if not period_data.empty:
                    previous_period_last_value = period_data.iloc[-1]['value']

            # Concatenate all periods
            if combined_parts:
                result[freq] = pd.concat(combined_parts).sort_index()
                logger.info(f"Master {master_id} {freq}: {len(result[freq])} points")

        master_results[master_id] = result

    logger.info(f"Completed processing {len(master_results)} master meters")

    return master_results


@asset(
    group_name="processing",
    compute_kind="python",
    description="Calculate consumption values from meter readings"
)
def consumption_data(
    context: AssetExecutionContext,
    daily_interpolated_series: Dict[str, pd.DataFrame],
    master_meter_series: Dict[str, Dict[str, pd.DataFrame]],
    config: ConfigResource
) -> Dict[str, pd.DataFrame]:
    """
    Calculate consumption values from meter readings

    Returns:
        Dictionary mapping meter_id to consumption DataFrame
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

    for meter_id, readings in all_meters.items():
        if not readings.empty:
            consumption = calculator.calculate_consumption_from_readings(readings)
            consumption_results[meter_id] = consumption
            total_points += len(consumption)
            logger.info(f"Calculated {len(consumption)} consumption points for {meter_id}")

    logger.info(f"Total consumption points calculated: {total_points}")

    return consumption_results


@asset(
    group_name="processing",
    compute_kind="python",
    description="Calculate virtual meters using subtraction logic"
)
def virtual_meter_data(
    context: AssetExecutionContext,
    consumption_data: Dict[str, pd.DataFrame],
    config: ConfigResource
) -> Dict[str, pd.DataFrame]:
    """
    Calculate virtual meters from consumption data

    Returns:
        Dictionary with virtual meter consumption data
    """
    logger = context.log
    cfg = config.load_config()

    virtual_meters = config.get_meters_by_type(cfg, "virtual")
    logger.info(f"Processing {len(virtual_meters)} virtual meters")

    gas_conversion_params = config.get_gas_conversion_params(cfg)
    gas_conversion_factor = (
        gas_conversion_params["energy_content"] *
        gas_conversion_params["z_factor"]
    )

    virtual_results = {}

    for virtual_config in virtual_meters:
        meter_id = virtual_config["meter_id"]
        base_meter = virtual_config.get("base_meter")
        subtract_meters = virtual_config.get("subtract_meters", [])
        subtract_conversions = virtual_config.get("subtract_meter_conversions", {})

        logger.info(f"Processing virtual meter: {meter_id} = {base_meter} - {subtract_meters}")

        if base_meter not in consumption_data:
            logger.warning(f"Base meter {base_meter} not found for virtual meter {meter_id}")
            continue

        base_consumption = consumption_data[base_meter].copy()

        for subtract_meter in subtract_meters:
            if subtract_meter not in consumption_data:
                logger.warning(f"Subtract meter {subtract_meter} not found")
                continue

            subtract_consumption = consumption_data[subtract_meter].copy()

            # Apply unit conversion if specified
            if subtract_meter in subtract_conversions:
                conversion = subtract_conversions[subtract_meter]
                from_unit = conversion.get("from_unit", "")
                to_unit = conversion.get("to_unit", "")

                if from_unit.lower() == "kwh" and to_unit.lower() == "m³":
                    if gas_conversion_factor > 0:
                        subtract_consumption['value'] = subtract_consumption['value'] / gas_conversion_factor

            # Subtract
            base_consumption = base_consumption.subtract(subtract_consumption, fill_value=0)

        # Clip negative values to zero
        base_consumption['value'] = base_consumption['value'].clip(lower=0)

        virtual_results[meter_id] = base_consumption
        logger.info(f"Created virtual meter {meter_id} with {len(base_consumption)} points")

    logger.info(f"Completed processing {len(virtual_results)} virtual meters")

    return virtual_results


@asset(
    group_name="analysis",
    compute_kind="python",
    description="Detect consumption anomalies using statistical methods"
)
def anomaly_detection(
    context: AssetExecutionContext,
    consumption_data: Dict[str, pd.DataFrame],
    virtual_meter_data: Dict[str, pd.DataFrame]
) -> Dict[str, pd.DataFrame]:
    """
    Detect anomalies in consumption data

    Detects consumption values > 2x rolling average

    Returns:
        Dictionary with anomaly DataFrames per meter
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
        if consumption.empty or len(consumption) < 30:  # Need enough data
            continue

        # Calculate rolling average (30-day window)
        rolling_avg = consumption['value'].rolling(window=30, min_periods=1).mean()

        # Find points where consumption > 2x rolling average
        anomaly_mask = consumption['value'] > (2 * rolling_avg)

        if anomaly_mask.any():
            anomaly_points = consumption[anomaly_mask].copy()
            anomaly_points['rolling_avg'] = rolling_avg[anomaly_mask]
            anomaly_points['threshold'] = 2 * rolling_avg[anomaly_mask]
            anomalies[meter_id] = anomaly_points
            total_anomalies += len(anomaly_points)
            logger.info(f"Found {len(anomaly_points)} anomalies for {meter_id}")

    logger.info(f"Total anomalies detected: {total_anomalies}")

    return anomalies
