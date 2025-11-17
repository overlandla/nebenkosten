import { NextRequest, NextResponse } from 'next/server';
import { getInfluxClient, getInfluxConfig, MeterReading, InfluxTableMeta } from '@/lib/influxdb';
import {
  getOptimalAggregation,
  getOptimalConsumptionAggregation,
  getOptimalInterpolatedAggregation,
  estimateDataPoints,
} from '@/lib/time-aggregation';

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

    // Calculate optimal aggregation based on time range and data type
    let aggregationConfig;
    if (dataType === 'consumption') {
      aggregationConfig = getOptimalConsumptionAggregation(start, end);
    } else if (dataType === 'interpolated_daily') {
      aggregationConfig = getOptimalInterpolatedAggregation(start, end, 'daily');
    } else if (dataType === 'interpolated_monthly') {
      aggregationConfig = getOptimalInterpolatedAggregation(start, end, 'monthly');
    } else {
      // raw data
      aggregationConfig = getOptimalAggregation(start, end);
    }

    const estimatedPoints = estimateDataPoints(start, end, aggregationConfig);

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
      // Query raw data from lampfi bucket with optional aggregation
      query = `
        from(bucket: "${bucket}")
          |> range(start: ${start}, stop: ${end})
          |> filter(fn: (r) => r["entity_id"] == "${meterId}")
          |> filter(fn: (r) => r["_field"] == "value")
          ${aggregationConfig.shouldAggregate
            ? `|> aggregateWindow(every: ${aggregationConfig.window}, fn: ${aggregationConfig.fn}, createEmpty: false)`
            : ''}
          |> sort(columns: ["_time"])
      `;
    } else {
      // Query processed data from lampfi_processed bucket with optional aggregation
      query = `
        from(bucket: "${bucket}")
          |> range(start: ${start}, stop: ${end})
          |> filter(fn: (r) => r["_measurement"] == "${measurement}")
          |> filter(fn: (r) => r["meter_id"] == "${meterId}")
          |> filter(fn: (r) => r["_field"] == "value")
          ${aggregationConfig.shouldAggregate
            ? `|> aggregateWindow(every: ${aggregationConfig.window}, fn: ${aggregationConfig.fn}, createEmpty: false)`
            : ''}
          |> sort(columns: ["_time"])
      `;
    }

    const readings: MeterReading[] = [];

    return new Promise<NextResponse>((resolve) => {
      queryApi.queryRows(query, {
        next(row: string[], tableMeta: any) {
          try {
            const o = tableMeta.toObject(row);

            // Validate required fields
            if (!o._time || o._value === undefined || o._value === null) {
              console.warn('Skipping row with missing data:', { time: o._time, value: o._value });
              return;
            }

            // Parse and validate numeric value
            const value = parseFloat(String(o._value));
            if (isNaN(value)) {
              console.warn('Skipping row with invalid numeric value:', o._value);
              return;
            }

            readings.push({
              timestamp: o._time,
              value,
              entity_id: dataType === 'raw' ? o.entity_id : meterId,
            });
          } catch (error) {
            console.error('Error processing row:', error);
            // Continue processing other rows instead of failing entirely
          }
        },
        error(error: Error) {
          console.error('Query error:', error);
          resolve(NextResponse.json({ error: error.message }, { status: 500 }));
        },
        complete() {
          resolve(NextResponse.json({
            readings,
            dataType,
            metadata: {
              aggregation: aggregationConfig.description,
              aggregationWindow: aggregationConfig.window || 'none',
              estimatedPoints,
              actualPoints: readings.length,
              timeRange: {
                start,
                end,
              },
            },
          }));
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
