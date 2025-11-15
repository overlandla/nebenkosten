/**
 * Unit tests for TimeRangeSelector component
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import TimeRangeSelector, { TimeRange } from '@/components/TimeRangeSelector';

// Mock useMediaQuery hook
jest.mock('@/hooks/useMediaQuery', () => ({
  __esModule: true,
  default: jest.fn(() => false), // Default to desktop
}));

describe('TimeRangeSelector', () => {
  const mockOnRangeChange = jest.fn();

  beforeEach(() => {
    mockOnRangeChange.mockClear();
  });

  it('should render all preset range buttons', () => {
    render(<TimeRangeSelector onRangeChange={mockOnRangeChange} />);

    expect(screen.getByText('Last 7 Days')).toBeInTheDocument();
    expect(screen.getByText('Last 30 Days')).toBeInTheDocument();
    expect(screen.getByText('Last 3 Months')).toBeInTheDocument();
    expect(screen.getByText('Last 6 Months')).toBeInTheDocument();
    expect(screen.getByText('Last Year')).toBeInTheDocument();
    expect(screen.getByText('Year to Date')).toBeInTheDocument();
    expect(screen.getByText('All Time')).toBeInTheDocument();
    expect(screen.getByText('Custom Range')).toBeInTheDocument();
  });

  it('should select Last 3 Months by default', () => {
    render(<TimeRangeSelector onRangeChange={mockOnRangeChange} />);

    const button = screen.getByText('Last 3 Months');
    expect(button).toHaveClass('bg-blue-600');
  });

  it('should call onRangeChange when preset is clicked', () => {
    render(<TimeRangeSelector onRangeChange={mockOnRangeChange} />);

    const button = screen.getByText('Last 7 Days');
    fireEvent.click(button);

    expect(mockOnRangeChange).toHaveBeenCalledTimes(1);
    const call = mockOnRangeChange.mock.calls[0][0] as TimeRange;
    expect(call.label).toBe('Last 7 Days');
    expect(call.start).toBeInstanceOf(Date);
    expect(call.end).toBeInstanceOf(Date);
  });

  it('should update selected state when preset is clicked', () => {
    render(<TimeRangeSelector onRangeChange={mockOnRangeChange} />);

    const button = screen.getByText('Last 30 Days');
    fireEvent.click(button);

    expect(button).toHaveClass('bg-blue-600');
    expect(screen.getByText('Last 3 Months')).not.toHaveClass('bg-blue-600');
  });

  it('should show custom date inputs when Custom Range is clicked', () => {
    render(<TimeRangeSelector onRangeChange={mockOnRangeChange} />);

    const customButton = screen.getByText('Custom Range');
    fireEvent.click(customButton);

    expect(screen.getByLabelText('Start Date')).toBeInTheDocument();
    expect(screen.getByLabelText('End Date')).toBeInTheDocument();
    expect(screen.getByText('Apply')).toBeInTheDocument();
  });

  it('should hide custom inputs when custom mode is toggled off', () => {
    render(<TimeRangeSelector onRangeChange={mockOnRangeChange} />);

    const customButton = screen.getByText('Custom Range');

    // Toggle on
    fireEvent.click(customButton);
    expect(screen.getByLabelText('Start Date')).toBeInTheDocument();

    // Toggle off
    fireEvent.click(customButton);
    expect(screen.queryByLabelText('Start Date')).not.toBeInTheDocument();
  });

  it('should allow entering custom start date', () => {
    render(<TimeRangeSelector onRangeChange={mockOnRangeChange} />);

    const customButton = screen.getByText('Custom Range');
    fireEvent.click(customButton);

    const startInput = screen.getByLabelText('Start Date') as HTMLInputElement;
    fireEvent.change(startInput, { target: { value: '2024-01-01' } });

    expect(startInput.value).toBe('2024-01-01');
  });

  it('should allow entering custom end date', () => {
    render(<TimeRangeSelector onRangeChange={mockOnRangeChange} />);

    const customButton = screen.getByText('Custom Range');
    fireEvent.click(customButton);

    const endInput = screen.getByLabelText('End Date') as HTMLInputElement;
    fireEvent.change(endInput, { target: { value: '2024-12-31' } });

    expect(endInput.value).toBe('2024-12-31');
  });

  it('should call onRangeChange when Apply is clicked with custom dates', () => {
    render(<TimeRangeSelector onRangeChange={mockOnRangeChange} />);

    const customButton = screen.getByText('Custom Range');
    fireEvent.click(customButton);

    const startInput = screen.getByLabelText('Start Date');
    const endInput = screen.getByLabelText('End Date');

    fireEvent.change(startInput, { target: { value: '2024-01-01' } });
    fireEvent.change(endInput, { target: { value: '2024-06-30' } });

    const applyButton = screen.getByText('Apply');
    fireEvent.click(applyButton);

    expect(mockOnRangeChange).toHaveBeenCalled();
    const call = mockOnRangeChange.mock.calls[0][0] as TimeRange;
    expect(call.label).toContain('2024');
    expect(call.start).toBeInstanceOf(Date);
    expect(call.end).toBeInstanceOf(Date);
  });

  it('should apply custom className when provided', () => {
    const { container } = render(
      <TimeRangeSelector
        onRangeChange={mockOnRangeChange}
        className="custom-class"
      />
    );

    const div = container.firstChild as HTMLElement;
    expect(div).toHaveClass('custom-class');
  });

  it('should deselect preset when custom range is applied', () => {
    render(<TimeRangeSelector onRangeChange={mockOnRangeChange} />);

    // Select a preset first
    const presetButton = screen.getByText('Last 7 Days');
    fireEvent.click(presetButton);
    expect(presetButton).toHaveClass('bg-blue-600');

    // Switch to custom
    const customButton = screen.getByText('Custom Range');
    fireEvent.click(customButton);
    fireEvent.click(screen.getByText('Apply'));

    // Preset should no longer be selected
    expect(presetButton).not.toHaveClass('bg-blue-600');
  });

  it('should handle Year to Date preset correctly', () => {
    render(<TimeRangeSelector onRangeChange={mockOnRangeChange} />);

    const ytdButton = screen.getByText('Year to Date');
    fireEvent.click(ytdButton);

    expect(mockOnRangeChange).toHaveBeenCalled();
    const call = mockOnRangeChange.mock.calls[0][0] as TimeRange;
    expect(call.label).toBe('Year to Date');

    const currentYear = new Date().getFullYear();
    expect(call.start.getFullYear()).toBe(currentYear);
    expect(call.start.getMonth()).toBe(0); // January
    expect(call.start.getDate()).toBe(1);
  });

  it('should handle All Time preset correctly', () => {
    render(<TimeRangeSelector onRangeChange={mockOnRangeChange} />);

    const allTimeButton = screen.getByText('All Time');
    fireEvent.click(allTimeButton);

    expect(mockOnRangeChange).toHaveBeenCalled();
    const call = mockOnRangeChange.mock.calls[0][0] as TimeRange;
    expect(call.label).toBe('All Time');
    expect(call.start.getFullYear()).toBe(2020);
  });
});
