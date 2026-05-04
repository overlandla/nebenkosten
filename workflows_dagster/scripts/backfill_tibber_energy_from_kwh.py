#!/usr/bin/env python3
"""
Backfill Dagster's Tibber energy schema from the legacy cumulative kWh series.

This migrates existing hourly Tibber fields from:
  bucket=lampfi, measurement=kWh, entity_id=haupt_strom, domain=input_number

into:
  bucket=lampfi, measurement=energy, entity_id=haupt_strom, domain=sensor

The script is dry-run by default. It never writes or repairs cumulative kWh/value
readings; it only fills missing energy-schema rows used by dashboard cost views.
"""

import argparse
import os
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Set

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS


DEFAULT_START = "2025-06-04T23:00:00Z"
DEFAULT_BUCKET = "lampfi"
DEFAULT_METER_ID = "haupt_strom"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill missing lampfi.energy rows from lampfi.kWh rows."
    )
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--stop", default="now()")
    parser.add_argument(
        "--bucket", default=os.getenv("INFLUX_BUCKET_RAW", DEFAULT_BUCKET)
    )
    parser.add_argument("--meter-id", default=DEFAULT_METER_ID)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Write points. Without this flag the script only reports what it would do.",
    )
    parser.add_argument(
        "--derive-missing-cost",
        action="store_true",
        help="Set cost=hourly_consumption*unit_price where legacy cost is missing.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional maximum number of points to write, useful for staged rollout.",
    )
    return parser.parse_args()


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def flux_time(value: str) -> str:
    if value == "now()":
        return value
    return normalize_timestamp(value).isoformat().replace("+00:00", "Z")


def normalize_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(
        timezone.utc
    )


def get_existing_energy_times(
    query_api, org: str, bucket: str, meter_id: str, start: str, stop: str
) -> Set[datetime]:
    query = f"""
    from(bucket: "{bucket}")
      |> range(start: {flux_time(start)}, stop: {flux_time(stop)})
      |> filter(fn: (r) => r["_measurement"] == "energy")
      |> filter(fn: (r) => r["entity_id"] == "{meter_id}")
      |> filter(fn: (r) => r["_field"] == "consumption")
      |> keep(columns: ["_time"])
    """
    timestamps = set()
    for table in query_api.query(query, org=org):
        for record in table.records:
            timestamps.add(record.get_time().astimezone(timezone.utc))
    return timestamps


def get_legacy_kwh_rows(
    query_api, org: str, bucket: str, meter_id: str, start: str, stop: str
) -> List[Dict]:
    query = f"""
    from(bucket: "{bucket}")
      |> range(start: {flux_time(start)}, stop: {flux_time(stop)})
      |> filter(fn: (r) => r["_measurement"] == "kWh")
      |> filter(fn: (r) => r["entity_id"] == "{meter_id}")
      |> filter(fn: (r) => r["domain"] == "input_number")
      |> filter(fn: (r) =>
        r["_field"] == "hourly_consumption" or
        r["_field"] == "cost" or
        r["_field"] == "unit_price"
      )
      |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> sort(columns: ["_time"])
    """
    rows = []
    for table in query_api.query(query, org=org):
        for record in table.records:
            values = record.values
            if "hourly_consumption" not in values:
                continue
            rows.append(
                {
                    "timestamp": values["_time"].astimezone(timezone.utc),
                    "consumption": float(values["hourly_consumption"]),
                    "cost": _optional_float(values.get("cost")),
                    "unit_price": _optional_float(values.get("unit_price")),
                }
            )
    return rows


def _optional_float(value) -> Optional[float]:
    if value is None:
        return None
    return float(value)


def build_energy_points(
    rows: Iterable[Dict],
    existing_times: Set[datetime],
    meter_id: str,
    derive_missing_cost: bool,
) -> List[Point]:
    points = []
    for row in rows:
        timestamp = row["timestamp"]
        if timestamp in existing_times:
            continue

        point = (
            Point("energy")
            .tag("entity_id", meter_id)
            .tag("domain", "sensor")
            .field("consumption", row["consumption"])
            .time(timestamp, WritePrecision.NS)
        )

        cost = row["cost"]
        if cost is None and derive_missing_cost and row["unit_price"] is not None:
            cost = row["consumption"] * row["unit_price"]

        if cost is not None:
            point = point.field("cost", cost)
        if row["unit_price"] is not None:
            point = point.field("unit_price", row["unit_price"])

        points.append(point)
    return points


def main() -> int:
    args = parse_args()
    url = os.getenv("INFLUX_URL", "http://192.168.1.75:8086")
    token = require_env("INFLUX_TOKEN")
    org = require_env("INFLUX_ORG")

    with InfluxDBClient(url=url, token=token, org=org, timeout=60000) as client:
        query_api = client.query_api()
        existing_times = get_existing_energy_times(
            query_api, org, args.bucket, args.meter_id, args.start, args.stop
        )
        legacy_rows = get_legacy_kwh_rows(
            query_api, org, args.bucket, args.meter_id, args.start, args.stop
        )
        points = build_energy_points(
            legacy_rows, existing_times, args.meter_id, args.derive_missing_cost
        )

        if args.limit > 0:
            points = points[: args.limit]

        print(f"bucket={args.bucket}")
        print(f"meter_id={args.meter_id}")
        print(f"range={args.start}..{args.stop}")
        print(f"legacy_rows={len(legacy_rows)}")
        print(f"existing_energy_rows={len(existing_times)}")
        print(f"missing_energy_rows={len(points)}")
        print(f"derive_missing_cost={args.derive_missing_cost}")
        print(f"mode={'execute' if args.execute else 'dry-run'}")

        if not args.execute:
            return 0

        if points:
            write_api = client.write_api(write_options=SYNCHRONOUS)
            write_api.write(bucket=args.bucket, org=org, record=points)
        print(f"written={len(points)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
