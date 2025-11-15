'use client';

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { format } from 'date-fns';
import useMediaQuery from '@/hooks/useMediaQuery';
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

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">{displayTitle}</h3>
      <ResponsiveContainer width="100%" height={chartHeight}>
        <BarChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
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
            formatter={(value: number) => [`${value.toFixed(2)} ${unit}`, 'Consumption']}
            contentStyle={{
              backgroundColor: 'rgba(255, 255, 255, 0.95)',
              border: '1px solid #e5e7eb',
              borderRadius: '6px',
            }}
          />
          <Legend />
          <Bar dataKey="value" fill={color} name="Consumption" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
