'use client';

import { useState, useEffect } from 'react';
import { format } from 'date-fns';
import Link from 'next/link';
import useMediaQuery from '@/hooks/useMediaQuery';
import TimeRangeSelector, { TimeRange } from '@/components/TimeRangeSelector';
import CostBreakdownChart from '@/components/CostBreakdownChart';
import CostAllocationTable from '@/components/CostAllocationTable';
import { HouseholdConfig, DEFAULT_HOUSEHOLD_CONFIG } from '@/types/household';
import { Button } from '@/components/ui/button';

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
    <div className="min-h-screen bg-white dark:bg-black">
      {/* Header */}
      <header className="border-b border-neutral-200 dark:border-neutral-800">
        <div className="max-w-7xl mx-auto px-6 sm:px-8 py-8">
          <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h1 className="text-3xl font-semibold text-black dark:text-white tracking-tight">Cost Analysis & Billing</h1>
              <p className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
                Detailed cost breakdown and household allocation
              </p>
            </div>
            <Button variant="outline" asChild>
              <Link href="/">
                ← Back to Dashboard
              </Link>
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 sm:px-8 py-12">
        {/* Time Range Selector */}
        <TimeRangeSelector onRangeChange={setTimeRange} className="mb-8" />

        {loading ? (
          <div className="flex items-center justify-center py-24">
            <div className="text-center">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-black dark:border-white"></div>
              <p className="mt-4 text-neutral-600 dark:text-neutral-400">Loading cost data...</p>
            </div>
          </div>
        ) : (
          <div className="space-y-8">
            {/* Summary Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
              <div className="border border-neutral-200 dark:border-neutral-800 p-8">
                <h3 className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-3">Total Costs</h3>
                <p className="text-4xl font-semibold text-black dark:text-white tabular-nums">€{grandTotal.toFixed(2)}</p>
                <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-2">{timeRange.label}</p>
              </div>
              <div className="border border-neutral-200 dark:border-neutral-800 p-8">
                <h3 className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-3">Electricity</h3>
                <p className="text-3xl font-semibold text-black dark:text-white tabular-nums">€{totalElectricityCost.toFixed(2)}</p>
                <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-2 font-mono">
                  {grandTotal > 0 ? ((totalElectricityCost / grandTotal) * 100).toFixed(1) : '0.0'}% of total
                </p>
              </div>
              <div className="border border-neutral-200 dark:border-neutral-800 p-8">
                <h3 className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-3">Gas</h3>
                <p className="text-3xl font-semibold text-black dark:text-white tabular-nums">€{totalGasCost.toFixed(2)}</p>
                <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-2 font-mono">
                  {grandTotal > 0 ? ((totalGasCost / grandTotal) * 100).toFixed(1) : '0.0'}% of total
                </p>
              </div>
              <div className="border border-neutral-200 dark:border-neutral-800 p-8">
                <h3 className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-3">Water</h3>
                <p className="text-3xl font-semibold text-black dark:text-white tabular-nums">€{totalWaterCost.toFixed(2)}</p>
                <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-2 font-mono">
                  {grandTotal > 0 ? ((totalWaterCost / grandTotal) * 100).toFixed(1) : '0.0'}% of total
                </p>
              </div>
              <div className="border border-neutral-200 dark:border-neutral-800 p-8">
                <h3 className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-3">Heat</h3>
                <p className="text-3xl font-semibold text-black dark:text-white tabular-nums">€{totalHeatCost.toFixed(2)}</p>
                <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-2 font-mono">
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
            <div className="border border-neutral-200 dark:border-neutral-800 p-8">
              <h3 className="text-sm font-semibold text-black dark:text-white mb-4">About Cost Analysis</h3>
              <div className="text-sm text-neutral-600 dark:text-neutral-400 space-y-3">
                <p>
                  This page displays comprehensive cost analysis from Tibber API (electricity) and
                  estimated costs for other utilities based on consumption data.
                </p>
                <ul className="list-disc list-inside space-y-2 ml-4">
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
