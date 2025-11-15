/**
 * Unit tests for /api/readings route
 */

import { GET } from '@/app/api/readings/route';
import { NextRequest } from 'next/server';
import { MockInfluxDB } from '@/__tests__/mocks/influxdb';
import { generateMeterReadings, createMockInfluxRows } from '@/__tests__/fixtures/meterData';

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

describe('/api/readings', () => {
  beforeAll(() => {
    mockInflux = new MockInfluxDB();
  });

  beforeEach(() => {
    mockInflux.getMockQueryApi().setMockData([]);
    mockInflux.getMockQueryApi().setShouldError(false);
  });

  function createRequest(params: Record<string, string>): NextRequest {
    const url = new URL('http://localhost:3000/api/readings');
    Object.entries(params).forEach(([key, value]) => {
      url.searchParams.set(key, value);
    });
    return new NextRequest(url);
  }

  it('should return error when meterId is missing', async () => {
    const request = createRequest({});
    const response = await GET(request);
    const data = await response.json();

    expect(response.status).toBe(400);
    expect(data.error).toBe('meterId is required');
  });

  it('should fetch raw readings for a meter', async () => {
    const mockReadings = generateMeterReadings({
      days: 5,
      meterId: 'strom_total',
    });

    const mockQueryApi = mockInflux.getMockQueryApi();
    mockQueryApi.setMockData(createMockInfluxRows(mockReadings));

    const request = createRequest({ meterId: 'strom_total', dataType: 'raw' });
    const response = await GET(request);
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.readings).toHaveLength(5);
    expect(data.dataType).toBe('raw');
    expect(data.readings[0]).toHaveProperty('timestamp');
    expect(data.readings[0]).toHaveProperty('value');
  });

  it('should fetch interpolated_daily readings', async () => {
    const mockReadings = generateMeterReadings({
      days: 10,
      meterId: 'gas_total',
    });

    const mockQueryApi = mockInflux.getMockQueryApi();
    mockQueryApi.setMockData(createMockInfluxRows(mockReadings));

    const request = createRequest({ meterId: 'gas_total', dataType: 'interpolated_daily' });
    const response = await GET(request);
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.readings).toHaveLength(10);
    expect(data.dataType).toBe('interpolated_daily');
  });

  it('should fetch consumption data', async () => {
    const mockReadings = generateMeterReadings({
      days: 7,
      meterId: 'wasser',
    });

    const mockQueryApi = mockInflux.getMockQueryApi();
    mockQueryApi.setMockData(createMockInfluxRows(mockReadings));

    const request = createRequest({ meterId: 'wasser', dataType: 'consumption' });
    const response = await GET(request);
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.readings).toHaveLength(7);
    expect(data.dataType).toBe('consumption');
  });

  it('should use default dataType of raw when not specified', async () => {
    const mockQueryApi = mockInflux.getMockQueryApi();
    mockQueryApi.setMockData([]);

    const request = createRequest({ meterId: 'strom_total' });
    const response = await GET(request);
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.dataType).toBe('raw');
  });

  it('should skip rows with missing timestamp', async () => {
    const mockQueryApi = mockInflux.getMockQueryApi();
    mockQueryApi.setMockData([
      { _time: '2024-01-01T00:00:00Z', _value: 100, entity_id: 'test' },
      { _time: null, _value: 200, entity_id: 'test' },
      { _time: '2024-01-02T00:00:00Z', _value: 300, entity_id: 'test' },
    ]);

    const request = createRequest({ meterId: 'test', dataType: 'raw' });
    const response = await GET(request);
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.readings).toHaveLength(2);
  });

  it('should skip rows with missing or invalid value', async () => {
    const mockQueryApi = mockInflux.getMockQueryApi();
    mockQueryApi.setMockData([
      { _time: '2024-01-01T00:00:00Z', _value: 100, entity_id: 'test' },
      { _time: '2024-01-02T00:00:00Z', _value: null, entity_id: 'test' },
      { _time: '2024-01-03T00:00:00Z', _value: 'invalid', entity_id: 'test' },
      { _time: '2024-01-04T00:00:00Z', _value: 400, entity_id: 'test' },
    ]);

    const request = createRequest({ meterId: 'test', dataType: 'raw' });
    const response = await GET(request);
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.readings).toHaveLength(2);
    expect(data.readings[0].value).toBe(100);
    expect(data.readings[1].value).toBe(400);
  });

  it('should handle custom date ranges', async () => {
    const mockQueryApi = mockInflux.getMockQueryApi();
    mockQueryApi.setMockData([]);

    const request = createRequest({
      meterId: 'strom_total',
      startDate: '2024-01-01T00:00:00Z',
      endDate: '2024-12-31T23:59:59Z',
    });
    const response = await GET(request);

    expect(response.status).toBe(200);
  });

  it('should handle query errors', async () => {
    const mockQueryApi = mockInflux.getMockQueryApi();
    mockQueryApi.setShouldError(true, 'Query timeout');

    const request = createRequest({ meterId: 'strom_total' });
    const response = await GET(request);
    const data = await response.json();

    expect(response.status).toBe(500);
    expect(data.error).toBe('Query timeout');
  });

  it('should handle exceptions gracefully', async () => {
    const { getInfluxClient } = require('@/lib/influxdb');
    getInfluxClient.mockImplementationOnce(() => {
      throw new Error('Config error');
    });

    const request = createRequest({ meterId: 'test' });
    const response = await GET(request);
    const data = await response.json();

    expect(response.status).toBe(500);
    expect(data.error).toBe('Failed to fetch readings');
  });
});
