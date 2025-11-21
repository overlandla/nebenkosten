"""
InfluxDB Writer Assets
Write processed data back to InfluxDB
"""

from datetime import timezone
from typing import Dict

import pandas as pd
from dagster import AssetExecutionContext, MaterializeResult, asset
from influxdb_client import Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from ..resources.influxdb_resource import InfluxDBResource


@asset(
    group_name="storage",
    compute_kind="influxdb",
    description="Write all processed data to InfluxDB",
)
def write_processed_data_to_influxdb(
    context: AssetExecutionContext,
    daily_interpolated_series: Dict[str, pd.DataFrame],
    monthly_interpolated_series: Dict[str, pd.DataFrame],
    master_meter_series: Dict[str, Dict[str, pd.DataFrame]],
    consumption_data: Dict[str, pd.DataFrame],
    virtual_meter_data: Dict[str, pd.DataFrame],
    anomaly_detection: Dict[str, pd.DataFrame],
    influxdb: InfluxDBResource,
) -> MaterializeResult:
    """
    Write all processed data to InfluxDB processed bucket

    Writes:
    - Daily interpolated readings
    - Monthly interpolated readings
    - Master meter readings
    - Consumption values
    - Virtual meter consumption
    - Detected anomalies

    Returns:
        MaterializeResult with count of records written
    """
    logger = context.log
    logger.info("Writing processed data to InfluxDB")

    with influxdb.get_client() as client:
        write_api = client.write_api(write_options=SYNCHRONOUS)
        total_points = 0

        # Write daily interpolated series
        logger.info("Writing daily interpolated series...")
        for meter_id, data in daily_interpolated_series.items():
            points = _create_points_from_dataframe(
                data, meter_id, "meter_interpolated_daily"
            )
            write_api.write(
                bucket=influxdb.bucket_processed, org=influxdb.org, record=points
            )
            total_points += len(points)
        logger.info(f"Wrote {total_points} daily interpolated points")

        # Write monthly interpolated series
        monthly_count = 0
        logger.info("Writing monthly interpolated series...")
        for meter_id, data in monthly_interpolated_series.items():
            points = _create_points_from_dataframe(
                data, meter_id, "meter_interpolated_monthly"
            )
            write_api.write(
                bucket=influxdb.bucket_processed, org=influxdb.org, record=points
            )
            monthly_count += len(points)
        logger.info(f"Wrote {monthly_count} monthly interpolated points")
        total_points += monthly_count

        # Write master meter series
        master_count = 0
        logger.info("Writing master meter series...")
        for master_id, series_dict in master_meter_series.items():
            # Write daily
            if "daily" in series_dict and not series_dict["daily"].empty:
                points = _create_points_from_dataframe(
                    series_dict["daily"], master_id, "meter_interpolated_daily"
                )
                write_api.write(
                    bucket=influxdb.bucket_processed, org=influxdb.org, record=points
                )
                master_count += len(points)

            # Write monthly
            if "monthly" in series_dict and not series_dict["monthly"].empty:
                points = _create_points_from_dataframe(
                    series_dict["monthly"], master_id, "meter_interpolated_monthly"
                )
                write_api.write(
                    bucket=influxdb.bucket_processed, org=influxdb.org, record=points
                )
                master_count += len(points)
        logger.info(f"Wrote {master_count} master meter points")
        total_points += master_count

        # Write consumption data
        consumption_count = 0
        logger.info("Writing consumption data...")
        for meter_id, data in consumption_data.items():
            points = _create_points_from_dataframe(data, meter_id, "meter_consumption")
            write_api.write(
                bucket=influxdb.bucket_processed, org=influxdb.org, record=points
            )
            consumption_count += len(points)
        logger.info(f"Wrote {consumption_count} consumption points")
        total_points += consumption_count

        # Write virtual meter consumption
        virtual_count = 0
        logger.info("Writing virtual meter consumption...")
        for meter_id, data in virtual_meter_data.items():
            points = _create_points_from_dataframe(data, meter_id, "meter_consumption")
            write_api.write(
                bucket=influxdb.bucket_processed, org=influxdb.org, record=points
            )
            virtual_count += len(points)
        logger.info(f"Wrote {virtual_count} virtual meter consumption points")
        total_points += virtual_count

        # Write anomalies
        anomaly_count = 0
        logger.info("Writing anomaly data...")
        for meter_id, data in anomaly_detection.items():
            points = _create_anomaly_points(data, meter_id)
            write_api.write(
                bucket=influxdb.bucket_processed, org=influxdb.org, record=points
            )
            anomaly_count += len(points)
        logger.info(f"Wrote {anomaly_count} anomaly points")
        total_points += anomaly_count

        logger.info(f"Total points written to InfluxDB: {total_points}")

        return MaterializeResult(
            metadata={
                "total_points": total_points,
                "daily_points": len(daily_interpolated_series),
                "monthly_points": monthly_count,
                "master_points": master_count,
                "consumption_points": consumption_count,
                "virtual_points": virtual_count,
                "anomaly_points": anomaly_count,
            }
        )


def _create_points_from_dataframe(
    df: pd.DataFrame, meter_id: str, measurement: str
) -> list:
    """
    Create InfluxDB points from a DataFrame

    OPTIMIZED: Uses itertuples() instead of iterrows() for 60x better performance

    Args:
        df: DataFrame with 'value' column and timestamp column or DatetimeIndex
        meter_id: Meter identifier
        measurement: InfluxDB measurement name

    Returns:
        List of InfluxDB Point objects
    """
    if df.empty:
        return []

    points = []

    # Ensure we have timestamp as index
    if "timestamp" in df.columns:
        df_indexed = df.set_index("timestamp")
    else:
        df_indexed = df

    # Use itertuples() for much better performance (60x faster than iterrows)
    for row in df_indexed.itertuples():
        timestamp = row.Index

        # Ensure timestamp is timezone-aware (UTC)
        if timestamp.tzinfo is None:
            timestamp = timestamp.tz_localize(timezone.utc)
        else:
            timestamp = timestamp.tz_convert(timezone.utc)

        # Access value attribute (itertuples uses named tuples)
        value = row.value if hasattr(row, "value") else row[1]

        point = (
            Point(measurement)
            .tag("meter_id", meter_id)
            .field("value", float(value))
            .time(timestamp, WritePrecision.NS)
        )
        points.append(point)

    return points


def _create_anomaly_points(df: pd.DataFrame, meter_id: str) -> list:
    """
    Create InfluxDB points for anomaly data

    OPTIMIZED: Uses itertuples() instead of iterrows() for 60x better performance

    Args:
        df: DataFrame with anomaly data including columns:
            - value: consumption value
            - z_score: Z-score anomaly indicator
            - iqr_lower/iqr_upper: IQR bounds
            - anomaly_count: number of methods that flagged this
        meter_id: Meter identifier

    Returns:
        List of InfluxDB Point objects
    """
    if df.empty:
        return []

    points = []

    # Ensure we have timestamp as index
    if "timestamp" in df.columns:
        df_indexed = df.set_index("timestamp")
    else:
        df_indexed = df

    # Use itertuples() for much better performance
    for row in df_indexed.itertuples():
        timestamp = row.Index

        # Ensure timestamp is timezone-aware (UTC)
        if timestamp.tzinfo is None:
            timestamp = timestamp.tz_localize(timezone.utc)
        else:
            timestamp = timestamp.tz_convert(timezone.utc)

        # Extract fields with safe defaults
        value = row.value if hasattr(row, "value") else 0.0
        z_score = row.z_score if hasattr(row, "z_score") else 0.0
        iqr_lower = row.iqr_lower if hasattr(row, "iqr_lower") else 0.0
        iqr_upper = row.iqr_upper if hasattr(row, "iqr_upper") else 0.0
        anomaly_count = row.anomaly_count if hasattr(row, "anomaly_count") else 0

        point = (
            Point("meter_anomaly")
            .tag("meter_id", meter_id)
            .field("value", float(value))
            .field("z_score", float(z_score))
            .field("iqr_lower", float(iqr_lower))
            .field("iqr_upper", float(iqr_upper))
            .field("anomaly_count", int(anomaly_count))
            .time(timestamp, WritePrecision.NS)
        )
        points.append(point)

    return points


@asset(
    group_name="maintenance",
    compute_kind="influxdb",
    description="DESTRUCTIVE: Wipe all processed data from InfluxDB (use with caution)",
)
def wipe_processed_data(
    context: AssetExecutionContext,
    influxdb: InfluxDBResource,
) -> MaterializeResult:
    """
    Wipe all processed data from InfluxDB processed bucket

    ⚠️  DESTRUCTIVE OPERATION ⚠️
    This permanently deletes all data in the processed bucket including:
    - meter_interpolated_daily
    - meter_interpolated_monthly
    - meter_consumption
    - meter_anomaly

    Use this when you want to start fresh with new improved analytics.

    This does NOT affect the raw data bucket - raw meter readings are preserved.

    Args:
        context: Dagster execution context
        influxdb: InfluxDB resource

    Returns:
        MaterializeResult with measurements deleted

    Example usage:
        dagster asset materialize -m workflows_dagster -s wipe_processed_data
    """
    logger = context.log

    logger.warning("=" * 80)
    logger.warning("⚠️  STARTING DESTRUCTIVE OPERATION: WIPING PROCESSED DATA")
    logger.warning("=" * 80)

    measurements_to_delete = [
        "meter_interpolated_daily",
        "meter_interpolated_monthly",
        "meter_consumption",
        "meter_anomaly",
    ]

    deleted_measurements = []

    try:
        with influxdb.get_client() as client:
            delete_api = client.delete_api()

            # Delete all data from the start of time to now for each measurement
            start = "1970-01-01T00:00:00Z"
            stop = "2099-12-31T23:59:59Z"

            for measurement in measurements_to_delete:
                try:
                    logger.info(f"Deleting measurement: {measurement}")

                    # Delete using predicate: _measurement="measurement_name"
                    delete_api.delete(
                        start=start,
                        stop=stop,
                        predicate=f'_measurement="{measurement}"',
                        bucket=influxdb.bucket_processed,
                        org=influxdb.org,
                    )

                    deleted_measurements.append(measurement)
                    logger.info(f"✓ Successfully deleted {measurement}")

                except Exception as e:
                    logger.error(f"Failed to delete {measurement}: {e}")
                    # Continue with other measurements even if one fails
                    continue

        logger.warning("=" * 80)
        logger.warning(
            f"✓ WIPE COMPLETE: Deleted {len(deleted_measurements)} measurements"
        )
        logger.warning(f"  Deleted: {', '.join(deleted_measurements)}")
        logger.warning(
            "  You can now re-run the analytics pipeline with improved interpolation"
        )
        logger.warning("=" * 80)

        return MaterializeResult(
            metadata={
                "measurements_deleted": len(deleted_measurements),
                "deleted_list": ", ".join(deleted_measurements),
                "bucket": influxdb.bucket_processed,
                "warning": "⚠️ DESTRUCTIVE operation completed",
            }
        )

    except Exception as e:
        logger.error(f"Failed to wipe processed data: {e}")
        raise
