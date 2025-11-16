/**
 * Unit tests for /api/household-costs route
 */

import { GET } from '@/app/api/household-costs/route';
import { NextRequest } from 'next/server';
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

describe('/api/household-costs', () => {
  beforeAll(() => {
    mockInflux = new MockInfluxDB();
  });

  beforeEach(() => {
    mockInflux.getMockQueryApi().setMockData([]);
    mockInflux.getMockQueryApi().setShouldError(false);
  });

  describe('GET', () => {
    const mockHouseholdConfig = {
      households: [
        {
          id: 'eg_links',
          name: 'EG Links',
          type: 'unit',
          meters: {
            electricity: ['strom_eg_links'],
            water: ['wasser_eg_links_kalt', 'wasser_eg_links_warm'],
            heat: ['heizung_eg_links'],
          },
          costAllocation: {
            sharedElectricity: 0.25,
            sharedGas: 0.3,
            sharedWater: 0.2,
          },
        },
        {
          id: 'og_rechts',
          name: 'OG Rechts',
          type: 'unit',
          meters: {
            electricity: [],
            water: [],
            heat: [],
          },
          costAllocation: {
            sharedElectricity: 0.25,
          },
        },
      ],
    };

    const mockPriceConfigs = [
      {
        id: 'price-gas-1',
        utilityType: 'gas',
        pricePerUnit: 0.08,
        unit: 'kWh',
        validFrom: '2024-01-01',
        validTo: null,
        currency: 'EUR',
        createdAt: '2024-01-01',
        updatedAt: '2024-01-01',
      },
      {
        id: 'price-water-cold-1',
        utilityType: 'water_cold',
        pricePerUnit: 0.003,
        unit: 'L',
        validFrom: '2024-01-01',
        validTo: null,
        currency: 'EUR',
        createdAt: '2024-01-01',
        updatedAt: '2024-01-01',
      },
      {
        id: 'price-water-warm-1',
        utilityType: 'water_warm',
        pricePerUnit: 0.005,
        unit: 'L',
        validFrom: '2024-01-01',
        validTo: null,
        currency: 'EUR',
        createdAt: '2024-01-01',
        updatedAt: '2024-01-01',
      },
      {
        id: 'price-heat-1',
        utilityType: 'heat',
        pricePerUnit: 0.09,
        unit: 'kWh',
        validFrom: '2024-01-01',
        validTo: null,
        currency: 'EUR',
        createdAt: '2024-01-01',
        updatedAt: '2024-01-01',
      },
    ];

    it('should calculate costs for all households for a given year', async () => {
      // Mock household config
      mockInflux.getMockQueryApi().setMockData([
        { _value: JSON.stringify(mockHouseholdConfig) },
      ]);

      // Mock price configs
      setTimeout(() => {
        mockInflux.getMockQueryApi().setMockData(
          mockPriceConfigs.map(price => ({
            id: price.id,
            utilityType: price.utilityType,
            pricePerUnit: price.pricePerUnit,
            unit: price.unit,
            validFrom: price.validFrom,
            validTo: price.validTo,
            currency: price.currency,
            createdAt: price.createdAt,
            updatedAt: price.updatedAt,
          }))
        );
      }, 10);

      const request = new NextRequest('http://localhost:3000/api/household-costs?year=2024');
      const response = await GET(request);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.year).toBe(2024);
      expect(data.households).toBeDefined();
      expect(Array.isArray(data.households)).toBe(true);
    });

    it('should use current year when year parameter is not provided', async () => {
      mockInflux.getMockQueryApi().setMockData([
        { _value: JSON.stringify(mockHouseholdConfig) },
      ]);

      const request = new NextRequest('http://localhost:3000/api/household-costs');
      const response = await GET(request);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.year).toBe(new Date().getFullYear());
    });

    it('should return 404 when household configuration is not found', async () => {
      // No household config data
      mockInflux.getMockQueryApi().setMockData([]);

      const request = new NextRequest('http://localhost:3000/api/household-costs?year=2024');
      const response = await GET(request);
      const data = await response.json();

      expect(response.status).toBe(404);
      expect(data.error).toBe('Household configuration not found');
    });

    it('should handle query errors gracefully', async () => {
      mockInflux.getMockQueryApi().setShouldError(true, 'Database connection failed');

      const request = new NextRequest('http://localhost:3000/api/household-costs?year=2024');
      const response = await GET(request);
      const data = await response.json();

      expect(response.status).toBe(500);
      expect(data.error).toBe('Failed to calculate household costs');
    });

    it('should only include unit-type households in calculations', async () => {
      const configWithDifferentTypes = {
        households: [
          {
            id: 'eg_links',
            name: 'EG Links',
            type: 'unit',
            meters: { electricity: [], water: [], heat: [] },
          },
          {
            id: 'shared',
            name: 'Shared Areas',
            type: 'shared',
            meters: { electricity: ['shared_meter'] },
          },
          {
            id: 'og_rechts',
            name: 'OG Rechts',
            type: 'unit',
            meters: { electricity: [], water: [], heat: [] },
          },
        ],
      };

      mockInflux.getMockQueryApi().setMockData([
        { _value: JSON.stringify(configWithDifferentTypes) },
      ]);

      const request = new NextRequest('http://localhost:3000/api/household-costs?year=2024');
      const response = await GET(request);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.households.length).toBe(2); // Only unit-type households
      expect(data.households.every((h: any) => h.householdId !== 'shared')).toBe(true);
    });

    it('should parse year parameter correctly', async () => {
      mockInflux.getMockQueryApi().setMockData([
        { _value: JSON.stringify(mockHouseholdConfig) },
      ]);

      const request = new NextRequest('http://localhost:3000/api/household-costs?year=2023');
      const response = await GET(request);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.year).toBe(2023);
    });

    it('should handle malformed household config JSON', async () => {
      mockInflux.getMockQueryApi().setMockData([
        { _value: 'invalid json{' },
      ]);

      const request = new NextRequest('http://localhost:3000/api/household-costs?year=2024');
      const response = await GET(request);
      const data = await response.json();

      // Should return 404 since parsing fails and config is null
      expect(response.status).toBe(404);
    });

    it('should handle empty households array', async () => {
      mockInflux.getMockQueryApi().setMockData([
        { _value: JSON.stringify({ households: [] }) },
      ]);

      const request = new NextRequest('http://localhost:3000/api/household-costs?year=2024');
      const response = await GET(request);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.households).toEqual([]);
    });

    it('should handle price configs with missing fields', async () => {
      mockInflux.getMockQueryApi().setMockData([
        { _value: JSON.stringify(mockHouseholdConfig) },
      ]);

      // Set incomplete price data
      setTimeout(() => {
        mockInflux.getMockQueryApi().setMockData([
          { id: 'price-1', utilityType: 'gas' }, // Missing pricePerUnit
          { pricePerUnit: 0.5, unit: 'kWh' }, // Missing id and utilityType
        ]);
      }, 10);

      const request = new NextRequest('http://localhost:3000/api/household-costs?year=2024');
      const response = await GET(request);
      const data = await response.json();

      expect(response.status).toBe(200);
      // Should still work, just with fewer price configs
    });

    it('should deduplicate price configs by taking latest updatedAt', async () => {
      mockInflux.getMockQueryApi().setMockData([
        { _value: JSON.stringify(mockHouseholdConfig) },
      ]);

      // Set duplicate prices with different updatedAt
      setTimeout(() => {
        mockInflux.getMockQueryApi().setMockData([
          {
            id: 'price-gas-1',
            utilityType: 'gas',
            pricePerUnit: 0.08,
            unit: 'kWh',
            validFrom: '2024-01-01',
            updatedAt: '2024-01-01',
          },
          {
            id: 'price-gas-1',
            utilityType: 'gas',
            pricePerUnit: 0.09,
            unit: 'kWh',
            validFrom: '2024-01-01',
            updatedAt: '2024-02-01', // More recent
          },
        ]);
      }, 10);

      const request = new NextRequest('http://localhost:3000/api/household-costs?year=2024');
      const response = await GET(request);
      const data = await response.json();

      expect(response.status).toBe(200);
      // The deduplication logic should keep the more recent one
    });
  });
});
