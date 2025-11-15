import { NextRequest, NextResponse } from 'next/server';
import { getInfluxClient, getInfluxConfig, MeterReading } from '@/lib/influxdb';

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const meterId = searchParams.get('meterId');
    const startDate = searchParams.get('startDate');
    const endDate = searchParams.get('endDate');
    const interpolated = searchParams.get('interpolated') === 'true';

    if (!meterId) {
      return NextResponse.json({ error: 'meterId is required' }, { status: 400 });
    }

    const influx = getInfluxClient();
    const config = getInfluxConfig();
    const queryApi = influx.getQueryApi(config.org);

    // Default to last 90 days if not specified
    const start = startDate || '-90d';
    const end = endDate || 'now()';

    // Query for meter readings
    const query = `
      from(bucket: "${config.bucketRaw}")
        |> range(start: ${start}, stop: ${end})
        |> filter(fn: (r) => r["entity_id"] == "${meterId}")
        |> filter(fn: (r) => r["_field"] == "value")
        |> sort(columns: ["_time"])
    `;

    const readings: MeterReading[] = [];

    return new Promise((resolve) => {
      queryApi.queryRows(query, {
        next(row: string[], tableMeta: any) {
          const o = tableMeta.toObject(row);
          readings.push({
            timestamp: o._time,
            value: parseFloat(o._value),
            entity_id: o.entity_id,
          });
        },
        error(error: Error) {
          console.error('Query error:', error);
          resolve(NextResponse.json({ error: error.message }, { status: 500 }));
        },
        complete() {
          resolve(NextResponse.json({ readings }));
        },
      });
    });
  } catch (error) {
    console.error('Error fetching readings:', error);
    return NextResponse.json(
      { error: 'Failed to fetch readings' },
      { status: 500 }
    );
  }
}
