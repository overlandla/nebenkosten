'use client';

import React, { useState } from 'react';
import { subDays, subMonths, subYears, format } from 'date-fns';

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
    <div className={`bg-white rounded-lg shadow-sm border border-gray-200 p-4 ${className}`}>
      <div className="flex flex-wrap gap-2 mb-4">
        {PRESET_RANGES.map((preset) => (
          <button
            key={preset.label}
            onClick={() => handlePresetClick(preset)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              selectedPreset === preset.label && !customMode
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {preset.label}
          </button>
        ))}
        <button
          onClick={() => setCustomMode(!customMode)}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            customMode
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          Custom Range
        </button>
      </div>

      {customMode && (
        <div className="flex items-end gap-4 p-4 bg-gray-50 rounded-md">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Start Date
            </label>
            <input
              type="date"
              value={customStart}
              onChange={(e) => setCustomStart(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              End Date
            </label>
            <input
              type="date"
              value={customEnd}
              onChange={(e) => setCustomEnd(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <button
            onClick={handleCustomApply}
            className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            Apply
          </button>
        </div>
      )}
    </div>
  );
}
