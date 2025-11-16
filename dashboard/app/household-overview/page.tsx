'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line } from 'recharts';

interface HouseholdCosts {
  householdId: string;
  householdName: string;
  year: number;
  monthlyBreakdown: MonthlyHouseholdCost[];
  annualTotals: AnnualTotals;
}

interface MonthlyHouseholdCost {
  month: string;
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

interface AnnualTotals {
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

export default function HouseholdOverviewPage() {
  const currentYear = new Date().getFullYear();
  const [selectedYear, setSelectedYear] = useState(currentYear);
  const [householdCosts, setHouseholdCosts] = useState<HouseholdCosts[]>([]);
  const [selectedHousehold, setSelectedHousehold] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchHouseholdCosts();
  }, [selectedYear]);

  const fetchHouseholdCosts = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/household-costs?year=${selectedYear}`);
      const data = await response.json();

      if (data.households) {
        setHouseholdCosts(data.households);
        if (data.households.length > 0 && !selectedHousehold) {
          setSelectedHousehold(data.households[0].householdId);
        }
      }
    } catch (error) {
      console.error('Error fetching household costs:', error);
    } finally {
      setLoading(false);
    }
  };

  const selectedHouseholdData = householdCosts.find((h) => h.householdId === selectedHousehold);

  // Prepare chart data
  const monthlyChartData = selectedHouseholdData?.monthlyBreakdown.map((month) => ({
    name: month.month.slice(5), // Extract MM from YYYY-MM
    Electricity: month.electricityCost,
    Gas: month.gasCost,
    'Water (Cold)': month.waterColdCost,
    'Water (Warm)': month.waterWarmCost,
    Heat: month.heatCost,
    Total: month.totalCost,
  })) || [];

  const consumptionChartData = selectedHouseholdData?.monthlyBreakdown.map((month) => ({
    name: month.month.slice(5),
    'Electricity (kWh)': month.electricityConsumption,
    'Gas (kWh)': month.gasConsumption,
    'Water Cold (m³)': month.waterColdConsumption,
    'Water Warm (m³)': month.waterWarmConsumption,
    'Heat (MWh)': month.heatConsumption,
  })) || [];

  const yearOptions = Array.from({ length: 5 }, (_, i) => currentYear - i);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">
                Annual Household Overview
              </h1>
              <p className="mt-1 text-sm text-gray-600">
                Comprehensive consumption and cost breakdown per household
              </p>
            </div>
            <Link
              href="/"
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors text-center"
            >
              ← Back to Dashboard
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {/* Year Selector */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Select Year
          </label>
          <select
            value={selectedYear}
            onChange={(e) => setSelectedYear(parseInt(e.target.value))}
            className="px-4 py-2 border border-gray-300 rounded-lg"
          >
            {yearOptions.map((year) => (
              <option key={year} value={year}>
                {year}
              </option>
            ))}
          </select>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
              <p className="mt-4 text-gray-600">Loading household costs...</p>
            </div>
          </div>
        ) : householdCosts.length === 0 ? (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
            <p className="text-gray-500">
              No household cost data available for {selectedYear}.
            </p>
            <p className="text-sm text-gray-400 mt-2">
              Make sure you have configured households and price settings.
            </p>
          </div>
        ) : (
          <>
            {/* Household Selector */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Select Household
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {householdCosts.map((household) => (
                  <button
                    key={household.householdId}
                    onClick={() => setSelectedHousehold(household.householdId)}
                    className={`p-4 rounded-lg border-2 transition-all text-left ${
                      selectedHousehold === household.householdId
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <h3 className="font-semibold text-gray-900">{household.householdName}</h3>
                    <p className="text-2xl font-bold text-blue-600 mt-2">
                      €{household.annualTotals.totalCost.toFixed(2)}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">Annual Total</p>
                  </button>
                ))}
              </div>
            </div>

            {/* Selected Household Details */}
            {selectedHouseholdData && (
              <>
                {/* Annual Totals Summary */}
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
                  <h2 className="text-xl font-bold text-gray-900 mb-6">
                    {selectedHouseholdData.householdName} - {selectedYear} Annual Totals
                  </h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    <div className="bg-yellow-50 rounded-lg p-4 border border-yellow-200">
                      <h3 className="text-sm font-medium text-yellow-900 mb-1">⚡ Electricity</h3>
                      <p className="text-2xl font-bold text-yellow-700">
                        €{selectedHouseholdData.annualTotals.electricityCost.toFixed(2)}
                      </p>
                      <p className="text-sm text-yellow-600 mt-1">
                        {selectedHouseholdData.annualTotals.electricityConsumption.toFixed(2)} kWh
                      </p>
                    </div>

                    <div className="bg-orange-50 rounded-lg p-4 border border-orange-200">
                      <h3 className="text-sm font-medium text-orange-900 mb-1">🔥 Gas</h3>
                      <p className="text-2xl font-bold text-orange-700">
                        €{selectedHouseholdData.annualTotals.gasCost.toFixed(2)}
                      </p>
                      <p className="text-sm text-orange-600 mt-1">
                        {selectedHouseholdData.annualTotals.gasConsumption.toFixed(2)} kWh
                      </p>
                    </div>

                    <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                      <h3 className="text-sm font-medium text-blue-900 mb-1">💧 Water (Cold)</h3>
                      <p className="text-2xl font-bold text-blue-700">
                        €{selectedHouseholdData.annualTotals.waterColdCost.toFixed(2)}
                      </p>
                      <p className="text-sm text-blue-600 mt-1">
                        {selectedHouseholdData.annualTotals.waterColdConsumption.toFixed(2)} m³
                      </p>
                    </div>

                    <div className="bg-cyan-50 rounded-lg p-4 border border-cyan-200">
                      <h3 className="text-sm font-medium text-cyan-900 mb-1">🌡️ Water (Warm)</h3>
                      <p className="text-2xl font-bold text-cyan-700">
                        €{selectedHouseholdData.annualTotals.waterWarmCost.toFixed(2)}
                      </p>
                      <p className="text-sm text-cyan-600 mt-1">
                        {selectedHouseholdData.annualTotals.waterWarmConsumption.toFixed(2)} m³
                      </p>
                    </div>

                    <div className="bg-red-50 rounded-lg p-4 border border-red-200">
                      <h3 className="text-sm font-medium text-red-900 mb-1">🏠 Heat</h3>
                      <p className="text-2xl font-bold text-red-700">
                        €{selectedHouseholdData.annualTotals.heatCost.toFixed(2)}
                      </p>
                      <p className="text-sm text-red-600 mt-1">
                        {selectedHouseholdData.annualTotals.heatConsumption.toFixed(2)} MWh
                      </p>
                    </div>

                    <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
                      <h3 className="text-sm font-medium text-gray-100 mb-1">💰 Total</h3>
                      <p className="text-2xl font-bold text-white">
                        €{selectedHouseholdData.annualTotals.totalCost.toFixed(2)}
                      </p>
                      <p className="text-sm text-gray-300 mt-1">All utilities</p>
                    </div>
                  </div>
                </div>

                {/* Monthly Cost Chart */}
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
                  <h2 className="text-xl font-bold text-gray-900 mb-6">
                    Monthly Cost Breakdown
                  </h2>
                  <ResponsiveContainer width="100%" height={400}>
                    <BarChart data={monthlyChartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis label={{ value: 'Cost (€)', angle: -90, position: 'insideLeft' }} />
                      <Tooltip formatter={(value: any) => `€${value.toFixed(2)}`} />
                      <Legend />
                      <Bar dataKey="Electricity" stackId="a" fill="#fbbf24" />
                      <Bar dataKey="Gas" stackId="a" fill="#f97316" />
                      <Bar dataKey="Water (Cold)" stackId="a" fill="#3b82f6" />
                      <Bar dataKey="Water (Warm)" stackId="a" fill="#06b6d4" />
                      <Bar dataKey="Heat" stackId="a" fill="#ef4444" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                {/* Monthly Consumption Chart */}
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
                  <h2 className="text-xl font-bold text-gray-900 mb-6">
                    Monthly Consumption Trends
                  </h2>
                  <ResponsiveContainer width="100%" height={400}>
                    <LineChart data={consumptionChartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Line type="monotone" dataKey="Electricity (kWh)" stroke="#fbbf24" strokeWidth={2} />
                      <Line type="monotone" dataKey="Gas (kWh)" stroke="#f97316" strokeWidth={2} />
                      <Line type="monotone" dataKey="Water Cold (m³)" stroke="#3b82f6" strokeWidth={2} />
                      <Line type="monotone" dataKey="Water Warm (m³)" stroke="#06b6d4" strokeWidth={2} />
                      <Line type="monotone" dataKey="Heat (MWh)" stroke="#ef4444" strokeWidth={2} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>

                {/* Monthly Details Table */}
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
                  <div className="p-6">
                    <h2 className="text-xl font-bold text-gray-900 mb-6">
                      Monthly Breakdown Table
                    </h2>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Month</th>
                          <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Electricity</th>
                          <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Gas</th>
                          <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Water (Cold)</th>
                          <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Water (Warm)</th>
                          <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Heat</th>
                          <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase font-bold">Total</th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {selectedHouseholdData.monthlyBreakdown.map((month) => (
                          <tr key={month.month} className="hover:bg-gray-50">
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                              {month.month}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-right">
                              <div className="text-sm text-gray-900">€{month.electricityCost.toFixed(2)}</div>
                              <div className="text-xs text-gray-500">{month.electricityConsumption.toFixed(1)} kWh</div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-right">
                              <div className="text-sm text-gray-900">€{month.gasCost.toFixed(2)}</div>
                              <div className="text-xs text-gray-500">{month.gasConsumption.toFixed(1)} kWh</div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-right">
                              <div className="text-sm text-gray-900">€{month.waterColdCost.toFixed(2)}</div>
                              <div className="text-xs text-gray-500">{month.waterColdConsumption.toFixed(1)} m³</div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-right">
                              <div className="text-sm text-gray-900">€{month.waterWarmCost.toFixed(2)}</div>
                              <div className="text-xs text-gray-500">{month.waterWarmConsumption.toFixed(1)} m³</div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-right">
                              <div className="text-sm text-gray-900">€{month.heatCost.toFixed(2)}</div>
                              <div className="text-xs text-gray-500">{month.heatConsumption.toFixed(2)} MWh</div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-bold text-gray-900">
                              €{month.totalCost.toFixed(2)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </>
            )}
          </>
        )}
      </main>
    </div>
  );
}
