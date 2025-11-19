'use client';

import React, { useState } from 'react';
import { subDays, subMonths, subYears, format } from 'date-fns';
import useMediaQuery from '@/hooks/useMediaQuery';
import { Button } from '@/components/ui/button';

export interface TimeRange {
  start: Date;
  end: Date;
  label: string;
}

interface TimeRangeSelectorProps {
  onRangeChange: (range: TimeRange) => void;
  className?: string;
}

const PRESET_RANGES = [
  { label: 'Last 7 Days', getDates: () => ({ start: subDays(new Date(), 7), end: new Date() }) },
  { label: 'Last 30 Days', getDates: () => ({ start: subDays(new Date(), 30), end: new Date() }) },
  { label: 'Last 3 Months', getDates: () => ({ start: subMonths(new Date(), 3), end: new Date() }) },
  { label: 'Last 6 Months', getDates: () => ({ start: subMonths(new Date(), 6), end: new Date() }) },
  { label: 'Last Year', getDates: () => ({ start: subYears(new Date(), 1), end: new Date() }) },
  { label: 'Year to Date', getDates: () => ({ start: new Date(new Date().getFullYear(), 0, 1), end: new Date() }) },
  { label: 'All Time', getDates: () => ({ start: new Date(2020, 0, 1), end: new Date() }) },
];

export default function TimeRangeSelector({ onRangeChange, className = '' }: TimeRangeSelectorProps) {
  const isMobile = useMediaQuery('(max-width: 640px)');
  const [selectedPreset, setSelectedPreset] = useState('Last 3 Months');
  const [customMode, setCustomMode] = useState(false);
  const [customStart, setCustomStart] = useState(format(subMonths(new Date(), 3), 'yyyy-MM-dd'));
  const [customEnd, setCustomEnd] = useState(format(new Date(), 'yyyy-MM-dd'));

  const handlePresetClick = (preset: typeof PRESET_RANGES[0]) => {
    setSelectedPreset(preset.label);
    setCustomMode(false);
    const dates = preset.getDates();
    onRangeChange({
      start: dates.start,
      end: dates.end,
      label: preset.label,
    });
  };

  const handleCustomApply = () => {
    const start = new Date(customStart);
    const end = new Date(customEnd);
    onRangeChange({
      start,
      end,
      label: `${format(start, 'MMM d, yyyy')} - ${format(end, 'MMM d, yyyy')}`,
    });
    setSelectedPreset('Custom');
  };

  return (
    <div className={`bg-white dark:bg-neutral-950 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-800 p-4 ${className}`}>
      <div className="flex flex-wrap gap-2 mb-4">
        {PRESET_RANGES.map((preset) => (
          <Button
            key={preset.label}
            onClick={() => handlePresetClick(preset)}
            variant={selectedPreset === preset.label && !customMode ? 'default' : 'secondary'}
            size="sm"
          >
            {preset.label}
          </Button>
        ))}
        <Button
          onClick={() => setCustomMode(!customMode)}
          variant={customMode ? 'default' : 'secondary'}
          size="sm"
        >
          Custom Range
        </Button>
      </div>

      {customMode && (
        <div className={`p-4 bg-neutral-50 dark:bg-neutral-900 rounded-md ${isMobile ? 'space-y-4' : 'flex items-end gap-4'}`}>
          <div className="flex-1">
            <label htmlFor="custom-start-date" className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
              Start Date
            </label>
            <input
              id="custom-start-date"
              type="date"
              value={customStart}
              onChange={(e) => setCustomStart(e.target.value)}
              className="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-950 text-neutral-900 dark:text-neutral-50 rounded-md focus:outline-none focus:ring-2 focus:ring-neutral-950 dark:focus:ring-neutral-300"
            />
          </div>
          <div className="flex-1">
            <label htmlFor="custom-end-date" className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
              End Date
            </label>
            <input
              id="custom-end-date"
              type="date"
              value={customEnd}
              onChange={(e) => setCustomEnd(e.target.value)}
              className="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-950 text-neutral-900 dark:text-neutral-50 rounded-md focus:outline-none focus:ring-2 focus:ring-neutral-950 dark:focus:ring-neutral-300"
            />
          </div>
          <Button
            onClick={handleCustomApply}
            className={isMobile ? 'w-full' : ''}
          >
            Apply
          </Button>
        </div>
      )}
    </div>
  );
}
