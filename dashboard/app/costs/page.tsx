'use client';

import { useState, useEffect } from 'react';
import { format } from 'date-fns';
import Link from 'next/link';
import useMediaQuery from '@/hooks/useMediaQuery';
import TimeRangeSelector, { TimeRange } from '@/components/TimeRangeSelector';
import CostBreakdownChart from '@/components/CostBreakdownChart';
import CostAllocationTable from '@/components/CostAllocationTable';
import { HouseholdConfig, DEFAULT_HOUSEHOLD_CONFIG } from '@/types/household';

const STORAGE_KEY = 'household_config';

interface CostData {
  timestamp: string;
  consumption: number;
  cost: number;
  unit_price: number;
  unit_price_vat: number;
}

export default function CostsPage() {
  const isMobile = useMediaQuery('(max-width: 640px)');

  const [timeRange, setTimeRange] = useState<TimeRange>({
    start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), // Last 30 days
    end: new Date(),
    label: 'Last 30 Days',
  });

  const [costData, setCostData] = useState<CostData[]>([]);
  const [householdConfig, setHouseholdConfig] = useState<HouseholdConfig>(DEFAULT_HOUSEHOLD_CONFIG);
  const [loading, setLoading] = useState(true);

  // Load household config from localStorage
  useEffect(() => {
    // Check if running in browser (SSR safety)
    if (typeof window === 'undefined') return;

    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        // Validate structure before setting
        if (parsed && parsed.version && Array.isArray(parsed.households)) {
          setHouseholdConfig(parsed);
        } else {
          console.warn('Invalid household config structure in localStorage');
        }
      }
    } catch (error) {
      console.error('Failed to parse stored config:', error);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    const fetchCostData = async () => {
      setLoading(true);
      try {
        const startDate = format(timeRange.start, 'yyyy-MM-dd');
        const endDate = format(timeRange.end, 'yyyy-MM-dd');
        const response = await fetch(
          `/api/costs?startDate=${startDate}T00:00:00Z&endDate=${endDate}T23:59:59Z&aggregation=daily`,
          { signal: controller.signal }
        );
        const data = await response.json();
        setCostData(data.costs || []);
      } catch (error) {
        if (error instanceof Error && error.name === 'AbortError') {
          console.log('Fetch aborted');
          return;
        }
        console.error('Error fetching cost data:', error);
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    };

    fetchCostData();

    return () => {
      controller.abort();
    };
  }, [timeRange]);

  // Calculate total costs (placeholder values - would need actual data from all meters)
  const totalElectricityCost = costData.reduce((sum, item) => sum + item.cost, 0);
  const totalGasCost = totalElectricityCost * 1.5; // Placeholder: estimate gas as 1.5x electricity
  const totalWaterCost = totalElectricityCost * 0.3; // Placeholder: estimate water as 0.3x electricity
  const totalHeatCost = totalElectricityCost * 2.0; // Placeholder: estimate heat as 2x electricity

  const totalCosts = {
    electricity: totalElectricityCost,
    gas: totalGasCost,
    water: totalWaterCost,
    heat: totalHeatCost,
  };

  const grandTotal = totalElectricityCost + totalGasCost + totalWaterCost + totalHeatCost;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      {/* Header */}
      <header className="bg-gradient-to-r from-emerald-600 to-emerald-700 dark:from-emerald-700 dark:to-emerald-800 shadow-lg border-b border-emerald-800">
        <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold text-white">Cost Analysis & Billing</h1>
              <p className="mt-1 text-sm text-emerald-100">
                Detailed cost breakdown and household allocation
              </p>
            </div>
            <Link
              href="/"
              className="px-4 py-2 bg-white/10 text-white rounded-lg hover:bg-white/20 transition-colors text-center border border-white/20"
            >
              ← Back to Dashboard
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {/* Time Range Selector */}
        <TimeRangeSelector onRangeChange={setTimeRange} className="mb-8" />

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600 dark:border-emerald-400"></div>
              <p className="mt-4 text-slate-600 dark:text-slate-300">Loading cost data...</p>
            </div>
          </div>
        ) : (
          <div className="space-y-8">
            {/* Summary Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6">
              <div className="bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-800 dark:to-slate-700 rounded-xl shadow-lg border border-slate-200 dark:border-slate-600 p-6 hover:shadow-xl transition-shadow">
                <h3 className="text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">Total Costs</h3>
                <p className="text-3xl font-bold text-slate-900 dark:text-slate-100">€{grandTotal.toFixed(2)}</p>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{timeRange.label}</p>
              </div>
              <div className="bg-gradient-to-br from-yellow-50 to-yellow-100 dark:from-yellow-900/30 dark:to-yellow-800/30 rounded-xl shadow-lg border border-yellow-200 dark:border-yellow-700 p-6 hover:shadow-xl transition-shadow">
                <h3 className="text-sm font-medium text-yellow-900 dark:text-yellow-300 mb-1">Electricity</h3>
                <p className="text-2xl font-bold text-yellow-700 dark:text-yellow-400">€{totalElectricityCost.toFixed(2)}</p>
                <p className="text-xs text-yellow-600 dark:text-yellow-400/70 mt-1">
                  {grandTotal > 0 ? ((totalElectricityCost / grandTotal) * 100).toFixed(1) : '0.0'}% of total
                </p>
              </div>
              <div className="bg-gradient-to-br from-orange-50 to-orange-100 dark:from-orange-900/30 dark:to-orange-800/30 rounded-xl shadow-lg border border-orange-200 dark:border-orange-700 p-6 hover:shadow-xl transition-shadow">
                <h3 className="text-sm font-medium text-orange-900 dark:text-orange-300 mb-1">Gas</h3>
                <p className="text-2xl font-bold text-orange-700 dark:text-orange-400">€{totalGasCost.toFixed(2)}</p>
                <p className="text-xs text-orange-600 dark:text-orange-400/70 mt-1">
                  {grandTotal > 0 ? ((totalGasCost / grandTotal) * 100).toFixed(1) : '0.0'}% of total
                </p>
              </div>
              <div className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/30 dark:to-blue-800/30 rounded-xl shadow-lg border border-blue-200 dark:border-blue-700 p-6 hover:shadow-xl transition-shadow">
                <h3 className="text-sm font-medium text-blue-900 dark:text-blue-300 mb-1">Water</h3>
                <p className="text-2xl font-bold text-blue-700 dark:text-blue-400">€{totalWaterCost.toFixed(2)}</p>
                <p className="text-xs text-blue-600 dark:text-blue-400/70 mt-1">
                  {grandTotal > 0 ? ((totalWaterCost / grandTotal) * 100).toFixed(1) : '0.0'}% of total
                </p>
              </div>
              <div className="bg-gradient-to-br from-red-50 to-red-100 dark:from-red-900/30 dark:to-red-800/30 rounded-xl shadow-lg border border-red-200 dark:border-red-700 p-6 hover:shadow-xl transition-shadow">
                <h3 className="text-sm font-medium text-red-900 dark:text-red-300 mb-1">Heat</h3>
                <p className="text-2xl font-bold text-red-700 dark:text-red-400">€{totalHeatCost.toFixed(2)}</p>
                <p className="text-xs text-red-600 dark:text-red-400/70 mt-1">
                  {grandTotal > 0 ? ((totalHeatCost / grandTotal) * 100).toFixed(1) : '0.0'}% of total
                </p>
              </div>
            </div>

            {/* Cost Breakdown Chart */}
            {costData.length > 0 && (
              <CostBreakdownChart
                data={costData}
                title="Daily Electricity Costs & Pricing"
                showConsumption={true}
              />
            )}

            {/* Cost Allocation Table */}
            <CostAllocationTable households={householdConfig.households} totalCosts={totalCosts} />

            {/* Info Box */}
            <div className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/30 dark:to-blue-800/30 rounded-xl border border-blue-200 dark:border-blue-700 p-6 shadow-md">
              <h3 className="text-lg font-semibold text-blue-900 dark:text-blue-100 mb-2">About Cost Analysis</h3>
              <div className="text-blue-800 dark:text-blue-200 space-y-2">
                <p>
                  This page displays comprehensive cost analysis from Tibber API (electricity) and
                  estimated costs for other utilities based on consumption data.
                </p>
                <ul className="list-disc list-inside space-y-1 mt-3">
                  <li>
                    <strong>Electricity costs:</strong> Real-time data from Tibber API including hourly
                    pricing
                  </li>
                  <li>
                    <strong>Cost allocation:</strong> Distribution of shared utility costs across
                    households based on configured percentages
                  </li>
                  <li>
                    <strong>Note:</strong> Gas, water, and heat costs are currently estimated. Configure
                    actual pricing in settings for accurate billing.
                  </li>
                  <li>All costs shown include VAT where applicable</li>
                </ul>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
