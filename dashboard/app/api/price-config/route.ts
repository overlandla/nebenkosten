import { NextRequest, NextResponse } from 'next/server';
import { getInfluxClient, getInfluxConfig } from '@/lib/influxdb';
import { Point } from '@influxdata/influxdb-client';
import type { PriceConfig, PriceConfigInput, UtilityType } from '@/types/price';

const MEASUREMENT_NAME = 'price_config';

/**
 * GET /api/price-config
 * Fetches all price configurations or filters by utilityType
 */
export async function GET(request: NextRequest): Promise<NextResponse> {
  try {
    const searchParams = request.nextUrl.searchParams;
    const utilityType = searchParams.get('utilityType') as UtilityType | null;
    const activeOnly = searchParams.get('activeOnly') === 'true';

    const influx = getInfluxClient();
    const config = getInfluxConfig();
    const queryApi = influx.getQueryApi(config.org);

    let query = `
      from(bucket: "${config.bucketRaw}")
        |> range(start: 0)
        |> filter(fn: (r) => r["_measurement"] == "${MEASUREMENT_NAME}")
    `;

    if (utilityType) {
      query += `
        |> filter(fn: (r) => r["utilityType"] == "${utilityType}")
      `;
    }

    query += `
      |> pivot(rowKey:["_time", "id"], columnKey: ["_field"], valueColumn: "_value")
      |> sort(columns: ["_time"], desc: true)
    `;

    const prices: PriceConfig[] = [];
    const now = new Date().toISOString();

    return new Promise<NextResponse>((resolve) => {
      queryApi.queryRows(query, {
        next(row: string[], tableMeta) {
          try {
            const o = tableMeta.toObject(row) as any;

            // Skip if required fields are missing
            if (!o.id || !o.utilityType || o.pricePerUnit === undefined) {
              return;
            }

            const priceConfig: PriceConfig = {
              id: String(o.id),
              utilityType: String(o.utilityType) as UtilityType,
              pricePerUnit: parseFloat(o.pricePerUnit),
              unit: String(o.unit || ''),
              validFrom: String(o.validFrom || o._time),
              validTo: o.validTo ? String(o.validTo) : null,
              currency: String(o.currency || 'EUR'),
              description: o.description ? String(o.description) : undefined,
              createdAt: String(o.createdAt || o._time),
              updatedAt: String(o.updatedAt || o._time),
            };

            // Filter for active prices only if requested
            if (activeOnly) {
              const isActive =
                priceConfig.validFrom <= now &&
                (!priceConfig.validTo || priceConfig.validTo >= now);
              if (!isActive) return;
            }

            prices.push(priceConfig);
          } catch (error) {
            console.error('Error processing price config row:', error);
          }
        },
        error(error: Error) {
          console.error('Query error:', error);
          resolve(NextResponse.json({ error: error.message }, { status: 500 }));
        },
        complete() {
          // Remove duplicates by ID (keep most recent)
          const uniquePrices = Array.from(
            prices
              .reduce((map, price) => {
                const existing = map.get(price.id);
                if (!existing || price.updatedAt > existing.updatedAt) {
                  map.set(price.id, price);
                }
                return map;
              }, new Map<string, PriceConfig>())
              .values()
          );

          resolve(NextResponse.json({ prices: uniquePrices }));
        },
      });
    });
  } catch (error) {
    console.error('Error fetching price configs:', error);
    return NextResponse.json(
      { error: 'Failed to fetch price configurations' },
      { status: 500 }
    );
  }
}

/**
 * POST /api/price-config
 * Creates a new price configuration
 */
export async function POST(request: NextRequest): Promise<NextResponse> {
  try {
    const body: PriceConfigInput = await request.json();

    // Validate input
    if (!body.utilityType || body.pricePerUnit === undefined || !body.validFrom) {
      return NextResponse.json(
        { error: 'Missing required fields: utilityType, pricePerUnit, validFrom' },
        { status: 400 }
      );
    }

    if (body.pricePerUnit <= 0) {
      return NextResponse.json(
        { error: 'pricePerUnit must be greater than 0' },
        { status: 400 }
      );
    }

    const influx = getInfluxClient();
    const config = getInfluxConfig();
    const writeApi = influx.getWriteApi(config.org, config.bucketRaw, 'ms');

    const id = `price_${body.utilityType}_${Date.now()}`;
    const now = new Date().toISOString();

    const point = new Point(MEASUREMENT_NAME)
      .tag('id', id)
      .tag('utilityType', body.utilityType)
      .stringField('id', id)
      .stringField('utilityType', body.utilityType)
      .floatField('pricePerUnit', body.pricePerUnit)
      .stringField('unit', body.unit)
      .stringField('validFrom', body.validFrom)
      .stringField('currency', body.currency || 'EUR')
      .stringField('createdAt', now)
      .stringField('updatedAt', now);

    if (body.validTo) {
      point.stringField('validTo', body.validTo);
    }

    if (body.description) {
      point.stringField('description', body.description);
    }

    writeApi.writePoint(point);
    await writeApi.close();

    const newPrice: PriceConfig = {
      id,
      utilityType: body.utilityType,
      pricePerUnit: body.pricePerUnit,
      unit: body.unit,
      validFrom: body.validFrom,
      validTo: body.validTo || null,
      currency: body.currency || 'EUR',
      description: body.description,
      createdAt: now,
      updatedAt: now,
    };

    return NextResponse.json({ price: newPrice }, { status: 201 });
  } catch (error) {
    console.error('Error creating price config:', error);
    return NextResponse.json(
      { error: 'Failed to create price configuration' },
      { status: 500 }
    );
  }
}

/**
 * PUT /api/price-config
 * Updates an existing price configuration
 */
export async function PUT(request: NextRequest): Promise<NextResponse> {
  try {
    const body = await request.json();
    const { id, ...updates } = body;

    if (!id) {
      return NextResponse.json(
        { error: 'Missing required field: id' },
        { status: 400 }
      );
    }

    const influx = getInfluxClient();
    const config = getInfluxConfig();

    // First, fetch the existing price config
    const queryApi = influx.getQueryApi(config.org);
    const query = `
      from(bucket: "${config.bucketRaw}")
        |> range(start: 0)
        |> filter(fn: (r) => r["_measurement"] == "${MEASUREMENT_NAME}")
        |> filter(fn: (r) => r["id"] == "${id}")
        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        |> last()
    `;

    let existingPrice: any = null;

    await new Promise<void>((resolve, reject) => {
      queryApi.queryRows(query, {
        next(row: string[], tableMeta) {
          existingPrice = tableMeta.toObject(row);
        },
        error: reject,
        complete: resolve,
      });
    });

    if (!existingPrice) {
      return NextResponse.json(
        { error: 'Price configuration not found' },
        { status: 404 }
      );
    }

    // Write updated price config
    const writeApi = influx.getWriteApi(config.org, config.bucketRaw, 'ms');
    const now = new Date().toISOString();

    const point = new Point(MEASUREMENT_NAME)
      .tag('id', id)
      .tag('utilityType', existingPrice.utilityType)
      .stringField('id', id)
      .stringField('utilityType', existingPrice.utilityType)
      .floatField('pricePerUnit', updates.pricePerUnit ?? parseFloat(existingPrice.pricePerUnit))
      .stringField('unit', updates.unit ?? existingPrice.unit)
      .stringField('validFrom', updates.validFrom ?? existingPrice.validFrom)
      .stringField('currency', existingPrice.currency || 'EUR')
      .stringField('createdAt', existingPrice.createdAt || now)
      .stringField('updatedAt', now);

    const validTo = updates.validTo !== undefined ? updates.validTo : existingPrice.validTo;
    if (validTo) {
      point.stringField('validTo', validTo);
    }

    const description = updates.description !== undefined ? updates.description : existingPrice.description;
    if (description) {
      point.stringField('description', description);
    }

    writeApi.writePoint(point);
    await writeApi.close();

    return NextResponse.json({ success: true, id });
  } catch (error) {
    console.error('Error updating price config:', error);
    return NextResponse.json(
      { error: 'Failed to update price configuration' },
      { status: 500 }
    );
  }
}

/**
 * DELETE /api/price-config
 * Soft deletes a price configuration by setting validTo to now
 */
export async function DELETE(request: NextRequest): Promise<NextResponse> {
  try {
    const searchParams = request.nextUrl.searchParams;
    const id = searchParams.get('id');

    if (!id) {
      return NextResponse.json(
        { error: 'Missing required parameter: id' },
        { status: 400 }
      );
    }

    // Soft delete by setting validTo to now
    const now = new Date().toISOString();

    const influx = getInfluxClient();
    const config = getInfluxConfig();

    // Fetch existing price to get all fields
    const queryApi = influx.getQueryApi(config.org);
    const query = `
      from(bucket: "${config.bucketRaw}")
        |> range(start: 0)
        |> filter(fn: (r) => r["_measurement"] == "${MEASUREMENT_NAME}")
        |> filter(fn: (r) => r["id"] == "${id}")
        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        |> last()
    `;

    let existingPrice: any = null;

    await new Promise<void>((resolve, reject) => {
      queryApi.queryRows(query, {
        next(row: string[], tableMeta) {
          existingPrice = tableMeta.toObject(row);
        },
        error: reject,
        complete: resolve,
      });
    });

    if (!existingPrice) {
      return NextResponse.json(
        { error: 'Price configuration not found' },
        { status: 404 }
      );
    }

    // Write with validTo set to now
    const writeApi = influx.getWriteApi(config.org, config.bucketRaw, 'ms');

    const point = new Point(MEASUREMENT_NAME)
      .tag('id', id)
      .tag('utilityType', existingPrice.utilityType)
      .stringField('id', id)
      .stringField('utilityType', existingPrice.utilityType)
      .floatField('pricePerUnit', parseFloat(existingPrice.pricePerUnit))
      .stringField('unit', existingPrice.unit)
      .stringField('validFrom', existingPrice.validFrom)
      .stringField('validTo', now) // Set validTo to now (soft delete)
      .stringField('currency', existingPrice.currency || 'EUR')
      .stringField('createdAt', existingPrice.createdAt || now)
      .stringField('updatedAt', now);

    if (existingPrice.description) {
      point.stringField('description', existingPrice.description);
    }

    writeApi.writePoint(point);
    await writeApi.close();

    return NextResponse.json({ success: true, id });
  } catch (error) {
    console.error('Error deleting price config:', error);
    return NextResponse.json(
      { error: 'Failed to delete price configuration' },
      { status: 500 }
    );
  }
}
