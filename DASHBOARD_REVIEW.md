# Next.js Dashboard Review & Improvement Plan

**Date:** 2025-11-15
**Current Dashboard:** Next.js 16.0.3 with React 19.2.0
**Data Source:** Dagster Pipeline → InfluxDB (buckets: `lampfi`, `lampfi_processed`)

---

## Executive Summary

The current Next.js dashboard provides solid basic visualization for electricity, gas, water, and environmental data. However, **significant data available in Dagster is not being utilized**. The dashboard is missing:

- **5 heat meters** (critical for multi-unit building management)
- **Solar storage** visualization
- **Cost analysis** from Tibber API
- **Anomaly detection** alerts
- **Virtual meters** (fireplace gas, general electricity)
- **Individual floor water meters** (4 additional meters)
- **Household/unit grouping** functionality

---

## Current Dashboard Coverage

### ✅ Currently Implemented

| Utility Type | Meters Displayed | Chart Type | Data Source |
|--------------|------------------|------------|-------------|
| **Electricity** | 6 meters (haupt_strom, NT, HT, eg_strom, og1_strom, og2_strom) | Line charts, consumption bars, breakdown stacks | InfluxDB raw |
| **Gas** | 2 meters (gas_total, gastherme_gesamt) | Line charts, consumption bars | InfluxDB raw |
| **Water** | 2 meters (haupt_wasser_kalt, haupt_wasser_warm) | Line charts, consumption bars | InfluxDB raw |
| **Environmental** | 3 lake temperatures (Schliersee, Tegernsee, Isar) | Multi-line chart | InfluxDB raw |

**Total Meters Displayed:** 13 out of 39 available meters (33% coverage)

---

## Missing Data & Visualizations

### 🔴 Critical Gaps

#### 1. **Heat Meters (5 meters) - COMPLETELY MISSING**
Available in Dagster but not displayed:
- `eg_nord_heat` - Ground floor north heating (MWh)
- `eg_sud_heat` - Ground floor south heating (MWh)
- `og1_heat` - First floor heating (MWh)
- `og2_heat` - Second floor heating (MWh)
- `buro_heat` - Office heating (MWh)

**Impact:** Cannot track heating consumption per floor/unit - critical for cost allocation in multi-unit buildings.

**Recommended Charts:**
- Monthly heat consumption by floor (stacked bar chart)
- Heat consumption trends (line chart with floor breakdown)
- Year-over-year heating comparison
- Heat degree-day correlation chart

---

#### 2. **Solar Storage - MISSING**
Available meter: `solarspeicher` (kWh)

**Impact:** Cannot monitor solar energy production/storage efficiency.

**Recommended Charts:**
- Solar storage charge/discharge patterns (daily line chart)
- Monthly solar contribution to total electricity
- Solar efficiency metrics (charge/discharge ratio)

---

#### 3. **Cost Analysis from Tibber API - NOT UTILIZED**
Available data (hourly):
- `consumption` - Hourly electricity usage
- `cost` - Hourly cost in EUR
- `unit_price` - Price per kWh
- `unit_price_vat` - Price per kWh including VAT

**Impact:** Cannot track electricity costs or optimize consumption based on pricing.

**Recommended Charts:**
- Daily/monthly cost breakdown
- Hourly price trends (identify peak pricing periods)
- Cost per unit breakdown (electricity, gas, water, heat)
- Running cost tracker (cumulative monthly spend)
- Price vs. consumption correlation

---

#### 4. **Anomaly Detection - NOT VISUALIZED**
Available data from `anomaly_detection` asset:
- Detected anomalies (consumption > 2x rolling average)
- Rolling 30-day averages
- Threshold values

**Impact:** Cannot identify unusual consumption spikes or potential issues.

**Recommended Features:**
- Alert badges on charts where anomalies detected
- Anomaly timeline view
- Anomaly severity indicators
- Notification system for new anomalies

---

#### 5. **Virtual Meters - MISSING**
Available calculated meters:
- `eg_kalfire` - Fireplace gas consumption (gas_total - gastherme_gesamt)
- `strom_allgemein` - General electricity (strom_total - individual floors)

**Impact:** Cannot separate fireplace vs. heating gas or identify general electricity usage.

**Recommended Charts:**
- Fireplace usage patterns (winter/summer comparison)
- General electricity breakdown
- Virtual meter contribution to total consumption

---

#### 6. **Individual Floor Water Meters - PARTIALLY MISSING**
Available but not displayed:
- `og1_wasser_kalt` - Floor 1 cold water
- `og1_wasser_warm` - Floor 1 hot water
- `og2_wasser_kalt` - Floor 2 cold water
- `og2_wasser_warm` - Floor 2 hot water

Currently showing only: `haupt_wasser_kalt`, `haupt_wasser_warm`

**Impact:** Cannot track water usage per floor for cost allocation.

**Recommended Charts:**
- Water consumption by floor (stacked bars)
- Hot vs. cold water ratio per floor
- Water usage trends per floor

---

### 🟡 Enhancement Opportunities

#### 7. **Master Meters - NOT EXPLICITLY SHOWN**
Available composite meters:
- `strom_total` - Total electricity across meter replacements
- `gas_total` - Total gas across meter replacements

**Recommendation:** Use master meters as primary data source instead of raw physical meters to handle meter replacement continuity.

---

#### 8. **Processed Data from Dagster - UNDERUTILIZED**
The dashboard currently queries **raw InfluxDB data** (`lampfi` bucket).
Dagster writes **processed data** to `lampfi_processed` bucket:
- `meter_interpolated_daily` - Gap-filled daily readings
- `meter_interpolated_monthly` - Monthly aggregations
- `meter_consumption` - Calculated consumption values
- `meter_anomaly` - Anomaly detection results

**Impact:** Dashboard does interpolation client-side instead of using pre-processed data.

**Recommendation:** Switch to querying processed bucket for better performance and consistency.

---

#### 9. **Additional Visualization Types**

**Missing Chart Types:**
- **Heatmaps:** Hourly consumption patterns (day of week × hour of day)
- **Comparison Charts:** Year-over-year, month-over-month
- **Forecasting:** Predicted consumption based on rolling averages
- **Efficiency Metrics:** Cost per m² for heat, cost per person
- **Correlation Charts:** Temperature vs. heating consumption, solar production vs. electricity usage
- **Distribution Charts:** Consumption distribution histograms
- **Gauges:** Real-time current consumption vs. average

---

## Household Grouping Feature - NEW REQUIREMENT

### Problem Statement
The building has multiple units/floors that need separate utility tracking:
- **EG (Ground Floor):** North + South + potentially Kalfire (fireplace)
- **OG1 (First Floor):** Separate electricity, water, heat
- **OG2 (Second Floor):** Separate electricity, water, heat
- **Büro (Office):** Separate heat
- **Shared/Common:** Main meters (total electricity, gas, water)

Currently, all meters are displayed in a flat list without organizational structure.

### Proposed Solution

#### A. Household Configuration Structure

```typescript
interface Household {
  id: string;                    // e.g., "eg_nord", "og1", "shared"
  name: string;                  // e.g., "Ground Floor North", "Shared Utilities"
  type: "unit" | "shared";       // Distinguish between individual units and shared
  color: string;                 // For consistent chart coloring
  meters: {
    electricity?: string[];       // Meter IDs
    gas?: string[];
    water?: string[];
    heat?: string[];
    solar?: string[];
  };
  costAllocation?: {
    sharedElectricity?: number;  // % share of shared electricity costs
    sharedGas?: number;          // % share of shared gas costs
    sharedWater?: number;        // % share of shared water costs
  };
}
```

#### B. Example Configuration

```json
{
  "households": [
    {
      "id": "eg_nord",
      "name": "Ground Floor North",
      "type": "unit",
      "color": "#3b82f6",
      "meters": {
        "electricity": ["eg_strom"],
        "heat": ["eg_nord_heat"]
      },
      "costAllocation": {
        "sharedGas": 25
      }
    },
    {
      "id": "og1",
      "name": "First Floor",
      "type": "unit",
      "color": "#10b981",
      "meters": {
        "electricity": ["og1_strom"],
        "water": ["og1_wasser_kalt", "og1_wasser_warm"],
        "heat": ["og1_heat"]
      },
      "costAllocation": {
        "sharedElectricity": 30,
        "sharedGas": 25
      }
    },
    {
      "id": "shared",
      "name": "Shared Utilities",
      "type": "shared",
      "color": "#6b7280",
      "meters": {
        "electricity": ["haupt_strom", "strom_total"],
        "gas": ["gas_total"],
        "water": ["haupt_wasser"]
      }
    }
  ]
}
```

#### C. Features to Implement

1. **Settings Page (`/settings`)**
   - Create/edit/delete households
   - Assign meters to households
   - Set cost allocation percentages
   - Visual meter picker (grouped by type)
   - Validation (ensure meters aren't assigned to multiple units)
   - Import/export configuration (JSON)

2. **Dashboard Reorganization**
   - Top-level navigation: "All Units" | "EG Nord" | "EG Süd" | "OG1" | "OG2" | "Büro" | "Shared"
   - Filter all charts by selected household
   - Household summary cards (total consumption, cost, trends)
   - Comparison view (side-by-side household consumption)

3. **Cost Allocation Calculator**
   - Calculate shared utility costs
   - Distribute costs per allocation percentages
   - Generate monthly cost reports per household
   - Export cost allocation for billing

4. **Household-Specific Dashboards**
   - Custom dashboard per household showing only relevant meters
   - Household consumption trends
   - Cost breakdown per household
   - Comparison to building average

---

## Recommended Implementation Priority

### Phase 1: Critical Missing Data (Week 1-2)
1. ✅ Add heat meter visualizations (5 meters)
2. ✅ Add solar storage chart
3. ✅ Add individual floor water meters
4. ✅ Add virtual meters (kalfire, strom_allgemein)
5. ✅ Switch to using processed data from Dagster

### Phase 2: Household Grouping (Week 2-3)
6. ✅ Design household configuration data structure
7. ✅ Create settings page for household management
8. ✅ Implement household filtering in dashboard
9. ✅ Add household summary cards
10. ✅ Persist configuration (localStorage + optional backend)

### Phase 3: Cost Analysis (Week 3-4)
11. ✅ Integrate Tibber cost data
12. ✅ Add cost breakdown charts
13. ✅ Implement cost allocation calculator
14. ✅ Generate monthly cost reports

### Phase 4: Advanced Analytics (Week 4-5)
15. ✅ Add anomaly detection visualization
16. ✅ Implement comparison charts (YoY, MoM)
17. ✅ Add heatmap visualizations
18. ✅ Create efficiency metrics

---

## Technical Recommendations

### 1. Data Fetching Strategy
**Current:** Queries raw InfluxDB data with client-side interpolation
**Recommended:** Query Dagster processed data (`lampfi_processed` bucket)

Benefits:
- Consistent with Dagster analytics
- Pre-computed consumption values
- Gap-filled interpolated series
- Anomaly detection included
- Better performance (less client-side processing)

### 2. State Management
**Current:** Local state in components
**Recommended:** Add Zustand or Jotai for global state

Why:
- Household configuration needs to be accessible across components
- Time range selection shared across charts
- Selected household filtering
- Persistent user preferences

### 3. Database for Configuration
**Current:** No persistent storage
**Recommended:** Add SQLite with Prisma or use Supabase

Store:
- Household configurations
- User preferences
- Custom alerts/thresholds
- Historical cost allocation

### 4. API Route Consolidation
**Current:** 3 separate API routes
**Recommended:** Single `/api/meters` endpoint with query parameters

Example:
```
GET /api/meters?type=electricity&household=og1&range=30d&processed=true
```

Benefits:
- Easier to maintain
- Consistent error handling
- Better caching strategy
- Simpler client code

---

## UI/UX Improvements

### 1. Dashboard Layout
**Current:** Single scrolling page with all charts
**Recommended:** Multi-page dashboard with navigation

Suggested pages:
- **Overview:** Summary cards, key metrics, anomalies
- **Electricity:** All electricity charts, cost analysis
- **Gas & Heating:** Gas + heat meters, virtual meters
- **Water:** Water consumption by floor, hot vs. cold
- **Environmental:** Lake temperatures, solar production
- **Costs:** Cost breakdown, allocation, billing
- **Settings:** Household configuration, preferences

### 2. Navigation
Add sidebar or top navigation:
```
├── Overview
├── By Household
│   ├── Ground Floor North
│   ├── Ground Floor South
│   ├── First Floor
│   ├── Second Floor
│   ├── Office
│   └── Shared Utilities
├── By Utility Type
│   ├── Electricity & Solar
│   ├── Gas & Heating
│   ├── Water
│   └── Environmental
├── Costs & Billing
└── Settings
```

### 3. Summary Cards
Add metric cards at the top of each page:
```
┌─────────────────┬─────────────────┬─────────────────┬─────────────────┐
│ This Month      │ vs. Last Month  │ Anomalies       │ Estimated Cost  │
│ 450 kWh         │ ↑ 12%           │ 2 detected      │ €89.50          │
└─────────────────┴─────────────────┴─────────────────┴─────────────────┘
```

### 4. Interactive Features
- **Drill-down:** Click chart to see hourly/daily detail
- **Tooltips:** Rich tooltips with multiple metrics
- **Export:** Download data as CSV/Excel
- **Alerts:** Visual indicators for anomalies
- **Annotations:** Mark events (e.g., "meter replaced", "vacation")

---

## Data Completeness Matrix

| Meter Type | Available in Dagster | Displayed in Dashboard | Coverage |
|------------|---------------------|------------------------|----------|
| Electricity | 6 physical + 2 virtual + 1 master | 6 physical | 67% |
| Gas | 4 physical + 1 master + 1 virtual | 2 physical | 33% |
| Water | 6 physical + 1 master | 2 physical | 33% |
| Heat | 5 physical | 0 | **0%** ❌ |
| Solar | 1 physical | 0 | **0%** ❌ |
| Environmental | 3 temperature sensors | 3 sensors | 100% ✅ |
| Cost Data | Tibber hourly costs | 0 | **0%** ❌ |
| Anomalies | All meters | 0 | **0%** ❌ |

**Overall Coverage:** 13 / 39 meters = **33%**

---

## Proposed File Structure Changes

```
dashboard/
├── app/
│   ├── page.tsx                    # Overview dashboard
│   ├── households/
│   │   └── [id]/page.tsx          # Household-specific dashboard
│   ├── utilities/
│   │   ├── electricity/page.tsx
│   │   ├── gas-heat/page.tsx
│   │   ├── water/page.tsx
│   │   └── environmental/page.tsx
│   ├── costs/page.tsx             # Cost analysis & allocation
│   ├── settings/page.tsx          # Household configuration
│   └── api/
│       ├── meters/route.ts        # Consolidated meter data endpoint
│       ├── costs/route.ts         # Tibber cost data
│       ├── anomalies/route.ts     # Anomaly detection results
│       └── households/route.ts    # CRUD for household config
├── components/
│   ├── charts/
│   │   ├── HeatConsumptionChart.tsx
│   │   ├── SolarStorageChart.tsx
│   │   ├── CostBreakdownChart.tsx
│   │   ├── AnomalyChart.tsx
│   │   ├── HeatmapChart.tsx
│   │   └── ComparisonChart.tsx
│   ├── households/
│   │   ├── HouseholdSelector.tsx
│   │   ├── HouseholdSummaryCard.tsx
│   │   └── MeterAssignment.tsx
│   ├── navigation/
│   │   ├── Sidebar.tsx
│   │   └── TopNav.tsx
│   └── ui/
│       ├── MetricCard.tsx
│       ├── AnomalyBadge.tsx
│       └── ExportButton.tsx
├── lib/
│   ├── stores/
│   │   ├── householdStore.ts      # Zustand store for household config
│   │   └── preferencesStore.ts
│   └── utils/
│       ├── costCalculator.ts      # Cost allocation logic
│       └── householdHelpers.ts
└── types/
    └── households.ts               # TypeScript interfaces
```

---

## Summary of Key Improvements

### What's Working Well ✅
- Clean React component architecture
- Recharts integration
- Time range selector
- Responsive design
- InfluxDB integration

### Critical Additions Needed 🔴
1. **Heat meters** (5 meters) - 0% coverage
2. **Solar storage** - 0% coverage
3. **Household grouping** - Core feature missing
4. **Cost analysis** - Tibber data unused
5. **Anomaly visualization** - Data available but not shown
6. **Virtual meters** - Calculated but not displayed

### Impact
These additions will:
- Increase data coverage from 33% → 95%
- Enable proper cost allocation for multi-unit building
- Provide actionable insights through anomaly detection
- Support billing and accounting workflows
- Improve user experience with organized navigation

---

## Next Steps

1. **Review this document** - Confirm priorities and scope
2. **Choose implementation approach:**
   - Option A: Incremental (add features to existing page)
   - Option B: Major refactor (multi-page app with navigation)
3. **Start with Phase 1** - Add missing critical data visualizations
4. **Design household settings UI** - Mockup configuration interface
5. **Implement household grouping** - Core feature for cost allocation
6. **Deploy and iterate** - Progressive enhancement

---

**Estimated Total Effort:** 4-5 weeks
**Recommended Approach:** Phased implementation with weekly deployments
**Expected Outcome:** Comprehensive multi-household utility management dashboard
