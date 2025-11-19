'use client';

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { format } from 'date-fns';
import useMediaQuery from '@/hooks/useMediaQuery';
import { useTheme } from '@/components/theme-provider';

interface WaterTempData {
  timestamp: string;
  value: number;
  lake: string;
}

interface WaterTemperatureChartProps {
  data: WaterTempData[];
  title?: string;
}

const LAKE_COLORS: { [key: string]: string } = {
  Schliersee: '#3b82f6',
  Tegernsee: '#10b981',
  Isar: '#f59e0b',
};

export default function WaterTemperatureChart({
  data,
  title = 'Water Temperature',
}: WaterTemperatureChartProps) {
  const isMobile = useMediaQuery('(max-width: 640px)');
  const { actualTheme } = useTheme();
  const isDark = actualTheme === 'dark';

  // Group data by lake
  const lakeData = new Map<string, Map<string, number>>();
  const timestamps = new Set<string>();

  data.forEach((item) => {
    const timestamp = new Date(item.timestamp).getTime().toString();
    timestamps.add(timestamp);

    if (!lakeData.has(item.lake)) {
      lakeData.set(item.lake, new Map());
    }
    lakeData.get(item.lake)!.set(timestamp, item.value);
  });

  const chartData = Array.from(timestamps)
    .map((timestamp) => {
      const dataPoint: any = {
        timestamp: parseInt(timestamp),
        formattedDate: format(new Date(parseInt(timestamp)), 'MMM d, yyyy'),
      };

      lakeData.forEach((values, lake) => {
        dataPoint[lake] = values.get(timestamp) || null;
      });

      return dataPoint;
    })
    .sort((a, b) => a.timestamp - b.timestamp);

  const lakes = Array.from(lakeData.keys());

  const chartHeight = isMobile ? 300 : 400;
  const xAxisAngle = isMobile ? -90 : -45;
  const xAxisHeight = isMobile ? 100 : 80;

  const textColor = isDark ? '#a3a3a3' : '#525252';
  const gridColor = isDark ? '#404040' : '#e5e5e5';
  const tooltipBg = isDark ? 'rgba(10, 10, 10, 0.95)' : 'rgba(255, 255, 255, 0.95)';
  const tooltipBorder = isDark ? '#404040' : '#e5e5e5';

  return (
    <div className="bg-white dark:bg-neutral-950 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-800 p-6">
      <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50 mb-4">{title}</h3>
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
            label={{ value: '°C', angle: -90, position: 'insideLeft', style: { fill: textColor } }}
          />
          <Tooltip
            labelFormatter={(timestamp) => format(new Date(timestamp), 'MMM d, yyyy')}
            formatter={(value: number) => [`${value?.toFixed(1)}°C`, '']}
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
          {lakes.map((lake) => (
            <Line
              key={lake}
              type="monotone"
              dataKey={lake}
              stroke={LAKE_COLORS[lake] || '#6b7280'}
              strokeWidth={2}
              dot={false}
              name={lake}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
