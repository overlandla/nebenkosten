import { useQuery, useQueries } from '@tanstack/react-query'
import { MeterReading, ConsumptionData } from '@/types/meter'

export type DataType = 'raw' | 'consumption' | 'interpolated_daily' | 'interpolated_monthly'

interface MeterDataParams {
  meterId: string
  startDate: Date
  endDate: Date
  dataType: DataType
}

async function fetchMeterReadings(params: MeterDataParams): Promise<MeterReading[] | ConsumptionData[]> {
  const { meterId, startDate, endDate, dataType } = params

  const response = await fetch(
    `/api/readings?meterId=${meterId}&startDate=${startDate.toISOString()}&endDate=${endDate.toISOString()}&dataType=${dataType}`
  )

  if (!response.ok) {
    throw new Error(`Failed to fetch meter readings for ${meterId}`)
  }

  return response.json()
}

/**
 * Hook to fetch data for a single meter
 */
export function useMeterReadings(params: MeterDataParams) {
  return useQuery({
    queryKey: ['meterReadings', params.meterId, params.dataType, params.startDate.toISOString(), params.endDate.toISOString()],
    queryFn: () => fetchMeterReadings(params),
    enabled: Boolean(params.meterId),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

/**
 * Hook to fetch data for multiple meters in parallel
 */
export function useMultipleMeterReadings(
  meterIds: string[],
  startDate: Date,
  endDate: Date,
  dataType: DataType
) {
  return useQueries({
    queries: meterIds.map((meterId) => ({
      queryKey: ['meterReadings', meterId, dataType, startDate.toISOString(), endDate.toISOString()],
      queryFn: () => fetchMeterReadings({ meterId, startDate, endDate, dataType }),
      staleTime: 5 * 60 * 1000,
    })),
  })
}

/**
 * Hook to fetch the list of available meters
 */
export function useMeters() {
  return useQuery({
    queryKey: ['meters'],
    queryFn: async () => {
      const response = await fetch('/api/meters')
      if (!response.ok) {
        throw new Error('Failed to fetch meters')
      }
      return response.json()
    },
    staleTime: 30 * 60 * 1000, // Meters list is relatively static, cache for 30 minutes
  })
}

/**
 * Hook to fetch costs data
 */
export function useCostsData(
  startDate: Date,
  endDate: Date,
  utilityType?: string
) {
  return useQuery({
    queryKey: ['costs', startDate.toISOString(), endDate.toISOString(), utilityType],
    queryFn: async () => {
      const params = new URLSearchParams({
        startDate: startDate.toISOString(),
        endDate: endDate.toISOString(),
      })

      if (utilityType) {
        params.append('utilityType', utilityType)
      }

      const response = await fetch(`/api/costs?${params}`)
      if (!response.ok) {
        throw new Error('Failed to fetch costs data')
      }
      return response.json()
    },
    staleTime: 5 * 60 * 1000,
  })
}

/**
 * Hook to fetch household costs
 */
export function useHouseholdCosts(
  householdId: string,
  startDate: Date,
  endDate: Date
) {
  return useQuery({
    queryKey: ['householdCosts', householdId, startDate.toISOString(), endDate.toISOString()],
    queryFn: async () => {
      const response = await fetch(
        `/api/household-costs?householdId=${householdId}&startDate=${startDate.toISOString()}&endDate=${endDate.toISOString()}`
      )
      if (!response.ok) {
        throw new Error(`Failed to fetch costs for household ${householdId}`)
      }
      return response.json()
    },
    enabled: Boolean(householdId),
    staleTime: 5 * 60 * 1000,
  })
}

/**
 * Hook to fetch water temperature data
 */
export function useWaterTemperature(startDate: Date, endDate: Date) {
  return useQuery({
    queryKey: ['waterTemp', startDate.toISOString(), endDate.toISOString()],
    queryFn: async () => {
      const response = await fetch(
        `/api/water-temp?startDate=${startDate.toISOString()}&endDate=${endDate.toISOString()}`
      )
      if (!response.ok) {
        throw new Error('Failed to fetch water temperature data')
      }
      return response.json()
    },
    staleTime: 5 * 60 * 1000,
  })
}
