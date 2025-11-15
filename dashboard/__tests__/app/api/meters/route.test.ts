/**
 * Unit tests for /api/meters route
 */

import { GET } from '@/app/api/meters/route';
import { MockInfluxDB } from '@/__tests__/mocks/influxdb';

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

describe('/api/meters', () => {
  beforeAll(() => {
    mockInflux = new MockInfluxDB();
  });

  beforeEach(() => {
    // Reset mock data before each test
    mockInflux.getMockQueryApi().setMockData([]);
    mockInflux.getMockQueryApi().setShouldError(false);
  });

  it('should return list of meters sorted alphabetically', async () => {
    const mockQueryApi = mockInflux.getMockQueryApi();
    mockQueryApi.setMockData([
      { meter_id: 'gas_total' },
      { meter_id: 'strom_total' },
      { meter_id: 'wasser' },
    ]);

    const response = await GET();
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.meters).toEqual(['gas_total', 'strom_total', 'wasser']);
  });

  it('should handle duplicate meter_ids', async () => {
    const mockQueryApi = mockInflux.getMockQueryApi();
    mockQueryApi.setMockData([
      { meter_id: 'gas_total' },
      { meter_id: 'gas_total' },
      { meter_id: 'strom_total' },
    ]);

    const response = await GET();
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.meters).toEqual(['gas_total', 'gas_total', 'strom_total']);
  });

  it('should skip rows with missing meter_id', async () => {
    const mockQueryApi = mockInflux.getMockQueryApi();
    mockQueryApi.setMockData([
      { meter_id: 'gas_total' },
      { meter_id: null },
      { meter_id: 'strom_total' },
      {},
    ]);

    const response = await GET();
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.meters).toEqual(['gas_total', 'strom_total']);
  });

  it('should skip rows with non-string meter_id', async () => {
    const mockQueryApi = mockInflux.getMockQueryApi();
    mockQueryApi.setMockData([
      { meter_id: 'gas_total' },
      { meter_id: 123 },
      { meter_id: 'strom_total' },
    ]);

    const response = await GET();
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.meters).toEqual(['gas_total', 'strom_total']);
  });

  it('should return empty array when no meters found', async () => {
    const mockQueryApi = mockInflux.getMockQueryApi();
    mockQueryApi.setMockData([]);

    const response = await GET();
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.meters).toEqual([]);
  });

  it('should handle query errors', async () => {
    const mockQueryApi = mockInflux.getMockQueryApi();
    mockQueryApi.setShouldError(true, 'Database connection failed');

    const response = await GET();
    const data = await response.json();

    expect(response.status).toBe(500);
    expect(data.error).toBe('Database connection failed');
  });

  it('should handle exceptions gracefully', async () => {
    // Force an exception by mocking getInfluxClient to throw
    const { getInfluxClient } = require('@/lib/influxdb');
    getInfluxClient.mockImplementationOnce(() => {
      throw new Error('Config error');
    });

    const response = await GET();
    const data = await response.json();

    expect(response.status).toBe(500);
    expect(data.error).toBe('Failed to discover meters');
  });
});
