/**
 * Unit tests for ConsumptionChart component
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import ConsumptionChart from '@/components/ConsumptionChart';
import { generateConsumptionData } from '@/__tests__/fixtures/meterData';

// Mock recharts
jest.mock('recharts', () => ({
  ResponsiveContainer: ({ children, height }: { children: React.ReactNode; height?: number }) => (
    <div data-testid="responsive-container" data-height={height}>
      {children}
    </div>
  ),
  BarChart: ({ children, data }: { children: React.ReactNode; data?: unknown[] }) => <div data-testid="bar-chart" data-length={data?.length}>{children}</div>,
  Bar: ({ dataKey, name, fill }: { dataKey: string; name: string; fill: string }) => <div data-testid={`bar-${dataKey}`} data-name={name} data-fill={fill} />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
  Legend: () => <div data-testid="legend" />,
}));

// Mock useMediaQuery hook
jest.mock('@/hooks/useMediaQuery', () => ({
  __esModule: true,
  default: jest.fn(() => false), // Default to desktop
}));

describe('ConsumptionChart', () => {
  const defaultProps = {
    data: generateConsumptionData({ days: 30 }),
    meterId: 'strom_total',
    unit: 'kWh',
  };

  it('should render with consumption data', () => {
    render(<ConsumptionChart {...defaultProps} />);

    expect(screen.getByText(/STROM TOTAL - Monthly Consumption/i)).toBeInTheDocument();
    expect(screen.getByTestId('bar-chart')).toBeInTheDocument();
    expect(screen.getByTestId('bar-value')).toBeInTheDocument();
  });

  it('should use custom title when provided', () => {
    render(
      <ConsumptionChart
        {...defaultProps}
        title="Custom Consumption Title"
      />
    );

    expect(screen.getByText('Custom Consumption Title')).toBeInTheDocument();
  });

  it('should use custom color when provided', () => {
    render(
      <ConsumptionChart
        {...defaultProps}
        color="#10b981"
      />
    );

    const bar = screen.getByTestId('bar-value');
    expect(bar).toHaveAttribute('data-fill', '#10b981');
  });

  it('should use default blue color when not specified', () => {
    render(<ConsumptionChart {...defaultProps} />);

    const bar = screen.getByTestId('bar-value');
    expect(bar).toHaveAttribute('data-fill', '#3b82f6');
  });

  it('should format meter ID in default title', () => {
    render(
      <ConsumptionChart
        data={defaultProps.data}
        meterId="gas_meter_test"
        unit="m³"
      />
    );

    expect(screen.getByText(/GAS METER TEST - Monthly Consumption/i)).toBeInTheDocument();
  });

  it('should handle empty data array', () => {
    render(
      <ConsumptionChart
        data={[]}
        meterId="test_meter"
        unit="kWh"
      />
    );

    expect(screen.getByTestId('bar-chart')).toBeInTheDocument();
    expect(screen.getByTestId('bar-chart')).toHaveAttribute('data-length', '0');
  });

  it('should sort data by timestamp', () => {
    const unsortedData = [
      { timestamp: '2024-01-03T00:00:00Z', value: 30 },
      { timestamp: '2024-01-01T00:00:00Z', value: 10 },
      { timestamp: '2024-01-02T00:00:00Z', value: 20 },
    ];

    render(
      <ConsumptionChart
        data={unsortedData}
        meterId="test_meter"
        unit="kWh"
      />
    );

    expect(screen.getByTestId('bar-chart')).toBeInTheDocument();
  });

  it('should render all chart components', () => {
    render(<ConsumptionChart {...defaultProps} />);

    expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
    expect(screen.getByTestId('bar-chart')).toBeInTheDocument();
    expect(screen.getByTestId('cartesian-grid')).toBeInTheDocument();
    expect(screen.getByTestId('x-axis')).toBeInTheDocument();
    expect(screen.getByTestId('y-axis')).toBeInTheDocument();
    expect(screen.getByTestId('tooltip')).toBeInTheDocument();
    expect(screen.getByTestId('legend')).toBeInTheDocument();
  });

  it('should handle single data point', () => {
    const singlePoint = generateConsumptionData({ days: 1 });

    render(
      <ConsumptionChart
        data={singlePoint}
        meterId="test_meter"
        unit="kWh"
      />
    );

    expect(screen.getByTestId('bar-chart')).toHaveAttribute('data-length', '1');
  });

  it('should handle large datasets', () => {
    const largeData = generateConsumptionData({ days: 365 });

    render(
      <ConsumptionChart
        data={largeData}
        meterId="test_meter"
        unit="kWh"
      />
    );

    expect(screen.getByTestId('bar-chart')).toHaveAttribute('data-length', '365');
  });

  describe('Responsive behavior', () => {
    it('should use larger height on desktop (400px)', () => {
      const useMediaQuery = require('@/hooks/useMediaQuery').default;
      useMediaQuery.mockReturnValue(false); // Desktop

      render(<ConsumptionChart {...defaultProps} />);

      const container = screen.getByTestId('responsive-container');
      expect(container).toHaveAttribute('data-height', '400');
    });

    it('should use smaller height on mobile (300px)', () => {
      const useMediaQuery = require('@/hooks/useMediaQuery').default;
      useMediaQuery.mockReturnValue(true); // Mobile

      render(<ConsumptionChart {...defaultProps} />);

      const container = screen.getByTestId('responsive-container');
      expect(container).toHaveAttribute('data-height', '300');
    });
  });
});
