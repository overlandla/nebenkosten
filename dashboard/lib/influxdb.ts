import { InfluxDB } from '@influxdata/influxdb-client';

export interface InfluxConfig {
  url: string;
  token: string;
  org: string;
  bucketRaw: string;
  bucketProcessed: string;
}

export function getInfluxConfig(): InfluxConfig {
  const url = process.env.INFLUX_URL;
  const token = process.env.INFLUX_TOKEN;
  const org = process.env.INFLUX_ORG;
  const bucketRaw = process.env.INFLUX_BUCKET_RAW;
  const bucketProcessed = process.env.INFLUX_BUCKET_PROCESSED;

  // Validate required environment variables
  if (!url || !token || !org) {
    throw new Error(
      'Missing required InfluxDB environment variables. Please check your .env.local file.\n' +
      `Required: INFLUX_URL, INFLUX_TOKEN, INFLUX_ORG\n` +
      `Got: url=${!!url}, token=${!!token}, org=${!!org}`
    );
  }

  if (token === 'your_token_here') {
    throw new Error(
      'INFLUX_TOKEN is still set to placeholder value. Please update .env.local with your actual InfluxDB token.'
    );
  }

  return {
    url,
    token,
    org,
    bucketRaw: bucketRaw || 'homeassistant_raw',
    bucketProcessed: bucketProcessed || 'homeassistant_processed',
  };
}

export function getInfluxClient(): InfluxDB {
  const config = getInfluxConfig();
  return new InfluxDB({ url: config.url, token: config.token });
}

export interface MeterReading {
  timestamp: string;
  value: number;
  entity_id?: string;
}

export interface ConsumptionData {
  timestamp: string;
  value: number;
  entity_id?: string;
}
