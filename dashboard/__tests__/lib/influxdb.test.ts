/**
 * Unit tests for lib/influxdb.ts
 */

import { getInfluxConfig, getInfluxClient } from '@/lib/influxdb';
import { InfluxDB } from '@influxdata/influxdb-client';

// Mock InfluxDB
jest.mock('@influxdata/influxdb-client');

describe('lib/influxdb', () => {
  const originalEnv = process.env;

  beforeEach(() => {
    // Reset environment variables before each test
    jest.resetModules();
    process.env = { ...originalEnv };
  });

  afterAll(() => {
    process.env = originalEnv;
  });

  describe('getInfluxConfig', () => {
    it('should return config with all environment variables', () => {
      process.env.INFLUX_URL = 'http://influxdb:8086';
      process.env.INFLUX_TOKEN = 'my-secret-token';
      process.env.INFLUX_ORG = 'my-org';
      process.env.INFLUX_BUCKET_RAW = 'raw_data';
      process.env.INFLUX_BUCKET_PROCESSED = 'processed_data';

      const config = getInfluxConfig();

      expect(config).toEqual({
        url: 'http://influxdb:8086',
        token: 'my-secret-token',
        org: 'my-org',
        bucketRaw: 'raw_data',
        bucketProcessed: 'processed_data',
      });
    });

    it('should use default bucket names when not provided', () => {
      process.env.INFLUX_URL = 'http://influxdb:8086';
      process.env.INFLUX_TOKEN = 'my-secret-token';
      process.env.INFLUX_ORG = 'my-org';
      delete process.env.INFLUX_BUCKET_RAW;
      delete process.env.INFLUX_BUCKET_PROCESSED;

      const config = getInfluxConfig();

      expect(config.bucketRaw).toBe('homeassistant_raw');
      expect(config.bucketProcessed).toBe('homeassistant_processed');
    });

    it('should throw error when INFLUX_URL is missing', () => {
      delete process.env.INFLUX_URL;
      process.env.INFLUX_TOKEN = 'my-secret-token';
      process.env.INFLUX_ORG = 'my-org';

      expect(() => getInfluxConfig()).toThrow(
        'Missing required InfluxDB environment variables'
      );
      expect(() => getInfluxConfig()).toThrow('url=false');
    });

    it('should throw error when INFLUX_TOKEN is missing', () => {
      process.env.INFLUX_URL = 'http://influxdb:8086';
      delete process.env.INFLUX_TOKEN;
      process.env.INFLUX_ORG = 'my-org';

      expect(() => getInfluxConfig()).toThrow(
        'Missing required InfluxDB environment variables'
      );
      expect(() => getInfluxConfig()).toThrow('token=false');
    });

    it('should throw error when INFLUX_ORG is missing', () => {
      process.env.INFLUX_URL = 'http://influxdb:8086';
      process.env.INFLUX_TOKEN = 'my-secret-token';
      delete process.env.INFLUX_ORG;

      expect(() => getInfluxConfig()).toThrow(
        'Missing required InfluxDB environment variables'
      );
      expect(() => getInfluxConfig()).toThrow('org=false');
    });

    it('should throw error when token is placeholder value', () => {
      process.env.INFLUX_URL = 'http://influxdb:8086';
      process.env.INFLUX_TOKEN = 'your_token_here';
      process.env.INFLUX_ORG = 'my-org';

      expect(() => getInfluxConfig()).toThrow(
        'INFLUX_TOKEN is still set to placeholder value'
      );
      expect(() => getInfluxConfig()).toThrow(
        'Please update .env.local with your actual InfluxDB token'
      );
    });

    it('should throw error when multiple env vars are missing', () => {
      delete process.env.INFLUX_URL;
      delete process.env.INFLUX_TOKEN;
      delete process.env.INFLUX_ORG;

      expect(() => getInfluxConfig()).toThrow(
        'Missing required InfluxDB environment variables'
      );
      expect(() => getInfluxConfig()).toThrow(
        'url=false, token=false, org=false'
      );
    });
  });

  describe('getInfluxClient', () => {
    beforeEach(() => {
      // Set valid environment variables
      process.env.INFLUX_URL = 'http://influxdb:8086';
      process.env.INFLUX_TOKEN = 'my-secret-token';
      process.env.INFLUX_ORG = 'my-org';
    });

    it('should create InfluxDB client with correct config', () => {
      getInfluxClient();

      expect(InfluxDB).toHaveBeenCalledWith({
        url: 'http://influxdb:8086',
        token: 'my-secret-token',
      });
    });

    it('should return InfluxDB instance', () => {
      const mockInfluxDB = { mock: 'instance' };
      (InfluxDB as jest.Mock).mockReturnValue(mockInfluxDB);

      const client = getInfluxClient();

      expect(client).toBe(mockInfluxDB);
    });

    it('should throw error if config is invalid', () => {
      delete process.env.INFLUX_TOKEN;

      expect(() => getInfluxClient()).toThrow(
        'Missing required InfluxDB environment variables'
      );
    });
  });
});
