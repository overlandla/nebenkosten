'use client';

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { format } from 'date-fns';
import useMediaQuery from '@/hooks/useMediaQuery';
import { useTheme } from '@/components/theme-provider';

interface MeterReading {
  timestamp: string;
  value: number;
}

interface MeterReadingsChartProps {
  rawReadings?: MeterReading[];
  interpolatedReadings?: MeterReading[];
  meterId: string;
  unit: string;
  title?: string;
}

export default function MeterReadingsChart({
  rawReadings = [],
  interpolatedReadings = [],
  meterId,
  unit,
  title,
}: MeterReadingsChartProps) {
  const isMobile = useMediaQuery('(max-width: 640px)');
  const { actualTheme } = useTheme();
  const isDark = actualTheme === 'dark';

  // Combine raw and interpolated data
  const combinedData = new Map<string, any>();

  rawReadings.forEach((reading) => {
    const timestamp = new Date(reading.timestamp).getTime();
    combinedData.set(timestamp.toString(), {
      timestamp,
      raw: reading.value,
    });
  });

  interpolatedReadings.forEach((reading) => {
    const timestamp = new Date(reading.timestamp).getTime();
    const existing = combinedData.get(timestamp.toString()) || { timestamp };
    existing.interpolated = reading.value;
    combinedData.set(timestamp.toString(), existing);
  });

  const chartData = Array.from(combinedData.values())
    .sort((a, b) => a.timestamp - b.timestamp)
    .map((item) => ({
      ...item,
      formattedDate: format(new Date(item.timestamp), 'MMM d, yyyy'),
    }));

  const displayTitle = title || `${meterId.replace(/_/g, ' ').toUpperCase()} - Readings`;

  const chartHeight = isMobile ? 300 : 400;
  const xAxisAngle = isMobile ? -90 : -45;
  const xAxisHeight = isMobile ? 100 : 80;

  const textColor = isDark ? '#a3a3a3' : '#525252';
  const gridColor = isDark ? '#404040' : '#e5e5e5';
  const tooltipBg = isDark ? 'rgba(10, 10, 10, 0.95)' : 'rgba(255, 255, 255, 0.95)';
  const tooltipBorder = isDark ? '#404040' : '#e5e5e5';

  return (
    <div className="bg-white dark:bg-neutral-950 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-800 p-6">
      <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50 mb-4">{displayTitle}</h3>
      <ResponsiveContainer width="100%" height={chartHeight}>
        <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
          <XAxis
            dataKey="timestamp"
            type="number"
            domain={['auto', 'auto']}
            tickFormatter={(timestamp) => format(new Date(timestamp), 'MMM d')}
            stroke={textColor}
          />
          <YAxis
            stroke={textColor}
            label={{ value: unit, angle: -90, position: 'insideLeft', style: { fill: textColor } }}
          />
          <Tooltip
            labelFormatter={(timestamp) => format(new Date(timestamp), 'MMM d, yyyy HH:mm')}
            formatter={(value: number) => [`${value.toFixed(2)} ${unit}`, '']}
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
          {rawReadings.length > 0 && (
            <Line
              type="monotone"
              dataKey="raw"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={false}
              name="Raw Readings"
            />
          )}
          {interpolatedReadings.length > 0 && (
            <Line
              type="monotone"
              dataKey="interpolated"
              stroke="#10b981"
              strokeWidth={2}
              dot={false}
              name="Interpolated"
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
