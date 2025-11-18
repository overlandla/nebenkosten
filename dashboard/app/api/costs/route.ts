import { NextRequest, NextResponse } from 'next/server';
import { getInfluxClient, getInfluxConfig, InfluxTableMeta } from '@/lib/influxdb';
import type { CostData } from '@/types/meter';
import {
  getOptimalConsumptionAggregation,
  estimateDataPoints,
} from '@/lib/time-aggregation';

// Re-export for backward compatibility
export type { CostData };

export async function GET(request: NextRequest): Promise<NextResponse> {
  try {
    const searchParams = request.nextUrl.searchParams;
    const startDate = searchParams.get('startDate') || '-90d';
    const endDate = searchParams.get('endDate') || 'now()';
    const aggregationParam = searchParams.get('aggregation'); // hourly, daily, monthly, or auto

    const influx = getInfluxClient();
    const config = getInfluxConfig();
    const queryApi = influx.getQueryApi(config.org);

    // Determine aggregation - use smart aggregation if 'auto' or not specified
    let window = '1d';
    let aggregationDescription = 'Daily totals';
    let aggregation = aggregationParam || 'auto';

    if (aggregation === 'auto') {
      // Use intelligent aggregation based on time range
      const aggConfig = getOptimalConsumptionAggregation(startDate, endDate);
      if (aggConfig.shouldAggregate) {
        window = aggConfig.window;
        aggregationDescription = aggConfig.description;
        // Map window to aggregation type for response
        if (window.includes('h')) {
          aggregation = 'hourly';
        } else if (window === '1d') {
          aggregation = 'daily';
        } else if (window.includes('w') || window.includes('mo')) {
          aggregation = 'weekly/monthly';
        }
      } else {
        // For very short ranges, use hourly
        window = '1h';
        aggregation = 'hourly';
        aggregationDescription = 'Hourly totals';
      }
    } else {
      // Use explicit aggregation parameter
      if (aggregation === 'hourly') {
        window = '1h';
        aggregationDescription = 'Hourly totals';
      } else if (aggregation === 'daily') {
        window = '1d';
        aggregationDescription = 'Daily totals';
      } else if (aggregation === 'monthly') {
        window = '1mo';
        aggregationDescription = 'Monthly totals';
      }
    }

    const estimatedPoints = estimateDataPoints(startDate, endDate, {
      window,
      windowMs: 0, // not used for estimation here
      fn: 'sum',
      description: aggregationDescription,
      shouldAggregate: true,
    });

    // Query Tibber cost data with aggregation
    const query = `
      from(bucket: "${config.bucketRaw}")
        |> range(start: ${startDate}, stop: ${endDate})
        |> filter(fn: (r) => r["_measurement"] == "energy")
        |> filter(fn: (r) => r["entity_id"] == "haupt_strom")
        |> filter(fn: (r) =>
          r["_field"] == "consumption" or
          r["_field"] == "cost" or
          r["_field"] == "unit_price" or
          r["_field"] == "unit_price_vat"
        )
        |> aggregateWindow(every: ${window}, fn: sum, createEmpty: false)
        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        |> sort(columns: ["_time"])
    `;

    const costs: CostData[] = [];

    return new Promise<NextResponse>((resolve) => {
      queryApi.queryRows(query, {
        next(row: string[], tableMeta: any) {
          try {
            const o = tableMeta.toObject(row);

            // Validate required fields
            if (!o._time || o.consumption === undefined) {
              return;
            }

            const consumption = parseFloat(String(o.consumption));
            const cost = parseFloat(String(o.cost ?? 0));
            const unit_price = parseFloat(String(o.unit_price ?? 0));
            const unit_price_vat = parseFloat(String(o.unit_price_vat ?? 0));

            // Validate numeric values
            if (isNaN(consumption) && isNaN(cost)) {
              console.warn('Skipping cost row with all invalid numeric values');
              return;
            }

            costs.push({
              timestamp: o._time,
              consumption: isNaN(consumption) ? 0 : consumption,
              cost: isNaN(cost) ? 0 : cost,
              unit_price: isNaN(unit_price) ? 0 : unit_price,
              unit_price_vat: isNaN(unit_price_vat) ? 0 : unit_price_vat,
            });
          } catch (error) {
            console.error('Error processing cost row:', error);
            // Continue processing other rows
          }
        },
        error(error: Error) {
          console.error('Query error:', error);
          resolve(NextResponse.json({ error: error.message }, { status: 500 }));
        },
        complete() {
          resolve(NextResponse.json({
            costs,
            aggregation,
            metadata: {
              aggregation: aggregationDescription,
              aggregationWindow: window,
              estimatedPoints,
              actualPoints: costs.length,
              timeRange: {
                start: startDate,
                end: endDate,
              },
            },
          }));
        },
      });
    });
  } catch (error) {
    console.error('Error fetching cost data:', error);
    return NextResponse.json(
      { error: 'Failed to fetch cost data' },
      { status: 500 }
    );
  }
}
