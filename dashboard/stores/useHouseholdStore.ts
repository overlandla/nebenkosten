import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import {
  Household,
  HouseholdConfig,
  DEFAULT_HOUSEHOLD_CONFIG,
  validateCostAllocation,
  CostAllocation,
} from '@/types/household'

interface HouseholdStore {
  config: HouseholdConfig

  // Actions
  setConfig: (config: HouseholdConfig) => void
  updateConfig: (updates: Partial<HouseholdConfig>) => void
  addHousehold: (household: Household) => void
  updateHousehold: (id: string, updates: Partial<Household>) => void
  deleteHousehold: (id: string) => void
  resetConfig: () => void

  // Sync to API
  syncToAPI: () => Promise<void>

  // Validation helpers
  validateAllocation: (utilityType: keyof CostAllocation) => { valid: boolean; total: number; error?: string }
}

export const useHouseholdStore = create<HouseholdStore>()(
  persist(
    (set, get) => ({
      config: DEFAULT_HOUSEHOLD_CONFIG,

      setConfig: (config) => {
        set({
          config: {
            ...config,
            lastUpdated: new Date().toISOString(),
          }
        })
      },

      updateConfig: (updates) => {
        set((state) => ({
          config: {
            ...state.config,
            ...updates,
            lastUpdated: new Date().toISOString(),
          }
        }))
      },

      addHousehold: (household) => {
        set((state) => ({
          config: {
            ...state.config,
            households: [...state.config.households, household],
            lastUpdated: new Date().toISOString(),
          }
        }))
      },

      updateHousehold: (id, updates) => {
        set((state) => ({
          config: {
            ...state.config,
            households: state.config.households.map((h) =>
              h.id === id ? { ...h, ...updates } : h
            ),
            lastUpdated: new Date().toISOString(),
          }
        }))
      },

      deleteHousehold: (id) => {
        set((state) => ({
          config: {
            ...state.config,
            households: state.config.households.filter((h) => h.id !== id),
            lastUpdated: new Date().toISOString(),
          }
        }))
      },

      resetConfig: () => {
        set({ config: DEFAULT_HOUSEHOLD_CONFIG })
      },

      syncToAPI: async () => {
        const { config } = get()
        try {
          const response = await fetch('/api/household-config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config),
          })

          if (!response.ok) {
            throw new Error('Failed to sync household config to API')
          }
        } catch (error) {
          console.error('Error syncing household config:', error)
          throw error
        }
      },

      validateAllocation: (utilityType) => {
        const { config } = get()
        return validateCostAllocation(config.households, utilityType)
      },
    }),
    {
      name: 'household-config',
      version: 1,
    }
  )
)
