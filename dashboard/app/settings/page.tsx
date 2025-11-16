'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import useMediaQuery from '@/hooks/useMediaQuery';
import {
  Household,
  HouseholdConfig,
  DEFAULT_HOUSEHOLD_CONFIG,
  validateCostAllocation,
  getHouseholdMeters,
} from '@/types/household';
import PriceManagement from '@/components/PriceManagement';

const STORAGE_KEY = 'household_config';

type TabType = 'households' | 'prices';

export default function SettingsPage() {
  const isMobile = useMediaQuery('(max-width: 640px)');

  const [activeTab, setActiveTab] = useState<TabType>('households');
  const [config, setConfig] = useState<HouseholdConfig>(DEFAULT_HOUSEHOLD_CONFIG);
  const [selectedHousehold, setSelectedHousehold] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string>('');

  // Load config from localStorage on mount
  useEffect(() => {
    // Check if running in browser (SSR safety)
    if (typeof window === 'undefined') return;

    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        // Validate structure before setting
        if (parsed && parsed.version && Array.isArray(parsed.households)) {
          setConfig(parsed);
        } else {
          console.warn('Invalid household config structure in localStorage');
        }
      }
    } catch (error) {
      console.error('Failed to parse stored config:', error);
    }
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      const updatedConfig = {
        ...config,
        lastUpdated: new Date().toISOString(),
      };

      // Save to localStorage
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updatedConfig));

      // Also save to InfluxDB
      try {
        const response = await fetch('/api/household-config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(updatedConfig),
        });

        if (response.ok) {
          setSaveMessage('✓ Configuration saved to localStorage and InfluxDB!');
        } else {
          setSaveMessage('✓ Configuration saved to localStorage (InfluxDB sync failed)');
        }
      } catch (apiError) {
        console.error('InfluxDB sync error:', apiError);
        setSaveMessage('✓ Configuration saved to localStorage (InfluxDB sync failed)');
      }

      setConfig(updatedConfig);
      setTimeout(() => setSaveMessage(''), 3000);
    } catch (error) {
      setSaveMessage('✗ Failed to save configuration');
      console.error('Save error:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    if (confirm('Are you sure you want to reset to default configuration? This cannot be undone.')) {
      setConfig(DEFAULT_HOUSEHOLD_CONFIG);
      localStorage.removeItem(STORAGE_KEY);
      setSaveMessage('✓ Reset to default configuration');
      setTimeout(() => setSaveMessage(''), 3000);
    }
  };

  const handleExport = () => {
    const dataStr = JSON.stringify(config, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr);
    const exportFileDefaultName = `household-config-${new Date().toISOString().split('T')[0]}.json`;

    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
  };

  const handleImport = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const imported = JSON.parse(e.target?.result as string);
        setConfig(imported);
        setSaveMessage('✓ Configuration imported successfully');
        setTimeout(() => setSaveMessage(''), 3000);
      } catch (error) {
        setSaveMessage('✗ Failed to import configuration');
        console.error('Import error:', error);
      }
    };
    reader.readAsText(file);
  };

  const updateHousehold = (id: string, updates: Partial<Household>) => {
    setConfig({
      ...config,
      households: config.households.map((h) =>
        h.id === id ? { ...h, ...updates } : h
      ),
    });
  };

  const addHousehold = () => {
    const newId = `household_${Date.now()}`;
    const newHousehold: Household = {
      id: newId,
      name: 'New Household',
      type: 'unit',
      color: '#3b82f6',
      meters: {},
    };
    setConfig({
      ...config,
      households: [...config.households, newHousehold],
    });
    setSelectedHousehold(newId);
  };

  const deleteHousehold = (id: string) => {
    if (confirm('Are you sure you want to delete this household?')) {
      setConfig({
        ...config,
        households: config.households.filter((h) => h.id !== id),
      });
      if (selectedHousehold === id) {
        setSelectedHousehold(null);
      }
    }
  };

  const selectedHouseholdData = config.households.find((h) => h.id === selectedHousehold);

  // Calculate allocation totals
  const allocationTotals = {
    sharedElectricity: config.households.reduce((sum, h) => sum + (h.costAllocation?.sharedElectricity || 0), 0),
    sharedGas: config.households.reduce((sum, h) => sum + (h.costAllocation?.sharedGas || 0), 0),
    sharedWater: config.households.reduce((sum, h) => sum + (h.costAllocation?.sharedWater || 0), 0),
    sharedHeat: config.households.reduce((sum, h) => sum + (h.costAllocation?.sharedHeat || 0), 0),
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">Household Settings</h1>
              <p className="mt-1 text-sm text-gray-600">
                Configure households and cost allocation for multi-unit building management
              </p>
            </div>
            <Link
              href="/"
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors text-center"
            >
              ← Back to Dashboard
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {/* Tabs */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-2 mb-8">
          <div className="flex space-x-2">
            <button
              onClick={() => setActiveTab('households')}
              className={`flex-1 px-6 py-3 rounded-lg font-medium transition-colors ${
                activeTab === 'households'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              🏠 Households & Allocation
            </button>
            <button
              onClick={() => setActiveTab('prices')}
              className={`flex-1 px-6 py-3 rounded-lg font-medium transition-colors ${
                activeTab === 'prices'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              💰 Price Management
            </button>
          </div>
        </div>

        {/* Household Configuration Tab */}
        {activeTab === 'households' && (
          <>
            {/* Action Buttons */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
          <div className="flex flex-wrap gap-3">
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              {saving ? 'Saving...' : '💾 Save Configuration'}
            </button>
            <button
              onClick={handleReset}
              className="px-6 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
            >
              🔄 Reset to Default
            </button>
            <button
              onClick={handleExport}
              className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            >
              📤 Export Config
            </button>
            <label className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors cursor-pointer">
              📥 Import Config
              <input
                type="file"
                accept=".json"
                onChange={handleImport}
                className="hidden"
              />
            </label>
            <button
              onClick={addHousehold}
              className="px-6 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors"
            >
              ➕ Add Household
            </button>
          </div>
          {saveMessage && (
            <div className={`mt-4 p-3 rounded-lg ${saveMessage.includes('✓') ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
              {saveMessage}
            </div>
          )}
        </div>

        {/* Cost Allocation Summary */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Cost Allocation Summary</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {Object.entries(allocationTotals).map(([key, total]) => {
              const isValid = Math.abs(total - 100) < 0.01 || total === 0;
              return (
                <div
                  key={key}
                  className={`p-4 rounded-lg border-2 ${
                    total === 0
                      ? 'border-gray-200 bg-gray-50'
                      : isValid
                      ? 'border-green-200 bg-green-50'
                      : 'border-red-200 bg-red-50'
                  }`}
                >
                  <h3 className="text-sm font-medium text-gray-600 mb-1">
                    {key.replace('shared', '').replace(/([A-Z])/g, ' $1')}
                  </h3>
                  <p className={`text-2xl font-bold ${
                    total === 0 ? 'text-gray-400' : isValid ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {total.toFixed(1)}%
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    {total === 0 ? 'Not allocated' : isValid ? '✓ Valid' : '✗ Must equal 100%'}
                  </p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Households List */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left: Household List */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">
                Households ({config.households.length})
              </h2>
              <div className="space-y-2">
                {config.households.map((household) => (
                  <button
                    key={household.id}
                    onClick={() => setSelectedHousehold(household.id)}
                    className={`w-full text-left p-4 rounded-lg border-2 transition-all ${
                      selectedHousehold === household.id
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <div
                          className="w-4 h-4 rounded-full"
                          style={{ backgroundColor: household.color }}
                        />
                        <div>
                          <h3 className="font-medium text-gray-900">{household.name}</h3>
                          <p className="text-xs text-gray-500 capitalize">{household.type}</p>
                        </div>
                      </div>
                      <span className="text-xs text-gray-400">
                        {getHouseholdMeters(household).length} meters
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Right: Household Details */}
          <div className="lg:col-span-2">
            {selectedHouseholdData ? (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-xl font-bold text-gray-900">Edit Household</h2>
                  <button
                    onClick={() => deleteHousehold(selectedHouseholdData.id)}
                    className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm"
                  >
                    🗑️ Delete
                  </button>
                </div>

                <div className="space-y-6">
                  {/* Basic Info */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Name
                      </label>
                      <input
                        type="text"
                        value={selectedHouseholdData.name}
                        onChange={(e) =>
                          updateHousehold(selectedHouseholdData.id, { name: e.target.value })
                        }
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Type
                      </label>
                      <select
                        value={selectedHouseholdData.type}
                        onChange={(e) =>
                          updateHousehold(selectedHouseholdData.id, {
                            type: e.target.value as 'unit' | 'shared',
                          })
                        }
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      >
                        <option value="unit">Unit</option>
                        <option value="shared">Shared</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Color
                      </label>
                      <input
                        type="color"
                        value={selectedHouseholdData.color}
                        onChange={(e) =>
                          updateHousehold(selectedHouseholdData.id, { color: e.target.value })
                        }
                        className="w-full h-10 rounded-lg cursor-pointer"
                      />
                    </div>
                  </div>

                  {/* Description */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Description
                    </label>
                    <textarea
                      value={selectedHouseholdData.description || ''}
                      onChange={(e) =>
                        updateHousehold(selectedHouseholdData.id, { description: e.target.value })
                      }
                      rows={2}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="Optional description..."
                    />
                  </div>

                  {/* Cost Allocation */}
                  {selectedHouseholdData.type === 'unit' && (
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900 mb-3">
                        Cost Allocation (% of Shared Utilities)
                      </h3>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        {(['sharedElectricity', 'sharedGas', 'sharedWater', 'sharedHeat'] as const).map(
                          (key) => (
                            <div key={key}>
                              <label className="block text-sm font-medium text-gray-700 mb-2">
                                {key.replace('shared', '')}
                              </label>
                              <div className="relative">
                                <input
                                  type="number"
                                  min="0"
                                  max="100"
                                  step="0.1"
                                  value={selectedHouseholdData.costAllocation?.[key] || 0}
                                  onChange={(e) => {
                                    let value = parseFloat(e.target.value);
                                    // Validate and clamp to 0-100 range
                                    if (isNaN(value)) value = 0;
                                    value = Math.max(0, Math.min(100, value));
                                    updateHousehold(selectedHouseholdData.id, {
                                      costAllocation: {
                                        ...selectedHouseholdData.costAllocation,
                                        [key]: value,
                                      },
                                    });
                                  }}
                                  onBlur={(e) => {
                                    // Ensure value is clamped on blur as well
                                    let value = parseFloat(e.target.value);
                                    if (isNaN(value) || value < 0 || value > 100) {
                                      if (isNaN(value)) value = 0;
                                      value = Math.max(0, Math.min(100, value));
                                      updateHousehold(selectedHouseholdData.id, {
                                        costAllocation: {
                                          ...selectedHouseholdData.costAllocation,
                                          [key]: value,
                                        },
                                      });
                                    }
                                  }}
                                  className="w-full px-4 py-2 pr-8 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                />
                                <span className="absolute right-3 top-2 text-gray-500">%</span>
                              </div>
                            </div>
                          )
                        )}
                      </div>
                    </div>
                  )}

                  {/* Assigned Meters */}
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-3">
                      Assigned Meters ({getHouseholdMeters(selectedHouseholdData).length})
                    </h3>
                    <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                      <p className="text-sm text-gray-600 mb-2">
                        Meters assigned to this household:
                      </p>
                      {getHouseholdMeters(selectedHouseholdData).length > 0 ? (
                        <div className="flex flex-wrap gap-2">
                          {getHouseholdMeters(selectedHouseholdData).map((meterId) => (
                            <span
                              key={meterId}
                              className="px-3 py-1 bg-white border border-gray-300 rounded-lg text-sm"
                            >
                              {meterId}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-gray-400 italic">No meters assigned yet</p>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 mt-2">
                      Note: Use the main dashboard to assign meters to households
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
                <p className="text-gray-500">Select a household to edit its configuration</p>
              </div>
            )}
          </div>
        </div>
          </>
        )}

        {/* Price Management Tab */}
        {activeTab === 'prices' && (
          <PriceManagement />
        )}
      </main>
    </div>
  );
}
