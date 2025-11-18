/**
 * Unit tests for /api/costs route
 */

import { GET } from '@/app/api/costs/route';
import { NextRequest } from 'next/server';
import { MockInfluxDB } from '@/__tests__/mocks/influxdb';
import { generateCostData, createMockInfluxRows } from '@/__tests__/fixtures/meterData';

// Mock the influxdb module
jest.mock('@influxdata/influxdb-client');

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

describe('/api/costs', () => {
  beforeAll(() => {
    mockInflux = new MockInfluxDB();
  });

  beforeEach(() => {
    mockInflux.getMockQueryApi().setMockData([]);
    mockInflux.getMockQueryApi().setShouldError(false);
  });

  function createRequest(params: Record<string, string> = {}): NextRequest {
    const url = new URL('http://localhost:3000/api/costs');
    Object.entries(params).forEach(([key, value]) => {
      url.searchParams.set(key, value);
    });
    return new NextRequest(url);
  }

  it('should fetch cost data with default parameters', async () => {
    const mockCosts = generateCostData({ days: 5 });

    const mockQueryApi = mockInflux.getMockQueryApi();
    mockQueryApi.setMockData(createMockInfluxRows(mockCosts));

    const request = createRequest();
    const response = await GET(request);
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.costs).toHaveLength(5);
    // Default uses auto aggregation which may be hourly or daily depending on time range
    expect(['hourly', 'daily']).toContain(data.aggregation);
    expect(data.costs[0]).toHaveProperty('timestamp');
    expect(data.costs[0]).toHaveProperty('consumption');
    expect(data.costs[0]).toHaveProperty('cost');
    expect(data.costs[0]).toHaveProperty('unit_price');
    expect(data.costs[0]).toHaveProperty('unit_price_vat');
  });

  it('should handle daily aggregation', async () => {
    const mockCosts = generateCostData({ days: 10 });

    const mockQueryApi = mockInflux.getMockQueryApi();
    mockQueryApi.setMockData(createMockInfluxRows(mockCosts));

    const request = createRequest({ aggregation: 'daily' });
    const response = await GET(request);
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.aggregation).toBe('daily');
  });

  it('should handle hourly aggregation', async () => {
    const mockCosts = generateCostData({ days: 1 });

    const mockQueryApi = mockInflux.getMockQueryApi();
    mockQueryApi.setMockData(createMockInfluxRows(mockCosts));

    const request = createRequest({ aggregation: 'hourly' });
    const response = await GET(request);
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.aggregation).toBe('hourly');
  });

  it('should handle monthly aggregation', async () => {
    const mockCosts = generateCostData({ days: 60 });

    const mockQueryApi = mockInflux.getMockQueryApi();
    mockQueryApi.setMockData(createMockInfluxRows(mockCosts));

    const request = createRequest({ aggregation: 'monthly' });
    const response = await GET(request);
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.aggregation).toBe('monthly');
  });

  it('should handle custom date ranges', async () => {
    const mockQueryApi = mockInflux.getMockQueryApi();
    mockQueryApi.setMockData([]);

    const request = createRequest({
      startDate: '2024-01-01T00:00:00Z',
      endDate: '2024-12-31T23:59:59Z',
    });
    const response = await GET(request);

    expect(response.status).toBe(200);
  });

  it('should skip rows with missing timestamp', async () => {
    const mockQueryApi = mockInflux.getMockQueryApi();
    mockQueryApi.setMockData([
      { _time: '2024-01-01T00:00:00Z', consumption: 10, cost: 3, unit_price: 0.3, unit_price_vat: 0.357 },
      { _time: null, consumption: 20, cost: 6, unit_price: 0.3, unit_price_vat: 0.357 },
      { _time: '2024-01-02T00:00:00Z', consumption: 15, cost: 4.5, unit_price: 0.3, unit_price_vat: 0.357 },
    ]);

    const request = createRequest();
    const response = await GET(request);
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.costs).toHaveLength(2);
  });

  it('should skip rows with missing consumption', async () => {
    const mockQueryApi = mockInflux.getMockQueryApi();
    mockQueryApi.setMockData([
      { _time: '2024-01-01T00:00:00Z', consumption: 10, cost: 3 },
      { _time: '2024-01-02T00:00:00Z', cost: 6 },
      { _time: '2024-01-03T00:00:00Z', consumption: 15, cost: 4.5 },
    ]);

    const request = createRequest();
    const response = await GET(request);
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.costs).toHaveLength(2);
  });

  it('should handle invalid numeric values gracefully', async () => {
    const mockQueryApi = mockInflux.getMockQueryApi();
    mockQueryApi.setMockData([
      { _time: '2024-01-01T00:00:00Z', consumption: 'invalid', cost: 'invalid', unit_price: 0.3, unit_price_vat: 0.357 },
      { _time: '2024-01-02T00:00:00Z', consumption: 10, cost: 3, unit_price: 0.3, unit_price_vat: 0.357 },
    ]);

    const request = createRequest();
    const response = await GET(request);
    const data = await response.json();

    expect(response.status).toBe(200);
    // First row should be skipped due to both consumption and cost being invalid
    expect(data.costs).toHaveLength(1);
    expect(data.costs[0].consumption).toBe(10);
  });

  it('should default NaN values to 0', async () => {
    const mockQueryApi = mockInflux.getMockQueryApi();
    mockQueryApi.setMockData([
      { _time: '2024-01-01T00:00:00Z', consumption: 10, cost: 'invalid', unit_price: 'invalid', unit_price_vat: 'invalid' },
    ]);

    const request = createRequest();
    const response = await GET(request);
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.costs).toHaveLength(1);
    expect(data.costs[0].consumption).toBe(10);
    expect(data.costs[0].cost).toBe(0);
    expect(data.costs[0].unit_price).toBe(0);
    expect(data.costs[0].unit_price_vat).toBe(0);
  });

  it('should handle query errors', async () => {
    const mockQueryApi = mockInflux.getMockQueryApi();
    mockQueryApi.setShouldError(true, 'Database connection lost');

    const request = createRequest();
    const response = await GET(request);
    const data = await response.json();

    expect(response.status).toBe(500);
    expect(data.error).toBe('Database connection lost');
  });

  it('should handle exceptions gracefully', async () => {
    const { getInfluxClient } = require('@/lib/influxdb');
    getInfluxClient.mockImplementationOnce(() => {
      throw new Error('Config error');
    });

    const request = createRequest();
    const response = await GET(request);
    const data = await response.json();

    expect(response.status).toBe(500);
    expect(data.error).toBe('Failed to fetch cost data');
  });
});
