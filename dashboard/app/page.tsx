'use client';

import { useState, useEffect } from 'react';
import { format } from 'date-fns';
import TimeRangeSelector, { TimeRange } from '@/components/TimeRangeSelector';
import MeterReadingsChart from '@/components/MeterReadingsChart';
import ConsumptionChart from '@/components/ConsumptionChart';
import WaterTemperatureChart from '@/components/WaterTemperatureChart';

interface MeterReading {
  timestamp: string;
  value: number;
}

interface WaterTempData {
  timestamp: string;
  value: number;
  lake: string;
}

// Predefined list of meters to display based on the Dagster setup
const METERS_CONFIG = [
  { id: 'gas_zahler', unit: 'm³', name: 'Gas Meter' },
  { id: 'gastherme_gesamt', unit: 'kWh', name: 'Gas Heating' },
  { id: 'strom_zahler_nt', unit: 'kWh', name: 'Electricity NT' },
  { id: 'strom_zahler_ht', unit: 'kWh', name: 'Electricity HT' },
  { id: 'haupt_strom', unit: 'kWh', name: 'Main Electricity' },
  { id: 'eg_strom', unit: 'kWh', name: 'Ground Floor Electricity' },
  { id: 'og1_strom', unit: 'kWh', name: '1st Floor Electricity' },
  { id: 'og2_strom', unit: 'kWh', name: '2nd Floor Electricity' },
  { id: 'wasser_kalt', unit: 'm³', name: 'Cold Water' },
  { id: 'wasser_warm', unit: 'm³', name: 'Hot Water' },
];

export default function Home() {
  const [timeRange, setTimeRange] = useState<TimeRange>({
    start: new Date(Date.now() - 90 * 24 * 60 * 60 * 1000),
    end: new Date(),
    label: 'Last 3 Months',
  });

  const [meterData, setMeterData] = useState<{ [key: string]: MeterReading[] }>({});
  const [waterTempData, setWaterTempData] = useState<WaterTempData[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedMeters, setSelectedMeters] = useState<string[]>(
    METERS_CONFIG.slice(0, 4).map((m) => m.id)
  );

  useEffect(() => {
    fetchData();
  }, [timeRange, selectedMeters]);

  const fetchData = async () => {
    setLoading(true);
    try {
      // Fetch data for selected meters
      const meterPromises = selectedMeters.map(async (meterId) => {
        const startDate = format(timeRange.start, 'yyyy-MM-dd');
        const endDate = format(timeRange.end, 'yyyy-MM-dd');
        const response = await fetch(
          `/api/readings?meterId=${meterId}&startDate=${startDate}T00:00:00Z&endDate=${endDate}T23:59:59Z`
        );
        const data = await response.json();
        return { meterId, readings: data.readings || [] };
      });

      const results = await Promise.all(meterPromises);
      const newMeterData: { [key: string]: MeterReading[] } = {};
      results.forEach(({ meterId, readings }) => {
        newMeterData[meterId] = readings;
      });
      setMeterData(newMeterData);

      // Fetch water temperature data
      const waterResponse = await fetch(
        `/api/water-temp?startDate=${format(timeRange.start, 'yyyy-MM-dd')}T00:00:00Z&endDate=${format(timeRange.end, 'yyyy-MM-dd')}T23:59:59Z`
      );
      const waterData = await waterResponse.json();
      setWaterTempData(waterData.temperatures || []);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleMeterToggle = (meterId: string) => {
    setSelectedMeters((prev) =>
      prev.includes(meterId)
        ? prev.filter((id) => id !== meterId)
        : [...prev, meterId]
    );
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold text-gray-900">
            Utility Meter Dashboard
          </h1>
          <p className="mt-1 text-sm text-gray-600">
            Real-time monitoring and analysis of utility consumption
          </p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {/* Time Range Selector */}
        <TimeRangeSelector onRangeChange={setTimeRange} className="mb-8" />

        {/* Meter Selection */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Select Meters to Display
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
            {METERS_CONFIG.map((meter) => (
              <label
                key={meter.id}
                className="flex items-center space-x-2 cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={selectedMeters.includes(meter.id)}
                  onChange={() => handleMeterToggle(meter.id)}
                  className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">{meter.name}</span>
              </label>
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
            {/* Meter Readings Charts */}
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-4">
                Meter Readings
              </h2>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {selectedMeters.map((meterId) => {
                  const meterConfig = METERS_CONFIG.find((m) => m.id === meterId);
                  if (!meterConfig) return null;

                  return (
                    <MeterReadingsChart
                      key={meterId}
                      meterId={meterId}
                      rawReadings={meterData[meterId] || []}
                      unit={meterConfig.unit}
                      title={`${meterConfig.name} - Readings`}
                    />
                  );
                })}
              </div>
            </div>

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
            <div className="bg-blue-50 rounded-lg border border-blue-200 p-6">
              <h3 className="text-lg font-semibold text-blue-900 mb-2">
                About This Dashboard
              </h3>
              <div className="text-blue-800 space-y-2">
                <p>
                  This dashboard displays real-time utility meter data from your InfluxDB instance.
                  Select the time range and meters you want to analyze using the controls above.
                </p>
                <ul className="list-disc list-inside space-y-1 mt-3">
                  <li>Raw readings show the actual meter values collected</li>
                  <li>Interpolated readings fill gaps in the data for continuous analysis</li>
                  <li>Water temperature data is collected from Bavarian lakes</li>
                  <li>All timestamps are displayed in your local timezone</li>
                </ul>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
