'use client';

import { useState, useEffect } from 'react';
import { format } from 'date-fns';
import Link from 'next/link';
import useMediaQuery from '@/hooks/useMediaQuery';
import { useHouseholdStore } from '@/stores/useHouseholdStore';
import TimeRangeSelector, { TimeRange } from '@/components/TimeRangeSelector';
import ConsumptionChart from '@/components/ConsumptionChart';
import WaterTemperatureChart from '@/components/WaterTemperatureChart';
import SeasonalPatternChart from '@/components/SeasonalPatternChart';
import FloorComparisonChart from '@/components/FloorComparisonChart';
import YearOverYearChart from '@/components/YearOverYearChart';
import IndividualMeterChart from '@/components/IndividualMeterChart';
import FilterPanel from '@/components/FilterPanel';
import AggregationInfo from '@/components/AggregationInfo';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { getHouseholdMeters } from '@/types/household';
import type { MeterReading, WaterTemperature, MeterConfig } from '@/types/meter';
import {
  Home as HomeIcon,
  DollarSign,
  Settings,
  Zap,
  Flame,
  Droplets,
  Thermometer,
  Sun,
  Activity,
} from 'lucide-react';

const METERS_CONFIG: MeterConfig[] = [
  // Electricity - Master & Physical Meters
  { id: 'strom_total', unit: 'kWh', name: 'Total Electricity (Master)', category: 'electricity', type: 'master' },
  { id: 'haupt_strom', unit: 'kWh', name: 'Main Electricity', category: 'electricity', type: 'physical' },
  { id: 'strom_1LOG0007013695_NT', unit: 'kWh', name: 'Old Meter NT', category: 'electricity', type: 'physical' },
  { id: 'strom_1LOG0007013695_HT', unit: 'kWh', name: 'Old Meter HT', category: 'electricity', type: 'physical' },
  { id: 'eg_strom', unit: 'kWh', name: 'Ground Floor Electricity', category: 'electricity', type: 'physical' },
  { id: 'og1_strom', unit: 'kWh', name: '1st Floor Electricity', category: 'electricity', type: 'physical' },
  { id: 'og2_strom', unit: 'kWh', name: '2nd Floor Electricity', category: 'electricity', type: 'physical' },

  // Electricity - Virtual Meters
  { id: 'strom_allgemein', unit: 'kWh', name: 'General Electricity', category: 'virtual', type: 'virtual' },

  // Gas - Master & Physical Meters
  { id: 'gas_total', unit: 'm³', name: 'Total Gas (Master)', category: 'gas', type: 'master' },
  { id: 'gas_zahler', unit: 'm³', name: 'Gas Meter (Current)', category: 'gas', type: 'physical' },
  { id: 'gas_zahler_alt', unit: 'm³', name: 'Gas Meter (Old)', category: 'gas', type: 'physical' },
  { id: 'gastherme_gesamt', unit: 'kWh', name: 'Gas Heating Total', category: 'gas', type: 'physical' },
  { id: 'gastherme_heizen', unit: 'kWh', name: 'Gas Heating Only', category: 'gas', type: 'physical' },
  { id: 'gastherme_warmwasser', unit: 'kWh', name: 'Gas Hot Water', category: 'gas', type: 'physical' },

  // Gas - Virtual Meters
  { id: 'eg_kalfire', unit: 'm³', name: 'Fireplace Gas', category: 'virtual', type: 'virtual' },

  // Water - Physical Meters
  { id: 'haupt_wasser', unit: 'm³', name: 'Main Water', category: 'water', type: 'physical' },
  { id: 'og1_wasser_kalt', unit: 'm³', name: '1st Floor Cold Water', category: 'water', type: 'physical' },
  { id: 'og1_wasser_warm', unit: 'm³', name: '1st Floor Hot Water', category: 'water', type: 'physical' },
  { id: 'og2_wasser_kalt', unit: 'm³', name: '2nd Floor Cold Water', category: 'water', type: 'physical' },
  { id: 'og2_wasser_warm', unit: 'm³', name: '2nd Floor Hot Water', category: 'water', type: 'physical' },

  // Heat - Physical Meters
  { id: 'eg_nord_heat', unit: 'MWh', name: 'Ground Floor North Heat', category: 'heat', type: 'physical' },
  { id: 'eg_sud_heat', unit: 'MWh', name: 'Ground Floor South Heat', category: 'heat', type: 'physical' },
  { id: 'og1_heat', unit: 'MWh', name: '1st Floor Heat', category: 'heat', type: 'physical' },
  { id: 'og2_heat', unit: 'MWh', name: '2nd Floor Heat', category: 'heat', type: 'physical' },
  { id: 'buro_heat', unit: 'MWh', name: 'Office Heat', category: 'heat', type: 'physical' },

  // Solar - Physical Meters
  { id: 'solarspeicher', unit: 'kWh', name: 'Solar Storage', category: 'solar', type: 'physical' },
];

export default function Home() {
  const isMobile = useMediaQuery('(max-width: 640px)');

  // Use Zustand store for household config
  const { config: householdConfig } = useHouseholdStore();

  const [timeRange, setTimeRange] = useState<TimeRange>({
    start: new Date(Date.now() - 90 * 24 * 60 * 60 * 1000),
    end: new Date(),
    label: 'Last 3 Months',
  });

  const [meterData, setMeterData] = useState<{ [key: string]: MeterReading[] }>({});
  const [rawMeterData, setRawMeterData] = useState<{ [key: string]: MeterReading[] }>({});
  const [interpolatedMeterData, setInterpolatedMeterData] = useState<{ [key: string]: MeterReading[] }>({});
  const [waterTempData, setWaterTempData] = useState<WaterTemperature[]>([]);
  const [aggregationMetadata, setAggregationMetadata] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<'raw' | 'consumption'>('consumption');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedHousehold, setSelectedHousehold] = useState<string | null>(null);
  const [selectedMeters, setSelectedMeters] = useState<string[]>([
    'strom_total',
    'gas_total',
    'eg_strom',
    'og1_strom',
    'og2_strom',
    'eg_nord_heat',
    'og1_heat',
    'og2_heat',
  ]);
  const [searchTerm, setSearchTerm] = useState<string>('');

  useEffect(() => {
    const controller = new AbortController();

    const fetchData = async () => {
      setLoading(true);
      try {
        const startDate = format(timeRange.start, 'yyyy-MM-dd');
        const endDate = format(timeRange.end, 'yyyy-MM-dd');

        if (viewMode === 'raw') {
          // Fetch raw and interpolated data for raw meter view
          const rawPromises = selectedMeters.map(async (meterId) => {
            const response = await fetch(
              `/api/readings?meterId=${meterId}&startDate=${startDate}T00:00:00Z&endDate=${endDate}T23:59:59Z&dataType=raw`,
              { signal: controller.signal }
            );
            const data = await response.json();
            return { meterId, readings: data.readings || [] };
          });

          const interpolatedPromises = selectedMeters.map(async (meterId) => {
            const response = await fetch(
              `/api/readings?meterId=${meterId}&startDate=${startDate}T00:00:00Z&endDate=${endDate}T23:59:59Z&dataType=interpolated_daily`,
              { signal: controller.signal }
            );
            const data = await response.json();
            return { meterId, readings: data.readings || [] };
          });

          // Use allSettled to handle partial failures gracefully
          const [rawResults, interpolatedResults] = await Promise.all([
            Promise.allSettled(rawPromises),
            Promise.allSettled(interpolatedPromises),
          ]);

          const newRawData: { [key: string]: MeterReading[] } = {};
          const newInterpolatedData: { [key: string]: MeterReading[] } = {};

          rawResults.forEach((result, index) => {
            if (result.status === 'fulfilled') {
              const { meterId, readings } = result.value;
              newRawData[meterId] = readings;
            } else {
              console.error(`Failed to fetch raw data for ${selectedMeters[index]}:`, result.reason);
            }
          });

          interpolatedResults.forEach((result, index) => {
            if (result.status === 'fulfilled') {
              const { meterId, readings } = result.value;
              newInterpolatedData[meterId] = readings;
            } else {
              console.error(`Failed to fetch interpolated data for ${selectedMeters[index]}:`, result.reason);
            }
          });

          // Store metadata from first successful raw result
          const firstRawSuccess = rawResults.find((r) => r.status === 'fulfilled');
          if (firstRawSuccess && firstRawSuccess.status === 'fulfilled' && selectedMeters.length > 0) {
            const data = await fetch(
              `/api/readings?meterId=${selectedMeters[0]}&startDate=${startDate}T00:00:00Z&endDate=${endDate}T23:59:59Z&dataType=raw`
            ).then((r) => r.json());
            setAggregationMetadata(data.metadata);
          }

          setRawMeterData(newRawData);
          setInterpolatedMeterData(newInterpolatedData);
        } else {
          // Fetch data for selected meters using processed consumption data
          const meterPromises = selectedMeters.map(async (meterId) => {
            const response = await fetch(
              `/api/readings?meterId=${meterId}&startDate=${startDate}T00:00:00Z&endDate=${endDate}T23:59:59Z&dataType=consumption`,
              { signal: controller.signal }
            );
            const data = await response.json();
            return { meterId, readings: data.readings || [] };
          });

          // Use allSettled to handle partial failures gracefully
          const results = await Promise.allSettled(meterPromises);
          const newMeterData: { [key: string]: MeterReading[] } = {};

          results.forEach((result, index) => {
            if (result.status === 'fulfilled') {
              const { meterId, readings } = result.value;
              newMeterData[meterId] = readings;
            } else {
              console.error(`Failed to fetch meter ${selectedMeters[index]}:`, result.reason);
            }
          });

          // Store metadata from first successful result
          const firstSuccess = results.find((r) => r.status === 'fulfilled');
          if (firstSuccess && firstSuccess.status === 'fulfilled') {
            const data = await fetch(
              `/api/readings?meterId=${selectedMeters[0]}&startDate=${startDate}T00:00:00Z&endDate=${endDate}T23:59:59Z&dataType=consumption`
            ).then((r) => r.json());
            setAggregationMetadata(data.metadata);
          }

          setMeterData(newMeterData);
        }

        // Fetch water temperature data
        const waterResponse = await fetch(
          `/api/water-temp?startDate=${startDate}T00:00:00Z&endDate=${endDate}T23:59:59Z`,
          { signal: controller.signal }
        );
        const waterData = await waterResponse.json();
        setWaterTempData(waterData.temperatures || []);
      } catch (error) {
        if (error instanceof Error && error.name === 'AbortError') {
          console.log('Fetch aborted');
          return;
        }
        console.error('Error fetching data:', error);
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    };

    fetchData();

    return () => {
      controller.abort();
    };
  }, [timeRange, selectedMeters, viewMode]);

  const handleMeterToggle = (meterId: string) => {
    setSelectedMeters((prev) =>
      prev.includes(meterId)
        ? prev.filter((id) => id !== meterId)
        : [...prev, meterId]
    );
  };

  const handleHouseholdSelect = (householdId: string | null) => {
    setSelectedHousehold(householdId);
    if (householdId === null) {
      // Show default meters when no household selected
      setSelectedMeters([
        'strom_total',
        'gas_total',
        'eg_nord_heat',
        'og1_heat',
        'og2_heat',
        'haupt_wasser',
        'solarspeicher',
      ]);
    } else {
      // Show meters for selected household
      const household = householdConfig.households.find((h) => h.id === householdId);
      if (household) {
        const meters = getHouseholdMeters(household);
        setSelectedMeters(meters);
      }
    }
    setSelectedCategory('all');
  };

  const handleCategoryToggle = (category: string) => {
    if (category === 'all') {
      // If a household is selected, show all its meters
      if (selectedHousehold) {
        const household = householdConfig.households.find((h) => h.id === selectedHousehold);
        if (household) {
          const meters = getHouseholdMeters(household);
          setSelectedMeters(meters);
        }
      } else {
        // Select default meters from each category
        setSelectedMeters([
          'strom_total',
          'gas_total',
          'eg_nord_heat',
          'og1_heat',
          'og2_heat',
          'haupt_wasser',
          'solarspeicher',
        ]);
      }
    } else {
      // Select all meters in the category
      let categoryMeters = METERS_CONFIG.filter((m) => m.category === category).map((m) => m.id);

      // If a household is selected, filter to only meters in that household
      if (selectedHousehold) {
        const household = householdConfig.households.find((h) => h.id === selectedHousehold);
        if (household) {
          const householdMeters = getHouseholdMeters(household);
          categoryMeters = categoryMeters.filter((m) => householdMeters.includes(m));
        }
      }

      setSelectedMeters(categoryMeters);
    }
    setSelectedCategory(category);
  };

  // Group meters by category for display
  const metersByCategory = METERS_CONFIG.reduce((acc, meter) => {
    if (!acc[meter.category]) {
      acc[meter.category] = [];
    }
    acc[meter.category].push(meter);
    return acc;
  }, {} as Record<string, MeterConfig[]>);

  return (
    <div className="min-h-screen bg-white dark:bg-black">
      <header className="border-b border-neutral-200 dark:border-neutral-800">
        <div className="max-w-7xl mx-auto px-6 sm:px-8 py-8">
          <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h1 className="text-3xl font-semibold text-black dark:text-white tracking-tight">
                Utility Meter Dashboard
              </h1>
              <p className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
                Real-time monitoring and analysis of utility consumption
              </p>
            </div>
            <div className="flex gap-3">
              <Button variant="outline" size={isMobile ? 'icon' : 'default'} asChild>
                <Link href="/household-overview" title="Household Overview">
                  <HomeIcon className="h-4 w-4" />
                  {!isMobile && <span className="ml-2">Annual Overview</span>}
                </Link>
              </Button>
              <Button variant="outline" size={isMobile ? 'icon' : 'default'} asChild>
                <Link href="/costs" title="Costs & Billing">
                  <DollarSign className="h-4 w-4" />
                  {!isMobile && <span className="ml-2">Costs & Billing</span>}
                </Link>
              </Button>
              <Button variant="outline" size={isMobile ? 'icon' : 'default'} asChild>
                <Link href="/settings" title="Settings">
                  <Settings className="h-4 w-4" />
                  {!isMobile && <span className="ml-2">Settings</span>}
                </Link>
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 sm:px-8 py-12">
        {/* Time Range Selector */}
        <TimeRangeSelector onRangeChange={setTimeRange} className="mb-6" />

        {/* Aggregation Info */}
        {aggregationMetadata && (
          <AggregationInfo metadata={aggregationMetadata} className="mb-6" />
        )}

        {/* Filter Panel */}
        <FilterPanel
          viewMode={viewMode}
          onViewModeChange={setViewMode}
          selectedCategory={selectedCategory}
          onCategoryChange={handleCategoryToggle}
          categories={[
            { id: 'all', label: 'All Categories', count: METERS_CONFIG.length },
            { id: 'electricity', label: 'Electricity', count: METERS_CONFIG.filter(m => m.category === 'electricity').length },
            { id: 'gas', label: 'Gas', count: METERS_CONFIG.filter(m => m.category === 'gas').length },
            { id: 'heat', label: 'Heat', count: METERS_CONFIG.filter(m => m.category === 'heat').length },
            { id: 'water', label: 'Water', count: METERS_CONFIG.filter(m => m.category === 'water').length },
            { id: 'solar', label: 'Solar', count: METERS_CONFIG.filter(m => m.category === 'solar').length },
            { id: 'virtual', label: 'Virtual', count: METERS_CONFIG.filter(m => m.category === 'virtual').length },
          ]}
          selectedHousehold={selectedHousehold}
          onHouseholdChange={handleHouseholdSelect}
          households={householdConfig.households.map(h => ({
            id: h.id,
            name: h.name,
            color: h.color,
          }))}
          selectedMeters={selectedMeters}
          onMetersChange={setSelectedMeters}
          availableMeters={METERS_CONFIG.map(m => ({
            id: m.id,
            name: m.name,
            category: m.category,
          }))}
          searchTerm={searchTerm}
          onSearchChange={setSearchTerm}
        />

        {loading ? (
          <div className="flex items-center justify-center py-24">
            <div className="text-center">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-black dark:border-white"></div>
              <p className="mt-4 text-neutral-600 dark:text-neutral-400">Loading data...</p>
            </div>
          </div>
        ) : (
          <div className="space-y-8">
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <Card className="border border-neutral-200 dark:border-neutral-800">
                <CardContent className="p-8">
                  <h3 className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-3">
                    Selected Meters
                  </h3>
                  <p className="text-5xl font-semibold text-black dark:text-white tabular-nums">
                    {selectedMeters.length}
                  </p>
                  <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-2">
                    of {METERS_CONFIG.length} available
                  </p>
                </CardContent>
              </Card>
              <Card className="border border-neutral-200 dark:border-neutral-800">
                <CardContent className="p-8">
                  <h3 className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-3">
                    Time Range
                  </h3>
                  <p className="text-xl font-semibold text-black dark:text-white">
                    {timeRange.label}
                  </p>
                  <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-2 font-mono">
                    {format(timeRange.start, 'MMM d, yyyy')} – {format(timeRange.end, 'MMM d, yyyy')}
                  </p>
                </CardContent>
              </Card>
              <Card className="border border-neutral-200 dark:border-neutral-800">
                <CardContent className="p-8">
                  <h3 className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-3">
                    Categories Active
                  </h3>
                  <p className="text-5xl font-semibold text-black dark:text-white tabular-nums">
                    {new Set(
                      selectedMeters
                        .map((id) => METERS_CONFIG.find((m) => m.id === id))
                        .filter((m): m is MeterConfig => m !== undefined)
                        .map((m) => m.category)
                    ).size}
                  </p>
                  <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-2">
                    utility types
                  </p>
                </CardContent>
              </Card>
              <Card className="border border-neutral-200 dark:border-neutral-800">
                <CardContent className="p-8">
                  <h3 className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-3">
                    Data Source
                  </h3>
                  <p className="text-xl font-semibold text-black dark:text-white capitalize">
                    {viewMode}
                  </p>
                  <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-2">
                    {viewMode === 'raw' ? 'Unprocessed meter data' : 'Calculated usage'}
                  </p>
                </CardContent>
              </Card>
            </div>

            {/* Raw Meter View */}
            {viewMode === 'raw' && (
              <div className="space-y-6">
                {/* Individual meter charts */}
                {(() => {
                  const meterColors = [
                    '#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6',
                    '#ec4899', '#06b6d4', '#f97316', '#84cc16', '#6366f1',
                  ];

                  if (selectedMeters.length === 0) {
                    return (
                      <div className="border border-neutral-200 dark:border-neutral-800 p-12 text-center">
                        <p className="text-neutral-500 dark:text-neutral-400">
                          No meters selected. Please select meters from the filter panel above.
                        </p>
                      </div>
                    );
                  }

                  return selectedMeters.map((meterId, index) => {
                    const config = METERS_CONFIG.find((m) => m.id === meterId);
                    if (!config) return null;

                    return (
                      <IndividualMeterChart
                        key={meterId}
                        meterId={meterId}
                        meterName={config.name}
                        unit={config.unit}
                        rawData={rawMeterData[meterId] || []}
                        interpolatedData={interpolatedMeterData[meterId] || []}
                        color={meterColors[index % meterColors.length]}
                      />
                    );
                  });
                })()}

                {/* Info Section for Raw View */}
                {selectedMeters.length > 0 && (
                  <div className="border border-neutral-200 dark:border-neutral-800 p-8">
                    <h3 className="text-sm font-semibold text-black dark:text-white mb-4">
                      About Raw Meter Readings
                    </h3>
                    <div className="text-sm text-neutral-600 dark:text-neutral-400 space-y-3">
                      <p>
                        This view displays the actual cumulative meter readings directly from your sensors.
                      </p>
                      <ul className="list-disc list-inside space-y-2 ml-4">
                        <li><strong>Raw readings (points):</strong> Actual sensor values as scatter points - may have gaps or irregular timing</li>
                        <li><strong>Interpolated data (line):</strong> Daily interpolated values as smooth lines for trend analysis</li>
                        <li><strong>Cumulative values:</strong> Shows total consumption since meter installation</li>
                        <li><strong>Data validation:</strong> Use this view to spot anomalies, sensor issues, or data gaps</li>
                      </ul>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Consumption Analysis View */}
            {viewMode === 'consumption' && (
              <div className="space-y-8">
                {/* Consumption Charts by Category */}
            {Object.entries(metersByCategory).map(([category, meters]) => {
              const selectedInCategory = meters.filter((m) => selectedMeters.includes(m.id));
              if (selectedInCategory.length === 0) return null;

              const IconComponent =
                category === 'electricity' ? Zap :
                category === 'gas' ? Flame :
                category === 'heat' ? Thermometer :
                category === 'water' ? Droplets :
                category === 'solar' ? Sun :
                Activity;

              return (
                <div key={category}>
                  <h2 className="text-xl font-semibold text-black dark:text-white mb-6 capitalize border-b border-neutral-200 dark:border-neutral-800 pb-4">
                    {category} Consumption
                  </h2>
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {selectedInCategory.map((meter) => (
                      <ConsumptionChart
                        key={meter.id}
                        meterId={meter.id}
                        data={meterData[meter.id] || []}
                        unit={meter.unit}
                        title={`${meter.name}`}
                      />
                    ))}
                  </div>
                </div>
              );
            })}

            {/* Seasonal Pattern Charts */}
            {(() => {
              // Heat seasonal patterns
              const heatMeters = METERS_CONFIG.filter((m) =>
                m.category === 'heat' && selectedMeters.includes(m.id)
              );

              // Gas seasonal patterns
              const gasMeters = METERS_CONFIG.filter((m) =>
                (m.id === 'gas_total' || m.id === 'gastherme_gesamt') && selectedMeters.includes(m.id)
              );

              return (
                <>
                  {heatMeters.length > 1 && (
                    <div>
                      <h2 className="text-xl font-semibold text-black dark:text-white mb-6 border-b border-neutral-200 dark:border-neutral-800 pb-4">
                        Seasonal Heating Patterns
                      </h2>
                      <SeasonalPatternChart
                        data={meterData}
                        meters={heatMeters.map((m) => ({ ...m, color: '#ef4444' }))}
                        title="Heat Consumption Across Seasons"
                      />
                    </div>
                  )}

                  {gasMeters.length > 0 && (
                    <div>
                      <h2 className="text-xl font-semibold text-black dark:text-white mb-6 border-b border-neutral-200 dark:border-neutral-800 pb-4">
                        Seasonal Gas Patterns
                      </h2>
                      <SeasonalPatternChart
                        data={meterData}
                        meters={gasMeters.map((m, idx) => ({
                          ...m,
                          color: idx === 0 ? '#f97316' : '#fb923c',
                        }))}
                        title="Gas Consumption Across Seasons"
                      />
                    </div>
                  )}
                </>
              );
            })()}

            {/* Floor Comparison Charts */}
            {(() => {
              // Heat by floor
              const heatByFloor = [
                { id: 'eg_nord_heat', name: 'EG North', floor: 'EG', color: '#ef4444' },
                { id: 'eg_sud_heat', name: 'EG South', floor: 'EG', color: '#f87171' },
                { id: 'og1_heat', name: 'OG1', floor: 'OG1', color: '#fb923c' },
                { id: 'og2_heat', name: 'OG2', floor: 'OG2', color: '#fdba74' },
                { id: 'buro_heat', name: 'Office', floor: 'Office', color: '#fcd34d' },
              ].filter((m) => selectedMeters.includes(m.id));

              // Water by floor (hot vs cold)
              const waterByFloor = [
                { id: 'og1_wasser_kalt', name: 'OG1 Cold', floor: 'OG1', color: '#60a5fa' },
                { id: 'og1_wasser_warm', name: 'OG1 Hot', floor: 'OG1', color: '#f87171' },
                { id: 'og2_wasser_kalt', name: 'OG2 Cold', floor: 'OG2', color: '#3b82f6' },
                { id: 'og2_wasser_warm', name: 'OG2 Hot', floor: 'OG2', color: '#ef4444' },
              ].filter((m) => selectedMeters.includes(m.id));

              // Electricity by floor
              const electricityByFloor = [
                { id: 'eg_strom', name: 'Ground Floor', floor: 'EG', color: '#fbbf24' },
                { id: 'og1_strom', name: 'First Floor', floor: 'OG1', color: '#f59e0b' },
                { id: 'og2_strom', name: 'Second Floor', floor: 'OG2', color: '#d97706' },
              ].filter((m) => selectedMeters.includes(m.id));

              return (
                <>
                  {heatByFloor.length > 1 && (
                    <div>
                      <h2 className="text-xl font-semibold text-black dark:text-white mb-6 border-b border-neutral-200 dark:border-neutral-800 pb-4">
                        Heat Consumption by Floor
                      </h2>
                      <FloorComparisonChart
                        data={meterData}
                        meters={heatByFloor}
                        title="Monthly Heat Consumption per Floor"
                        unit="MWh"
                        stacked={true}
                      />
                    </div>
                  )}

                  {waterByFloor.length > 1 && (
                    <div>
                      <h2 className="text-xl font-semibold text-black dark:text-white mb-6 border-b border-neutral-200 dark:border-neutral-800 pb-4">
                        Water Consumption by Floor
                      </h2>
                      <FloorComparisonChart
                        data={meterData}
                        meters={waterByFloor}
                        title="Monthly Water Consumption: Hot vs Cold"
                        unit="m³"
                        stacked={false}
                      />
                    </div>
                  )}

                  {electricityByFloor.length > 1 && (
                    <div>
                      <h2 className="text-xl font-semibold text-black dark:text-white mb-6 border-b border-neutral-200 dark:border-neutral-800 pb-4">
                        Electricity Consumption by Floor
                      </h2>
                      <FloorComparisonChart
                        data={meterData}
                        meters={electricityByFloor}
                        title="Monthly Electricity Consumption per Floor"
                        unit="kWh"
                        stacked={true}
                      />
                    </div>
                  )}
                </>
              );
            })()}

            {/* Year-over-Year Comparisons */}
            {(() => {
              // Key meters for YoY comparison
              const keyMeters = [
                { id: 'gas_total', name: 'Total Gas', unit: 'm³' },
                { id: 'strom_total', name: 'Total Electricity', unit: 'kWh' },
                { id: 'og1_heat', name: 'First Floor Heat', unit: 'MWh' },
              ].filter((m) => selectedMeters.includes(m.id) && meterData[m.id]?.length > 30);

              return (
                <>
                  {keyMeters.length > 0 && (
                    <div>
                      <h2 className="text-xl font-semibold text-black dark:text-white mb-6 border-b border-neutral-200 dark:border-neutral-800 pb-4">
                        Year-over-Year Comparison
                      </h2>
                      <div className="grid grid-cols-1 gap-6">
                        {keyMeters.map((meter) => (
                          <YearOverYearChart
                            key={meter.id}
                            data={meterData[meter.id] || []}
                            meterId={meter.id}
                            meterName={meter.name}
                            unit={meter.unit}
                          />
                        ))}
                      </div>
                    </div>
                  )}
                </>
              );
            })()}

            {/* Water Temperature Chart */}
            {waterTempData.length > 0 && (
              <div>
                <h2 className="text-xl font-semibold text-black dark:text-white mb-6 border-b border-neutral-200 dark:border-neutral-800 pb-4">
                  Water Temperature
                </h2>
                <WaterTemperatureChart
                  data={waterTempData}
                  title="Bavarian Lakes Water Temperature"
                />
              </div>
            )}

            {/* Info Section */}
            <div className="border border-neutral-200 dark:border-neutral-800 p-8">
              <h3 className="text-sm font-semibold text-black dark:text-white mb-4">
                About Consumption Analysis
              </h3>
              <div className="text-sm text-neutral-600 dark:text-neutral-400 space-y-3">
                <p>
                  This view displays comprehensive utility consumption data processed by the Dagster pipeline
                  and stored in InfluxDB. All data is pre-processed, interpolated, and ready for analysis.
                </p>
                <ul className="list-disc list-inside space-y-2 ml-4">
                  <li><strong>Consumption data:</strong> Calculated usage per period (not cumulative)</li>
                  <li><strong>Seasonal patterns:</strong> Identify usage trends across different seasons</li>
                  <li><strong>Floor comparisons:</strong> Compare consumption across different floors</li>
                  <li><strong>Year-over-year:</strong> Track consumption changes over time</li>
                  <li><strong>Cost allocation:</strong> Use this data for household billing</li>
                </ul>
              </div>
            </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
