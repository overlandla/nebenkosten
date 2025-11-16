import { NextRequest, NextResponse } from 'next/server';
import { getInfluxClient, getInfluxConfig } from '@/lib/influxdb';
import type { PriceConfig } from '@/types/price';
import type { HouseholdConfig } from '@/types/household';

interface HouseholdCosts {
  householdId: string;
  householdName: string;
  year: number;
  monthlyBreakdown: MonthlyHouseholdCost[];
  annualTotals: {
    electricityCost: number;
    electricityConsumption: number;
    gasCost: number;
    gasConsumption: number;
    waterColdCost: number;
    waterColdConsumption: number;
    waterWarmCost: number;
    waterWarmConsumption: number;
    heatCost: number;
    heatConsumption: number;
    totalCost: number;
  };
}

interface MonthlyHouseholdCost {
  month: string;  // YYYY-MM
  electricityCost: number;
  electricityConsumption: number;
  gasCost: number;
  gasConsumption: number;
  waterColdCost: number;
  waterColdConsumption: number;
  waterWarmCost: number;
  waterWarmConsumption: number;
  heatCost: number;
  heatConsumption: number;
  totalCost: number;
}

/**
 * GET /api/household-costs?year=2024
 * Calculate costs for all households for a given year
 */
export async function GET(request: NextRequest): Promise<NextResponse> {
  try {
    const searchParams = request.nextUrl.searchParams;
    const year = parseInt(searchParams.get('year') || new Date().getFullYear().toString());

    const influx = getInfluxClient();
    const config = getInfluxConfig();

    // 1. Fetch household configuration
    const householdConfig = await fetchHouseholdConfig(influx, config);
    if (!householdConfig) {
      return NextResponse.json(
        { error: 'Household configuration not found' },
        { status: 404 }
      );
    }

    // 2. Fetch price configurations
    const prices = await fetchPriceConfigs(influx, config);

    // 3. Calculate costs for each household
    const householdCosts: HouseholdCosts[] = [];

    for (const household of householdConfig.households.filter(h => h.type === 'unit')) {
      const costs = await calculateHouseholdCosts(
        household.id,
        household.name,
        household,
        year,
        prices,
        influx,
        config
      );
      householdCosts.push(costs);
    }

    return NextResponse.json({
      year,
      households: householdCosts,
    });
  } catch (error) {
    console.error('Error calculating household costs:', error);
    return NextResponse.json(
      { error: 'Failed to calculate household costs' },
      { status: 500 }
    );
  }
}

async function fetchHouseholdConfig(influx: any, config: any): Promise<HouseholdConfig | null> {
  const queryApi = influx.getQueryApi(config.org);

  const query = `
    from(bucket: "${config.bucketRaw}")
      |> range(start: 0)
      |> filter(fn: (r) => r["_measurement"] == "household_config")
      |> filter(fn: (r) => r["_field"] == "config_json")
      |> last()
  `;

  let householdConfig: HouseholdConfig | null = null;

  await new Promise<void>((resolve, reject) => {
    queryApi.queryRows(query, {
      next(row: string[], tableMeta: any) {
        try {
          const o = tableMeta.toObject(row) as any;
          if (o._value) {
            householdConfig = JSON.parse(String(o._value));
          }
        } catch (error) {
          console.error('Error parsing household config:', error);
        }
      },
      error: reject,
      complete: resolve,
    });
  });

  return householdConfig;
}

async function fetchPriceConfigs(influx: any, config: any): Promise<PriceConfig[]> {
  const queryApi = influx.getQueryApi(config.org);

  const query = `
    from(bucket: "${config.bucketRaw}")
      |> range(start: 0)
      |> filter(fn: (r) => r["_measurement"] == "price_config")
      |> pivot(rowKey:["_time", "id"], columnKey: ["_field"], valueColumn: "_value")
      |> sort(columns: ["_time"], desc: true)
  `;

  const prices: PriceConfig[] = [];

  await new Promise<void>((resolve, reject) => {
    queryApi.queryRows(query, {
      next(row: string[], tableMeta: any) {
        try {
          const o = tableMeta.toObject(row) as any;

          if (!o.id || !o.utilityType || o.pricePerUnit === undefined) {
            return;
          }

          const priceConfig: PriceConfig = {
            id: String(o.id),
            utilityType: String(o.utilityType) as any,
            pricePerUnit: parseFloat(o.pricePerUnit),
            unit: String(o.unit || ''),
            validFrom: String(o.validFrom || o._time),
            validTo: o.validTo ? String(o.validTo) : null,
            currency: String(o.currency || 'EUR'),
            description: o.description ? String(o.description) : undefined,
            createdAt: String(o.createdAt || o._time),
            updatedAt: String(o.updatedAt || o._time),
          };

          prices.push(priceConfig);
        } catch (error) {
          console.error('Error processing price config row:', error);
        }
      },
      error: reject,
      complete: resolve,
    });
  });

  // Remove duplicates
  const uniquePrices = Array.from(
    prices
      .reduce((map, price) => {
        const existing = map.get(price.id);
        if (!existing || price.updatedAt > existing.updatedAt) {
          map.set(price.id, price);
        }
        return map;
      }, new Map<string, PriceConfig>())
      .values()
  );

  return uniquePrices;
}

async function calculateHouseholdCosts(
  householdId: string,
  householdName: string,
  household: any,
  year: number,
  prices: PriceConfig[],
  influx: any,
  config: any
): Promise<HouseholdCosts> {
  const monthlyBreakdown: MonthlyHouseholdCost[] = [];

  // Initialize annual totals
  const annualTotals = {
    electricityCost: 0,
    electricityConsumption: 0,
    gasCost: 0,
    gasConsumption: 0,
    waterColdCost: 0,
    waterColdConsumption: 0,
    waterWarmCost: 0,
    waterWarmConsumption: 0,
    heatCost: 0,
    heatConsumption: 0,
    totalCost: 0,
  };

  // Process each month
  for (let month = 1; month <= 12; month++) {
    const monthStr = `${year}-${month.toString().padStart(2, '0')}`;

    const monthlyCost: MonthlyHouseholdCost = {
      month: monthStr,
      electricityCost: 0,
      electricityConsumption: 0,
      gasCost: 0,
      gasConsumption: 0,
      waterColdCost: 0,
      waterColdConsumption: 0,
      waterWarmCost: 0,
      waterWarmConsumption: 0,
      heatCost: 0,
      heatConsumption: 0,
      totalCost: 0,
    };

    // Calculate electricity costs (using Tibber prices for direct meters, allocation for shared)
    if (household.meters.electricity?.length > 0) {
      const elecCost = await calculateElectricityCost(
        household.meters.electricity,
        monthStr,
        influx,
        config
      );
      monthlyCost.electricityCost += elecCost.cost;
      monthlyCost.electricityConsumption += elecCost.consumption;
    }

    // Add shared electricity allocation
    if (household.costAllocation?.sharedElectricity) {
      const sharedElec = await calculateSharedElectricityCost(
        monthStr,
        household.costAllocation.sharedElectricity,
        influx,
        config
      );
      monthlyCost.electricityCost += sharedElec.cost;
      monthlyCost.electricityConsumption += sharedElec.consumption;
    }

    // Calculate gas costs (using custom prices + allocation)
    const gasPrice = getActivePriceForMonth(prices, 'gas', monthStr);
    if (gasPrice && household.costAllocation?.sharedGas) {
      const gasCost = await calculateSharedUtilityCost(
        'gas_total',
        monthStr,
        household.costAllocation.sharedGas,
        gasPrice.pricePerUnit,
        influx,
        config
      );
      monthlyCost.gasCost = gasCost.cost;
      monthlyCost.gasConsumption = gasCost.consumption;
    }

    // Calculate water costs (cold and warm)
    const waterColdPrice = getActivePriceForMonth(prices, 'water_cold', monthStr);
    const waterWarmPrice = getActivePriceForMonth(prices, 'water_warm', monthStr);

    if (household.meters.water?.length > 0) {
      for (const meterId of household.meters.water) {
        if (meterId.includes('kalt') && waterColdPrice) {
          const cost = await calculateMeterCost(meterId, monthStr, waterColdPrice.pricePerUnit, influx, config);
          monthlyCost.waterColdCost += cost.cost;
          monthlyCost.waterColdConsumption += cost.consumption;
        } else if (meterId.includes('warm') && waterWarmPrice) {
          const cost = await calculateMeterCost(meterId, monthStr, waterWarmPrice.pricePerUnit, influx, config);
          monthlyCost.waterWarmCost += cost.cost;
          monthlyCost.waterWarmConsumption += cost.consumption;
        }
      }
    }

    // Add shared water allocation
    if (household.costAllocation?.sharedWater && waterColdPrice) {
      const sharedWater = await calculateSharedUtilityCost(
        'haupt_wasser',
        monthStr,
        household.costAllocation.sharedWater,
        waterColdPrice.pricePerUnit,
        influx,
        config
      );
      monthlyCost.waterColdCost += sharedWater.cost;
      monthlyCost.waterColdConsumption += sharedWater.consumption;
    }

    // Calculate heat costs
    const heatPrice = getActivePriceForMonth(prices, 'heat', monthStr);
    if (household.meters.heat?.length > 0 && heatPrice) {
      for (const meterId of household.meters.heat) {
        const cost = await calculateMeterCost(meterId, monthStr, heatPrice.pricePerUnit, influx, config);
        monthlyCost.heatCost += cost.cost;
        monthlyCost.heatConsumption += cost.consumption;
      }
    }

    // Calculate total for the month
    monthlyCost.totalCost =
      monthlyCost.electricityCost +
      monthlyCost.gasCost +
      monthlyCost.waterColdCost +
      monthlyCost.waterWarmCost +
      monthlyCost.heatCost;

    monthlyBreakdown.push(monthlyCost);

    // Add to annual totals
    annualTotals.electricityCost += monthlyCost.electricityCost;
    annualTotals.electricityConsumption += monthlyCost.electricityConsumption;
    annualTotals.gasCost += monthlyCost.gasCost;
    annualTotals.gasConsumption += monthlyCost.gasConsumption;
    annualTotals.waterColdCost += monthlyCost.waterColdCost;
    annualTotals.waterColdConsumption += monthlyCost.waterColdConsumption;
    annualTotals.waterWarmCost += monthlyCost.waterWarmCost;
    annualTotals.waterWarmConsumption += monthlyCost.waterWarmConsumption;
    annualTotals.heatCost += monthlyCost.heatCost;
    annualTotals.heatConsumption += monthlyCost.heatConsumption;
    annualTotals.totalCost += monthlyCost.totalCost;
  }

  return {
    householdId,
    householdName,
    year,
    monthlyBreakdown,
    annualTotals,
  };
}

function getActivePriceForMonth(prices: PriceConfig[], utilityType: string, monthStr: string): PriceConfig | null {
  const monthDate = new Date(`${monthStr}-15T12:00:00Z`); // Middle of the month
  const monthISO = monthDate.toISOString();

  const activePrices = prices.filter((price) => {
    if (price.utilityType !== utilityType) return false;
    if (price.validFrom > monthISO) return false;
    if (price.validTo && price.validTo < monthISO) return false;
    return true;
  });

  if (activePrices.length === 0) return null;

  activePrices.sort((a, b) => b.validFrom.localeCompare(a.validFrom));
  return activePrices[0];
}

async function calculateElectricityCost(
  meterIds: string[],
  monthStr: string,
  influx: any,
  config: any
): Promise<{ cost: number; consumption: number }> {
  let totalCost = 0;
  let totalConsumption = 0;

  for (const meterId of meterIds) {
    // Fetch consumption and cost from Tibber data
    const queryApi = influx.getQueryApi(config.org);
    const query = `
      from(bucket: "${config.bucketRaw}")
        |> range(start: ${monthStr}-01T00:00:00Z, stop: ${monthStr}-31T23:59:59Z)
        |> filter(fn: (r) => r["_measurement"] == "energy")
        |> filter(fn: (r) => r["entity_id"] == "${meterId}")
        |> filter(fn: (r) => r["_field"] == "consumption" or r["_field"] == "cost")
        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        |> sum()
    `;

    await new Promise<void>((resolve, reject) => {
      queryApi.queryRows(query, {
        next(row: string[], tableMeta: any) {
          const o = tableMeta.toObject(row) as any;
          if (o.consumption) totalConsumption += parseFloat(o.consumption);
          if (o.cost) totalCost += parseFloat(o.cost);
        },
        error: reject,
        complete: resolve,
      });
    });
  }

  return { cost: totalCost, consumption: totalConsumption };
}

async function calculateSharedElectricityCost(
  monthStr: string,
  allocationPercent: number,
  influx: any,
  config: any
): Promise<{ cost: number; consumption: number }> {
  const queryApi = influx.getQueryApi(config.org);
  const query = `
    from(bucket: "${config.bucketRaw}")
      |> range(start: ${monthStr}-01T00:00:00Z, stop: ${monthStr}-31T23:59:59Z)
      |> filter(fn: (r) => r["_measurement"] == "energy")
      |> filter(fn: (r) => r["entity_id"] == "strom_allgemein" or r["entity_id"] == "haupt_strom")
      |> filter(fn: (r) => r["_field"] == "consumption" or r["_field"] == "cost")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> sum()
  `;

  let totalCost = 0;
  let totalConsumption = 0;

  await new Promise<void>((resolve, reject) => {
    queryApi.queryRows(query, {
      next(row: string[], tableMeta: any) {
        const o = tableMeta.toObject(row) as any;
        if (o.consumption) totalConsumption += parseFloat(o.consumption);
        if (o.cost) totalCost += parseFloat(o.cost);
      },
      error: reject,
      complete: resolve,
    });
  });

  return {
    cost: totalCost * (allocationPercent / 100),
    consumption: totalConsumption * (allocationPercent / 100),
  };
}

async function calculateMeterCost(
  meterId: string,
  monthStr: string,
  pricePerUnit: number,
  influx: any,
  config: any
): Promise<{ cost: number; consumption: number }> {
  const queryApi = influx.getQueryApi(config.org);
  const query = `
    from(bucket: "${config.bucketProcessed}")
      |> range(start: ${monthStr}-01T00:00:00Z, stop: ${monthStr}-31T23:59:59Z)
      |> filter(fn: (r) => r["_measurement"] == "meter_consumption")
      |> filter(fn: (r) => r["meter_id"] == "${meterId}")
      |> filter(fn: (r) => r["_field"] == "consumption")
      |> sum()
  `;

  let consumption = 0;

  await new Promise<void>((resolve, reject) => {
    queryApi.queryRows(query, {
      next(row: string[], tableMeta: any) {
        const o = tableMeta.toObject(row) as any;
        if (o._value) consumption = parseFloat(o._value);
      },
      error: reject,
      complete: resolve,
    });
  });

  return {
    cost: consumption * pricePerUnit,
    consumption,
  };
}

async function calculateSharedUtilityCost(
  meterId: string,
  monthStr: string,
  allocationPercent: number,
  pricePerUnit: number,
  influx: any,
  config: any
): Promise<{ cost: number; consumption: number }> {
  const result = await calculateMeterCost(meterId, monthStr, pricePerUnit, influx, config);

  return {
    cost: result.cost * (allocationPercent / 100),
    consumption: result.consumption * (allocationPercent / 100),
  };
}
