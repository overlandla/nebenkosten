/**
 * Unit tests for ChartSkeleton component
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import ChartSkeleton from '@/components/ChartSkeleton';

describe('ChartSkeleton', () => {
  it('should render without title by default', () => {
    const { container } = render(<ChartSkeleton />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it('should render with title when provided', () => {
    const { container } = render(<ChartSkeleton title="Loading Chart" />);

    // Title skeleton should be present
    const titleSkeleton = container.querySelector('.h-6.bg-gray-200.rounded');
    expect(titleSkeleton).toBeInTheDocument();
  });

  it('should not render title skeleton when title is not provided', () => {
    const { container } = render(<ChartSkeleton />);

    // Title skeleton should not be present
    const titleSkeleton = container.querySelector('.h-6.bg-gray-200.rounded');
    expect(titleSkeleton).not.toBeInTheDocument();
  });

  it('should use default height of 400px', () => {
    const { container } = render(<ChartSkeleton />);

    const chartArea = container.querySelector('.space-y-3') as HTMLElement;
    expect(chartArea).toHaveStyle({ height: '400px' });
  });

  it('should use custom height when provided', () => {
    const { container } = render(<ChartSkeleton height={600} />);

    const chartArea = container.querySelector('.space-y-3') as HTMLElement;
    expect(chartArea).toHaveStyle({ height: '600px' });
  });

  it('should render 12 skeleton bars', () => {
    const { container } = render(<ChartSkeleton />);

    const bars = container.querySelectorAll('.flex-1.bg-gray-200.rounded-t');
    expect(bars).toHaveLength(12);
  });

  it('should render 6 x-axis labels', () => {
    const { container } = render(<ChartSkeleton />);

    const labels = container.querySelectorAll('.h-3.bg-gray-200.rounded.w-12');
    expect(labels).toHaveLength(6);
  });

  it('should have animate-pulse class on skeleton elements', () => {
    const { container } = render(<ChartSkeleton title="Test" />);

    const animatedElements = container.querySelectorAll('.animate-pulse');
    expect(animatedElements.length).toBeGreaterThan(0);
  });

  it('should have proper container styling', () => {
    const { container } = render(<ChartSkeleton />);

    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper).toHaveClass('bg-white');
    expect(wrapper).toHaveClass('rounded-lg');
    expect(wrapper).toHaveClass('shadow-sm');
    expect(wrapper).toHaveClass('border');
    expect(wrapper).toHaveClass('border-gray-200');
    expect(wrapper).toHaveClass('p-6');
  });

  it('should render with both title and custom height', () => {
    const { container } = render(<ChartSkeleton title="Custom Title" height={500} />);

    const titleSkeleton = container.querySelector('.h-6.bg-gray-200.rounded');
    expect(titleSkeleton).toBeInTheDocument();

    const chartArea = container.querySelector('.space-y-3') as HTMLElement;
    expect(chartArea).toHaveStyle({ height: '500px' });
  });

  it('should have staggered animation delays on bars', () => {
    const { container } = render(<ChartSkeleton />);

    const bars = container.querySelectorAll('.flex-1.bg-gray-200.rounded-t');

    // Check that different bars have different animation delays
    const firstBar = bars[0] as HTMLElement;
    const secondBar = bars[1] as HTMLElement;

    expect(firstBar.style.animationDelay).not.toBe(secondBar.style.animationDelay);
  });

  it('should have random heights for skeleton bars', () => {
    const { container } = render(<ChartSkeleton />);

    const bars = container.querySelectorAll('.flex-1.bg-gray-200.rounded-t');

    // Check that bars have height styles applied
    const firstBar = bars[0] as HTMLElement;
    expect(firstBar.style.height).toBeTruthy();
    expect(firstBar.style.height).toMatch(/%$/); // Should end with %
  });
});
