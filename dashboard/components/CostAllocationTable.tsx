'use client';

import useMediaQuery from '@/hooks/useMediaQuery';
import { Household } from '@/types/household';

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
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        Cost Allocation by Household
      </h3>

      {/* Mobile Card View */}
      {isMobile ? (
        <div className="space-y-4">
          {unitAllocations.map(({ household, costs }) => (
            <div
              key={household.id}
              className="border border-gray-200 rounded-lg p-4 space-y-3"
            >
              <div className="flex items-center justify-between pb-2 border-b border-gray-200">
                <div className="flex items-center space-x-2">
                  <div
                    className="w-4 h-4 rounded-full"
                    style={{ backgroundColor: household.color }}
                  />
                  <span className="font-semibold text-gray-900">{household.name}</span>
                </div>
                <span className="text-sm text-gray-500">
                  {((costs.total / grandTotal) * 100).toFixed(1)}%
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <p className="text-xs text-gray-500">⚡ Electricity</p>
                  <p className="text-lg font-semibold text-gray-900">€{costs.electricity.toFixed(2)}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">🔥 Gas</p>
                  <p className="text-lg font-semibold text-gray-900">€{costs.gas.toFixed(2)}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">💧 Water</p>
                  <p className="text-lg font-semibold text-gray-900">€{costs.water.toFixed(2)}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">🌡️ Heat</p>
                  <p className="text-lg font-semibold text-gray-900">€{costs.heat.toFixed(2)}</p>
                </div>
              </div>

              <div className="pt-2 border-t border-gray-200">
                <p className="text-xs text-gray-500">Total</p>
                <p className="text-2xl font-bold text-gray-900">€{costs.total.toFixed(2)}</p>
              </div>
            </div>
          ))}

          {/* Mobile Total Card */}
          <div className="border-2 border-gray-900 rounded-lg p-4 bg-gray-50">
            <div className="flex items-center justify-between pb-2 border-b border-gray-300">
              <span className="font-bold text-gray-900">Total Allocated</span>
              <span className="text-sm text-gray-600">100%</span>
            </div>

            <div className="grid grid-cols-2 gap-3 mt-3">
              <div>
                <p className="text-xs text-gray-500">⚡ Electricity</p>
                <p className="text-lg font-semibold text-gray-900">
                  €{unitAllocations.reduce((sum, a) => sum + a.costs.electricity, 0).toFixed(2)}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500">🔥 Gas</p>
                <p className="text-lg font-semibold text-gray-900">
                  €{unitAllocations.reduce((sum, a) => sum + a.costs.gas, 0).toFixed(2)}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500">💧 Water</p>
                <p className="text-lg font-semibold text-gray-900">
                  €{unitAllocations.reduce((sum, a) => sum + a.costs.water, 0).toFixed(2)}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500">🌡️ Heat</p>
                <p className="text-lg font-semibold text-gray-900">
                  €{unitAllocations.reduce((sum, a) => sum + a.costs.heat, 0).toFixed(2)}
                </p>
              </div>
            </div>

            <div className="pt-3 border-t border-gray-300 mt-3">
              <p className="text-xs text-gray-500">Grand Total</p>
              <p className="text-2xl font-bold text-gray-900">€{grandTotal.toFixed(2)}</p>
            </div>
          </div>
        </div>
      ) : (
        /* Desktop Table View */
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Household
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Electricity
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Gas
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Water
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Heat
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Total
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                % of Total
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {unitAllocations.map(({ household, costs }) => (
              <tr key={household.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center space-x-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: household.color }}
                    />
                    <span className="text-sm font-medium text-gray-900">
                      {household.name}
                    </span>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                  €{costs.electricity.toFixed(2)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                  €{costs.gas.toFixed(2)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                  €{costs.water.toFixed(2)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                  €{costs.heat.toFixed(2)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-bold text-gray-900">
                  €{costs.total.toFixed(2)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-500">
                  {((costs.total / grandTotal) * 100).toFixed(1)}%
                </td>
              </tr>
            ))}
            <tr className="bg-gray-100 font-bold">
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                Total Allocated
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                €{unitAllocations.reduce((sum, a) => sum + a.costs.electricity, 0).toFixed(2)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                €{unitAllocations.reduce((sum, a) => sum + a.costs.gas, 0).toFixed(2)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                €{unitAllocations.reduce((sum, a) => sum + a.costs.water, 0).toFixed(2)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                €{unitAllocations.reduce((sum, a) => sum + a.costs.heat, 0).toFixed(2)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                €{grandTotal.toFixed(2)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                100%
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
        <div className="bg-yellow-50 rounded-lg p-4 border border-yellow-200">
          <h4 className="text-sm font-medium text-yellow-900 mb-1">⚡ Electricity</h4>
          <p className="text-2xl font-bold text-yellow-700">€{totalCosts.electricity.toFixed(2)}</p>
        </div>
        <div className="bg-orange-50 rounded-lg p-4 border border-orange-200">
          <h4 className="text-sm font-medium text-orange-900 mb-1">🔥 Gas</h4>
          <p className="text-2xl font-bold text-orange-700">€{totalCosts.gas.toFixed(2)}</p>
        </div>
        <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
          <h4 className="text-sm font-medium text-blue-900 mb-1">💧 Water</h4>
          <p className="text-2xl font-bold text-blue-700">€{totalCosts.water.toFixed(2)}</p>
        </div>
        <div className="bg-red-50 rounded-lg p-4 border border-red-200">
          <h4 className="text-sm font-medium text-red-900 mb-1">🌡️ Heat</h4>
          <p className="text-2xl font-bold text-red-700">€{totalCosts.heat.toFixed(2)}</p>
        </div>
      </div>
    </div>
  );
}
