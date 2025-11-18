'use client';

import { useState, useEffect } from 'react';
import { format } from 'date-fns';
import type { PriceConfig, PriceConfigInput, UtilityType, PriceConfigUpdate } from '@/types/price';

const UTILITY_LABELS: Record<UtilityType, { label: string; icon: string; defaultUnit: string }> = {
  electricity: { label: 'Electricity', icon: '⚡', defaultUnit: 'kWh' },
  gas: { label: 'Gas', icon: '🔥', defaultUnit: 'kWh' },
  water_cold: { label: 'Cold Water', icon: '💧', defaultUnit: 'm³' },
  water_warm: { label: 'Warm Water', icon: '🌡️', defaultUnit: 'm³' },
  heat: { label: 'Heat', icon: '🏠', defaultUnit: 'MWh' },
};

export default function PriceManagement() {
  const [prices, setPrices] = useState<PriceConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [selectedUtility, setSelectedUtility] = useState<UtilityType | 'all'>('all');
  const [showActiveOnly, setShowActiveOnly] = useState(false);
  const [editingPrice, setEditingPrice] = useState<PriceConfig | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  const [formData, setFormData] = useState<PriceConfigInput>({
    utilityType: 'gas',
    pricePerUnit: 0,
    unit: 'kWh',
    validFrom: format(new Date(), "yyyy-MM-dd'T'HH:mm"),
    validTo: null,
    currency: 'EUR',
    description: '',
  });

  useEffect(() => {
    fetchPrices();
  }, [selectedUtility, showActiveOnly]);

  const fetchPrices = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (selectedUtility !== 'all') {
        params.set('utilityType', selectedUtility);
      }
      if (showActiveOnly) {
        params.set('activeOnly', 'true');
      }

      const response = await fetch(`/api/price-config?${params}`);
      const data = await response.json();

      if (data.prices) {
        setPrices(data.prices);
      }
    } catch (error) {
      console.error('Error fetching prices:', error);
      showMessage('error', 'Failed to load price configurations');
    } finally {
      setLoading(false);
    }
  };

  const showMessage = (type: 'success' | 'error', text: string) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 5000);
  };

  const handleCreate = () => {
    setIsCreating(true);
    setEditingPrice(null);
    setFormData({
      utilityType: 'gas',
      pricePerUnit: 0,
      unit: 'kWh',
      validFrom: format(new Date(), "yyyy-MM-dd'T'HH:mm"),
      validTo: null,
      currency: 'EUR',
      description: '',
    });
  };

  const handleEdit = (price: PriceConfig) => {
    setEditingPrice(price);
    setIsCreating(false);
    setFormData({
      utilityType: price.utilityType,
      pricePerUnit: price.pricePerUnit,
      unit: price.unit,
      validFrom: price.validFrom.slice(0, 16), // Format for datetime-local
      validTo: price.validTo ? price.validTo.slice(0, 16) : null,
      currency: price.currency,
      description: price.description || '',
    });
  };

  const handleCancel = () => {
    setIsCreating(false);
    setEditingPrice(null);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      let response;

      if (isCreating) {
        // Create new price
        response = await fetch('/api/price-config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            ...formData,
            validFrom: new Date(formData.validFrom).toISOString(),
            validTo: formData.validTo ? new Date(formData.validTo).toISOString() : null,
          }),
        });
      } else if (editingPrice) {
        // Update existing price
        response = await fetch('/api/price-config', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            id: editingPrice.id,
            pricePerUnit: formData.pricePerUnit,
            unit: formData.unit,
            validFrom: new Date(formData.validFrom).toISOString(),
            validTo: formData.validTo ? new Date(formData.validTo).toISOString() : null,
            description: formData.description,
          }),
        });
      }

      if (response && response.ok) {
        showMessage('success', isCreating ? 'Price created successfully' : 'Price updated successfully');
        setIsCreating(false);
        setEditingPrice(null);
        fetchPrices();
      } else {
        const error = await response?.json();
        showMessage('error', error?.error || 'Failed to save price');
      }
    } catch (error) {
      console.error('Error saving price:', error);
      showMessage('error', 'Failed to save price configuration');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (priceId: string) => {
    if (!confirm('Are you sure you want to deactivate this price? It will be set to expire now.')) {
      return;
    }

    try {
      const response = await fetch(`/api/price-config?id=${priceId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        showMessage('success', 'Price deactivated successfully');
        fetchPrices();
      } else {
        const error = await response.json();
        showMessage('error', error?.error || 'Failed to deactivate price');
      }
    } catch (error) {
      console.error('Error deleting price:', error);
      showMessage('error', 'Failed to deactivate price');
    }
  };

  const filteredPrices = prices.filter((price) => {
    if (selectedUtility !== 'all' && price.utilityType !== selectedUtility) {
      return false;
    }
    return true;
  });

  const isActive = (price: PriceConfig) => {
    const now = new Date().toISOString();
    return price.validFrom <= now && (!price.validTo || price.validTo >= now);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-neutral-900">Price Management</h2>
          <p className="mt-1 text-sm text-neutral-600">
            Configure time-based pricing for utilities (electricity uses Tibber prices)
          </p>
        </div>
        <button
          onClick={handleCreate}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          ➕ Add New Price
        </button>
      </div>

      {/* Message */}
      {message && (
        <div
          className={`p-4 rounded-lg ${
            message.type === 'success'
              ? 'bg-green-50 text-green-800 border border-green-200'
              : 'bg-red-50 text-red-800 border border-red-200'
          }`}
        >
          {message.text}
        </div>
      )}

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-sm border border-neutral-200 p-4">
        <div className="flex flex-wrap gap-4">
          <div className="flex items-center space-x-2">
            <label className="text-sm font-medium text-neutral-700">Filter:</label>
            <select
              value={selectedUtility}
              onChange={(e) => setSelectedUtility(e.target.value as UtilityType | 'all')}
              className="px-3 py-1.5 border border-neutral-300 rounded-lg text-sm"
            >
              <option value="all">All Utilities</option>
              {Object.entries(UTILITY_LABELS).map(([type, { label, icon }]) => (
                <option key={type} value={type}>
                  {icon} {label}
                </option>
              ))}
            </select>
          </div>
          <label className="flex items-center space-x-2 cursor-pointer">
            <input
              type="checkbox"
              checked={showActiveOnly}
              onChange={(e) => setShowActiveOnly(e.target.checked)}
              className="w-4 h-4 text-blue-600 border-neutral-300 rounded"
            />
            <span className="text-sm text-neutral-700">Show active prices only</span>
          </label>
        </div>
      </div>

      {/* Create/Edit Form */}
      {(isCreating || editingPrice) && (
        <div className="bg-blue-50 rounded-lg border-2 border-blue-200 p-6">
          <h3 className="text-lg font-semibold text-neutral-900 mb-4">
            {isCreating ? 'Create New Price' : 'Edit Price'}
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-2">
                Utility Type
              </label>
              <select
                value={formData.utilityType}
                onChange={(e) => {
                  const utilityType = e.target.value as UtilityType;
                  setFormData({
                    ...formData,
                    utilityType,
                    unit: UTILITY_LABELS[utilityType].defaultUnit,
                  });
                }}
                disabled={!isCreating}
                className="w-full px-4 py-2 border border-neutral-300 rounded-lg"
              >
                {Object.entries(UTILITY_LABELS).map(([type, { label, icon }]) => (
                  <option key={type} value={type}>
                    {icon} {label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-2">
                Price per Unit (EUR)
              </label>
              <input
                type="number"
                step="0.0001"
                value={formData.pricePerUnit}
                onChange={(e) =>
                  setFormData({ ...formData, pricePerUnit: parseFloat(e.target.value) || 0 })
                }
                className="w-full px-4 py-2 border border-neutral-300 rounded-lg"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-2">
                Unit
              </label>
              <input
                type="text"
                value={formData.unit}
                onChange={(e) => setFormData({ ...formData, unit: e.target.value })}
                className="w-full px-4 py-2 border border-neutral-300 rounded-lg"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-2">
                Currency
              </label>
              <input
                type="text"
                value={formData.currency}
                onChange={(e) => setFormData({ ...formData, currency: e.target.value })}
                className="w-full px-4 py-2 border border-neutral-300 rounded-lg"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-2">
                Valid From
              </label>
              <input
                type="datetime-local"
                value={formData.validFrom}
                onChange={(e) => setFormData({ ...formData, validFrom: e.target.value })}
                className="w-full px-4 py-2 border border-neutral-300 rounded-lg"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-2">
                Valid To (optional)
              </label>
              <input
                type="datetime-local"
                value={formData.validTo || ''}
                onChange={(e) =>
                  setFormData({ ...formData, validTo: e.target.value || null })
                }
                className="w-full px-4 py-2 border border-neutral-300 rounded-lg"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-neutral-700 mb-2">
                Description (optional)
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                rows={2}
                className="w-full px-4 py-2 border border-neutral-300 rounded-lg"
                placeholder="e.g., Winter rate 2024-2025"
              />
            </div>
          </div>
          <div className="flex gap-3 mt-4">
            <button
              onClick={handleSave}
              disabled={saving || formData.pricePerUnit <= 0}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              {saving ? 'Saving...' : isCreating ? 'Create Price' : 'Update Price'}
            </button>
            <button
              onClick={handleCancel}
              className="px-6 py-2 bg-neutral-600 text-white rounded-lg hover:bg-neutral-700 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Prices List */}
      <div className="bg-white rounded-lg shadow-sm border border-neutral-200">
        {loading ? (
          <div className="p-12 text-center text-neutral-500">Loading prices...</div>
        ) : filteredPrices.length === 0 ? (
          <div className="p-12 text-center text-neutral-500">
            No price configurations found. Click "Add New Price" to create one.
          </div>
        ) : (
          <div className="divide-y divide-neutral-200">
            {filteredPrices.map((price) => {
              const utilityInfo = UTILITY_LABELS[price.utilityType];
              const active = isActive(price);

              return (
                <div
                  key={price.id}
                  className={`p-6 ${active ? 'bg-green-50' : 'bg-neutral-50'} hover:bg-neutral-100 transition-colors`}
                >
                  <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3">
                        <span className="text-2xl">{utilityInfo.icon}</span>
                        <div>
                          <h3 className="text-lg font-semibold text-neutral-900">
                            {utilityInfo.label}
                          </h3>
                          <p className="text-sm text-neutral-600">
                            {price.description || 'No description'}
                          </p>
                        </div>
                        {active && (
                          <span className="px-2 py-1 bg-green-600 text-white text-xs font-medium rounded">
                            ACTIVE
                          </span>
                        )}
                      </div>
                      <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                        <div>
                          <span className="text-neutral-600">Price:</span>
                          <p className="font-semibold text-neutral-900">
                            {price.pricePerUnit.toFixed(4)} {price.currency}/{price.unit}
                          </p>
                        </div>
                        <div>
                          <span className="text-neutral-600">Valid From:</span>
                          <p className="font-semibold text-neutral-900">
                            {format(new Date(price.validFrom), 'MMM d, yyyy')}
                          </p>
                        </div>
                        <div>
                          <span className="text-neutral-600">Valid To:</span>
                          <p className="font-semibold text-neutral-900">
                            {price.validTo
                              ? format(new Date(price.validTo), 'MMM d, yyyy')
                              : 'No expiry'}
                          </p>
                        </div>
                        <div>
                          <span className="text-neutral-600">Last Updated:</span>
                          <p className="font-semibold text-neutral-900">
                            {format(new Date(price.updatedAt), 'MMM d, yyyy')}
                          </p>
                        </div>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleEdit(price)}
                        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
                      >
                        ✏️ Edit
                      </button>
                      <button
                        onClick={() => handleDelete(price.id)}
                        className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm"
                        disabled={!active}
                      >
                        🗑️ Deactivate
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
