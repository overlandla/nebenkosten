/**
 * Centralized type definitions for meter data and API responses
 */

// ============================================================================
// Base Meter Data Types
// ============================================================================

export interface MeterReading {
  timestamp: string;
  value: number;
  entity_id?: string;
}

export interface ConsumptionData {
  timestamp: string;
  value: number;
  entity_id?: string;
}

export interface WaterTemperature {
  timestamp: string;
  value: number;
  lake: string;
  entity_id?: string;
}

export interface CostData {
  timestamp: string;
  consumption: number;    // kWh
  cost: number;          // EUR
  unit_price: number;    // EUR/kWh
  unit_price_vat: number; // EUR/kWh including VAT
}

// ============================================================================
// InfluxDB Types
// ============================================================================

export interface InfluxRow {
  _time: string;
  _value: string | number;
  _field: string;
  _measurement?: string;
  entity_id?: string;
  meter_id?: string;
  lake?: string;
  consumption?: string | number;
  cost?: string | number;
  unit_price?: string | number;
  unit_price_vat?: string | number;
  [key: string]: string | number | undefined;
}

export interface InfluxTableMeta {
  toObject(row: string[]): InfluxRow;
}

// ============================================================================
// Meter Configuration Types
// ============================================================================

export type MeterCategory = 'electricity' | 'gas' | 'water' | 'heat' | 'solar' | 'virtual';
export type MeterType = 'physical' | 'master' | 'virtual';

export interface MeterConfig {
  id: string;
  unit: string;
  name: string;
  category: MeterCategory;
  type: MeterType;
}

// ============================================================================
// Chart Data Types
// ============================================================================

export interface FloorMeter {
  id: string;
  name: string;
  floor: string;
  color: string;
}

export interface ChartMeterData {
  [meterId: string]: MeterReading[];
}

// ============================================================================
// API Response Types
// ============================================================================

export interface ReadingsAPIResponse {
  readings: MeterReading[];
  dataType?: string;
}

export interface MetersAPIResponse {
  meters: string[];
}

export interface WaterTempAPIResponse {
  temperatures: WaterTemperature[];
}

export interface CostsAPIResponse {
  costs: CostData[];
  aggregation?: string;
}

export interface APIError {
  error: string;
}
