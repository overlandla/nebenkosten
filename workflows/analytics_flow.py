"""
Analytics Flow
Main workflow for processing utility meter data with Prefect orchestration
"""
from prefect import flow, task, get_run_logger
from prefect.task_runners import ConcurrentTaskRunner
import sys
import os
from pathlib import Path
from typing import Dict, List, Any
import pandas as pd
from datetime import datetime, timedelta

# Add parent directory to path to import existing modules
sys.path.insert(0, str(Path(__file__).parent.parent / "Nebenkosten"))

from src.influx_client import InfluxClient
from src.data_processor import DataProcessor
from src.calculator import ConsumptionCalculator


@task(name="Discover Available Meters", retries=2, retry_delay_seconds=30)
def discover_meters(config: Dict) -> List[str]:
    """Discover all available meters in InfluxDB"""
    logger = get_run_logger()
    logger.info("Discovering available meters from InfluxDB...")

    influx_client = InfluxClient(
        url=config["influxdb"]["url"],
        token=config["influx_token"],
        org=config["influx_org"],
        bucket=config["influxdb"]["bucket_raw"]
    )

    meters = influx_client.discover_available_meters()
    logger.info(f"Found {len(meters)} physical meters: {meters}")

    return meters


@task(name="Fetch Raw Meter Data", retries=2, retry_delay_seconds=30)
def fetch_raw_data(meter_id: str, config: Dict, start_date: datetime) -> pd.DataFrame:
    """Fetch raw data for a specific meter"""
    logger = get_run_logger()
    logger.info(f"Fetching raw data for {meter_id}")

    influx_client = InfluxClient(
        url=config["influxdb"]["url"],
        token=config["influx_token"],
        org=config["influx_org"],
        bucket=config["influxdb"]["bucket_raw"]
    )

    data = influx_client.fetch_all_meter_data(meter_id, start_date)
    logger.info(f"Fetched {len(data)} data points for {meter_id}")

    return data


@task(name="Create Standardized Daily Series")
def create_daily_series(
    meter_id: str,
    raw_data: pd.DataFrame,
    config: Dict,
    start_date_str: str,
    end_date_str: str
) -> pd.DataFrame:
    """Create standardized daily reading series"""
    logger = get_run_logger()
    logger.info(f"Creating daily series for {meter_id}")

    influx_client = InfluxClient(
        url=config["influxdb"]["url"],
        token=config["influx_token"],
        org=config["influx_org"],
        bucket=config["influxdb"]["bucket_raw"]
    )

    # Pre-populate cache with raw data
    influx_client.meter_data_cache[meter_id] = raw_data

    data_processor = DataProcessor(influx_client)
    daily_series = data_processor.create_standardized_daily_series(
        meter_id,
        start_date_str,
        end_date_str
    )

    logger.info(f"Created {len(daily_series)} daily points for {meter_id}")

    return daily_series


@task(name="Aggregate to Monthly")
def aggregate_to_monthly(meter_id: str, daily_series: pd.DataFrame, config: Dict) -> pd.DataFrame:
    """Aggregate daily series to monthly"""
    logger = get_run_logger()
    logger.info(f"Aggregating {meter_id} to monthly")

    influx_client = InfluxClient(
        url=config["influxdb"]["url"],
        token=config["influx_token"],
        org=config["influx_org"],
        bucket=config["influxdb"]["bucket_raw"]
    )

    data_processor = DataProcessor(influx_client)
    monthly_series = data_processor.aggregate_daily_to_frequency(daily_series, 'M')

    logger.info(f"Created {len(monthly_series)} monthly points for {meter_id}")

    return monthly_series


@task(name="Process Master Meter")
def process_master_meter(
    master_config: Dict,
    daily_readings: Dict[str, pd.DataFrame],
    monthly_readings: Dict[str, pd.DataFrame],
    config: Dict
) -> Dict[str, pd.DataFrame]:
    """Process master meter by combining source meters across periods"""
    logger = get_run_logger()
    master_id = master_config["meter_id"]
    logger.info(f"Processing master meter: {master_id}")

    gas_conversion_factor = (
        config["gas_conversion"]["energy_content"] *
        config["gas_conversion"]["z_factor"]
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

    # Process periods for both daily and monthly
    result = {"daily": pd.DataFrame(), "monthly": pd.DataFrame()}

    for freq_label, readings_dict in [("daily", daily_readings), ("monthly", monthly_readings)]:
        segments = []
        last_segment = None

        for period_idx, period in enumerate(master_config["periods"]):
            logger.info(f"  Period {period_idx + 1}: {period['start_date']} to {period['end_date']}")

            # Get source meter data
            source_series = []
            for src_id in period["source_meters"]:
                if src_id not in readings_dict:
                    logger.warning(f"    Source meter {src_id} not found")
                    continue

                src_series = readings_dict[src_id]

                # Convert units if needed
                converted = convert_series(
                    src_series,
                    period["source_unit"],
                    master_config["output_unit"]
                )

                source_series.append(converted)

            if not source_series:
                logger.warning(f"    No valid source meters for period {period_idx + 1}")
                continue

            # Compose period data
            if period["composition_type"] == "single":
                period_data = source_series[0]
            elif period["composition_type"] == "sum":
                # Sum all source meters
                indexed = [s.set_index('timestamp')[['value']] for s in source_series]
                period_data = pd.concat(indexed, axis=1).sum(axis=1).to_frame(name='value').reset_index()
            else:
                logger.warning(f"    Unknown composition type: {period['composition_type']}")
                continue

            # Filter to period date range
            period_start = pd.Timestamp(period["start_date"], tz='UTC')
            period_end = pd.Timestamp(period["end_date"], tz='UTC')
            period_data = period_data[
                (period_data['timestamp'] >= period_start) &
                (period_data['timestamp'] <= period_end)
            ]

            # Apply offset if requested
            if period.get("apply_offset_from_previous_period") and last_segment is not None:
                if not last_segment.empty and not period_data.empty:
                    offset = last_segment.iloc[-1]["value"] - period_data.iloc[0]["value"]
                    period_data = period_data.copy()
                    period_data["value"] = period_data["value"] + offset
                    logger.info(f"    Applied offset: {offset:.2f}")

            segments.append(period_data)
            last_segment = period_data

        # Concatenate all period segments
        if segments:
            result[freq_label] = pd.concat(segments, ignore_index=True).sort_values('timestamp')
            logger.info(f"  Master meter {master_id} ({freq_label}): {len(result[freq_label])} points")

    return result


@task(name="Calculate Consumption")
def calculate_consumption(meter_id: str, monthly_series: pd.DataFrame, config: Dict) -> pd.DataFrame:
    """Calculate consumption from monthly readings"""
    logger = get_run_logger()
    logger.info(f"Calculating consumption for {meter_id}")

    calculator = ConsumptionCalculator()
    consumption = calculator.calculate_period_consumption(monthly_series)

    logger.info(f"Calculated {len(consumption)} consumption values for {meter_id}")

    return consumption


@task(name="Process Virtual Meter")
def process_virtual_meter(
    virtual_config: Dict,
    consumption_data: Dict[str, pd.DataFrame],
    config: Dict
) -> pd.DataFrame:
    """Calculate virtual meter by subtracting other meters from base"""
    logger = get_run_logger()
    vm_id = virtual_config["meter_id"]
    logger.info(f"Processing virtual meter: {vm_id}")

    base_meter = virtual_config["base_meter"]
    subtract_meters = virtual_config.get("subtract_meters", [])

    if base_meter not in consumption_data:
        logger.warning(f"  Base meter {base_meter} not found")
        return pd.DataFrame()

    # Start with base consumption
    result = consumption_data[base_meter].copy()

    # Subtract each meter
    for sub_meter in subtract_meters:
        if sub_meter not in consumption_data:
            logger.warning(f"  Subtract meter {sub_meter} not found")
            continue

        sub_data = consumption_data[sub_meter]

        # Handle unit conversion if needed
        conversions = virtual_config.get("subtract_meter_conversions", {})
        if sub_meter in conversions:
            conv = conversions[sub_meter]
            from_unit = conv["from_unit"]
            to_unit = conv["to_unit"]

            if from_unit != to_unit:
                gas_conversion = (
                    config["gas_conversion"]["energy_content"] *
                    config["gas_conversion"]["z_factor"]
                )

                if from_unit.lower() == 'kwh' and to_unit.lower() == 'm³':
                    sub_data = sub_data.copy()
                    sub_data['consumption'] = sub_data['consumption'] / gas_conversion
                    logger.info(f"  Converted {sub_meter} from {from_unit} to {to_unit}")

        # Merge and subtract
        result = result.merge(
            sub_data[['timestamp', 'consumption']],
            on='timestamp',
            how='left',
            suffixes=('', f'_{sub_meter}')
        )
        result['consumption'] = result['consumption'] - result[f'consumption_{sub_meter}'].fillna(0)
        result = result[['timestamp', 'consumption']]

    # Clip to non-negative
    result['consumption'] = result['consumption'].clip(lower=0)

    logger.info(f"Virtual meter {vm_id}: {len(result)} consumption values")

    return result


@task(name="Detect Anomalies")
def detect_anomalies(meter_id: str, consumption: pd.DataFrame, threshold_multiplier: float = 2.0) -> List[Dict]:
    """Detect consumption anomalies"""
    logger = get_run_logger()

    if consumption.empty:
        return []

    # Calculate rolling average
    consumption = consumption.sort_values('timestamp')
    rolling_avg = consumption['consumption'].rolling(window=7, min_periods=1).mean()
    threshold = rolling_avg * threshold_multiplier

    # Find anomalies
    anomalies = consumption[consumption['consumption'] > threshold]

    if len(anomalies) > 0:
        logger.warning(f"Found {len(anomalies)} anomalies for {meter_id}")
        return anomalies.to_dict('records')
    else:
        logger.info(f"No anomalies detected for {meter_id}")
        return []


@task(name="Write Results to InfluxDB", retries=2, retry_delay_seconds=30)
def write_results(
    meter_id: str,
    daily_series: pd.DataFrame,
    monthly_series: pd.DataFrame,
    consumption: pd.DataFrame,
    anomalies: List[Dict],
    config: Dict
) -> int:
    """Write processed results to InfluxDB"""
    logger = get_run_logger()
    logger.info(f"Writing results for {meter_id} to InfluxDB")

    from influxdb_client import InfluxDBClient, Point, WritePrecision
    from influxdb_client.client.write_api import SYNCHRONOUS

    points_written = 0

    with InfluxDBClient(
        url=config["influxdb"]["url"],
        token=config["influx_token"],
        org=config["influx_org"]
    ) as client:
        write_api = client.write_api(write_options=SYNCHRONOUS)
        bucket = config["influxdb"]["bucket_processed"]

        # Write daily interpolated series
        if not daily_series.empty:
            points = []
            for _, row in daily_series.iterrows():
                p = (
                    Point("meter_interpolated_daily")
                    .tag("meter_id", meter_id)
                    .field("value", float(row["value"]))
                    .time(row["timestamp"], WritePrecision.NS)
                )
                points.append(p)

            write_api.write(bucket=bucket, record=points)
            points_written += len(points)
            logger.info(f"  Wrote {len(points)} daily interpolated points")

        # Write monthly interpolated series
        if not monthly_series.empty:
            points = []
            for _, row in monthly_series.iterrows():
                p = (
                    Point("meter_interpolated_monthly")
                    .tag("meter_id", meter_id)
                    .field("value", float(row["value"]))
                    .time(row["timestamp"], WritePrecision.NS)
                )
                points.append(p)

            write_api.write(bucket=bucket, record=points)
            points_written += len(points)
            logger.info(f"  Wrote {len(points)} monthly interpolated points")

        # Write consumption
        if not consumption.empty:
            points = []
            for _, row in consumption.iterrows():
                p = (
                    Point("meter_consumption")
                    .tag("meter_id", meter_id)
                    .field("consumption", float(row["consumption"]))
                    .time(row["timestamp"], WritePrecision.NS)
                )
                points.append(p)

            write_api.write(bucket=bucket, record=points)
            points_written += len(points)
            logger.info(f"  Wrote {len(points)} consumption points")

        # Write anomalies
        if anomalies:
            points = []
            for anomaly in anomalies:
                p = (
                    Point("meter_anomaly")
                    .tag("meter_id", meter_id)
                    .field("consumption", float(anomaly["consumption"]))
                    .field("severity", "warning")
                    .time(anomaly["timestamp"], WritePrecision.NS)
                )
                points.append(p)

            write_api.write(bucket=bucket, record=points)
            points_written += len(points)
            logger.info(f"  Wrote {len(points)} anomaly records")

    logger.info(f"Total points written for {meter_id}: {points_written}")
    return points_written


@flow(name="Daily Analytics", task_runner=ConcurrentTaskRunner(), log_prints=True)
def analytics_flow(config: Dict) -> Dict[str, Any]:
    """
    Main analytics workflow

    Args:
        config: Full configuration dictionary

    Returns:
        Summary of processing results
    """
    logger = get_run_logger()
    logger.info("=" * 60)
    logger.info("Starting Daily Analytics Flow")
    logger.info("=" * 60)

    start_year = config["workflows"]["analytics"]["start_year"]
    start_date = datetime(start_year, 1, 1, tzinfo=pd.Timestamp.now().tz)
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = (datetime.now().date() + timedelta(days=1)).strftime('%Y-%m-%d')

    logger.info(f"Processing date range: {start_date_str} to {end_date_str}")

    # Step 1: Discover meters
    physical_meters = discover_meters(config)

    # Step 2: Fetch raw data for all physical meters (in parallel)
    logger.info(f"Fetching raw data for {len(physical_meters)} physical meters...")
    raw_data_futures = {}
    for meter in physical_meters:
        future = fetch_raw_data.submit(meter, config, start_date)
        raw_data_futures[meter] = future

    # Wait for all fetches to complete
    raw_data = {meter: future.result() for meter, future in raw_data_futures.items()}

    # Step 3: Create daily series for all meters (in parallel)
    logger.info("Creating daily series...")
    daily_futures = {}
    for meter, data in raw_data.items():
        if not data.empty:
            future = create_daily_series.submit(meter, data, config, start_date_str, end_date_str)
            daily_futures[meter] = future

    daily_readings = {meter: future.result() for meter, future in daily_futures.items()}

    # Step 4: Aggregate to monthly (in parallel)
    logger.info("Aggregating to monthly...")
    monthly_futures = {}
    for meter, daily in daily_readings.items():
        if not daily.empty:
            future = aggregate_to_monthly.submit(meter, daily, config)
            monthly_futures[meter] = future

    monthly_readings = {meter: future.result() for meter, future in monthly_futures.items()}

    # Step 5: Process master meters
    master_meters = [m for m in config["meters"] if m["type"] == "master"]
    logger.info(f"Processing {len(master_meters)} master meters...")

    for master in master_meters:
        master_result = process_master_meter(master, daily_readings, monthly_readings, config)
        daily_readings[master["meter_id"]] = master_result["daily"]
        monthly_readings[master["meter_id"]] = master_result["monthly"]

    # Step 6: Calculate consumption for all meters (in parallel)
    logger.info("Calculating consumption...")
    consumption_futures = {}
    for meter, monthly in monthly_readings.items():
        if not monthly.empty:
            future = calculate_consumption.submit(meter, monthly, config)
            consumption_futures[meter] = future

    consumption_data = {meter: future.result() for meter, future in consumption_futures.items()}

    # Step 7: Process virtual meters
    virtual_meters = [m for m in config["meters"] if m["type"] == "virtual"]
    logger.info(f"Processing {len(virtual_meters)} virtual meters...")

    for virtual in virtual_meters:
        vm_consumption = process_virtual_meter(virtual, consumption_data, config)
        if not vm_consumption.empty:
            consumption_data[virtual["meter_id"]] = vm_consumption

            # Create pseudo-readings for virtual meters (cumulative consumption)
            vm_readings = vm_consumption.copy()
            vm_readings["value"] = vm_readings["consumption"].cumsum()
            monthly_readings[virtual["meter_id"]] = vm_readings[["timestamp", "value"]]

    # Step 8: Detect anomalies (in parallel)
    logger.info("Detecting anomalies...")
    anomaly_futures = {}
    for meter, consumption in consumption_data.items():
        future = detect_anomalies.submit(meter, consumption)
        anomaly_futures[meter] = future

    anomalies = {meter: future.result() for meter, future in anomaly_futures.items()}

    # Step 9: Write results to InfluxDB (in parallel)
    logger.info("Writing results to InfluxDB...")
    write_futures = {}
    for meter in consumption_data.keys():
        future = write_results.submit(
            meter,
            daily_readings.get(meter, pd.DataFrame()),
            monthly_readings.get(meter, pd.DataFrame()),
            consumption_data.get(meter, pd.DataFrame()),
            anomalies.get(meter, []),
            config
        )
        write_futures[meter] = future

    points_written = {meter: future.result() for meter, future in write_futures.items()}

    # Summary
    total_points = sum(points_written.values())
    total_anomalies = sum(len(a) for a in anomalies.values())

    logger.info("=" * 60)
    logger.info("Analytics Flow Completed")
    logger.info(f"Meters processed: {len(consumption_data)}")
    logger.info(f"Total points written: {total_points}")
    logger.info(f"Total anomalies detected: {total_anomalies}")
    logger.info("=" * 60)

    return {
        "meters_processed": len(consumption_data),
        "points_written": total_points,
        "anomalies_detected": total_anomalies,
        "anomalies_by_meter": {m: len(a) for m, a in anomalies.items() if a}
    }


if __name__ == "__main__":
    # For local testing
    from config_loader import get_config_loader
    from logging_config import setup_logging

    # Load configuration
    config_loader = get_config_loader()
    config = config_loader.get_full_config()

    # Setup logging
    setup_logging(config)

    # Run flow
    result = analytics_flow(config)
    print(f"Result: {result}")
