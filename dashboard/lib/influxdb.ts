import { InfluxDB } from '@influxdata/influxdb-client';

export interface InfluxConfig {
  url: string;
  token: string;
  org: string;
  bucketRaw: string;
  bucketProcessed: string;
}

export function getInfluxConfig(): InfluxConfig {
  return {
    url: process.env.INFLUX_URL || 'http://localhost:8086',
    token: process.env.INFLUX_TOKEN || '',
    org: process.env.INFLUX_ORG || '',
    bucketRaw: process.env.INFLUX_BUCKET_RAW || 'homeassistant_raw',
    bucketProcessed: process.env.INFLUX_BUCKET_PROCESSED || 'homeassistant_processed',
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
