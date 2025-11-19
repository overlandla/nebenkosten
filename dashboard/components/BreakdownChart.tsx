'use client';

import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { format } from 'date-fns';
import useMediaQuery from '@/hooks/useMediaQuery';
import { useTheme } from '@/components/theme-provider';

interface ComponentData {
  [key: string]: number;
}

interface BreakdownDataPoint {
  timestamp: string;
  total?: number;
  [key: string]: any;
}

interface BreakdownChartProps {
  data: BreakdownDataPoint[];
  title: string;
  unit: string;
  components: Array<{
    key: string;
    label: string;
    color: string;
  }>;
  showTotal?: boolean;
}

export default function BreakdownChart({
  data,
  title,
  unit,
  components,
  showTotal = true,
}: BreakdownChartProps) {
  const isMobile = useMediaQuery('(max-width: 640px)');
  const { actualTheme } = useTheme();
  const isDark = actualTheme === 'dark';

  const chartData = data
    .map((item) => ({
      ...item,
      timestamp: new Date(item.timestamp).getTime(),
      formattedDate: format(new Date(item.timestamp), 'MMM yyyy'),
    }))
    .sort((a, b) => a.timestamp - b.timestamp);

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
        <ComposedChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
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
            formatter={(value: number, name: string) => [`${value.toFixed(2)} ${unit}`, name]}
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

          {components.map((component) => (
            <Bar
              key={component.key}
              dataKey={component.key}
              stackId="a"
              fill={component.color}
              name={component.label}
            />
          ))}

          {showTotal && (
            <Line
              type="monotone"
              dataKey="total"
              stroke="#000000"
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={{ r: 4 }}
              name="Total"
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
