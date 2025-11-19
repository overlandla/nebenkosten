'use client';

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts';
import { format, parseISO } from 'date-fns';
import useMediaQuery from '@/hooks/useMediaQuery';
import { useTheme } from '@/components/theme-provider';

interface MeterReading {
  timestamp: string;
  value: number;
}

interface SeasonalPatternChartProps {
  data: { [meterId: string]: MeterReading[] };
  meters: Array<{ id: string; name: string; color: string; unit: string }>;
  title?: string;
}

export default function SeasonalPatternChart({
  data,
  meters,
  title = 'Seasonal Consumption Patterns',
}: SeasonalPatternChartProps) {
  const isMobile = useMediaQuery('(max-width: 640px)');
  const { actualTheme } = useTheme();
  const isDark = actualTheme === 'dark';

  // Combine all meter data into single timeline
  const combinedData: { [timestamp: string]: any } = {};

  meters.forEach((meter) => {
    const meterData = data[meter.id] || [];
    meterData.forEach((reading) => {
      const timestamp = reading.timestamp;
      if (!combinedData[timestamp]) {
        combinedData[timestamp] = {
          timestamp,
          formattedDate: format(parseISO(timestamp), 'MMM yyyy'),
          month: parseISO(timestamp).getMonth(),
        };
      }
      combinedData[timestamp][meter.id] = reading.value;
    });
  });

  const chartData = Object.values(combinedData).sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );

  // Get season for reference lines
  const getSeasonLabel = (month: number): string => {
    if (month >= 2 && month <= 4) return 'Spring';
    if (month >= 5 && month <= 7) return 'Summer';
    if (month >= 8 && month <= 10) return 'Fall';
    return 'Winter';
  };

  // Calculate totals for summary
  const totals = meters.map((meter) => {
    const total = chartData.reduce((sum, item) => sum + (item[meter.id] || 0), 0);
    const avg = total / chartData.length;
    return { meter, total, avg };
  });

  const chartHeight = isMobile ? 300 : 400;
  const xAxisAngle = isMobile ? -90 : -45;
  const xAxisHeight = isMobile ? 100 : 80;

  const textColor = isDark ? '#a3a3a3' : '#525252';
  const gridColor = isDark ? '#404040' : '#e5e5e5';
  const tooltipBg = isDark ? 'rgba(10, 10, 10, 0.95)' : 'rgba(255, 255, 255, 0.95)';
  const tooltipBorder = isDark ? '#404040' : '#e5e5e5';

  return (
    <div className="bg-white dark:bg-neutral-950 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-800 p-6">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50 mb-4">{title}</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-3">
          {totals.map(({ meter, avg }) => (
            <div key={meter.id} className="bg-neutral-50 rounded p-3">
              <p className="text-xs text-neutral-600">{meter.name}</p>
              <p className="text-lg font-bold" style={{ color: meter.color }}>
                {avg.toFixed(2)} {meter.unit}/mo
              </p>
            </div>
          ))}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={chartHeight}>
        <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
          <XAxis
            dataKey="formattedDate"
            stroke={textColor}
            angle={xAxisAngle}
            textAnchor="end"
            height={xAxisHeight}
            style={{ fontSize: isMobile ? '12px' : '14px' }}
          />
          <YAxis
            stroke={textColor}
            label={{ value: meters[0]?.unit || 'Units', angle: -90, position: 'insideLeft', style: { fill: textColor } }}
          />
          <Tooltip
            formatter={(value: number, name: string) => {
              const meter = meters.find((m) => m.id === name);
              return [`${value.toFixed(2)} ${meter?.unit || ''}`, meter?.name || name];
            }}
            contentStyle={{
              backgroundColor: tooltipBg,
              border: `1px solid ${tooltipBorder}`,
              borderRadius: '6px',
              color: isDark ? '#fafafa' : '#0a0a0a',
            }}
            labelStyle={{
              color: isDark ? '#fafafa' : '#0a0a0a',
            }}
            labelFormatter={(label) => `Period: ${label}`}
          />
          <Legend />
          {meters.map((meter) => (
            <Line
              key={meter.id}
              type="monotone"
              dataKey={meter.id}
              stroke={meter.color}
              strokeWidth={2}
              dot={{ r: 4 }}
              name={meter.name}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>

      {/* Season Indicators */}
      <div className="mt-4 flex flex-wrap items-center justify-center gap-4 md:gap-6 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-green-200 rounded"></div>
          <span className="text-neutral-600">Spring (Mar-May)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-yellow-200 rounded"></div>
          <span className="text-neutral-600">Summer (Jun-Aug)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-orange-200 rounded"></div>
          <span className="text-neutral-600">Fall (Sep-Nov)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-blue-200 rounded"></div>
          <span className="text-neutral-600">Winter (Dec-Feb)</span>
        </div>
      </div>
    </div>
  );
}
