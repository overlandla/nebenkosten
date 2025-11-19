'use client';

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { format } from 'date-fns';
import useMediaQuery from '@/hooks/useMediaQuery';
import { useTheme } from '@/components/theme-provider';
import type { ConsumptionData } from '@/types/meter';

interface ConsumptionChartProps {
  data: ConsumptionData[];
  meterId: string;
  unit: string;
  title?: string;
  color?: string;
}

export default function ConsumptionChart({
  data,
  meterId,
  unit,
  title,
  color = '#3b82f6',
}: ConsumptionChartProps) {
  const isMobile = useMediaQuery('(max-width: 640px)');
  const { actualTheme } = useTheme();
  const isDark = actualTheme === 'dark';

  const chartData = data
    .map((item) => ({
      timestamp: new Date(item.timestamp).getTime(),
      value: item.value,
      formattedDate: format(new Date(item.timestamp), 'MMM yyyy'),
    }))
    .sort((a, b) => a.timestamp - b.timestamp);

  const displayTitle = title || `${meterId.replace(/_/g, ' ').toUpperCase()} - Monthly Consumption`;
  const chartHeight = isMobile ? 300 : 400;
  const xAxisAngle = isMobile ? -90 : -45;
  const xAxisHeight = isMobile ? 100 : 80;

  // Dark mode colors
  const textColor = isDark ? '#a3a3a3' : '#525252';
  const gridColor = isDark ? '#404040' : '#e5e5e5';
  const tooltipBg = isDark ? 'rgba(10, 10, 10, 0.95)' : 'rgba(255, 255, 255, 0.95)';
  const tooltipBorder = isDark ? '#404040' : '#e5e5e5';

  return (
    <div className="bg-white dark:bg-neutral-950 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-800 p-6">
      <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50 mb-4">{displayTitle}</h3>
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
            formatter={(value: number) => [`${value.toFixed(2)} ${unit}`, 'Consumption']}
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
          <Bar dataKey="value" fill={color} name="Consumption" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
