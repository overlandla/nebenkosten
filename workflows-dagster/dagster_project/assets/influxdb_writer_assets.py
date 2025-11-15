"""
InfluxDB Writer Assets
Write processed data back to InfluxDB
"""
from typing import Dict
import pandas as pd
from datetime import timezone
from dagster import asset, AssetExecutionContext, MaterializeResult
from influxdb_client import Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from ..resources.influxdb_resource import InfluxDBResource


@asset(
    group_name="storage",
    compute_kind="influxdb",
    description="Write all processed data to InfluxDB",
    deps=[
        "daily_interpolated_series",
        "monthly_interpolated_series",
        "master_meter_series",
        "consumption_data",
        "virtual_meter_data",
        "anomaly_detection"
    ]
)
def write_processed_data_to_influxdb(
    context: AssetExecutionContext,
    daily_interpolated_series: Dict[str, pd.DataFrame],
    monthly_interpolated_series: Dict[str, pd.DataFrame],
    master_meter_series: Dict[str, Dict[str, pd.DataFrame]],
    consumption_data: Dict[str, pd.DataFrame],
    virtual_meter_data: Dict[str, pd.DataFrame],
    anomaly_detection: Dict[str, pd.DataFrame],
    influxdb: InfluxDBResource
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
                bucket=influxdb.bucket_processed,
                org=influxdb.org,
                record=points
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
                bucket=influxdb.bucket_processed,
                org=influxdb.org,
                record=points
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
                    bucket=influxdb.bucket_processed,
                    org=influxdb.org,
                    record=points
                )
                master_count += len(points)

            # Write monthly
            if "monthly" in series_dict and not series_dict["monthly"].empty:
                points = _create_points_from_dataframe(
                    series_dict["monthly"], master_id, "meter_interpolated_monthly"
                )
                write_api.write(
                    bucket=influxdb.bucket_processed,
                    org=influxdb.org,
                    record=points
                )
                master_count += len(points)
        logger.info(f"Wrote {master_count} master meter points")
        total_points += master_count

        # Write consumption data
        consumption_count = 0
        logger.info("Writing consumption data...")
        for meter_id, data in consumption_data.items():
            points = _create_points_from_dataframe(
                data, meter_id, "meter_consumption"
            )
            write_api.write(
                bucket=influxdb.bucket_processed,
                org=influxdb.org,
                record=points
            )
            consumption_count += len(points)
        logger.info(f"Wrote {consumption_count} consumption points")
        total_points += consumption_count

        # Write virtual meter consumption
        virtual_count = 0
        logger.info("Writing virtual meter consumption...")
        for meter_id, data in virtual_meter_data.items():
            points = _create_points_from_dataframe(
                data, meter_id, "meter_consumption"
            )
            write_api.write(
                bucket=influxdb.bucket_processed,
                org=influxdb.org,
                record=points
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
                bucket=influxdb.bucket_processed,
                org=influxdb.org,
                record=points
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
                "anomaly_points": anomaly_count
            }
        )


def _create_points_from_dataframe(
    df: pd.DataFrame,
    meter_id: str,
    measurement: str
) -> list:
    """
    Create InfluxDB points from a DataFrame

    Args:
        df: DataFrame with 'value' column and DatetimeIndex
        meter_id: Meter identifier
        measurement: InfluxDB measurement name

    Returns:
        List of InfluxDB Point objects
    """
    points = []

    for timestamp, row in df.iterrows():
        # Ensure timestamp is timezone-aware (UTC)
        if timestamp.tzinfo is None:
            timestamp = timestamp.tz_localize(timezone.utc)
        else:
            timestamp = timestamp.tz_convert(timezone.utc)

        point = (
            Point(measurement)
            .tag("meter_id", meter_id)
            .field("value", float(row['value']))
            .time(timestamp, WritePrecision.NS)
        )
        points.append(point)

    return points


def _create_anomaly_points(df: pd.DataFrame, meter_id: str) -> list:
    """
    Create InfluxDB points for anomaly data

    Args:
        df: DataFrame with anomaly data
        meter_id: Meter identifier

    Returns:
        List of InfluxDB Point objects
    """
    points = []

    for timestamp, row in df.iterrows():
        # Ensure timestamp is timezone-aware (UTC)
        if timestamp.tzinfo is None:
            timestamp = timestamp.tz_localize(timezone.utc)
        else:
            timestamp = timestamp.tz_convert(timezone.utc)

        point = (
            Point("meter_anomaly")
            .tag("meter_id", meter_id)
            .field("value", float(row['value']))
            .field("rolling_avg", float(row.get('rolling_avg', 0)))
            .field("threshold", float(row.get('threshold', 0)))
            .time(timestamp, WritePrecision.NS)
        )
        points.append(point)

    return points
