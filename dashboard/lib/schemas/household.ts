import { z } from 'zod'

/**
 * Household Form Validation Schema
 *
 * Defines validation rules for household configuration forms
 */

export const householdSchema = z.object({
  id: z.string().min(1, 'ID is required').regex(/^[a-z0-9_]+$/, 'ID must contain only lowercase letters, numbers, and underscores'),
  name: z.string().min(1, 'Name is required'),
  type: z.enum(['unit', 'shared']),
  color: z.string().regex(/^#[0-9A-Fa-f]{6}$/, 'Must be a valid hex color'),
  meters: z.object({
    electricity: z.array(z.string()).optional(),
    gas: z.array(z.string()).optional(),
    water: z.array(z.string()).optional(),
    heat: z.array(z.string()).optional(),
    solar: z.array(z.string()).optional(),
    virtual: z.array(z.string()).optional(),
  }).default({}),
  costAllocation: z.object({
    sharedElectricity: z.number().min(0).max(100).optional(),
    sharedGas: z.number().min(0).max(100).optional(),
    sharedWater: z.number().min(0).max(100).optional(),
    sharedHeat: z.number().min(0).max(100).optional(),
  }).optional(),
  description: z.string().optional(),
})

export type HouseholdFormData = z.infer<typeof householdSchema>
