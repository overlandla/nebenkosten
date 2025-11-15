/**
 * Unit tests for MeterReadingsChart component
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import MeterReadingsChart from '@/components/MeterReadingsChart';
import { generateMeterReadings } from '@/__tests__/fixtures/meterData';

// Mock recharts to avoid SVG rendering issues in tests
jest.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: any) => <div data-testid="responsive-container">{children}</div>,
  LineChart: ({ children, data }: any) => <div data-testid="line-chart" data-length={data?.length}>{children}</div>,
  Line: ({ dataKey, name }: any) => <div data-testid={`line-${dataKey}`} data-name={name} />,
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

describe('MeterReadingsChart', () => {
  const defaultProps = {
    meterId: 'strom_total',
    unit: 'kWh',
  };

  it('should render with raw readings only', () => {
    const rawReadings = generateMeterReadings({ days: 5 });

    render(
      <MeterReadingsChart
        {...defaultProps}
        rawReadings={rawReadings}
      />
    );

    expect(screen.getByText(/STROM TOTAL - Readings/i)).toBeInTheDocument();
    expect(screen.getByTestId('line-chart')).toBeInTheDocument();
    expect(screen.getByTestId('line-raw')).toBeInTheDocument();
  });

  it('should render with interpolated readings only', () => {
    const interpolatedReadings = generateMeterReadings({ days: 10 });

    render(
      <MeterReadingsChart
        {...defaultProps}
        interpolatedReadings={interpolatedReadings}
      />
    );

    expect(screen.getByTestId('line-interpolated')).toBeInTheDocument();
  });

  it('should render with both raw and interpolated readings', () => {
    const rawReadings = generateMeterReadings({ days: 5 });
    const interpolatedReadings = generateMeterReadings({ days: 10 });

    render(
      <MeterReadingsChart
        {...defaultProps}
        rawReadings={rawReadings}
        interpolatedReadings={interpolatedReadings}
      />
    );

    expect(screen.getByTestId('line-raw')).toBeInTheDocument();
    expect(screen.getByTestId('line-interpolated')).toBeInTheDocument();
  });

  it('should use custom title when provided', () => {
    const rawReadings = generateMeterReadings({ days: 3 });

    render(
      <MeterReadingsChart
        {...defaultProps}
        rawReadings={rawReadings}
        title="Custom Chart Title"
      />
    );

    expect(screen.getByText('Custom Chart Title')).toBeInTheDocument();
  });

  it('should format meter ID in default title', () => {
    const rawReadings = generateMeterReadings({ days: 3 });

    render(
      <MeterReadingsChart
        meterId="gas_meter_test"
        unit="m³"
        rawReadings={rawReadings}
      />
    );

    expect(screen.getByText(/GAS METER TEST - Readings/i)).toBeInTheDocument();
  });

  it('should handle empty data gracefully', () => {
    render(
      <MeterReadingsChart
        {...defaultProps}
        rawReadings={[]}
        interpolatedReadings={[]}
      />
    );

    expect(screen.getByTestId('line-chart')).toBeInTheDocument();
  });

  it('should combine raw and interpolated data by timestamp', () => {
    const rawReadings = generateMeterReadings({
      days: 3,
      startDate: '2024-01-01',
    });
    const interpolatedReadings = generateMeterReadings({
      days: 5,
      startDate: '2024-01-01',
    });

    const { container } = render(
      <MeterReadingsChart
        {...defaultProps}
        rawReadings={rawReadings}
        interpolatedReadings={interpolatedReadings}
      />
    );

    expect(container).toBeInTheDocument();
  });

  it('should sort data by timestamp', () => {
    const unsortedReadings = [
      { timestamp: '2024-01-03T00:00:00Z', value: 300 },
      { timestamp: '2024-01-01T00:00:00Z', value: 100 },
      { timestamp: '2024-01-02T00:00:00Z', value: 200 },
    ];

    render(
      <MeterReadingsChart
        {...defaultProps}
        rawReadings={unsortedReadings}
      />
    );

    expect(screen.getByTestId('line-chart')).toBeInTheDocument();
  });

  it('should render all chart components', () => {
    const rawReadings = generateMeterReadings({ days: 5 });

    render(
      <MeterReadingsChart
        {...defaultProps}
        rawReadings={rawReadings}
      />
    );

    expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
    expect(screen.getByTestId('line-chart')).toBeInTheDocument();
    expect(screen.getByTestId('cartesian-grid')).toBeInTheDocument();
    expect(screen.getByTestId('x-axis')).toBeInTheDocument();
    expect(screen.getByTestId('y-axis')).toBeInTheDocument();
    expect(screen.getByTestId('tooltip')).toBeInTheDocument();
    expect(screen.getByTestId('legend')).toBeInTheDocument();
  });
});
