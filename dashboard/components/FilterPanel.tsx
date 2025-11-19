'use client';

import React from 'react';
import { Button } from '@/components/ui/button';

interface FilterPanelProps {
  // View mode
  viewMode: 'raw' | 'consumption';
  onViewModeChange: (mode: 'raw' | 'consumption') => void;

  // Category filter
  selectedCategory: string;
  onCategoryChange: (category: string) => void;
  categories: { id: string; label: string; count: number }[];

  // Household filter
  selectedHousehold: string | null;
  onHouseholdChange: (household: string | null) => void;
  households: { id: string; name: string; color: string }[];

  // Meter selection
  selectedMeters: string[];
  onMetersChange: (meters: string[]) => void;
  availableMeters: { id: string; name: string; category: string }[];

  // Search/filter
  searchTerm: string;
  onSearchChange: (term: string) => void;
}

export default function FilterPanel({
  viewMode,
  onViewModeChange,
  selectedCategory,
  onCategoryChange,
  categories,
  selectedHousehold,
  onHouseholdChange,
  households,
  selectedMeters,
  onMetersChange,
  availableMeters,
  searchTerm,
  onSearchChange,
}: FilterPanelProps) {
  const [metersDropdownOpen, setMetersDropdownOpen] = React.useState(false);
  const dropdownRef = React.useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  React.useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setMetersDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const toggleMeter = (meterId: string) => {
    if (selectedMeters.includes(meterId)) {
      onMetersChange(selectedMeters.filter(id => id !== meterId));
    } else {
      onMetersChange([...selectedMeters, meterId]);
    }
  };

  const selectAllMeters = () => {
    onMetersChange(availableMeters.map(m => m.id));
  };

  const clearAllMeters = () => {
    onMetersChange([]);
  };

  const filteredMeters = availableMeters.filter(meter => {
    const matchesCategory = selectedCategory === 'all' || meter.category === selectedCategory;
    const matchesSearch = searchTerm === '' ||
      meter.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      meter.id.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  return (
    <div className="bg-white dark:bg-neutral-950 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-800 p-6 mb-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">

        {/* View Mode Selector */}
        <div>
          <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
            View Mode
          </label>
          <select
            value={viewMode}
            onChange={(e) => onViewModeChange(e.target.value as 'raw' | 'consumption')}
            className="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-950 text-neutral-900 dark:text-neutral-50 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-neutral-950 dark:focus:ring-neutral-300"
          >
            <option value="raw">Raw Meter Readings</option>
            <option value="consumption">Consumption Analysis</option>
          </select>
        </div>

        {/* Household Selector */}
        <div>
          <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
            Household
          </label>
          <select
            value={selectedHousehold || 'all'}
            onChange={(e) => onHouseholdChange(e.target.value === 'all' ? null : e.target.value)}
            className="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-950 text-neutral-900 dark:text-neutral-50 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-neutral-950 dark:focus:ring-neutral-300"
          >
            <option value="all">All Households</option>
            {households.map(household => (
              <option key={household.id} value={household.id}>
                {household.name}
              </option>
            ))}
          </select>
        </div>

        {/* Category Filter */}
        <div>
          <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
            Category
          </label>
          <select
            value={selectedCategory}
            onChange={(e) => onCategoryChange(e.target.value)}
            className="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-950 text-neutral-900 dark:text-neutral-50 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-neutral-950 dark:focus:ring-neutral-300"
          >
            {categories.map(cat => (
              <option key={cat.id} value={cat.id}>
                {cat.label} ({cat.count})
              </option>
            ))}
          </select>
        </div>

        {/* Meter Multi-Select */}
        <div className="relative" ref={dropdownRef}>
          <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
            Meters
          </label>
          <button
            onClick={() => setMetersDropdownOpen(!metersDropdownOpen)}
            className="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-950 text-neutral-900 dark:text-neutral-50 rounded-md shadow-sm text-left focus:outline-none focus:ring-2 focus:ring-neutral-950 dark:focus:ring-neutral-300 flex justify-between items-center"
          >
            <span className="truncate">
              {selectedMeters.length === 0
                ? 'Select meters...'
                : `${selectedMeters.length} meter${selectedMeters.length !== 1 ? 's' : ''} selected`}
            </span>
            <svg
              className={`w-5 h-5 transition-transform ${metersDropdownOpen ? 'transform rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {metersDropdownOpen && (
            <div className="absolute z-10 mt-1 w-full bg-white dark:bg-neutral-950 border border-neutral-300 dark:border-neutral-700 rounded-md shadow-lg max-h-96 overflow-hidden flex flex-col">
              {/* Search box */}
              <div className="p-3 border-b border-neutral-200 dark:border-neutral-800">
                <input
                  type="text"
                  placeholder="Search meters..."
                  value={searchTerm}
                  onChange={(e) => onSearchChange(e.target.value)}
                  className="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-950 text-neutral-900 dark:text-neutral-50 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-neutral-950 dark:focus:ring-neutral-300"
                />
              </div>

              {/* Select/Clear all */}
              <div className="p-2 border-b border-neutral-200 dark:border-neutral-800 flex gap-2">
                <Button
                  onClick={selectAllMeters}
                  size="sm"
                  className="flex-1"
                >
                  Select All
                </Button>
                <Button
                  onClick={clearAllMeters}
                  size="sm"
                  variant="secondary"
                  className="flex-1"
                >
                  Clear All
                </Button>
              </div>

              {/* Meter list */}
              <div className="overflow-y-auto flex-1">
                {filteredMeters.length === 0 ? (
                  <div className="p-3 text-sm text-neutral-500 dark:text-neutral-400 text-center">
                    No meters found
                  </div>
                ) : (
                  filteredMeters.map(meter => (
                    <label
                      key={meter.id}
                      className="flex items-center px-3 py-2 hover:bg-neutral-100 dark:hover:bg-neutral-900 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={selectedMeters.includes(meter.id)}
                        onChange={() => toggleMeter(meter.id)}
                        className="mr-3 h-4 w-4 rounded border-neutral-300 dark:border-neutral-700 text-neutral-900 dark:text-neutral-50 focus:ring-neutral-950 dark:focus:ring-neutral-300"
                      />
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-neutral-900 dark:text-neutral-50 truncate">
                          {meter.name}
                        </div>
                        <div className="text-xs text-neutral-500 dark:text-neutral-400 truncate">
                          {meter.id}
                        </div>
                      </div>
                      <span className="ml-2 px-2 py-1 text-xs rounded-full bg-neutral-200 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300">
                        {meter.category}
                      </span>
                    </label>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Active filters summary */}
      {(selectedHousehold || selectedCategory !== 'all' || selectedMeters.length > 0) && (
        <div className="mt-4 pt-4 border-t border-neutral-200 dark:border-neutral-800">
          <div className="flex flex-wrap gap-2 items-center">
            <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300">Active filters:</span>

            {selectedHousehold && (
              <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-neutral-100 dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200">
                Household: {households.find(h => h.id === selectedHousehold)?.name}
                <button
                  onClick={() => onHouseholdChange(null)}
                  className="ml-2 hover:text-neutral-900 dark:hover:text-neutral-100"
                >
                  ×
                </button>
              </span>
            )}

            {selectedCategory !== 'all' && (
              <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-neutral-100 dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200">
                Category: {categories.find(c => c.id === selectedCategory)?.label}
                <button
                  onClick={() => onCategoryChange('all')}
                  className="ml-2 hover:text-neutral-900 dark:hover:text-neutral-100"
                >
                  ×
                </button>
              </span>
            )}

            {selectedMeters.length > 0 && (
              <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-neutral-100 dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200">
                {selectedMeters.length} meter{selectedMeters.length !== 1 ? 's' : ''} selected
                <button
                  onClick={clearAllMeters}
                  className="ml-2 hover:text-neutral-900 dark:hover:text-neutral-100"
                >
                  ×
                </button>
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
