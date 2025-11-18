'use client';

import React from 'react';
import {
  ComposedChart,
  Line,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { MeterReading } from '../types/meter';

interface IndividualMeterChartProps {
  meterId: string;
  meterName: string;
  unit: string;
  rawData: MeterReading[];
  interpolatedData: MeterReading[];
  color?: string;
}

// Custom tooltip component
function CustomTooltip({ active, payload, unit, color }: any) {
  if (!active || !payload || !payload.length) return null;

  const data = payload[0].payload;
  const date = new Date(data.timestamp);

  const formatValue = (value: number) => {
    return `${value.toFixed(2)} ${unit}`;
  };

  return (
    <div className="bg-white dark:bg-gray-800 p-3 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg">
      <p className="text-sm font-medium text-gray-900 dark:text-white mb-2">
        {date.toLocaleString('de-DE', {
          dateStyle: 'medium',
          timeStyle: 'short',
        })}
      </p>
      {data.raw !== undefined && (
        <p className="text-sm text-gray-600 dark:text-gray-300">
          <span className="inline-block w-3 h-3 rounded-full mr-2" style={{ backgroundColor: color }} />
          Raw: {formatValue(data.raw)}
        </p>
      )}
      {data.interpolated !== undefined && (
        <p className="text-sm text-gray-600 dark:text-gray-300">
          <span className="inline-block w-3 h-3 rounded-full mr-2" style={{ backgroundColor: color, opacity: 0.6 }} />
          Interpolated: {formatValue(data.interpolated)}
        </p>
      )}
    </div>
  );
}

export default function IndividualMeterChart({
  meterId,
  meterName,
  unit,
  rawData,
  interpolatedData,
  color = '#3b82f6',
}: IndividualMeterChartProps) {
  // Combine and sort data by timestamp
  const combinedData = React.useMemo(() => {
    const dataMap = new Map<string, { timestamp: string; raw?: number; interpolated?: number }>();

    // Add raw data
    rawData.forEach(reading => {
      const timestamp = new Date(reading.timestamp).getTime();
      const key = timestamp.toString();
      dataMap.set(key, {
        timestamp: reading.timestamp,
        raw: reading.value,
      });
    });

    // Add interpolated data
    interpolatedData.forEach(reading => {
      const timestamp = new Date(reading.timestamp).getTime();
      const key = timestamp.toString();
      const existing = dataMap.get(key);
      if (existing) {
        existing.interpolated = reading.value;
      } else {
        dataMap.set(key, {
          timestamp: reading.timestamp,
          interpolated: reading.value,
        });
      }
    });

    // Convert to array and sort by timestamp
    return Array.from(dataMap.values()).sort(
      (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );
  }, [rawData, interpolatedData]);

  const formatDate = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleDateString('de-DE', {
      month: 'short',
      day: 'numeric',
      hour: combinedData.length < 100 ? '2-digit' : undefined,
      minute: combinedData.length < 100 ? '2-digit' : undefined,
    });
  };

  const hasData = rawData.length > 0 || interpolatedData.length > 0;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{meterName}</h3>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {meterId} • {rawData.length} raw readings, {interpolatedData.length} interpolated points
        </p>
      </div>

      {!hasData ? (
        <div className="h-80 flex items-center justify-center text-gray-500 dark:text-gray-400">
          No data available for the selected time range
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={400}>
          <ComposedChart data={combinedData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-gray-300 dark:stroke-gray-600" />
            <XAxis
              dataKey="timestamp"
              tickFormatter={formatDate}
              className="text-xs"
              stroke="#9ca3af"
              tick={{ fill: '#6b7280' }}
            />
            <YAxis
              label={{ value: unit, angle: -90, position: 'insideLeft' }}
              className="text-xs"
              stroke="#9ca3af"
              tick={{ fill: '#6b7280' }}
            />
            <Tooltip content={<CustomTooltip unit={unit} color={color} />} />
            <Legend
              wrapperStyle={{ paddingTop: '20px' }}
              iconType="circle"
            />

            {/* Interpolated data as line */}
            <Line
              type="monotone"
              dataKey="interpolated"
              stroke={color}
              strokeWidth={2}
              name="Interpolated"
              dot={false}
              connectNulls
              opacity={0.7}
            />

            {/* Raw data as scatter points */}
            <Scatter
              dataKey="raw"
              fill={color}
              name="Raw Readings"
              shape="circle"
            />
          </ComposedChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
