'use client';

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { format, parseISO, getYear, getMonth } from 'date-fns';
import useMediaQuery from '@/hooks/useMediaQuery';

interface MeterReading {
  timestamp: string;
  value: number;
}

interface YearOverYearChartProps {
  data: MeterReading[];
  meterId: string;
  meterName: string;
  unit: string;
  title?: string;
}

export default function YearOverYearChart({
  data,
  meterId,
  meterName,
  unit,
  title,
}: YearOverYearChartProps) {
  const isMobile = useMediaQuery('(max-width: 640px)');

  // Group data by year and month
  const yearlyData: { [year: number]: { [month: number]: number } } = {};

  data.forEach((reading) => {
    const date = parseISO(reading.timestamp);
    const year = getYear(date);
    const month = getMonth(date); // 0-11

    if (!yearlyData[year]) {
      yearlyData[year] = {};
    }

    if (!yearlyData[year][month]) {
      yearlyData[year][month] = 0;
    }

    yearlyData[year][month] += reading.value;
  });

  // Get unique years and sort them
  const years = Object.keys(yearlyData).map(Number).sort();

  // Create chart data with month as x-axis and years as series
  const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const chartData = monthNames.map((monthName, monthIndex) => {
    const dataPoint: any = { month: monthName };

    years.forEach((year) => {
      dataPoint[`year_${year}`] = yearlyData[year]?.[monthIndex] || 0;
    });

    return dataPoint;
  });

  // Color palette for different years
  const yearColors = [
    '#3b82f6', // blue
    '#10b981', // green
    '#f59e0b', // orange
    '#8b5cf6', // purple
    '#ef4444', // red
    '#06b6d4', // cyan
  ];

  // Calculate totals per year
  const yearTotals = years.map((year, index) => {
    const total = Object.values(yearlyData[year] || {}).reduce((sum, val) => sum + val, 0);
    const avg = total / 12;
    return {
      year,
      total,
      avg,
      color: yearColors[index % yearColors.length],
    };
  });

  const chartHeight = isMobile ? 300 : 400;

  return (
    <div className="bg-white rounded-lg shadow-sm border border-neutral-200 p-6">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-neutral-900">
          {title || `Year-over-Year Comparison: ${meterName}`}
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mt-3">
          {yearTotals.map(({ year, avg, color }) => (
            <div key={year} className="bg-neutral-50 rounded p-3 border-l-4" style={{ borderColor: color }}>
              <p className="text-xs text-neutral-600">Year {year}</p>
              <p className="text-lg font-bold" style={{ color }}>
                {avg.toFixed(2)} {unit}/mo
              </p>
            </div>
          ))}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={chartHeight}>
        <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="month" stroke="#6b7280" />
          <YAxis
            stroke="#6b7280"
            label={{ value: unit, angle: -90, position: 'insideLeft' }}
          />
          <Tooltip
            formatter={(value: number, name: string) => {
              const year = name.replace('year_', '');
              return [`${value.toFixed(2)} ${unit}`, year];
            }}
            contentStyle={{
              backgroundColor: 'rgba(255, 255, 255, 0.95)',
              border: '1px solid #e5e7eb',
              borderRadius: '6px',
            }}
          />
          <Legend
            formatter={(value) => value.replace('year_', '')}
          />
          {years.map((year, index) => (
            <Line
              key={year}
              type="monotone"
              dataKey={`year_${year}`}
              stroke={yearColors[index % yearColors.length]}
              strokeWidth={2}
              dot={{ r: 4 }}
              name={`year_${year}`}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>

      {/* Year Comparison Summary */}
      {years.length >= 2 && (
        <div className="mt-4 bg-blue-50 rounded-lg p-4 border border-blue-200">
          <p className="text-sm text-blue-900">
            <strong>Year-over-Year Change:</strong>{' '}
            {(() => {
              const currentYear = years[years.length - 1];
              const previousYear = years[years.length - 2];
              const currentTotal = yearTotals.find((yt) => yt.year === currentYear)?.total || 0;
              const previousTotal = yearTotals.find((yt) => yt.year === previousYear)?.total || 0;
              const change = previousTotal > 0 ? ((currentTotal - previousTotal) / previousTotal) * 100 : 0;
              const isIncrease = change > 0;

              return (
                <span className={isIncrease ? 'text-red-700' : 'text-green-700'}>
                  {isIncrease ? '↑' : '↓'} {Math.abs(change).toFixed(1)}% from {previousYear} to {currentYear}
                </span>
              );
            })()}
          </p>
        </div>
      )}
    </div>
  );
}
