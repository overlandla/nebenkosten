import { NextResponse } from 'next/server';
import { getInfluxClient, getInfluxConfig } from '@/lib/influxdb';

export async function GET(): Promise<NextResponse> {
  try {
    const influx = getInfluxClient();
    const config = getInfluxConfig();
    const queryApi = influx.getQueryApi(config.org);

    // Query to discover all unique meter_ids from processed bucket
    // This includes physical, master, and virtual meters
    const query = `
      from(bucket: "${config.bucketProcessed}")
        |> range(start: -90d)
        |> filter(fn: (r) => r["_measurement"] == "meter_consumption" or r["_measurement"] == "meter_interpolated_daily")
        |> filter(fn: (r) => r["_field"] == "value")
        |> keep(columns: ["meter_id"])
        |> distinct(column: "meter_id")
    `;

    const meters: string[] = [];

    return new Promise<NextResponse>((resolve) => {
      queryApi.queryRows(query, {
        next(row: string[], tableMeta: any) {
          const o = tableMeta.toObject(row);
          if (o.meter_id) {
            meters.push(o.meter_id);
          }
        },
        error(error: Error) {
          console.error('Query error:', error);
          resolve(NextResponse.json({ error: error.message }, { status: 500 }));
        },
        complete() {
          resolve(NextResponse.json({ meters: meters.sort() }));
        },
      });
    });
  } catch (error) {
    console.error('Error discovering meters:', error);
    return NextResponse.json(
      { error: 'Failed to discover meters' },
      { status: 500 }
    );
  }
}
