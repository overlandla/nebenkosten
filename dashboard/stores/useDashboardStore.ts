import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type ViewMode = 'raw' | 'consumption'
export type MeterCategory = 'electricity' | 'gas' | 'water' | 'heat' | 'solar' | 'virtual'

export interface TimeRange {
  startDate: Date
  endDate: Date
  preset?: string
}

export interface DashboardFilters {
  viewMode: ViewMode
  selectedCategories: MeterCategory[]
  selectedHouseholds: string[]
  selectedMeters: string[]
  timeRange: TimeRange
  searchQuery: string
}

interface DashboardStore extends DashboardFilters {
  // Actions
  setViewMode: (mode: ViewMode) => void
  setSelectedCategories: (categories: MeterCategory[]) => void
  toggleCategory: (category: MeterCategory) => void
  setSelectedHouseholds: (households: string[]) => void
  toggleHousehold: (household: string) => void
  setSelectedMeters: (meters: string[]) => void
  toggleMeter: (meter: string) => void
  setTimeRange: (range: TimeRange) => void
  setSearchQuery: (query: string) => void
  resetFilters: () => void
}

const defaultTimeRange: TimeRange = {
  startDate: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), // 30 days ago
  endDate: new Date(),
  preset: 'last30days',
}

const initialState: DashboardFilters = {
  viewMode: 'consumption',
  selectedCategories: [],
  selectedHouseholds: [],
  selectedMeters: [],
  timeRange: defaultTimeRange,
  searchQuery: '',
}

export const useDashboardStore = create<DashboardStore>()(
  persist(
    (set, get) => ({
      ...initialState,

      setViewMode: (mode) => set({ viewMode: mode }),

      setSelectedCategories: (categories) => set({ selectedCategories: categories }),

      toggleCategory: (category) => {
        const current = get().selectedCategories
        const updated = current.includes(category)
          ? current.filter((c) => c !== category)
          : [...current, category]
        set({ selectedCategories: updated })
      },

      setSelectedHouseholds: (households) => set({ selectedHouseholds: households }),

      toggleHousehold: (household) => {
        const current = get().selectedHouseholds
        const updated = current.includes(household)
          ? current.filter((h) => h !== household)
          : [...current, household]
        set({ selectedHouseholds: updated })
      },

      setSelectedMeters: (meters) => set({ selectedMeters: meters }),

      toggleMeter: (meter) => {
        const current = get().selectedMeters
        const updated = current.includes(meter)
          ? current.filter((m) => m !== meter)
          : [...current, meter]
        set({ selectedMeters: updated })
      },

      setTimeRange: (range) => set({ timeRange: range }),

      setSearchQuery: (query) => set({ searchQuery: query }),

      resetFilters: () => set(initialState),
    }),
    {
      name: 'dashboard-filters',
      version: 1,
      // Custom serialization for Date objects
      partialize: (state) => ({
        viewMode: state.viewMode,
        selectedCategories: state.selectedCategories,
        selectedHouseholds: state.selectedHouseholds,
        selectedMeters: state.selectedMeters,
        timeRange: {
          startDate: state.timeRange.startDate.toISOString(),
          endDate: state.timeRange.endDate.toISOString(),
          preset: state.timeRange.preset,
        },
        searchQuery: state.searchQuery,
      }),
      merge: (persistedState, currentState) => {
        const persisted = persistedState as any
        return {
          ...currentState,
          ...persisted,
          timeRange: {
            startDate: new Date(persisted.timeRange?.startDate || defaultTimeRange.startDate),
            endDate: new Date(persisted.timeRange?.endDate || defaultTimeRange.endDate),
            preset: persisted.timeRange?.preset,
          },
        }
      },
    }
  )
)
