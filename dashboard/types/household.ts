/**
 * Household Configuration Types
 *
 * This module defines the data structures for organizing meters into households
 * for multi-unit building management and cost allocation.
 */

export type HouseholdType = 'unit' | 'shared';

export interface HouseholdMeters {
  electricity?: string[];
  gas?: string[];
  water?: string[];
  heat?: string[];
  solar?: string[];
  virtual?: string[];
}

export interface CostAllocation {
  sharedElectricity?: number;  // Percentage share (0-100)
  sharedGas?: number;          // Percentage share (0-100)
  sharedWater?: number;        // Percentage share (0-100)
  sharedHeat?: number;         // Percentage share (0-100)
}

export interface Household {
  id: string;
  name: string;
  type: HouseholdType;
  color: string;                // Hex color code for visualization
  meters: HouseholdMeters;
  costAllocation?: CostAllocation;
  description?: string;
}

export interface HouseholdConfig {
  households: Household[];
  lastUpdated: string;         // ISO timestamp
  version: string;             // Config schema version
}

/**
 * Default household configuration for the building
 */
export const DEFAULT_HOUSEHOLD_CONFIG: HouseholdConfig = {
  version: '1.0',
  lastUpdated: new Date().toISOString(),
  households: [
    {
      id: 'eg_nord',
      name: 'Ground Floor North',
      type: 'unit',
      color: '#3b82f6',
      meters: {
        electricity: ['eg_strom'],
        heat: ['eg_nord_heat'],
      },
      costAllocation: {
        sharedGas: 25,
        sharedWater: 20,
      },
      description: 'Ground floor north unit with fireplace',
    },
    {
      id: 'eg_sud',
      name: 'Ground Floor South',
      type: 'unit',
      color: '#10b981',
      meters: {
        heat: ['eg_sud_heat'],
      },
      costAllocation: {
        sharedElectricity: 20,
        sharedGas: 25,
        sharedWater: 20,
      },
      description: 'Ground floor south unit',
    },
    {
      id: 'og1',
      name: 'First Floor',
      type: 'unit',
      color: '#f59e0b',
      meters: {
        electricity: ['og1_strom'],
        water: ['og1_wasser_kalt', 'og1_wasser_warm'],
        heat: ['og1_heat'],
      },
      costAllocation: {
        sharedElectricity: 30,
        sharedGas: 25,
        sharedWater: 30,
      },
      description: 'First floor unit with individual meters',
    },
    {
      id: 'og2',
      name: 'Second Floor',
      type: 'unit',
      color: '#8b5cf6',
      meters: {
        electricity: ['og2_strom'],
        water: ['og2_wasser_kalt', 'og2_wasser_warm'],
        heat: ['og2_heat'],
      },
      costAllocation: {
        sharedElectricity: 30,
        sharedGas: 25,
        sharedWater: 30,
      },
      description: 'Second floor unit with individual meters',
    },
    {
      id: 'buro',
      name: 'Office',
      type: 'unit',
      color: '#ec4899',
      meters: {
        heat: ['buro_heat'],
      },
      costAllocation: {
        sharedElectricity: 20,
      },
      description: 'Office space',
    },
    {
      id: 'shared',
      name: 'Shared Utilities',
      type: 'shared',
      color: '#6b7280',
      meters: {
        electricity: ['strom_total', 'haupt_strom', 'strom_allgemein'],
        gas: ['gas_total', 'gas_zahler', 'gastherme_gesamt', 'gastherme_heizen', 'gastherme_warmwasser'],
        water: ['haupt_wasser'],
        solar: ['solarspeicher'],
        virtual: ['eg_kalfire', 'strom_allgemein'],
      },
      description: 'Shared meters and master meters',
    },
  ],
};

/**
 * Validates that cost allocation percentages sum to approximately 100%
 */
export function validateCostAllocation(
  households: Household[],
  utilityType: keyof CostAllocation
): { valid: boolean; total: number; error?: string } {
  const total = households.reduce((sum, h) => {
    return sum + (h.costAllocation?.[utilityType] || 0);
  }, 0);

  if (Math.abs(total - 100) > 0.01 && total > 0) {
    return {
      valid: false,
      total,
      error: `${utilityType} allocation totals ${total}%, must equal 100%`,
    };
  }

  return { valid: true, total };
}

/**
 * Gets all meters assigned to a specific household
 */
export function getHouseholdMeters(household: Household): string[] {
  const allMeters: string[] = [];
  Object.values(household.meters).forEach((meterList) => {
    if (meterList) {
      allMeters.push(...meterList);
    }
  });
  return allMeters;
}

/**
 * Checks if a meter is assigned to any household
 */
export function isMeterAssigned(meterId: string, households: Household[]): boolean {
  return households.some((h) => getHouseholdMeters(h).includes(meterId));
}

/**
 * Gets the household that a meter belongs to
 */
export function getMeterHousehold(meterId: string, households: Household[]): Household | undefined {
  return households.find((h) => getHouseholdMeters(h).includes(meterId));
}
