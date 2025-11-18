'use client';

import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ComposedChart } from 'recharts';
import { format } from 'date-fns';
import useMediaQuery from '@/hooks/useMediaQuery';

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

  return (
    <div className="bg-white rounded-lg shadow-sm border border-neutral-200 p-6">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-neutral-900">{title}</h3>
        <div className="flex items-center justify-between mt-2">
          <div>
            <p className="text-sm text-neutral-600">
              Total Cost: <span className="font-bold text-green-600">€{totalCost.toFixed(2)}</span>
            </p>
            {showConsumption && (
              <p className="text-sm text-neutral-600">
                Total Consumption: <span className="font-bold text-blue-600">{totalConsumption.toFixed(2)} kWh</span>
              </p>
            )}
            <p className="text-sm text-neutral-600">
              Avg Price: <span className="font-bold text-orange-600">€{avgPrice.toFixed(4)}/kWh</span>
            </p>
          </div>
        </div>
      </div>

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
            yAxisId="left"
            stroke="#6b7280"
            label={{ value: '€', angle: -90, position: 'insideLeft' }}
          />
          {showConsumption && (
            <YAxis
              yAxisId="right"
              orientation="right"
              stroke="#6b7280"
              label={{ value: 'kWh', angle: 90, position: 'insideRight' }}
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
              backgroundColor: 'rgba(255, 255, 255, 0.95)',
              border: '1px solid #e5e7eb',
              borderRadius: '6px',
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
