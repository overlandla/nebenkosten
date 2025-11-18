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

  return (
    <div className="bg-white rounded-lg shadow-sm border border-neutral-200 p-6">
      <h3 className="text-lg font-semibold text-neutral-900 mb-4">{title}</h3>
      <ResponsiveContainer width="100%" height={chartHeight}>
        <ComposedChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="formattedDate"
            stroke="#6b7280"
            angle={xAxisAngle}
            textAnchor="end"
            height={xAxisHeight}
            style={{ fontSize: isMobile ? '12px' : '14px' }}
          />
          <YAxis
            stroke="#6b7280"
            label={{ value: unit, angle: -90, position: 'insideLeft' }}
          />
          <Tooltip
            formatter={(value: number, name: string) => [`${value.toFixed(2)} ${unit}`, name]}
            contentStyle={{
              backgroundColor: 'rgba(255, 255, 255, 0.95)',
              border: '1px solid #e5e7eb',
              borderRadius: '6px',
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
