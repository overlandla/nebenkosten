/**
 * Price Configuration Types
 *
 * This module defines the data structures for managing utility prices
 * with time-based validity periods.
 */

export type UtilityType = 'electricity' | 'gas' | 'water_cold' | 'water_warm' | 'heat';

export interface PriceConfig {
  id: string;                // Unique identifier
  utilityType: UtilityType;  // Type of utility
  pricePerUnit: number;      // Price per unit (EUR/kWh, EUR/m³, etc.)
  unit: string;              // Unit (kWh, m³, MWh)
  validFrom: string;         // ISO timestamp - when this price becomes effective
  validTo: string | null;    // ISO timestamp - when this price expires (null = current/no expiry)
  currency: string;          // Currency code (e.g., "EUR")
  description?: string;      // Optional description/note
  createdAt: string;         // ISO timestamp
  updatedAt: string;         // ISO timestamp
}

export interface PriceConfigInput {
  utilityType: UtilityType;
  pricePerUnit: number;
  unit: string;
  validFrom: string;
  validTo: string | null;
  currency?: string;
  description?: string;
}

export interface PriceConfigUpdate {
  pricePerUnit?: number;
  unit?: string;
  validFrom?: string;
  validTo?: string | null;
  description?: string;
}

/**
 * Helper to get the active price for a utility type at a given timestamp
 */
export function getActivePriceAt(
  prices: PriceConfig[],
  utilityType: UtilityType,
  timestamp: Date
): PriceConfig | null {
  const isoTimestamp = timestamp.toISOString();

  const activePrices = prices.filter((price) => {
    if (price.utilityType !== utilityType) return false;

    // Check if timestamp is after validFrom
    if (price.validFrom > isoTimestamp) return false;

    // Check if timestamp is before validTo (if validTo exists)
    if (price.validTo && price.validTo < isoTimestamp) return false;

    return true;
  });

  // Return the most recent valid price (in case of overlaps)
  if (activePrices.length === 0) return null;

  activePrices.sort((a, b) => b.validFrom.localeCompare(a.validFrom));
  return activePrices[0];
}

/**
 * Helper to get all prices for a utility type in a time range
 */
export function getPricesInRange(
  prices: PriceConfig[],
  utilityType: UtilityType,
  startDate: Date,
  endDate: Date
): PriceConfig[] {
  const startISO = startDate.toISOString();
  const endISO = endDate.toISOString();

  return prices.filter((price) => {
    if (price.utilityType !== utilityType) return false;

    // Price is valid if:
    // - It starts before the range ends AND
    // - It ends after the range starts (or has no end date)
    const startsBeforeRangeEnds = price.validFrom <= endISO;
    const endsAfterRangeStarts = !price.validTo || price.validTo >= startISO;

    return startsBeforeRangeEnds && endsAfterRangeStarts;
  });
}

/**
 * Validates a price configuration
 */
export function validatePriceConfig(config: PriceConfigInput): { valid: boolean; errors: string[] } {
  const errors: string[] = [];

  if (config.pricePerUnit <= 0) {
    errors.push('Price per unit must be greater than 0');
  }

  if (!config.unit || config.unit.trim() === '') {
    errors.push('Unit is required');
  }

  if (!config.validFrom) {
    errors.push('Valid from date is required');
  }

  if (config.validTo && config.validTo < config.validFrom) {
    errors.push('Valid to date must be after valid from date');
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

/**
 * Default price configurations for common utilities
 */
export const DEFAULT_PRICES: Partial<Record<UtilityType, number>> = {
  gas: 0.10,          // EUR/kWh
  water_cold: 2.50,   // EUR/m³
  water_warm: 5.00,   // EUR/m³
  heat: 100.00,       // EUR/MWh
};
