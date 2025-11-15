/**
 * Unit tests for /api/water-temp route
 */

import { GET } from '@/app/api/water-temp/route';
import { NextRequest } from 'next/server';
import { MockInfluxDB } from '@/__tests__/mocks/influxdb';
import { generateWaterTemperature, createMockInfluxRows } from '@/__tests__/fixtures/meterData';

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

describe('/api/water-temp', () => {
  beforeAll(() => {
    mockInflux = new MockInfluxDB();
  });

  beforeEach(() => {
    mockInflux.getMockQueryApi().setMockData([]);
    mockInflux.getMockQueryApi().setShouldError(false);
  });

  function createRequest(params: Record<string, string> = {}): NextRequest {
    const url = new URL('http://localhost:3000/api/water-temp');
    Object.entries(params).forEach(([key, value]) => {
      url.searchParams.set(key, value);
    });
    return new NextRequest(url);
  }

  it('should fetch water temperature data with default parameters', async () => {
    const mockTemps = generateWaterTemperature({
      days: 7,
      lake: 'Bodensee',
    });

    const mockQueryApi = mockInflux.getMockQueryApi();
    mockQueryApi.setMockData(createMockInfluxRows(mockTemps));

    const request = createRequest();
    const response = await GET(request);
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.temperatures).toHaveLength(7);
    expect(data.temperatures[0]).toHaveProperty('timestamp');
    expect(data.temperatures[0]).toHaveProperty('value');
    expect(data.temperatures[0]).toHaveProperty('lake');
  });

  it('should handle custom date ranges', async () => {
    const mockTemps = generateWaterTemperature({
      days: 30,
      lake: 'Bodensee',
    });

    const mockQueryApi = mockInflux.getMockQueryApi();
    mockQueryApi.setMockData(createMockInfluxRows(mockTemps));

    const request = createRequest({
      startDate: '2024-01-01T00:00:00Z',
      endDate: '2024-01-31T23:59:59Z',
    });
    const response = await GET(request);
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.temperatures).toHaveLength(30);
  });

  it('should handle multiple lakes', async () => {
    const bodensee = generateWaterTemperature({ days: 5, lake: 'Bodensee' });
    const zurich = generateWaterTemperature({ days: 5, lake: 'Zurich' });

    const mockQueryApi = mockInflux.getMockQueryApi();
    mockQueryApi.setMockData([
      ...createMockInfluxRows(bodensee),
      ...createMockInfluxRows(zurich),
    ]);

    const request = createRequest();
    const response = await GET(request);
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.temperatures).toHaveLength(10);

    const lakes = new Set(data.temperatures.map((t: any) => t.lake));
    expect(lakes.size).toBeGreaterThan(1);
  });

  it('should skip rows with missing timestamp', async () => {
    const mockQueryApi = mockInflux.getMockQueryApi();
    mockQueryApi.setMockData([
      { _time: '2024-01-01T00:00:00Z', _value: 15.5, lake: 'Bodensee' },
      { _time: null, _value: 16.0, lake: 'Bodensee' },
      { _time: '2024-01-02T00:00:00Z', _value: 16.5, lake: 'Bodensee' },
    ]);

    const request = createRequest();
    const response = await GET(request);
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.temperatures).toHaveLength(2);
  });

  it('should skip rows with missing value', async () => {
    const mockQueryApi = mockInflux.getMockQueryApi();
    mockQueryApi.setMockData([
      { _time: '2024-01-01T00:00:00Z', _value: 15.5, lake: 'Bodensee' },
      { _time: '2024-01-02T00:00:00Z', _value: null, lake: 'Bodensee' },
      { _time: '2024-01-03T00:00:00Z', _value: 16.5, lake: 'Bodensee' },
    ]);

    const request = createRequest();
    const response = await GET(request);
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.temperatures).toHaveLength(2);
  });

  it('should skip rows with missing lake', async () => {
    const mockQueryApi = mockInflux.getMockQueryApi();
    mockQueryApi.setMockData([
      { _time: '2024-01-01T00:00:00Z', _value: 15.5, lake: 'Bodensee' },
      { _time: '2024-01-02T00:00:00Z', _value: 16.0, lake: null },
      { _time: '2024-01-03T00:00:00Z', _value: 16.5, lake: '' },
      { _time: '2024-01-04T00:00:00Z', _value: 17.0, lake: 'Zurich' },
    ]);

    const request = createRequest();
    const response = await GET(request);
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.temperatures).toHaveLength(2);
  });

  it('should skip rows with invalid numeric value', async () => {
    const mockQueryApi = mockInflux.getMockQueryApi();
    mockQueryApi.setMockData([
      { _time: '2024-01-01T00:00:00Z', _value: 15.5, lake: 'Bodensee' },
      { _time: '2024-01-02T00:00:00Z', _value: 'invalid', lake: 'Bodensee' },
      { _time: '2024-01-03T00:00:00Z', _value: 16.5, lake: 'Bodensee' },
    ]);

    const request = createRequest();
    const response = await GET(request);
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.temperatures).toHaveLength(2);
    expect(data.temperatures[0].value).toBe(15.5);
    expect(data.temperatures[1].value).toBe(16.5);
  });

  it('should include entity_id when present', async () => {
    const mockQueryApi = mockInflux.getMockQueryApi();
    mockQueryApi.setMockData([
      { _time: '2024-01-01T00:00:00Z', _value: 15.5, lake: 'Bodensee', entity_id: 'bodensee_temp' },
    ]);

    const request = createRequest();
    const response = await GET(request);
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.temperatures[0].entity_id).toBe('bodensee_temp');
  });

  it('should handle query errors', async () => {
    const mockQueryApi = mockInflux.getMockQueryApi();
    mockQueryApi.setShouldError(true, 'Network timeout');

    const request = createRequest();
    const response = await GET(request);
    const data = await response.json();

    expect(response.status).toBe(500);
    expect(data.error).toBe('Network timeout');
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
    expect(data.error).toBe('Failed to fetch water temperatures');
  });

  it('should return empty array when no data found', async () => {
    const mockQueryApi = mockInflux.getMockQueryApi();
    mockQueryApi.setMockData([]);

    const request = createRequest();
    const response = await GET(request);
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.temperatures).toEqual([]);
  });
});
