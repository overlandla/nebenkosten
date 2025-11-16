import { NextRequest, NextResponse } from 'next/server';
import { getInfluxClient, getInfluxConfig } from '@/lib/influxdb';
import { Point } from '@influxdata/influxdb-client';
import type { HouseholdConfig } from '@/types/household';

const MEASUREMENT_NAME = 'household_config';

/**
 * GET /api/household-config
 * Fetches the latest household configuration
 */
export async function GET(request: NextRequest): Promise<NextResponse> {
  try {
    const influx = getInfluxClient();
    const config = getInfluxConfig();
    const queryApi = influx.getQueryApi(config.org);

    const query = `
      from(bucket: "${config.bucketRaw}")
        |> range(start: 0)
        |> filter(fn: (r) => r["_measurement"] == "${MEASUREMENT_NAME}")
        |> filter(fn: (r) => r["_field"] == "config_json")
        |> last()
    `;

    let householdConfig: HouseholdConfig | null = null;

    await new Promise<void>((resolve, reject) => {
      queryApi.queryRows(query, {
        next(row: string[], tableMeta) {
          try {
            const o = tableMeta.toObject(row) as any;
            if (o._value) {
              householdConfig = JSON.parse(String(o._value));
            }
          } catch (error) {
            console.error('Error parsing household config:', error);
          }
        },
        error: reject,
        complete: resolve,
      });
    });

    if (!householdConfig) {
      return NextResponse.json(
        { error: 'No household configuration found' },
        { status: 404 }
      );
    }

    return NextResponse.json({ config: householdConfig });
  } catch (error) {
    console.error('Error fetching household config:', error);
    return NextResponse.json(
      { error: 'Failed to fetch household configuration' },
      { status: 500 }
    );
  }
}

/**
 * POST /api/household-config
 * Saves a new household configuration
 */
export async function POST(request: NextRequest): Promise<NextResponse> {
  try {
    const body: HouseholdConfig = await request.json();

    // Validate input
    if (!body.households || !Array.isArray(body.households)) {
      return NextResponse.json(
        { error: 'Invalid configuration: households array is required' },
        { status: 400 }
      );
    }

    const influx = getInfluxClient();
    const config = getInfluxConfig();
    const writeApi = influx.getWriteApi(config.org, config.bucketRaw, 'ms');

    const now = new Date().toISOString();
    const configWithTimestamp: HouseholdConfig = {
      ...body,
      lastUpdated: now,
      version: body.version || '1.0',
    };

    const point = new Point(MEASUREMENT_NAME)
      .tag('config_type', 'household')
      .stringField('config_json', JSON.stringify(configWithTimestamp))
      .stringField('version', configWithTimestamp.version)
      .intField('household_count', configWithTimestamp.households.length);

    writeApi.writePoint(point);
    await writeApi.close();

    return NextResponse.json({
      success: true,
      config: configWithTimestamp
    }, { status: 201 });
  } catch (error) {
    console.error('Error saving household config:', error);
    return NextResponse.json(
      { error: 'Failed to save household configuration' },
      { status: 500 }
    );
  }
}
