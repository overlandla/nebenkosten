'use client';

import React from 'react';

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
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 mb-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">

        {/* View Mode Selector */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            View Mode
          </label>
          <select
            value={viewMode}
            onChange={(e) => onViewModeChange(e.target.value as 'raw' | 'consumption')}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
          >
            <option value="raw">Raw Meter Readings</option>
            <option value="consumption">Consumption Analysis</option>
          </select>
        </div>

        {/* Household Selector */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Household
          </label>
          <select
            value={selectedHousehold || 'all'}
            onChange={(e) => onHouseholdChange(e.target.value === 'all' ? null : e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
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
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Category
          </label>
          <select
            value={selectedCategory}
            onChange={(e) => onCategoryChange(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
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
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Meters
          </label>
          <button
            onClick={() => setMetersDropdownOpen(!metersDropdownOpen)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-left focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white flex justify-between items-center"
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
            <div className="absolute z-10 mt-1 w-full bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md shadow-lg max-h-96 overflow-hidden flex flex-col">
              {/* Search box */}
              <div className="p-3 border-b border-gray-200 dark:border-gray-600">
                <input
                  type="text"
                  placeholder="Search meters..."
                  value={searchTerm}
                  onChange={(e) => onSearchChange(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-white"
                />
              </div>

              {/* Select/Clear all */}
              <div className="p-2 border-b border-gray-200 dark:border-gray-600 flex gap-2">
                <button
                  onClick={selectAllMeters}
                  className="flex-1 px-3 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600"
                >
                  Select All
                </button>
                <button
                  onClick={clearAllMeters}
                  className="flex-1 px-3 py-1 text-xs bg-gray-500 text-white rounded hover:bg-gray-600"
                >
                  Clear All
                </button>
              </div>

              {/* Meter list */}
              <div className="overflow-y-auto flex-1">
                {filteredMeters.length === 0 ? (
                  <div className="p-3 text-sm text-gray-500 dark:text-gray-400 text-center">
                    No meters found
                  </div>
                ) : (
                  filteredMeters.map(meter => (
                    <label
                      key={meter.id}
                      className="flex items-center px-3 py-2 hover:bg-gray-100 dark:hover:bg-gray-600 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={selectedMeters.includes(meter.id)}
                        onChange={() => toggleMeter(meter.id)}
                        className="mr-3 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-gray-900 dark:text-white truncate">
                          {meter.name}
                        </div>
                        <div className="text-xs text-gray-500 dark:text-gray-400 truncate">
                          {meter.id}
                        </div>
                      </div>
                      <span className="ml-2 px-2 py-1 text-xs rounded-full bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-300">
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
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <div className="flex flex-wrap gap-2 items-center">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Active filters:</span>

            {selectedHousehold && (
              <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200">
                Household: {households.find(h => h.id === selectedHousehold)?.name}
                <button
                  onClick={() => onHouseholdChange(null)}
                  className="ml-2 hover:text-blue-900 dark:hover:text-blue-100"
                >
                  ×
                </button>
              </span>
            )}

            {selectedCategory !== 'all' && (
              <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200">
                Category: {categories.find(c => c.id === selectedCategory)?.label}
                <button
                  onClick={() => onCategoryChange('all')}
                  className="ml-2 hover:text-green-900 dark:hover:text-green-100"
                >
                  ×
                </button>
              </span>
            )}

            {selectedMeters.length > 0 && (
              <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200">
                {selectedMeters.length} meter{selectedMeters.length !== 1 ? 's' : ''} selected
                <button
                  onClick={clearAllMeters}
                  className="ml-2 hover:text-purple-900 dark:hover:text-purple-100"
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
