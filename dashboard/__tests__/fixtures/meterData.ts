/**
 * Test fixtures for meter data
 * Inspired by Dagster mock_data.py patterns
 */

import { MeterReading, ConsumptionData, WaterTemperature, CostData } from '@/types/meter';

/**
 * Generate meter readings for testing
 */
export function generateMeterReadings(options: {
  days?: number;
  startDate?: string;
  baseValue?: number;
  increment?: number;
  meterId?: string;
}): MeterReading[] {
  const {
    days = 30,
    startDate = '2024-01-01',
    baseValue = 1000,
    increment = 5,
    meterId = 'test_meter',
  } = options;

  const readings: MeterReading[] = [];
  const start = new Date(startDate);

  for (let i = 0; i < days; i++) {
    const timestamp = new Date(start);
    timestamp.setDate(timestamp.getDate() + i);

    readings.push({
      timestamp: timestamp.toISOString(),
      value: baseValue + i * increment,
      entity_id: meterId,
    });
  }

  return readings;
}

/**
 * Generate consumption data for testing
 */
export function generateConsumptionData(options: {
  days?: number;
  startDate?: string;
  baseConsumption?: number;
  variation?: number;
  meterId?: string;
}): ConsumptionData[] {
  const {
    days = 30,
    startDate = '2024-01-01',
    baseConsumption = 10,
    variation = 2,
    meterId = 'test_meter',
  } = options;

  const consumption: ConsumptionData[] = [];
  const start = new Date(startDate);

  for (let i = 0; i < days; i++) {
    const timestamp = new Date(start);
    timestamp.setDate(timestamp.getDate() + i);

    // Add random variation
    const randomVariation = (Math.random() - 0.5) * variation * 2;
    const value = Math.max(0, baseConsumption + randomVariation);

    consumption.push({
      timestamp: timestamp.toISOString(),
      value,
      entity_id: meterId,
    });
  }

  return consumption;
}

/**
 * Generate anomaly data for testing
 */
export function generateAnomalyData(options: {
  days?: number;
  startDate?: string;
  baseConsumption?: number;
  anomalyDays?: number[];
  anomalyMultiplier?: number;
}): ConsumptionData[] {
  const {
    days = 30,
    startDate = '2024-01-01',
    baseConsumption = 10,
    anomalyDays = [],
    anomalyMultiplier = 3,
  } = options;

  const consumption: ConsumptionData[] = [];
  const start = new Date(startDate);

  for (let i = 0; i < days; i++) {
    const timestamp = new Date(start);
    timestamp.setDate(timestamp.getDate() + i);

    const isAnomaly = anomalyDays.includes(i);
    const value = isAnomaly ? baseConsumption * anomalyMultiplier : baseConsumption;

    consumption.push({
      timestamp: timestamp.toISOString(),
      value,
      entity_id: 'test_meter',
    });
  }

  return consumption;
}

/**
 * Generate multi-meter data for testing master meters
 */
export function generateMultiMeterData(options: {
  meterIds: string[];
  days?: number;
  startDate?: string;
}): Record<string, MeterReading[]> {
  const { meterIds, days = 30, startDate = '2024-01-01' } = options;

  const result: Record<string, MeterReading[]> = {};

  meterIds.forEach((meterId, index) => {
    result[meterId] = generateMeterReadings({
      days,
      startDate,
      baseValue: 1000 + index * 100,
      increment: 5 + index,
      meterId,
    });
  });

  return result;
}

/**
 * Generate water temperature data
 */
export function generateWaterTemperature(options: {
  days?: number;
  startDate?: string;
  baseTempCelsius?: number;
  lake?: string;
}): WaterTemperature[] {
  const {
    days = 30,
    startDate = '2024-01-01',
    baseTempCelsius = 15,
    lake = 'test_lake',
  } = options;

  const temperatures: WaterTemperature[] = [];
  const start = new Date(startDate);

  for (let i = 0; i < days; i++) {
    const timestamp = new Date(start);
    timestamp.setDate(timestamp.getDate() + i);

    // Simulate seasonal variation
    const seasonalVariation = Math.sin((i / 365) * 2 * Math.PI) * 5;
    const value = baseTempCelsius + seasonalVariation;

    temperatures.push({
      timestamp: timestamp.toISOString(),
      value,
      lake,
      entity_id: `${lake}_temp`,
    });
  }

  return temperatures;
}

/**
 * Generate cost data
 */
export function generateCostData(options: {
  days?: number;
  startDate?: string;
  baseConsumption?: number;
  unitPrice?: number;
  vatRate?: number;
}): CostData[] {
  const {
    days = 30,
    startDate = '2024-01-01',
    baseConsumption = 10,
    unitPrice = 0.30,
    vatRate = 0.19,
  } = options;

  const costs: CostData[] = [];
  const start = new Date(startDate);

  for (let i = 0; i < days; i++) {
    const timestamp = new Date(start);
    timestamp.setDate(timestamp.getDate() + i);

    const consumption = baseConsumption + (Math.random() - 0.5) * 2;
    const cost = consumption * unitPrice;
    const unit_price_vat = unitPrice * (1 + vatRate);

    costs.push({
      timestamp: timestamp.toISOString(),
      consumption,
      cost,
      unit_price: unitPrice,
      unit_price_vat,
    });
  }

  return costs;
}

/**
 * Create mock InfluxDB row data for queryRows callback
 */
export function createMockInfluxRows(data: any[]): any[] {
  return data.map((item) => ({
    _time: item.timestamp,
    _value: item.value,
    _field: 'value',
    entity_id: item.entity_id,
    meter_id: item.meter_id || item.entity_id,
    lake: item.lake,
    consumption: item.consumption,
    cost: item.cost,
    unit_price: item.unit_price,
    unit_price_vat: item.unit_price_vat,
  }));
}
