import { NextRequest, NextResponse } from 'next/server';
import { getInfluxClient, getInfluxConfig, InfluxTableMeta } from '@/lib/influxdb';
import type { CostData } from '@/types/meter';

// Re-export for backward compatibility
export type { CostData };

export async function GET(request: NextRequest): Promise<NextResponse> {
  try {
    const searchParams = request.nextUrl.searchParams;
    const startDate = searchParams.get('startDate') || '-90d';
    const endDate = searchParams.get('endDate') || 'now()';
    const aggregation = searchParams.get('aggregation') || 'daily'; // hourly, daily, monthly

    const influx = getInfluxClient();
    const config = getInfluxConfig();
    const queryApi = influx.getQueryApi(config.org);

    // Build aggregation window
    let window = '1h';
    if (aggregation === 'daily') {
      window = '1d';
    } else if (aggregation === 'monthly') {
      window = '1mo';
    }

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
        next(row: string[], tableMeta: InfluxTableMeta) {
          try {
            const o = tableMeta.toObject(row);

            // Validate required fields
            if (!o._time || o.consumption === undefined) {
              return;
            }

            const consumption = parseFloat(o.consumption);
            const cost = parseFloat(o.cost);
            const unit_price = parseFloat(o.unit_price);
            const unit_price_vat = parseFloat(o.unit_price_vat);

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
          resolve(NextResponse.json({ costs, aggregation }));
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
