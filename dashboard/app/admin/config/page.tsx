'use client';

/**
 * Configuration Admin Page
 *
 * Manage meters, households, and their assignments
 */

import { useState, useEffect } from 'react';

type Meter = {
  id: string;
  name: string;
  meterType: string;
  category: string;
  unit: string;
  active: boolean;
  installationDate: string | null;
  deinstallationDate: string | null;
};

type Household = {
  id: string;
  name: string;
  floors: string[];
  active: boolean;
  householdMeters?: {
    meter: {
      id: string;
      name: string;
      meterType: string;
    };
  }[];
};

export default function ConfigAdminPage() {
  const [meters, setMeters] = useState<Meter[]>([]);
  const [households, setHouseholds] = useState<Household[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'meters' | 'households'>('meters');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);

    try {
      const [metersRes, householdsRes] = await Promise.all([
        fetch('/api/config/meters'),
        fetch('/api/config/households'),
      ]);

      if (!metersRes.ok || !householdsRes.ok) {
        throw new Error('Failed to load configuration');
      }

      const metersData = await metersRes.json();
      const householdsData = await householdsRes.json();

      setMeters(metersData.meters || []);
      setHouseholds(householdsData.households || []);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const toggleMeterActive = async (meterId: string, currentActive: boolean) => {
    try {
      const res = await fetch(`/api/config/meters?id=${meterId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active: !currentActive }),
      });

      if (!res.ok) throw new Error('Failed to update meter');

      await loadData();
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    }
  };

  const toggleHouseholdActive = async (householdId: string, currentActive: boolean) => {
    try {
      const res = await fetch(`/api/config/households?id=${householdId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active: !currentActive }),
      });

      if (!res.ok) throw new Error('Failed to update household');

      await loadData();
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-lg">Loading configuration...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-red-600">Error: {error}</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Configuration Management</h1>
        <p className="text-gray-600">
          Manage meters, households, and their assignments. Changes are stored in PostgreSQL
          and will be used by both the dashboard and Dagster workflows.
        </p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('meters')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'meters'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Meters ({meters.length})
          </button>
          <button
            onClick={() => setActiveTab('households')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'households'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Households ({households.length})
          </button>
        </nav>
      </div>

      {/* Meters Tab */}
      {activeTab === 'meters' && (
        <div>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-2xl font-semibold">Meters</h2>
            <button
              onClick={() => alert('Create meter functionality coming soon')}
              className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
            >
              Add Meter
            </button>
          </div>

          <div className="bg-white shadow overflow-hidden sm:rounded-lg">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    ID
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Category
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Unit
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {meters.map((meter) => (
                  <tr key={meter.id} className={!meter.active ? 'opacity-50' : ''}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900">
                      {meter.id}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {meter.name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                        {meter.meterType}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          meter.category === 'physical'
                            ? 'bg-green-100 text-green-800'
                            : meter.category === 'master'
                            ? 'bg-purple-100 text-purple-800'
                            : 'bg-orange-100 text-orange-800'
                        }`}
                      >
                        {meter.category}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {meter.unit}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <button
                        onClick={() => toggleMeterActive(meter.id, meter.active)}
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          meter.active
                            ? 'bg-green-100 text-green-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {meter.active ? 'Active' : 'Inactive'}
                      </button>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button
                        onClick={() => alert(`Edit meter: ${meter.id}`)}
                        className="text-blue-600 hover:text-blue-900 mr-4"
                      >
                        Edit
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Households Tab */}
      {activeTab === 'households' && (
        <div>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-2xl font-semibold">Households</h2>
            <button
              onClick={() => alert('Create household functionality coming soon')}
              className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
            >
              Add Household
            </button>
          </div>

          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {households.map((household) => (
              <div
                key={household.id}
                className={`bg-white shadow rounded-lg p-6 ${
                  !household.active ? 'opacity-50' : ''
                }`}
              >
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="text-lg font-semibold">{household.name}</h3>
                    <p className="text-sm text-gray-500 font-mono">{household.id}</p>
                  </div>
                  <button
                    onClick={() => toggleHouseholdActive(household.id, household.active)}
                    className={`px-3 py-1 rounded text-xs font-medium ${
                      household.active
                        ? 'bg-green-100 text-green-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {household.active ? 'Active' : 'Inactive'}
                  </button>
                </div>

                <div className="mb-4">
                  <p className="text-sm text-gray-600">
                    <strong>Floors:</strong> {household.floors.join(', ')}
                  </p>
                </div>

                <div className="mb-4">
                  <p className="text-sm font-medium text-gray-700 mb-2">
                    Assigned Meters ({household.householdMeters?.length || 0}):
                  </p>
                  <div className="space-y-1">
                    {household.householdMeters?.map((hm) => (
                      <div
                        key={hm.meter.id}
                        className="text-xs bg-gray-50 px-2 py-1 rounded"
                      >
                        <span className="font-mono">{hm.meter.id}</span>
                        <span className="text-gray-500 ml-2">({hm.meter.meterType})</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={() => alert(`Edit household: ${household.id}`)}
                    className="flex-1 bg-blue-50 text-blue-700 px-3 py-2 rounded text-sm hover:bg-blue-100"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => alert(`Manage meters for: ${household.id}`)}
                    className="flex-1 bg-gray-50 text-gray-700 px-3 py-2 rounded text-sm hover:bg-gray-100"
                  >
                    Meters
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Info Box */}
      <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="text-sm font-medium text-blue-900 mb-2">Database-Backed Configuration</h3>
        <p className="text-sm text-blue-700">
          All changes made here are stored in PostgreSQL and will be immediately available
          to both the Next.js dashboard and Dagster workflows. The system automatically
          falls back to YAML files if the database is unavailable.
        </p>
      </div>
    </div>
  );
}
