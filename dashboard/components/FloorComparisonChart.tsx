'use client';

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { format, parseISO } from 'date-fns';
import useMediaQuery from '@/hooks/useMediaQuery';
import type { MeterReading, FloorMeter, ChartMeterData } from '@/types/meter';
import { useTheme } from '@/components/theme-provider';

interface FloorComparisonChartProps {
  data: ChartMeterData;
  meters: FloorMeter[];
  title?: string;
  unit: string;
  stacked?: boolean;
}

interface CombinedDataPoint {
  timestamp: string;
  formattedDate: string;
  [meterId: string]: string | number;
}

export default function FloorComparisonChart({
  data,
  meters,
  title = 'Consumption by Floor',
  unit,
  stacked = true,
}: FloorComparisonChartProps) {
  const isMobile = useMediaQuery('(max-width: 640px)');
  const { actualTheme } = useTheme();
  const isDark = actualTheme === 'dark';

  // Combine all meter data into single timeline
  const combinedData: { [timestamp: string]: CombinedDataPoint } = {};

  meters.forEach((meter) => {
    const meterData = data[meter.id] || [];
    meterData.forEach((reading) => {
      const timestamp = reading.timestamp;
      if (!combinedData[timestamp]) {
        combinedData[timestamp] = {
          timestamp,
          formattedDate: format(parseISO(timestamp), 'MMM yyyy'),
        };
      }
      combinedData[timestamp][meter.id] = reading.value;
    });
  });

  const chartData = Object.values(combinedData).sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );

  // Calculate totals per floor
  const floorTotals = meters.map((meter) => {
    const total = chartData.reduce((sum, item) => sum + (Number(item[meter.id]) || 0), 0);
    return { meter, total };
  });

  const grandTotal = floorTotals.reduce((sum, ft) => sum + ft.total, 0);

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
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mt-3">
          {floorTotals.map(({ meter, total }) => (
            <div key={meter.id} className="bg-muted dark:bg-accent rounded p-3 border-l-4" style={{ borderColor: meter.color }}>
              <p className="text-xs text-muted-foreground">{meter.name}</p>
              <p className="text-lg font-bold" style={{ color: meter.color }}>
                {total.toFixed(2)} {unit}
              </p>
              <p className="text-xs text-muted-foreground">
                {grandTotal > 0 ? ((total / grandTotal) * 100).toFixed(1) : 0}% of total
              </p>
            </div>
          ))}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={chartHeight}>
        <BarChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
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
            label={{ value: unit, angle: -90, position: 'insideLeft', style: { fill: textColor } }}
          />
          <Tooltip
            formatter={(value: number, name: string) => {
              const meter = meters.find((m) => m.id === name);
              return [`${value.toFixed(2)} ${unit}`, meter?.name || name];
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
          />
          <Legend />
          {meters.map((meter) => (
            <Bar
              key={meter.id}
              dataKey={meter.id}
              fill={meter.color}
              name={meter.name}
              stackId={stacked ? 'stack' : undefined}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>

      {/* Total Summary */}
      <div className="mt-4 bg-neutral-100 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-neutral-700">Total Consumption:</span>
          <span className="text-xl font-bold text-neutral-900">
            {grandTotal.toFixed(2)} {unit}
          </span>
        </div>
      </div>
    </div>
  );
}
