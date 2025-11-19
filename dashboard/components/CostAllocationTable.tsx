'use client';

import useMediaQuery from '@/hooks/useMediaQuery';
import { Household } from '@/types/household';
import { Zap, Flame, Droplets, Thermometer } from 'lucide-react';

interface CostAllocationTableProps {
  households: Household[];
  totalCosts: {
    electricity: number;
    gas: number;
    water: number;
    heat: number;
  };
}

export default function CostAllocationTable({
  households,
  totalCosts,
}: CostAllocationTableProps) {
  const isMobile = useMediaQuery('(max-width: 768px)');

  // Calculate allocated costs for each household
  const allocations = households.map((household) => {
    const electricityCost =
      (household.costAllocation?.sharedElectricity || 0) / 100 * totalCosts.electricity;
    const gasCost =
      (household.costAllocation?.sharedGas || 0) / 100 * totalCosts.gas;
    const waterCost =
      (household.costAllocation?.sharedWater || 0) / 100 * totalCosts.water;
    const heatCost =
      (household.costAllocation?.sharedHeat || 0) / 100 * totalCosts.heat;

    return {
      household,
      costs: {
        electricity: electricityCost,
        gas: gasCost,
        water: waterCost,
        heat: heatCost,
        total: electricityCost + gasCost + waterCost + heatCost,
      },
    };
  });

  // Filter out shared household and zero-cost households
  const unitAllocations = allocations.filter(
    (a) => a.household.type === 'unit' && a.costs.total > 0
  );

  const grandTotal = unitAllocations.reduce((sum, a) => sum + a.costs.total, 0);

  return (
    <div className="bg-white dark:bg-neutral-950 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-800 p-6">
      <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50 mb-4">
        Cost Allocation by Household
      </h3>

      {/* Mobile Card View */}
      {isMobile ? (
        <div className="space-y-4">
          {unitAllocations.map(({ household, costs }) => (
            <div
              key={household.id}
              className="border border-neutral-200 dark:border-neutral-800 rounded-lg p-4 space-y-3"
            >
              <div className="flex items-center justify-between pb-2 border-b border-neutral-200 dark:border-neutral-800">
                <div className="flex items-center space-x-2">
                  <div
                    className="w-4 h-4 rounded-full border-2 border-neutral-200 dark:border-neutral-800"
                    style={{ backgroundColor: household.color }}
                  />
                  <span className="font-semibold text-neutral-900 dark:text-neutral-50">{household.name}</span>
                </div>
                <span className="text-sm text-neutral-500 dark:text-neutral-400">
                  {((costs.total / grandTotal) * 100).toFixed(1)}%
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="flex items-center gap-1.5 text-xs text-neutral-500 dark:text-neutral-400 mb-1">
                    <Zap className="h-3 w-3" />
                    <span>Electricity</span>
                  </div>
                  <p className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">€{costs.electricity.toFixed(2)}</p>
                </div>
                <div>
                  <div className="flex items-center gap-1.5 text-xs text-neutral-500 dark:text-neutral-400 mb-1">
                    <Flame className="h-3 w-3" />
                    <span>Gas</span>
                  </div>
                  <p className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">€{costs.gas.toFixed(2)}</p>
                </div>
                <div>
                  <div className="flex items-center gap-1.5 text-xs text-neutral-500 dark:text-neutral-400 mb-1">
                    <Droplets className="h-3 w-3" />
                    <span>Water</span>
                  </div>
                  <p className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">€{costs.water.toFixed(2)}</p>
                </div>
                <div>
                  <div className="flex items-center gap-1.5 text-xs text-neutral-500 dark:text-neutral-400 mb-1">
                    <Thermometer className="h-3 w-3" />
                    <span>Heat</span>
                  </div>
                  <p className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">€{costs.heat.toFixed(2)}</p>
                </div>
              </div>

              <div className="pt-2 border-t border-neutral-200 dark:border-neutral-800">
                <p className="text-xs text-neutral-500 dark:text-neutral-400">Total</p>
                <p className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">€{costs.total.toFixed(2)}</p>
              </div>
            </div>
          ))}

          {/* Mobile Total Card */}
          <div className="border-2 border-neutral-900 dark:border-neutral-50 rounded-lg p-4 bg-neutral-50 dark:bg-neutral-900">
            <div className="flex items-center justify-between pb-2 border-b border-neutral-300 dark:border-neutral-700">
              <span className="font-bold text-neutral-900 dark:text-neutral-50">Total Allocated</span>
              <span className="text-sm text-neutral-600 dark:text-neutral-400">100%</span>
            </div>

            <div className="grid grid-cols-2 gap-3 mt-3">
              <div>
                <div className="flex items-center gap-1.5 text-xs text-neutral-500 dark:text-neutral-400 mb-1">
                  <Zap className="h-3 w-3" />
                  <span>Electricity</span>
                </div>
                <p className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
                  €{unitAllocations.reduce((sum, a) => sum + a.costs.electricity, 0).toFixed(2)}
                </p>
              </div>
              <div>
                <div className="flex items-center gap-1.5 text-xs text-neutral-500 dark:text-neutral-400 mb-1">
                  <Flame className="h-3 w-3" />
                  <span>Gas</span>
                </div>
                <p className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
                  €{unitAllocations.reduce((sum, a) => sum + a.costs.gas, 0).toFixed(2)}
                </p>
              </div>
              <div>
                <div className="flex items-center gap-1.5 text-xs text-neutral-500 dark:text-neutral-400 mb-1">
                  <Droplets className="h-3 w-3" />
                  <span>Water</span>
                </div>
                <p className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
                  €{unitAllocations.reduce((sum, a) => sum + a.costs.water, 0).toFixed(2)}
                </p>
              </div>
              <div>
                <div className="flex items-center gap-1.5 text-xs text-neutral-500 dark:text-neutral-400 mb-1">
                  <Thermometer className="h-3 w-3" />
                  <span>Heat</span>
                </div>
                <p className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
                  €{unitAllocations.reduce((sum, a) => sum + a.costs.heat, 0).toFixed(2)}
                </p>
              </div>
            </div>

            <div className="pt-3 border-t border-neutral-300 dark:border-neutral-700 mt-3">
              <p className="text-xs text-neutral-500 dark:text-neutral-400">Grand Total</p>
              <p className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">€{grandTotal.toFixed(2)}</p>
            </div>
          </div>
        </div>
      ) : (
        /* Desktop Table View */
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-neutral-200 dark:divide-neutral-800">
          <thead className="bg-neutral-50 dark:bg-neutral-900">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
                Household
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
                Electricity
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
                Gas
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
                Water
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
                Heat
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
                Total
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
                % of Total
              </th>
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-neutral-950 divide-y divide-neutral-200 dark:divide-neutral-800">
            {unitAllocations.map(({ household, costs }) => (
              <tr key={household.id} className="hover:bg-neutral-50 dark:hover:bg-neutral-900">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center space-x-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: household.color }}
                    />
                    <span className="text-sm font-medium text-neutral-900 dark:text-neutral-50">
                      {household.name}
                    </span>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-neutral-900 dark:text-neutral-50">
                  €{costs.electricity.toFixed(2)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-neutral-900 dark:text-neutral-50">
                  €{costs.gas.toFixed(2)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-neutral-900 dark:text-neutral-50">
                  €{costs.water.toFixed(2)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-neutral-900 dark:text-neutral-50">
                  €{costs.heat.toFixed(2)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-bold text-neutral-900 dark:text-neutral-50">
                  €{costs.total.toFixed(2)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-neutral-500 dark:text-neutral-400">
                  {((costs.total / grandTotal) * 100).toFixed(1)}%
                </td>
              </tr>
            ))}
            <tr className="bg-neutral-100 dark:bg-neutral-900 font-bold">
              <td className="px-6 py-4 whitespace-nowrap text-sm text-neutral-900 dark:text-neutral-50">
                Total Allocated
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-neutral-900 dark:text-neutral-50">
                €{unitAllocations.reduce((sum, a) => sum + a.costs.electricity, 0).toFixed(2)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-neutral-900 dark:text-neutral-50">
                €{unitAllocations.reduce((sum, a) => sum + a.costs.gas, 0).toFixed(2)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-neutral-900 dark:text-neutral-50">
                €{unitAllocations.reduce((sum, a) => sum + a.costs.water, 0).toFixed(2)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-neutral-900 dark:text-neutral-50">
                €{unitAllocations.reduce((sum, a) => sum + a.costs.heat, 0).toFixed(2)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-neutral-900 dark:text-neutral-50">
                €{grandTotal.toFixed(2)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-neutral-900 dark:text-neutral-50">
                100%
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      )}

      {/* Summary Cards - Using semantic colors from design system */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
        <div className="bg-neutral-50 dark:bg-neutral-900 rounded-lg p-4 border border-neutral-200 dark:border-neutral-800">
          <div className="flex items-center gap-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
            <Zap className="h-4 w-4" style={{ color: 'var(--electricity)' }} />
            <h4>Electricity</h4>
          </div>
          <p className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">€{totalCosts.electricity.toFixed(2)}</p>
        </div>
        <div className="bg-neutral-50 dark:bg-neutral-900 rounded-lg p-4 border border-neutral-200 dark:border-neutral-800">
          <div className="flex items-center gap-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
            <Flame className="h-4 w-4" style={{ color: 'var(--gas)' }} />
            <h4>Gas</h4>
          </div>
          <p className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">€{totalCosts.gas.toFixed(2)}</p>
        </div>
        <div className="bg-neutral-50 dark:bg-neutral-900 rounded-lg p-4 border border-neutral-200 dark:border-neutral-800">
          <div className="flex items-center gap-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
            <Droplets className="h-4 w-4" style={{ color: 'var(--water)' }} />
            <h4>Water</h4>
          </div>
          <p className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">€{totalCosts.water.toFixed(2)}</p>
        </div>
        <div className="bg-neutral-50 dark:bg-neutral-900 rounded-lg p-4 border border-neutral-200 dark:border-neutral-800">
          <div className="flex items-center gap-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
            <Thermometer className="h-4 w-4" style={{ color: 'var(--heat)' }} />
            <h4>Heat</h4>
          </div>
          <p className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">€{totalCosts.heat.toFixed(2)}</p>
        </div>
      </div>
    </div>
  );
}
