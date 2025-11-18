/**
 * Unit tests for /api/price-config route
 */

import { GET, POST, PUT, DELETE } from '@/app/api/price-config/route';
import { NextRequest } from 'next/server';
import { MockInfluxDB } from '@/__tests__/mocks/influxdb';

// Mock Point class from InfluxDB
jest.mock('@influxdata/influxdb-client', () => ({
  Point: jest.fn().mockImplementation(function (measurement: string) {
    const fields: Record<string, unknown> = {};
    const tags: Record<string, string> = {};

    return {
      tag: jest.fn(function (key: string, value: string) {
        tags[key] = value;
        return this;
      }),
      stringField: jest.fn(function (key: string, value: string) {
        fields[key] = value;
        return this;
      }),
      floatField: jest.fn(function (key: string, value: number) {
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

describe('/api/price-config', () => {
  beforeAll(() => {
    mockInflux = new MockInfluxDB();
  });

  beforeEach(() => {
    mockInflux.getMockQueryApi().setMockData([]);
    mockInflux.getMockQueryApi().setShouldError(false);
    mockInflux.getMockWriteApi().clearPoints();
    mockInflux.getMockWriteApi().setShouldError(false);
  });

  function createRequest(path: string, params: Record<string, string> = {}): NextRequest {
    const url = new URL(path);
    Object.entries(params).forEach(([key, value]) => {
      url.searchParams.set(key, value);
    });
    return new NextRequest(url);
  }

  describe('GET', () => {
    it('should fetch all price configurations', async () => {
      const mockPrices = [
        {
          id: 'price_1',
          utilityType: 'gas',
          pricePerUnit: 0.10,
          unit: 'kWh',
          validFrom: '2024-01-01T00:00:00Z',
          validTo: '2024-12-31T23:59:59Z',
          currency: 'EUR',
          description: 'Gas price 2024',
          createdAt: '2024-01-01T00:00:00Z',
          updatedAt: '2024-01-01T00:00:00Z',
        },
        {
          id: 'price_2',
          utilityType: 'water_cold',
          pricePerUnit: 2.50,
          unit: 'm³',
          validFrom: '2024-01-01T00:00:00Z',
          validTo: null,
          currency: 'EUR',
          createdAt: '2024-01-01T00:00:00Z',
          updatedAt: '2024-01-01T00:00:00Z',
        },
      ];

      mockInflux.getMockQueryApi().setMockData(mockPrices);

      const request = createRequest('http://localhost:3000/api/price-config');
      const response = await GET(request);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.prices).toHaveLength(2);
      expect(data.prices[0].id).toBe('price_1');
      expect(data.prices[1].id).toBe('price_2');
    });

    it('should filter by utilityType', async () => {
      const mockPrices = [
        {
          id: 'price_1',
          utilityType: 'gas',
          pricePerUnit: 0.10,
          unit: 'kWh',
          validFrom: '2024-01-01T00:00:00Z',
          validTo: null,
          currency: 'EUR',
          createdAt: '2024-01-01T00:00:00Z',
          updatedAt: '2024-01-01T00:00:00Z',
        },
      ];

      mockInflux.getMockQueryApi().setMockData(mockPrices);

      const request = createRequest('http://localhost:3000/api/price-config', {
        utilityType: 'gas',
      });
      const response = await GET(request);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.prices).toHaveLength(1);
      expect(data.prices[0].utilityType).toBe('gas');
    });

    it('should filter active prices only', async () => {
      const now = new Date();
      const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
      const tomorrow = new Date(now.getTime() + 24 * 60 * 60 * 1000);

      const mockPrices = [
        {
          id: 'price_active',
          utilityType: 'gas',
          pricePerUnit: 0.10,
          unit: 'kWh',
          validFrom: yesterday.toISOString(),
          validTo: tomorrow.toISOString(),
          currency: 'EUR',
          createdAt: yesterday.toISOString(),
          updatedAt: yesterday.toISOString(),
        },
        {
          id: 'price_expired',
          utilityType: 'gas',
          pricePerUnit: 0.12,
          unit: 'kWh',
          validFrom: '2023-01-01T00:00:00Z',
          validTo: '2023-12-31T23:59:59Z',
          currency: 'EUR',
          createdAt: '2023-01-01T00:00:00Z',
          updatedAt: '2023-01-01T00:00:00Z',
        },
      ];

      mockInflux.getMockQueryApi().setMockData(mockPrices);

      const request = createRequest('http://localhost:3000/api/price-config', {
        activeOnly: 'true',
      });
      const response = await GET(request);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.prices).toHaveLength(1);
      expect(data.prices[0].id).toBe('price_active');
    });

    it('should handle query errors', async () => {
      mockInflux.getMockQueryApi().setShouldError(true, 'Query failed');

      const request = createRequest('http://localhost:3000/api/price-config');
      const response = await GET(request);
      const data = await response.json();

      expect(response.status).toBe(500);
      expect(data.error).toBe('Query failed');
    });
  });

  describe('POST', () => {
    it('should create new price configuration', async () => {
      const request = new NextRequest('http://localhost:3000/api/price-config', {
        method: 'POST',
        body: JSON.stringify({
          utilityType: 'gas',
          pricePerUnit: 0.10,
          unit: 'kWh',
          validFrom: '2024-01-01T00:00:00Z',
          validTo: '2024-12-31T23:59:59Z',
          currency: 'EUR',
          description: 'Test price',
        }),
      });

      const response = await POST(request);
      const data = await response.json();

      expect(response.status).toBe(201);
      expect(data.price).toBeDefined();
      expect(data.price.utilityType).toBe('gas');
      expect(data.price.pricePerUnit).toBe(0.10);
      expect(data.price.id).toMatch(/^price_gas_/);
    });

    it('should reject missing required fields', async () => {
      const request = new NextRequest('http://localhost:3000/api/price-config', {
        method: 'POST',
        body: JSON.stringify({
          utilityType: 'gas',
          // Missing pricePerUnit
          unit: 'kWh',
          validFrom: '2024-01-01T00:00:00Z',
        }),
      });

      const response = await POST(request);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.error).toContain('Missing required fields');
    });

    it('should reject zero or negative price', async () => {
      const request = new NextRequest('http://localhost:3000/api/price-config', {
        method: 'POST',
        body: JSON.stringify({
          utilityType: 'gas',
          pricePerUnit: 0,
          unit: 'kWh',
          validFrom: '2024-01-01T00:00:00Z',
        }),
      });

      const response = await POST(request);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.error).toContain('must be greater than 0');
    });

    it('should handle write errors', async () => {
      mockInflux.getMockWriteApi().setShouldError(true, 'Write failed');

      const request = new NextRequest('http://localhost:3000/api/price-config', {
        method: 'POST',
        body: JSON.stringify({
          utilityType: 'gas',
          pricePerUnit: 0.10,
          unit: 'kWh',
          validFrom: '2024-01-01T00:00:00Z',
        }),
      });

      const response = await POST(request);
      const data = await response.json();

      expect(response.status).toBe(500);
      expect(data.error).toBe('Failed to create price configuration');
    });
  });

  describe('PUT', () => {
    it('should update existing price configuration', async () => {
      // Set up existing price
      mockInflux.getMockQueryApi().setMockData([
        {
          id: 'price_1',
          utilityType: 'gas',
          pricePerUnit: 0.10,
          unit: 'kWh',
          validFrom: '2024-01-01T00:00:00Z',
          validTo: null,
          currency: 'EUR',
          createdAt: '2024-01-01T00:00:00Z',
          updatedAt: '2024-01-01T00:00:00Z',
        },
      ]);

      const request = new NextRequest('http://localhost:3000/api/price-config', {
        method: 'PUT',
        body: JSON.stringify({
          id: 'price_1',
          pricePerUnit: 0.12,
        }),
      });

      const response = await PUT(request);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.success).toBe(true);
      expect(data.id).toBe('price_1');
    });

    it('should reject missing id', async () => {
      const request = new NextRequest('http://localhost:3000/api/price-config', {
        method: 'PUT',
        body: JSON.stringify({
          pricePerUnit: 0.12,
        }),
      });

      const response = await PUT(request);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.error).toContain('Missing required field: id');
    });

    it('should return 404 for non-existent price', async () => {
      mockInflux.getMockQueryApi().setMockData([]);

      const request = new NextRequest('http://localhost:3000/api/price-config', {
        method: 'PUT',
        body: JSON.stringify({
          id: 'non_existent',
          pricePerUnit: 0.12,
        }),
      });

      const response = await PUT(request);
      const data = await response.json();

      expect(response.status).toBe(404);
      expect(data.error).toBe('Price configuration not found');
    });
  });

  describe('DELETE', () => {
    it('should soft delete price configuration', async () => {
      // Set up existing price
      mockInflux.getMockQueryApi().setMockData([
        {
          id: 'price_1',
          utilityType: 'gas',
          pricePerUnit: 0.10,
          unit: 'kWh',
          validFrom: '2024-01-01T00:00:00Z',
          validTo: null,
          currency: 'EUR',
          createdAt: '2024-01-01T00:00:00Z',
          updatedAt: '2024-01-01T00:00:00Z',
        },
      ]);

      const request = createRequest('http://localhost:3000/api/price-config', {
        id: 'price_1',
      });

      const response = await DELETE(request);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.success).toBe(true);
      expect(data.id).toBe('price_1');
    });

    it('should reject missing id parameter', async () => {
      const request = createRequest('http://localhost:3000/api/price-config');

      const response = await DELETE(request);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.error).toContain('Missing required parameter: id');
    });

    it('should return 404 for non-existent price', async () => {
      mockInflux.getMockQueryApi().setMockData([]);

      const request = createRequest('http://localhost:3000/api/price-config', {
        id: 'non_existent',
      });

      const response = await DELETE(request);
      const data = await response.json();

      expect(response.status).toBe(404);
      expect(data.error).toBe('Price configuration not found');
    });
  });
});
