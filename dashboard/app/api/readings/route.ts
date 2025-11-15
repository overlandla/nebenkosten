import { NextRequest, NextResponse } from 'next/server';
import { getInfluxClient, getInfluxConfig, MeterReading } from '@/lib/influxdb';

export async function GET(request: NextRequest): Promise<NextResponse> {
  try {
    const searchParams = request.nextUrl.searchParams;
    const meterId = searchParams.get('meterId');
    const startDate = searchParams.get('startDate');
    const endDate = searchParams.get('endDate');
    const dataType = searchParams.get('dataType') || 'raw'; // raw, interpolated_daily, interpolated_monthly, consumption

    if (!meterId) {
      return NextResponse.json({ error: 'meterId is required' }, { status: 400 });
    }

    const influx = getInfluxClient();
    const config = getInfluxConfig();
    const queryApi = influx.getQueryApi(config.org);

    // Default to last 90 days if not specified
    const start = startDate || '-90d';
    const end = endDate || 'now()';

    // Determine which bucket and measurement to use based on dataType
    let bucket = config.bucketRaw;
    let measurement = '';

    if (dataType === 'raw') {
      bucket = config.bucketRaw;
      // For raw data, query by entity_id without measurement filter
    } else if (dataType === 'interpolated_daily') {
      bucket = config.bucketProcessed;
      measurement = 'meter_interpolated_daily';
    } else if (dataType === 'interpolated_monthly') {
      bucket = config.bucketProcessed;
      measurement = 'meter_interpolated_monthly';
    } else if (dataType === 'consumption') {
      bucket = config.bucketProcessed;
      measurement = 'meter_consumption';
    }

    // Build query based on data type
    let query = '';
    if (dataType === 'raw') {
      // Query raw data from lampfi bucket
      query = `
        from(bucket: "${bucket}")
          |> range(start: ${start}, stop: ${end})
          |> filter(fn: (r) => r["entity_id"] == "${meterId}")
          |> filter(fn: (r) => r["_field"] == "value")
          |> sort(columns: ["_time"])
      `;
    } else {
      // Query processed data from lampfi_processed bucket
      query = `
        from(bucket: "${bucket}")
          |> range(start: ${start}, stop: ${end})
          |> filter(fn: (r) => r["_measurement"] == "${measurement}")
          |> filter(fn: (r) => r["meter_id"] == "${meterId}")
          |> filter(fn: (r) => r["_field"] == "value")
          |> sort(columns: ["_time"])
      `;
    }

    const readings: MeterReading[] = [];

    return new Promise<NextResponse>((resolve) => {
      queryApi.queryRows(query, {
        next(row: string[], tableMeta: any) {
          const o = tableMeta.toObject(row);
          readings.push({
            timestamp: o._time,
            value: parseFloat(o._value),
            entity_id: dataType === 'raw' ? o.entity_id : meterId,
          });
        },
        error(error: Error) {
          console.error('Query error:', error);
          resolve(NextResponse.json({ error: error.message }, { status: 500 }));
        },
        complete() {
          resolve(NextResponse.json({ readings, dataType }));
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
