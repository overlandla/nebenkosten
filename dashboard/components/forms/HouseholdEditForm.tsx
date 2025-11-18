'use client'

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { HexColorPicker } from 'react-colorful'
import { householdSchema, type HouseholdFormData } from '@/lib/schemas/household'
import { Household } from '@/types/household'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { useState } from 'react'

interface HouseholdEditFormProps {
  household?: Household
  onSubmit: (data: HouseholdFormData) => void
  onCancel: () => void
}

export function HouseholdEditForm({ household, onSubmit, onCancel }: HouseholdEditFormProps) {
  const [colorPickerOpen, setColorPickerOpen] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
  } = useForm<HouseholdFormData>({
    resolver: zodResolver(householdSchema),
    defaultValues: household || {
      id: '',
      name: '',
      type: 'unit',
      color: '#3b82f6',
      meters: {},
      costAllocation: {},
      description: '',
    },
  })

  const color = watch('color')
  const householdType = watch('type')

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      {/* Basic Information */}
      <div className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="id">Household ID</Label>
          <Input
            id="id"
            {...register('id')}
            placeholder="e.g., og1, eg_nord"
            disabled={!!household} // Disable editing ID for existing households
          />
          {errors.id && (
            <p className="text-sm text-red-500">{errors.id.message}</p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="name">Household Name</Label>
          <Input
            id="name"
            {...register('name')}
            placeholder="e.g., First Floor, Ground Floor North"
          />
          {errors.name && (
            <p className="text-sm text-red-500">{errors.name.message}</p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="type">Type</Label>
          <Select
            value={householdType}
            onValueChange={(value) => setValue('type', value as 'unit' | 'shared')}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="unit">Unit</SelectItem>
              <SelectItem value="shared">Shared</SelectItem>
            </SelectContent>
          </Select>
          {errors.type && (
            <p className="text-sm text-red-500">{errors.type.message}</p>
          )}
        </div>

        <div className="space-y-2">
          <Label>Color</Label>
          <div className="flex items-center gap-3">
            <Popover open={colorPickerOpen} onOpenChange={setColorPickerOpen}>
              <PopoverTrigger asChild>
                <button
                  type="button"
                  className="h-10 w-20 rounded-md border-2 border-neutral-200 transition-colors hover:border-neutral-300"
                  style={{ backgroundColor: color }}
                />
              </PopoverTrigger>
              <PopoverContent className="w-auto p-3">
                <HexColorPicker
                  color={color}
                  onChange={(newColor) => setValue('color', newColor)}
                />
              </PopoverContent>
            </Popover>
            <Input
              {...register('color')}
              placeholder="#3b82f6"
              className="flex-1"
            />
          </div>
          {errors.color && (
            <p className="text-sm text-red-500">{errors.color.message}</p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="description">Description (Optional)</Label>
          <Input
            id="description"
            {...register('description')}
            placeholder="e.g., Ground floor unit with fireplace"
          />
        </div>
      </div>

      <Separator />

      {/* Cost Allocation */}
      {householdType === 'unit' && (
        <div className="space-y-4">
          <div>
            <h3 className="text-lg font-semibold">Cost Allocation</h3>
            <p className="text-sm text-neutral-500">
              Percentage share of shared utilities (0-100%)
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="sharedElectricity">Shared Electricity %</Label>
              <Input
                id="sharedElectricity"
                type="number"
                min="0"
                max="100"
                step="0.1"
                {...register('costAllocation.sharedElectricity', {
                  valueAsNumber: true,
                  setValueAs: (v) => (v === '' ? undefined : parseFloat(v)),
                })}
                placeholder="0"
              />
              {errors.costAllocation?.sharedElectricity && (
                <p className="text-sm text-red-500">
                  {errors.costAllocation.sharedElectricity.message}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="sharedGas">Shared Gas %</Label>
              <Input
                id="sharedGas"
                type="number"
                min="0"
                max="100"
                step="0.1"
                {...register('costAllocation.sharedGas', {
                  valueAsNumber: true,
                  setValueAs: (v) => (v === '' ? undefined : parseFloat(v)),
                })}
                placeholder="0"
              />
              {errors.costAllocation?.sharedGas && (
                <p className="text-sm text-red-500">
                  {errors.costAllocation.sharedGas.message}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="sharedWater">Shared Water %</Label>
              <Input
                id="sharedWater"
                type="number"
                min="0"
                max="100"
                step="0.1"
                {...register('costAllocation.sharedWater', {
                  valueAsNumber: true,
                  setValueAs: (v) => (v === '' ? undefined : parseFloat(v)),
                })}
                placeholder="0"
              />
              {errors.costAllocation?.sharedWater && (
                <p className="text-sm text-red-500">
                  {errors.costAllocation.sharedWater.message}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="sharedHeat">Shared Heat %</Label>
              <Input
                id="sharedHeat"
                type="number"
                min="0"
                max="100"
                step="0.1"
                {...register('costAllocation.sharedHeat', {
                  valueAsNumber: true,
                  setValueAs: (v) => (v === '' ? undefined : parseFloat(v)),
                })}
                placeholder="0"
              />
              {errors.costAllocation?.sharedHeat && (
                <p className="text-sm text-red-500">
                  {errors.costAllocation.sharedHeat.message}
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Form Actions */}
      <div className="flex gap-2 justify-end pt-4">
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit">
          {household ? 'Update Household' : 'Add Household'}
        </Button>
      </div>
    </form>
  )
}
