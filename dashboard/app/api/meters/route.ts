import { NextResponse } from 'next/server';
import { getInfluxClient, getInfluxConfig } from '@/lib/influxdb';

export async function GET() {
  try {
    const influx = getInfluxClient();
    const config = getInfluxConfig();
    const queryApi = influx.getQueryApi(config.org);

    // Query to discover all unique entity_ids in the bucket
    const query = `
      from(bucket: "${config.bucketRaw}")
        |> range(start: -90d)
        |> filter(fn: (r) => r["_measurement"] == "kWh" or r["_measurement"] == "m³")
        |> filter(fn: (r) => r["_field"] == "value")
        |> keep(columns: ["entity_id"])
        |> distinct(column: "entity_id")
    `;

    const meters: string[] = [];

    return new Promise((resolve) => {
      queryApi.queryRows(query, {
        next(row: string[], tableMeta: any) {
          const o = tableMeta.toObject(row);
          if (o.entity_id) {
            meters.push(o.entity_id);
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
