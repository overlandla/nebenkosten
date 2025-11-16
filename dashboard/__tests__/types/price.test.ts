/**
 * Unit tests for price type helpers
 */

import {
  getActivePriceAt,
  getPricesInRange,
  validatePriceConfig,
  PriceConfig,
  PriceConfigInput,
} from '@/types/price';

describe('price type helpers', () => {
  const mockPrices: PriceConfig[] = [
    {
      id: 'price_1',
      utilityType: 'gas',
      pricePerUnit: 0.10,
      unit: 'kWh',
      validFrom: '2024-01-01T00:00:00Z',
      validTo: '2024-06-30T23:59:59Z',
      currency: 'EUR',
      description: 'Winter gas price',
      createdAt: '2024-01-01T00:00:00Z',
      updatedAt: '2024-01-01T00:00:00Z',
    },
    {
      id: 'price_2',
      utilityType: 'gas',
      pricePerUnit: 0.08,
      unit: 'kWh',
      validFrom: '2024-07-01T00:00:00Z',
      validTo: null,
      currency: 'EUR',
      description: 'Summer gas price',
      createdAt: '2024-07-01T00:00:00Z',
      updatedAt: '2024-07-01T00:00:00Z',
    },
    {
      id: 'price_3',
      utilityType: 'water_cold',
      pricePerUnit: 2.50,
      unit: 'm³',
      validFrom: '2024-01-01T00:00:00Z',
      validTo: null,
      currency: 'EUR',
      description: 'Cold water price',
      createdAt: '2024-01-01T00:00:00Z',
      updatedAt: '2024-01-01T00:00:00Z',
    },
  ];

  describe('getActivePriceAt', () => {
    it('should return active price for given timestamp', () => {
      const timestamp = new Date('2024-03-15T12:00:00Z');
      const activePrice = getActivePriceAt(mockPrices, 'gas', timestamp);

      expect(activePrice).not.toBeNull();
      expect(activePrice?.id).toBe('price_1');
      expect(activePrice?.pricePerUnit).toBe(0.10);
    });

    it('should return summer price after transition date', () => {
      const timestamp = new Date('2024-08-15T12:00:00Z');
      const activePrice = getActivePriceAt(mockPrices, 'gas', timestamp);

      expect(activePrice).not.toBeNull();
      expect(activePrice?.id).toBe('price_2');
      expect(activePrice?.pricePerUnit).toBe(0.08);
    });

    it('should return price with no end date as active', () => {
      const timestamp = new Date('2025-01-15T12:00:00Z');
      const activePrice = getActivePriceAt(mockPrices, 'water_cold', timestamp);

      expect(activePrice).not.toBeNull();
      expect(activePrice?.id).toBe('price_3');
    });

    it('should return null if no active price exists', () => {
      const timestamp = new Date('2023-01-15T12:00:00Z');
      const activePrice = getActivePriceAt(mockPrices, 'gas', timestamp);

      expect(activePrice).toBeNull();
    });

    it('should return null for non-existent utility type', () => {
      const timestamp = new Date('2024-03-15T12:00:00Z');
      const activePrice = getActivePriceAt(mockPrices, 'heat', timestamp);

      expect(activePrice).toBeNull();
    });

    it('should return most recent price when multiple are active', () => {
      const overlappingPrices: PriceConfig[] = [
        {
          id: 'price_old',
          utilityType: 'gas',
          pricePerUnit: 0.12,
          unit: 'kWh',
          validFrom: '2024-01-01T00:00:00Z',
          validTo: null,
          currency: 'EUR',
          createdAt: '2024-01-01T00:00:00Z',
          updatedAt: '2024-01-01T00:00:00Z',
        },
        {
          id: 'price_new',
          utilityType: 'gas',
          pricePerUnit: 0.10,
          unit: 'kWh',
          validFrom: '2024-06-01T00:00:00Z',
          validTo: null,
          currency: 'EUR',
          createdAt: '2024-06-01T00:00:00Z',
          updatedAt: '2024-06-01T00:00:00Z',
        },
      ];

      const timestamp = new Date('2024-08-15T12:00:00Z');
      const activePrice = getActivePriceAt(overlappingPrices, 'gas', timestamp);

      expect(activePrice).not.toBeNull();
      expect(activePrice?.id).toBe('price_new');
    });
  });

  describe('getPricesInRange', () => {
    it('should return prices valid within date range', () => {
      const startDate = new Date('2024-01-01T00:00:00Z');
      const endDate = new Date('2024-12-31T23:59:59Z');

      const pricesInRange = getPricesInRange(mockPrices, 'gas', startDate, endDate);

      expect(pricesInRange).toHaveLength(2);
      expect(pricesInRange.map(p => p.id)).toContain('price_1');
      expect(pricesInRange.map(p => p.id)).toContain('price_2');
    });

    it('should return price that starts before range and ends within range', () => {
      const startDate = new Date('2024-03-01T00:00:00Z');
      const endDate = new Date('2024-06-15T23:59:59Z');

      const pricesInRange = getPricesInRange(mockPrices, 'gas', startDate, endDate);

      expect(pricesInRange).toHaveLength(1);
      expect(pricesInRange[0].id).toBe('price_1');
    });

    it('should include prices with no end date', () => {
      const startDate = new Date('2024-01-01T00:00:00Z');
      const endDate = new Date('2024-12-31T23:59:59Z');

      const pricesInRange = getPricesInRange(mockPrices, 'water_cold', startDate, endDate);

      expect(pricesInRange).toHaveLength(1);
      expect(pricesInRange[0].id).toBe('price_3');
    });

    it('should return empty array if no prices in range', () => {
      const startDate = new Date('2023-01-01T00:00:00Z');
      const endDate = new Date('2023-12-31T23:59:59Z');

      const pricesInRange = getPricesInRange(mockPrices, 'gas', startDate, endDate);

      expect(pricesInRange).toHaveLength(0);
    });

    it('should filter by utility type', () => {
      const startDate = new Date('2024-01-01T00:00:00Z');
      const endDate = new Date('2024-12-31T23:59:59Z');

      const gasPrices = getPricesInRange(mockPrices, 'gas', startDate, endDate);
      const waterPrices = getPricesInRange(mockPrices, 'water_cold', startDate, endDate);

      expect(gasPrices).toHaveLength(2);
      expect(waterPrices).toHaveLength(1);
    });
  });

  describe('validatePriceConfig', () => {
    it('should validate correct price config', () => {
      const config: PriceConfigInput = {
        utilityType: 'gas',
        pricePerUnit: 0.10,
        unit: 'kWh',
        validFrom: '2024-01-01T00:00:00Z',
        validTo: '2024-12-31T23:59:59Z',
        currency: 'EUR',
        description: 'Test price',
      };

      const result = validatePriceConfig(config);

      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should reject zero or negative price', () => {
      const config: PriceConfigInput = {
        utilityType: 'gas',
        pricePerUnit: 0,
        unit: 'kWh',
        validFrom: '2024-01-01T00:00:00Z',
        validTo: null,
        currency: 'EUR',
      };

      const result = validatePriceConfig(config);

      expect(result.valid).toBe(false);
      expect(result.errors).toContain('Price per unit must be greater than 0');
    });

    it('should reject negative price', () => {
      const config: PriceConfigInput = {
        utilityType: 'gas',
        pricePerUnit: -0.10,
        unit: 'kWh',
        validFrom: '2024-01-01T00:00:00Z',
        validTo: null,
        currency: 'EUR',
      };

      const result = validatePriceConfig(config);

      expect(result.valid).toBe(false);
      expect(result.errors).toContain('Price per unit must be greater than 0');
    });

    it('should reject missing unit', () => {
      const config: PriceConfigInput = {
        utilityType: 'gas',
        pricePerUnit: 0.10,
        unit: '',
        validFrom: '2024-01-01T00:00:00Z',
        validTo: null,
        currency: 'EUR',
      };

      const result = validatePriceConfig(config);

      expect(result.valid).toBe(false);
      expect(result.errors).toContain('Unit is required');
    });

    it('should reject missing validFrom', () => {
      const config: PriceConfigInput = {
        utilityType: 'gas',
        pricePerUnit: 0.10,
        unit: 'kWh',
        validFrom: '',
        validTo: null,
        currency: 'EUR',
      };

      const result = validatePriceConfig(config);

      expect(result.valid).toBe(false);
      expect(result.errors).toContain('Valid from date is required');
    });

    it('should reject validTo before validFrom', () => {
      const config: PriceConfigInput = {
        utilityType: 'gas',
        pricePerUnit: 0.10,
        unit: 'kWh',
        validFrom: '2024-12-31T23:59:59Z',
        validTo: '2024-01-01T00:00:00Z',
        currency: 'EUR',
      };

      const result = validatePriceConfig(config);

      expect(result.valid).toBe(false);
      expect(result.errors).toContain('Valid to date must be after valid from date');
    });

    it('should accept validTo = null (no expiry)', () => {
      const config: PriceConfigInput = {
        utilityType: 'gas',
        pricePerUnit: 0.10,
        unit: 'kWh',
        validFrom: '2024-01-01T00:00:00Z',
        validTo: null,
        currency: 'EUR',
      };

      const result = validatePriceConfig(config);

      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should accumulate multiple errors', () => {
      const config: PriceConfigInput = {
        utilityType: 'gas',
        pricePerUnit: 0,
        unit: '',
        validFrom: '',
        validTo: null,
        currency: 'EUR',
      };

      const result = validatePriceConfig(config);

      expect(result.valid).toBe(false);
      expect(result.errors.length).toBeGreaterThan(1);
    });
  });
});
