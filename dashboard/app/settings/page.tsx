'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useHouseholdStore } from '@/stores/useHouseholdStore'
import { HouseholdEditForm } from '@/components/forms/HouseholdEditForm'
import { HouseholdFormData } from '@/lib/schemas/household'
import { Household, validateCostAllocation, getHouseholdMeters } from '@/types/household'
import PriceManagement from '@/components/PriceManagement'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { useToast } from '@/hooks/use-toast'
import {
  Home,
  Settings as SettingsIcon,
  DollarSign,
  Plus,
  Trash2,
  Save,
  RotateCcw,
  Download,
  Upload,
  AlertCircle,
} from 'lucide-react'

export default function SettingsPage() {
  const { config, addHousehold, updateHousehold, deleteHousehold, resetConfig, syncToAPI } = useHouseholdStore()
  const { toast } = useToast()

  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [editingHousehold, setEditingHousehold] = useState<Household | undefined>()
  const [saving, setSaving] = useState(false)

  const handleAddHousehold = () => {
    setEditingHousehold(undefined)
    setEditDialogOpen(true)
  }

  const handleEditHousehold = (household: Household) => {
    setEditingHousehold(household)
    setEditDialogOpen(true)
  }

  const handleFormSubmit = (data: HouseholdFormData) => {
    if (editingHousehold) {
      updateHousehold(editingHousehold.id, data)
      toast({
        title: 'Household updated',
        description: `${data.name} has been updated successfully.`,
      })
    } else {
      addHousehold(data as Household)
      toast({
        title: 'Household added',
        description: `${data.name} has been added successfully.`,
      })
    }
    setEditDialogOpen(false)
    setEditingHousehold(undefined)
  }

  const handleDeleteHousehold = (id: string, name: string) => {
    if (confirm(`Are you sure you want to delete "${name}"? This cannot be undone.`)) {
      deleteHousehold(id)
      toast({
        title: 'Household deleted',
        description: `${name} has been removed.`,
        variant: 'destructive',
      })
    }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await syncToAPI()
      toast({
        title: 'Success',
        description: 'Configuration saved to localStorage and API.',
      })
    } catch (error) {
      toast({
        title: 'Partial success',
        description: 'Configuration saved to localStorage, but API sync failed.',
        variant: 'destructive',
      })
    } finally {
      setSaving(false)
    }
  }

  const handleReset = () => {
    if (confirm('Are you sure you want to reset to default configuration? This cannot be undone.')) {
      resetConfig()
      toast({
        title: 'Configuration reset',
        description: 'Settings have been reset to defaults.',
      })
    }
  }

  const handleExport = () => {
    const dataStr = JSON.stringify(config, null, 2)
    const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr)
    const exportFileDefaultName = `household-config-${new Date().toISOString().split('T')[0]}.json`

    const linkElement = document.createElement('a')
    linkElement.setAttribute('href', dataUri)
    linkElement.setAttribute('download', exportFileDefaultName)
    linkElement.click()

    toast({
      title: 'Configuration exported',
      description: `Saved as ${exportFileDefaultName}`,
    })
  }

  const handleImport = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const imported = JSON.parse(e.target?.result as string)
        if (imported && imported.version && Array.isArray(imported.households)) {
          useHouseholdStore.setState({ config: imported })
          toast({
            title: 'Configuration imported',
            description: 'Settings have been successfully imported.',
          })
        } else {
          throw new Error('Invalid configuration format')
        }
      } catch (error) {
        toast({
          title: 'Import failed',
          description: 'Invalid configuration file format.',
          variant: 'destructive',
        })
      }
    }
    reader.readAsText(file)
  }

  // Validation summary
  const allocationValidation = {
    electricity: validateCostAllocation(config.households, 'sharedElectricity'),
    gas: validateCostAllocation(config.households, 'sharedGas'),
    water: validateCostAllocation(config.households, 'sharedWater'),
    heat: validateCostAllocation(config.households, 'sharedHeat'),
  }

  const hasValidationErrors = Object.values(allocationValidation).some((v) => !v.valid)

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      {/* Header */}
      <header className="bg-gradient-to-r from-purple-600 to-purple-700 dark:from-purple-700 dark:to-purple-800 shadow-lg border-b border-purple-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link href="/" className="flex items-center gap-2 text-purple-100 hover:text-white transition-colors">
                <Home className="h-5 w-5" />
                Dashboard
              </Link>
              <Separator orientation="vertical" className="h-6 bg-white/20" />
              <div className="flex items-center gap-2">
                <SettingsIcon className="h-5 w-5 text-white" />
                <h1 className="text-2xl font-bold text-white">Settings</h1>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button variant="secondary" size="sm" onClick={handleExport} className="bg-white/10 hover:bg-white/20 text-white border-white/20">
                <Download className="h-4 w-4 mr-2" />
                Export
              </Button>
              <Button variant="secondary" size="sm" asChild className="bg-white/10 hover:bg-white/20 text-white border-white/20">
                <label className="cursor-pointer">
                  <Upload className="h-4 w-4 mr-2" />
                  Import
                  <input
                    type="file"
                    accept=".json"
                    onChange={handleImport}
                    className="hidden"
                  />
                </label>
              </Button>
              <Button variant="secondary" size="sm" onClick={handleReset} className="bg-white/10 hover:bg-white/20 text-white border-white/20">
                <RotateCcw className="h-4 w-4 mr-2" />
                Reset
              </Button>
              <Button size="sm" onClick={handleSave} disabled={saving} className="bg-white text-purple-700 hover:bg-white/90">
                <Save className="h-4 w-4 mr-2" />
                {saving ? 'Saving...' : 'Save'}
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Tabs defaultValue="households" className="w-full">
          <TabsList className="grid w-full max-w-md grid-cols-2">
            <TabsTrigger value="households" className="gap-2">
              <Home className="h-4 w-4" />
              Households
            </TabsTrigger>
            <TabsTrigger value="prices" className="gap-2">
              <DollarSign className="h-4 w-4" />
              Prices
            </TabsTrigger>
          </TabsList>

          {/* Households Tab */}
          <TabsContent value="households" className="mt-6 space-y-6">
            {/* Validation Summary */}
            {hasValidationErrors && (
              <Card className="border-red-300 dark:border-red-700 bg-gradient-to-br from-red-50 to-red-100 dark:from-red-900/30 dark:to-red-800/30 shadow-lg">
                <CardHeader>
                  <CardTitle className="text-red-700 dark:text-red-300 flex items-center gap-2">
                    <AlertCircle className="h-5 w-5" />
                    Cost Allocation Errors
                  </CardTitle>
                  <CardDescription className="text-red-600 dark:text-red-400">
                    The following shared utilities have invalid allocations (must sum to 100%):
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {Object.entries(allocationValidation).map(([key, result]) => (
                      <div
                        key={key}
                        className={`p-3 rounded-lg shadow-sm ${
                          result.valid
                            ? 'bg-green-100 dark:bg-green-900/30 border border-green-300 dark:border-green-700'
                            : 'bg-red-100 dark:bg-red-900/50 border border-red-300 dark:border-red-700'
                        }`}
                      >
                        <div className="text-sm font-medium capitalize">{key}</div>
                        <div className={`text-lg font-bold ${result.valid ? 'text-green-700 dark:text-green-400' : 'text-red-700 dark:text-red-400'}`}>
                          {result.total.toFixed(1)}%
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Add Household Button */}
            <div className="flex justify-between items-center">
              <div>
                <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100">Manage Households</h2>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  Configure households and their cost allocations
                </p>
              </div>
              <Button onClick={handleAddHousehold} className="bg-purple-600 hover:bg-purple-700 text-white">
                <Plus className="h-4 w-4 mr-2" />
                Add Household
              </Button>
            </div>

            {/* Households List */}
            <Card className="shadow-md border-slate-200 dark:border-slate-700">
              <CardContent className="pt-6">
                <Accordion type="single" collapsible className="w-full">
                  {config.households.map((household) => (
                    <AccordionItem key={household.id} value={household.id}>
                      <AccordionTrigger className="hover:no-underline">
                        <div className="flex items-center gap-3 flex-1">
                          <div
                            className="h-4 w-4 rounded-full border-2 border-white shadow"
                            style={{ backgroundColor: household.color }}
                          />
                          <div className="flex items-center gap-2 flex-1">
                            <span className="font-medium">{household.name}</span>
                            <Badge variant={household.type === 'shared' ? 'secondary' : 'default'}>
                              {household.type}
                            </Badge>
                          </div>
                          {household.description && (
                            <span className="text-sm text-neutral-500 hidden md:block">
                              {household.description}
                            </span>
                          )}
                        </div>
                      </AccordionTrigger>
                      <AccordionContent>
                        <div className="space-y-4 pt-4">
                          {/* Meters */}
                          <div>
                            <h4 className="text-sm font-semibold mb-2">Assigned Meters</h4>
                            <div className="flex flex-wrap gap-2">
                              {Object.entries(household.meters).map(([category, meters]) =>
                                meters?.map((meter: string) => (
                                  <Badge key={meter} variant="outline">
                                    {meter}
                                  </Badge>
                                ))
                              )}
                              {getHouseholdMeters(household).length === 0 && (
                                <p className="text-sm text-neutral-500">No meters assigned</p>
                              )}
                            </div>
                          </div>

                          {/* Cost Allocation */}
                          {household.costAllocation && household.type === 'unit' && (
                            <div>
                              <h4 className="text-sm font-semibold mb-2">Cost Allocation</h4>
                              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                                {Object.entries(household.costAllocation).map(([key, value]) =>
                                  value ? (
                                    <div key={key} className="text-sm">
                                      <span className="text-neutral-500 capitalize">
                                        {key.replace('shared', '')}:
                                      </span>{' '}
                                      <span className="font-medium">{value}%</span>
                                    </div>
                                  ) : null
                                )}
                              </div>
                            </div>
                          )}

                          {/* Actions */}
                          <div className="flex gap-2 pt-2">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleEditHousehold(household)}
                            >
                              Edit
                            </Button>
                            <Button
                              size="sm"
                              variant="destructive"
                              onClick={() => handleDeleteHousehold(household.id, household.name)}
                            >
                              <Trash2 className="h-4 w-4 mr-2" />
                              Delete
                            </Button>
                          </div>
                        </div>
                      </AccordionContent>
                    </AccordionItem>
                  ))}
                </Accordion>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Prices Tab */}
          <TabsContent value="prices" className="mt-6">
            <Card className="shadow-md border-slate-200 dark:border-slate-700">
              <CardHeader>
                <CardTitle className="text-slate-900 dark:text-slate-100">Utility Price Management</CardTitle>
                <CardDescription className="text-slate-600 dark:text-slate-400">
                  Configure pricing for electricity, gas, water, and heat
                </CardDescription>
              </CardHeader>
              <CardContent>
                <PriceManagement />
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>

      {/* Edit/Add Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editingHousehold ? 'Edit Household' : 'Add New Household'}
            </DialogTitle>
            <DialogDescription>
              {editingHousehold
                ? 'Update the household information below.'
                : 'Fill in the details for the new household.'}
            </DialogDescription>
          </DialogHeader>
          <HouseholdEditForm
            household={editingHousehold}
            onSubmit={handleFormSubmit}
            onCancel={() => {
              setEditDialogOpen(false)
              setEditingHousehold(undefined)
            }}
          />
        </DialogContent>
      </Dialog>
    </div>
  )
}
