/**
 * Unit tests for /api/household-config route
 */

import { GET, POST } from '@/app/api/household-config/route';
import { NextRequest } from 'next/server';
import { MockInfluxDB } from '@/__tests__/mocks/influxdb';
import type { HouseholdConfig } from '@/types/household';

// Mock Point class
jest.mock('@influxdata/influxdb-client', () => ({
  Point: jest.fn().mockImplementation(function (measurement: string) {
    const fields: any = {};
    const tags: any = {};
    return {
      tag: jest.fn(function (key: string, value: string) {
        tags[key] = value;
        return this;
      }),
      stringField: jest.fn(function (key: string, value: string) {
        fields[key] = value;
        return this;
      }),
      intField: jest.fn(function (key: string, value: number) {
        fields[key] = value;
        return this;
      }),
      fields,
      tags,
      measurement,
    };
  }),
}));

let mockInflux: MockInfluxDB;

jest.mock('@/lib/influxdb', () => ({
  getInfluxClient: jest.fn(() => mockInflux),
  getInfluxConfig: jest.fn(() => ({
    url: 'http://test:8086',
    token: 'test-token',
    org: 'test-org',
    bucketRaw: 'test_raw',
    bucketProcessed: 'test_processed',
  })),
}));

describe('/api/household-config', () => {
  beforeAll(() => {
    mockInflux = new MockInfluxDB();
  });

  beforeEach(() => {
    mockInflux.getMockQueryApi().setMockData([]);
    mockInflux.getMockQueryApi().setShouldError(false);
    mockInflux.getMockWriteApi().clearPoints();
    mockInflux.getMockWriteApi().setShouldError(false);
  });

  const mockHouseholdConfig: HouseholdConfig = {
    version: '1.0',
    lastUpdated: '2024-01-01T00:00:00Z',
    households: [
      {
        id: 'household_1',
        name: 'Ground Floor',
        type: 'unit',
        color: '#3b82f6',
        meters: {
          electricity: ['eg_strom'],
          heat: ['eg_nord_heat'],
        },
        costAllocation: {
          sharedGas: 25,
          sharedWater: 20,
        },
      },
      {
        id: 'household_2',
        name: 'First Floor',
        type: 'unit',
        color: '#f59e0b',
        meters: {
          electricity: ['og1_strom'],
          water: ['og1_wasser_kalt', 'og1_wasser_warm'],
          heat: ['og1_heat'],
        },
        costAllocation: {
          sharedElectricity: 30,
          sharedGas: 25,
          sharedWater: 30,
        },
      },
    ],
  };

  describe('GET', () => {
    it('should fetch household configuration', async () => {
      mockInflux.getMockQueryApi().setMockData([
        {
          _time: '2024-01-01T00:00:00Z',
          _value: JSON.stringify(mockHouseholdConfig),
        },
      ]);

      const request = new NextRequest('http://localhost:3000/api/household-config');
      const response = await GET(request);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.config).toBeDefined();
      expect(data.config.version).toBe('1.0');
      expect(data.config.households).toHaveLength(2);
      expect(data.config.households[0].id).toBe('household_1');
    });

    it('should return 404 if no configuration exists', async () => {
      mockInflux.getMockQueryApi().setMockData([]);

      const request = new NextRequest('http://localhost:3000/api/household-config');
      const response = await GET(request);
      const data = await response.json();

      expect(response.status).toBe(404);
      expect(data.error).toBe('No household configuration found');
    });

    it('should handle query errors', async () => {
      mockInflux.getMockQueryApi().setShouldError(true, 'Query failed');

      const request = new NextRequest('http://localhost:3000/api/household-config');
      const response = await GET(request);
      const data = await response.json();

      expect(response.status).toBe(500);
      expect(data.error).toBe('Failed to fetch household configuration');
    });

    it('should handle malformed JSON', async () => {
      mockInflux.getMockQueryApi().setMockData([
        {
          _time: '2024-01-01T00:00:00Z',
          _value: 'invalid json{',
        },
      ]);

      const request = new NextRequest('http://localhost:3000/api/household-config');
      const response = await GET(request);
      const data = await response.json();

      expect(response.status).toBe(404);
      expect(data.error).toBe('No household configuration found');
    });
  });

  describe('POST', () => {
    it('should save household configuration', async () => {
      const request = new NextRequest('http://localhost:3000/api/household-config', {
        method: 'POST',
        body: JSON.stringify(mockHouseholdConfig),
      });

      const response = await POST(request);
      const data = await response.json();

      expect(response.status).toBe(201);
      expect(data.success).toBe(true);
      expect(data.config).toBeDefined();
      expect(data.config.version).toBe('1.0');
      expect(data.config.lastUpdated).toBeDefined();
    });

    it('should add lastUpdated timestamp if missing', async () => {
      const configWithoutTimestamp = {
        ...mockHouseholdConfig,
        lastUpdated: undefined,
      };

      const request = new NextRequest('http://localhost:3000/api/household-config', {
        method: 'POST',
        body: JSON.stringify(configWithoutTimestamp),
      });

      const response = await POST(request);
      const data = await response.json();

      expect(response.status).toBe(201);
      expect(data.config.lastUpdated).toBeDefined();
      expect(new Date(data.config.lastUpdated).getTime()).toBeGreaterThan(0);
    });

    it('should add version if missing', async () => {
      const configWithoutVersion = {
        ...mockHouseholdConfig,
        version: undefined,
      };

      const request = new NextRequest('http://localhost:3000/api/household-config', {
        method: 'POST',
        body: JSON.stringify(configWithoutVersion),
      });

      const response = await POST(request);
      const data = await response.json();

      expect(response.status).toBe(201);
      expect(data.config.version).toBe('1.0');
    });

    it('should reject invalid configuration (missing households)', async () => {
      const request = new NextRequest('http://localhost:3000/api/household-config', {
        method: 'POST',
        body: JSON.stringify({
          version: '1.0',
          // Missing households array
        }),
      });

      const response = await POST(request);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.error).toContain('households array is required');
    });

    it('should reject invalid households (not an array)', async () => {
      const request = new NextRequest('http://localhost:3000/api/household-config', {
        method: 'POST',
        body: JSON.stringify({
          version: '1.0',
          households: 'not an array',
        }),
      });

      const response = await POST(request);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.error).toContain('households array is required');
    });

    it('should handle write errors', async () => {
      mockInflux.getMockWriteApi().setShouldError(true, 'Write failed');

      const request = new NextRequest('http://localhost:3000/api/household-config', {
        method: 'POST',
        body: JSON.stringify(mockHouseholdConfig),
      });

      const response = await POST(request);
      const data = await response.json();

      expect(response.status).toBe(500);
      expect(data.error).toBe('Failed to save household configuration');
    });
  });
});
