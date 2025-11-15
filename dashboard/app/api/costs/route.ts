import { NextRequest, NextResponse } from 'next/server';
import { getInfluxClient, getInfluxConfig } from '@/lib/influxdb';

export interface CostData {
  timestamp: string;
  consumption: number;    // kWh
  cost: number;          // EUR
  unit_price: number;    // EUR/kWh
  unit_price_vat: number; // EUR/kWh including VAT
}

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
        next(row: string[], tableMeta: any) {
          const o = tableMeta.toObject(row);
          if (o.consumption !== undefined) {
            costs.push({
              timestamp: o._time,
              consumption: parseFloat(o.consumption) || 0,
              cost: parseFloat(o.cost) || 0,
              unit_price: parseFloat(o.unit_price) || 0,
              unit_price_vat: parseFloat(o.unit_price_vat) || 0,
            });
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
