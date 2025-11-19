'use client';

import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ComposedChart } from 'recharts';
import { format } from 'date-fns';
import useMediaQuery from '@/hooks/useMediaQuery';
import { useTheme } from '@/components/theme-provider';

export interface CostData {
  timestamp: string;
  consumption: number;
  cost: number;
  unit_price: number;
  unit_price_vat: number;
}

interface CostBreakdownChartProps {
  data: CostData[];
  title?: string;
  showConsumption?: boolean;
}

export default function CostBreakdownChart({
  data,
  title = 'Electricity Cost Breakdown',
  showConsumption = true,
}: CostBreakdownChartProps) {
  const isMobile = useMediaQuery('(max-width: 640px)');
  const { actualTheme } = useTheme();
  const isDark = actualTheme === 'dark';

  const chartData = data
    .map((item) => ({
      timestamp: new Date(item.timestamp).getTime(),
      formattedDate: format(new Date(item.timestamp), 'MMM dd, yyyy'),
      consumption: item.consumption,
      cost: item.cost,
      unit_price: item.unit_price_vat,
    }))
    .sort((a, b) => a.timestamp - b.timestamp);

  const totalCost = data.reduce((sum, item) => sum + item.cost, 0);
  const totalConsumption = data.reduce((sum, item) => sum + item.consumption, 0);
  const avgPrice = totalConsumption > 0 ? totalCost / totalConsumption : 0;

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
        <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">{title}</h3>
        <div className="flex items-center justify-between mt-2">
          <div>
            <p className="text-sm text-neutral-600 dark:text-neutral-400">
              Total Cost: <span className="font-bold text-green-600 dark:text-green-400">€{totalCost.toFixed(2)}</span>
            </p>
            {showConsumption && (
              <p className="text-sm text-neutral-600 dark:text-neutral-400">
                Total Consumption: <span className="font-bold text-blue-600 dark:text-blue-400">{totalConsumption.toFixed(2)} kWh</span>
              </p>
            )}
            <p className="text-sm text-neutral-600 dark:text-neutral-400">
              Avg Price: <span className="font-bold text-orange-600 dark:text-orange-400">€{avgPrice.toFixed(4)}/kWh</span>
            </p>
          </div>
        </div>
      </div>

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
            yAxisId="left"
            stroke={textColor}
            label={{ value: '€', angle: -90, position: 'insideLeft', style: { fill: textColor } }}
          />
          {showConsumption && (
            <YAxis
              yAxisId="right"
              orientation="right"
              stroke={textColor}
              label={{ value: 'kWh', angle: 90, position: 'insideRight', style: { fill: textColor } }}
            />
          )}
          <Tooltip
            formatter={(value: number, name: string) => {
              if (name === 'cost') return [`€${value.toFixed(2)}`, 'Cost'];
              if (name === 'consumption') return [`${value.toFixed(2)} kWh`, 'Consumption'];
              if (name === 'unit_price') return [`€${value.toFixed(4)}/kWh`, 'Unit Price'];
              return value;
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
          <Bar yAxisId="left" dataKey="cost" fill="#10b981" name="Cost (€)" />
          {showConsumption && (
            <Bar yAxisId="right" dataKey="consumption" fill="#3b82f6" name="Consumption (kWh)" />
          )}
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="unit_price"
            stroke="#f59e0b"
            strokeWidth={2}
            dot={false}
            name="Unit Price (€/kWh)"
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
