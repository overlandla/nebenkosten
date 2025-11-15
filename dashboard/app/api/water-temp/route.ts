import { NextRequest, NextResponse } from 'next/server';
import { getInfluxClient, getInfluxConfig } from '@/lib/influxdb';

export async function GET(request: NextRequest): Promise<NextResponse> {
  try {
    const searchParams = request.nextUrl.searchParams;
    const startDate = searchParams.get('startDate') || '-90d';
    const endDate = searchParams.get('endDate') || 'now()';

    const influx = getInfluxClient();
    const config = getInfluxConfig();
    const queryApi = influx.getQueryApi(config.org);

    // Query for water temperature data
    const query = `
      from(bucket: "${config.bucketRaw}")
        |> range(start: ${startDate}, stop: ${endDate})
        |> filter(fn: (r) => r["_measurement"] == "°C")
        |> filter(fn: (r) => r["_field"] == "value")
        |> filter(fn: (r) => r["lake"] != "")
        |> sort(columns: ["_time"])
    `;

    const temperatures: any[] = [];

    return new Promise<NextResponse>((resolve) => {
      queryApi.queryRows(query, {
        next(row: string[], tableMeta: any) {
          const o = tableMeta.toObject(row);
          temperatures.push({
            timestamp: o._time,
            value: parseFloat(o._value),
            lake: o.lake,
            entity_id: o.entity_id,
          });
        },
        error(error: Error) {
          console.error('Query error:', error);
          resolve(NextResponse.json({ error: error.message }, { status: 500 }));
        },
        complete() {
          resolve(NextResponse.json({ temperatures }));
        },
      });
    });
  } catch (error) {
    console.error('Error fetching water temperatures:', error);
    return NextResponse.json(
      { error: 'Failed to fetch water temperatures' },
      { status: 500 }
    );
  }
}
