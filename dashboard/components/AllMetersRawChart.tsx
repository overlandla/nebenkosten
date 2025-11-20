'use client';

import { ComposedChart, Line, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { format } from 'date-fns';
import useMediaQuery from '@/hooks/useMediaQuery';
import { useTheme } from '@/components/theme-provider';

interface MeterReading {
  timestamp: string;
  value: number;
}

interface MeterData {
  id: string;
  name: string;
  unit: string;
  color: string;
  rawReadings: MeterReading[];
  interpolatedReadings: MeterReading[];
}

interface AllMetersRawChartProps {
  meters: MeterData[];
  title?: string;
}

// Custom tooltip to show all meter values at a timestamp
function CustomTooltip({ active, payload, meters }: any) {
  if (!active || !payload || !payload.length) return null;

  const timestamp = payload[0]?.payload?.timestamp;
  if (!timestamp) return null;

  return (
    <div className="bg-white dark:bg-neutral-950 p-3 border border-neutral-300 dark:border-neutral-700 rounded-lg shadow-lg max-w-xs">
      <p className="font-semibold text-sm mb-2 text-neutral-900 dark:text-neutral-50">
        {format(new Date(timestamp), 'MMM d, yyyy HH:mm')}
      </p>
      <div className="space-y-1">
        {payload.map((entry: any, index: number) => {
          const meterId = entry.dataKey.replace('_raw', '').replace('_interpolated', '');
          const meter = meters.find((m: MeterData) => m.id === meterId);
          const isRaw = entry.dataKey.includes('_raw');

          if (!meter || entry.value === undefined) return null;

          return (
            <div key={index} className="text-xs flex items-center gap-2 text-neutral-900 dark:text-neutral-50">
              <div
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: entry.color }}
              />
              <span className="font-medium">{meter.name}</span>
              <span className="text-neutral-600 dark:text-neutral-400">
                ({isRaw ? 'Raw' : 'Interp'}):
              </span>
              <span className="font-semibold">
                {entry.value.toFixed(2)} {meter.unit}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function AllMetersRawChart({
  meters,
  title = 'All Meters - Raw and Interpolated Readings',
}: AllMetersRawChartProps) {
  const isMobile = useMediaQuery('(max-width: 640px)');
  const { actualTheme } = useTheme();
  const isDark = actualTheme === 'dark';

  // Combine all meter data into a single timeline
  const combinedData = new Map<string, any>();

  meters.forEach((meter) => {
    // Add raw readings as scatter points
    meter.rawReadings.forEach((reading) => {
      const timestamp = new Date(reading.timestamp).getTime();
      const key = timestamp.toString();

      if (!combinedData.has(key)) {
        combinedData.set(key, { timestamp });
      }

      const existing = combinedData.get(key);
      existing[`${meter.id}_raw`] = reading.value;
    });

    // Add interpolated readings for line chart
    meter.interpolatedReadings.forEach((reading) => {
      const timestamp = new Date(reading.timestamp).getTime();
      const key = timestamp.toString();

      if (!combinedData.has(key)) {
        combinedData.set(key, { timestamp });
      }

      const existing = combinedData.get(key);
      existing[`${meter.id}_interpolated`] = reading.value;
    });
  });

  const chartData = Array.from(combinedData.values())
    .sort((a, b) => a.timestamp - b.timestamp);

  const chartHeight = isMobile ? 400 : 600;

  const textColor = isDark ? '#a3a3a3' : '#525252';
  const gridColor = isDark ? '#404040' : '#e5e5e5';
  const tooltipBg = isDark ? 'rgba(10, 10, 10, 0.95)' : 'rgba(255, 255, 255, 0.95)';
  const tooltipBorder = isDark ? '#404040' : '#e5e5e5';

  return (
    <div className="bg-white dark:bg-neutral-950 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-800 p-6">
      <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50 mb-4">{title}</h3>

      {/* Legend explanation */}
      <div className="mb-4 p-3 bg-muted dark:bg-accent rounded border border-border">
        <p className="text-sm text-muted-foreground">
          <strong>Chart Legend:</strong> Points represent raw meter readings, lines show interpolated daily values.
          Each meter has a unique color for both raw points and interpolated lines.
        </p>
      </div>

      <ResponsiveContainer width="100%" height={chartHeight}>
        <ComposedChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 60 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
          <XAxis
            dataKey="timestamp"
            type="number"
            domain={['auto', 'auto']}
            tickFormatter={(timestamp) => format(new Date(timestamp), 'MMM d')}
            stroke={textColor}
            angle={isMobile ? -90 : -45}
            textAnchor="end"
            height={60}
          />
          <YAxis
            stroke={textColor}
            label={{ value: 'Reading Value', angle: -90, position: 'insideLeft', style: { fill: textColor } }}
          />
          <Tooltip content={<CustomTooltip meters={meters} />} />
          <Legend
            wrapperStyle={{ paddingTop: '20px' }}
            iconType="line"
          />

          {/* Render scatter plots for raw data */}
          {meters.map((meter) => (
            <Scatter
              key={`${meter.id}_raw`}
              dataKey={`${meter.id}_raw`}
              fill={meter.color}
              name={`${meter.name} (Raw)`}
              shape="circle"
            />
          ))}

          {/* Render lines for interpolated data */}
          {meters.map((meter) => (
            <Line
              key={`${meter.id}_interpolated`}
              type="monotone"
              dataKey={`${meter.id}_interpolated`}
              stroke={meter.color}
              strokeWidth={2}
              dot={false}
              name={`${meter.name} (Interpolated)`}
              connectNulls
            />
          ))}
        </ComposedChart>
      </ResponsiveContainer>

      {/* Meter list */}
      <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {meters.map((meter) => (
          <div
            key={meter.id}
            className="flex items-center gap-2 p-2 rounded bg-muted dark:bg-accent"
          >
            <div
              className="w-4 h-4 rounded-full flex-shrink-0"
              style={{ backgroundColor: meter.color }}
            />
            <div className="min-w-0">
              <p className="text-sm font-medium text-neutral-900 truncate">
                {meter.name}
              </p>
              <p className="text-xs text-neutral-500">
                {meter.unit} • {meter.rawReadings.length} raw / {meter.interpolatedReadings.length} interp
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
