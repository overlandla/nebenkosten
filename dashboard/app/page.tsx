'use client';

import { useState, useEffect } from 'react';
import { format } from 'date-fns';
import Link from 'next/link';
import useMediaQuery from '@/hooks/useMediaQuery';
import TimeRangeSelector, { TimeRange } from '@/components/TimeRangeSelector';
import MeterReadingsChart from '@/components/MeterReadingsChart';
import ConsumptionChart from '@/components/ConsumptionChart';
import WaterTemperatureChart from '@/components/WaterTemperatureChart';
import SeasonalPatternChart from '@/components/SeasonalPatternChart';
import FloorComparisonChart from '@/components/FloorComparisonChart';
import YearOverYearChart from '@/components/YearOverYearChart';
import AllMetersRawChart from '@/components/AllMetersRawChart';
import AggregationInfo from '@/components/AggregationInfo';
import { HouseholdConfig, DEFAULT_HOUSEHOLD_CONFIG, Household, getHouseholdMeters } from '@/types/household';
import type { MeterReading, WaterTemperature, MeterConfig } from '@/types/meter';

const STORAGE_KEY = 'household_config';

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
  const [householdConfig, setHouseholdConfig] = useState<HouseholdConfig>(DEFAULT_HOUSEHOLD_CONFIG);
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
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">
                Utility Meter Dashboard
              </h1>
              <p className="mt-1 text-sm text-gray-600">
                Real-time monitoring and analysis of utility consumption
              </p>
            </div>
            <div className="flex gap-2">
              <Link
                href="/household-overview"
                className="flex-1 sm:flex-none px-3 sm:px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors text-center"
                title="Household Overview"
              >
                {isMobile ? '🏠' : '🏠 Annual Overview'}
              </Link>
              <Link
                href="/costs"
                className="flex-1 sm:flex-none px-3 sm:px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-center"
                title="Costs & Billing"
              >
                {isMobile ? '💰' : '💰 Costs & Billing'}
              </Link>
              <Link
                href="/settings"
                className="flex-1 sm:flex-none px-3 sm:px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-center"
                title="Settings"
              >
                {isMobile ? '⚙️' : '⚙️ Settings'}
              </Link>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {/* Time Range Selector */}
        <TimeRangeSelector onRangeChange={setTimeRange} className="mb-8" />

        {/* Aggregation Info */}
        {aggregationMetadata && (
          <AggregationInfo metadata={aggregationMetadata} className="mb-8" />
        )}

        {/* View Mode Selector */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Dashboard View
          </h2>
          <div className="flex flex-wrap gap-4">
            <button
              onClick={() => setViewMode('raw')}
              className={`flex-1 min-w-[200px] px-6 py-4 rounded-lg font-semibold transition-all ${
                viewMode === 'raw'
                  ? 'bg-gradient-to-r from-blue-600 to-blue-700 text-white shadow-lg transform scale-105'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              <div className="flex flex-col items-center space-y-2">
                <span className="text-2xl">📊</span>
                <span className="text-base">Raw Meter Readings</span>
                <span className="text-xs opacity-75">
                  View cumulative meter values over time
                </span>
              </div>
            </button>
            <button
              onClick={() => setViewMode('consumption')}
              className={`flex-1 min-w-[200px] px-6 py-4 rounded-lg font-semibold transition-all ${
                viewMode === 'consumption'
                  ? 'bg-gradient-to-r from-green-600 to-green-700 text-white shadow-lg transform scale-105'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              <div className="flex flex-col items-center space-y-2">
                <span className="text-2xl">📈</span>
                <span className="text-base">Consumption Analysis</span>
                <span className="text-xs opacity-75">
                  Analyze usage patterns and trends
                </span>
              </div>
            </button>
          </div>
        </div>

        {/* Household Selector */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Select Household
          </h2>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => handleHouseholdSelect(null)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                selectedHousehold === null
                  ? 'bg-gray-900 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              🏢 All Meters
            </button>
            {householdConfig.households.map((household) => (
              <button
                key={household.id}
                onClick={() => handleHouseholdSelect(household.id)}
                className={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center space-x-2 ${
                  selectedHousehold === household.id
                    ? 'text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
                style={{
                  backgroundColor: selectedHousehold === household.id ? household.color : undefined,
                }}
              >
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: household.color }}
                />
                <span>{household.name}</span>
                <span className="text-xs opacity-75">
                  ({getHouseholdMeters(household).length})
                </span>
              </button>
            ))}
          </div>
          {selectedHousehold && (
            <div className="mt-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
              <p className="text-sm text-blue-800">
                <strong>Filtering by:</strong>{' '}
                {householdConfig.households.find((h) => h.id === selectedHousehold)?.name}
                {' - '}
                {householdConfig.households.find((h) => h.id === selectedHousehold)?.description}
              </p>
            </div>
          )}
        </div>

        {/* Category & Meter Selection */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Select Utility Category
          </h2>

          {/* Category Tabs */}
          <div className="flex flex-wrap gap-2 mb-6">
            <button
              onClick={() => handleCategoryToggle('all')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                selectedCategory === 'all'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              All
            </button>
            <button
              onClick={() => handleCategoryToggle('electricity')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                selectedCategory === 'electricity'
                  ? 'bg-yellow-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              ⚡ Electricity
            </button>
            <button
              onClick={() => handleCategoryToggle('gas')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                selectedCategory === 'gas'
                  ? 'bg-orange-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              🔥 Gas
            </button>
            <button
              onClick={() => handleCategoryToggle('heat')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                selectedCategory === 'heat'
                  ? 'bg-red-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              🌡️ Heat
            </button>
            <button
              onClick={() => handleCategoryToggle('water')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                selectedCategory === 'water'
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              💧 Water
            </button>
            <button
              onClick={() => handleCategoryToggle('solar')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                selectedCategory === 'solar'
                  ? 'bg-green-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              ☀️ Solar
            </button>
            <button
              onClick={() => handleCategoryToggle('virtual')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                selectedCategory === 'virtual'
                  ? 'bg-purple-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              🔮 Virtual
            </button>
          </div>

          {/* Individual Meter Selection */}
          <div className="space-y-4">
            {Object.entries(metersByCategory).map(([category, meters]) => (
              <div key={category} className="border-t border-gray-200 pt-4 first:border-t-0 first:pt-0">
                <h3 className="text-sm font-semibold text-gray-700 mb-3 capitalize">
                  {category === 'electricity' && '⚡ Electricity'}
                  {category === 'gas' && '🔥 Gas'}
                  {category === 'heat' && '🌡️ Heat'}
                  {category === 'water' && '💧 Water'}
                  {category === 'solar' && '☀️ Solar'}
                  {category === 'virtual' && '🔮 Virtual Meters'}
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                  {meters.map((meter) => (
                    <label
                      key={meter.id}
                      className="flex items-center space-x-2 cursor-pointer p-3 rounded hover:bg-gray-50 min-h-[44px]"
                    >
                      <input
                        type="checkbox"
                        checked={selectedMeters.includes(meter.id)}
                        onChange={() => handleMeterToggle(meter.id)}
                        className="w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500 flex-shrink-0"
                      />
                      <div className="flex flex-col">
                        <span className="text-sm text-gray-700">{meter.name}</span>
                        <span className="text-xs text-gray-500">
                          {meter.unit} • {meter.type}
                        </span>
                      </div>
                    </label>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
              <p className="mt-4 text-gray-600">Loading data...</p>
            </div>
          </div>
        ) : (
          <div className="space-y-8">
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <h3 className="text-sm font-medium text-gray-600 mb-1">
                  Selected Meters
                </h3>
                <p className="text-3xl font-bold text-blue-600">
                  {selectedMeters.length}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  of {METERS_CONFIG.length} available
                </p>
              </div>
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <h3 className="text-sm font-medium text-gray-600 mb-1">
                  Time Range
                </h3>
                <p className="text-lg font-bold text-gray-900">
                  {timeRange.label}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  {format(timeRange.start, 'MMM d, yyyy')} - {format(timeRange.end, 'MMM d, yyyy')}
                </p>
              </div>
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <h3 className="text-sm font-medium text-gray-600 mb-1">
                  Categories Active
                </h3>
                <p className="text-3xl font-bold text-green-600">
                  {new Set(
                    selectedMeters
                      .map((id) => METERS_CONFIG.find((m) => m.id === id))
                      .filter((m): m is MeterConfig => m !== undefined)
                      .map((m) => m.category)
                  ).size}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  utility types
                </p>
              </div>
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <h3 className="text-sm font-medium text-gray-600 mb-1">
                  Data Source
                </h3>
                <p className="text-lg font-bold text-purple-600">
                  {viewMode === 'raw' ? 'InfluxDB Raw' : 'Dagster'}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  {viewMode === 'raw' ? 'Raw & interpolated meter readings' : 'Processed consumption data'}
                </p>
              </div>
            </div>

            {/* Raw Meter View */}
            {viewMode === 'raw' && (
              <div className="space-y-8">
                {/* All Meters Combined Chart */}
                {(() => {
                  const meterColors = [
                    '#3b82f6', // blue
                    '#ef4444', // red
                    '#10b981', // green
                    '#f59e0b', // amber
                    '#8b5cf6', // violet
                    '#ec4899', // pink
                    '#06b6d4', // cyan
                    '#f97316', // orange
                    '#84cc16', // lime
                    '#6366f1', // indigo
                  ];

                  const metersData = selectedMeters
                    .map((meterId, index) => {
                      const config = METERS_CONFIG.find((m) => m.id === meterId);
                      if (!config) return null;

                      return {
                        id: meterId,
                        name: config.name,
                        unit: config.unit,
                        color: meterColors[index % meterColors.length],
                        rawReadings: rawMeterData[meterId] || [],
                        interpolatedReadings: interpolatedMeterData[meterId] || [],
                      };
                    })
                    .filter((m): m is NonNullable<typeof m> => m !== null);

                  return (
                    <>
                      {metersData.length > 0 && (
                        <AllMetersRawChart
                          meters={metersData}
                          title="All Selected Meters - Raw Points & Interpolated Lines"
                        />
                      )}

                      {/* Individual meter charts by category */}
                      {Object.entries(metersByCategory).map(([category, meters]) => {
                        const selectedInCategory = meters.filter((m) => selectedMeters.includes(m.id));
                        if (selectedInCategory.length === 0) return null;

                        return (
                          <div key={category}>
                            <h2 className="text-2xl font-bold text-gray-900 mb-4 capitalize">
                              {category === 'electricity' && '⚡ Electricity Meters'}
                              {category === 'gas' && '🔥 Gas Meters'}
                              {category === 'heat' && '🌡️ Heat Meters'}
                              {category === 'water' && '💧 Water Meters'}
                              {category === 'solar' && '☀️ Solar Meters'}
                              {category === 'virtual' && '🔮 Virtual Meters'}
                            </h2>
                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                              {selectedInCategory.map((meter) => (
                                <MeterReadingsChart
                                  key={meter.id}
                                  rawReadings={rawMeterData[meter.id] || []}
                                  interpolatedReadings={interpolatedMeterData[meter.id] || []}
                                  meterId={meter.id}
                                  unit={meter.unit}
                                  title={meter.name}
                                />
                              ))}
                            </div>
                          </div>
                        );
                      })}
                    </>
                  );
                })()}

                {/* Info Section for Raw View */}
                <div className="bg-blue-50 rounded-lg border border-blue-200 p-6">
                  <h3 className="text-lg font-semibold text-blue-900 mb-2">
                    About Raw Meter Readings
                  </h3>
                  <div className="text-blue-800 space-y-2">
                    <p>
                      This view displays the actual cumulative meter readings directly from your sensors.
                    </p>
                    <ul className="list-disc list-inside space-y-1 mt-3">
                      <li><strong>Raw readings:</strong> Actual sensor values as points (may have gaps)</li>
                      <li><strong>Interpolated readings:</strong> Daily interpolated values as smooth lines</li>
                      <li><strong>Cumulative values:</strong> Shows total consumption since meter installation</li>
                      <li><strong>Data validation:</strong> Use this view to spot anomalies or sensor issues</li>
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {/* Consumption Analysis View */}
            {viewMode === 'consumption' && (
              <div className="space-y-8">
                {/* Consumption Charts by Category */}
            {Object.entries(metersByCategory).map(([category, meters]) => {
              const selectedInCategory = meters.filter((m) => selectedMeters.includes(m.id));
              if (selectedInCategory.length === 0) return null;

              return (
                <div key={category}>
                  <h2 className="text-2xl font-bold text-gray-900 mb-4 capitalize">
                    {category === 'electricity' && '⚡ Electricity Consumption'}
                    {category === 'gas' && '🔥 Gas Consumption'}
                    {category === 'heat' && '🌡️ Heat Consumption'}
                    {category === 'water' && '💧 Water Consumption'}
                    {category === 'solar' && '☀️ Solar Storage'}
                    {category === 'virtual' && '🔮 Virtual Meters'}
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
                      <h2 className="text-2xl font-bold text-gray-900 mb-4">
                        🌡️ Seasonal Heating Patterns
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
                      <h2 className="text-2xl font-bold text-gray-900 mb-4">
                        🔥 Seasonal Gas Patterns
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
                      <h2 className="text-2xl font-bold text-gray-900 mb-4">
                        🏢 Heat Consumption by Floor
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
                      <h2 className="text-2xl font-bold text-gray-900 mb-4">
                        💧 Water Consumption by Floor
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
                      <h2 className="text-2xl font-bold text-gray-900 mb-4">
                        ⚡ Electricity Consumption by Floor
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
                      <h2 className="text-2xl font-bold text-gray-900 mb-4">
                        📊 Year-over-Year Comparison
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
                <h2 className="text-2xl font-bold text-gray-900 mb-4">
                  Water Temperature
                </h2>
                <WaterTemperatureChart
                  data={waterTempData}
                  title="Bavarian Lakes Water Temperature"
                />
              </div>
            )}

            {/* Info Section */}
            <div className="bg-green-50 rounded-lg border border-green-200 p-6">
              <h3 className="text-lg font-semibold text-green-900 mb-2">
                About Consumption Analysis
              </h3>
              <div className="text-green-800 space-y-2">
                <p>
                  This view displays comprehensive utility consumption data processed by the Dagster pipeline
                  and stored in InfluxDB. All data is pre-processed, interpolated, and ready for analysis.
                </p>
                <ul className="list-disc list-inside space-y-1 mt-3">
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
