# Test Improvement Plan

**Last Updated:** 2025-11-16
**Current Overall Coverage:** 24.21% (184/760 lines)
**Goal:** Increase to 70%+ coverage

---

## 🔴 Failing Tests (Fix First)

### 1. `__tests__/app/api/meters/route.test.ts`
**Status:** 1 test failing
**Issue:** Test expects database connection errors to be handled differently

**Failing Test:**
```typescript
it('should handle database errors gracefully', async () => {
  // This test is currently failing - error handling needs review
})
```

**Fix Required:**
- Review error handling in `app/api/meters/route.ts:32-34` (uncovered lines)
- Ensure MockQueryApi error callback matches actual InfluxDB behavior
- Update test expectations to match actual error response format

---

## 📊 Coverage Gaps by Priority

### HIGH PRIORITY (0% Coverage - Core Features)

#### 1. **Household Costs API** - `app/api/household-costs/route.ts`
- **Current Coverage:** 0% (0/491 lines)
- **Why Important:** Core cost calculation engine for annual overview feature
- **Test File to Create:** `__tests__/app/api/household-costs/route.test.ts`

**Recommended Test Cases:**
```typescript
describe('/api/household-costs', () => {
  describe('GET', () => {
    it('should calculate costs for all households for a given year')
    it('should handle mixed Tibber + custom price calculations')
    it('should apply shared meter allocation ratios correctly')
    it('should return monthly breakdown and annual totals')
    it('should handle missing price configurations gracefully')
    it('should handle households with no meters')
    it('should handle year parameter validation')
    it('should handle InfluxDB query errors')
  })
})
```

#### 2. **Household Overview Page** - `app/household-overview/page.tsx`
- **Current Coverage:** 0% (0/358 lines)
- **Why Important:** Main user-facing feature for annual overview
- **Test File to Create:** `__tests__/app/household-overview/page.test.tsx`

**Recommended Test Cases:**
```typescript
describe('HouseholdOverviewPage', () => {
  it('should render year selector')
  it('should fetch and display household costs on mount')
  it('should update data when year changes')
  it('should render annual total cards with color-coded utilities')
  it('should render monthly cost breakdown chart')
  it('should render monthly consumption trends chart')
  it('should render detailed monthly table')
  it('should handle loading state')
  it('should handle empty household data')
  it('should handle API errors gracefully')
  it('should format currency correctly')
})
```

#### 3. **Settings Page** - `app/settings/page.tsx`
- **Current Coverage:** 0% (0/527 lines)
- **Why Important:** Configuration hub for households and prices
- **Test File to Create:** `__tests__/app/settings/page.test.tsx`

**Recommended Test Cases:**
```typescript
describe('SettingsPage', () => {
  describe('Tab Navigation', () => {
    it('should render both tabs (Households & Prices)')
    it('should switch between tabs')
    it('should default to households tab')
  })

  describe('Households Tab', () => {
    it('should load household config from localStorage and InfluxDB')
    it('should render household editor')
    it('should save changes to both localStorage and InfluxDB')
    it('should handle save errors gracefully')
    it('should validate household configuration before saving')
  })

  describe('Prices Tab', () => {
    it('should render PriceManagement component')
  })
})
```

### MEDIUM PRIORITY (Partial Coverage)

#### 4. **PriceManagement Component** - `components/PriceManagement.tsx`
- **Current Coverage:** 79.08% statements, 35% functions
- **Uncovered Lines:** 84-94, 98-99, 103-148, 152-171, 206-214, 261-266, 287, 333
- **Test File:** `__tests__/components/PriceManagement.test.tsx` (already exists)

**Additional Test Cases Needed:**
```typescript
describe('PriceManagement - Extended Coverage', () => {
  describe('Create Flow', () => {
    it('should submit create form with valid data')
    it('should close form after successful creation')
    it('should show error message on creation failure')
    it('should reset form on cancel')
  })

  describe('Edit Flow', () => {
    it('should open edit form with pre-filled data')
    it('should submit edit form with updated data')
    it('should close form after successful edit')
    it('should show error message on edit failure')
  })

  describe('Delete Flow', () => {
    it('should delete price configuration')
    it('should refresh list after successful delete')
    it('should show error message on delete failure')
  })

  describe('Form Validation', () => {
    it('should validate required fields')
    it('should validate price > 0')
    it('should validate date range (validTo >= validFrom)')
  })
})
```

#### 5. **API Routes** - Improve existing coverage

**`app/api/price-config/route.ts`** (8.4% → target 80%+)
- Uncovered: Lines 13-108, 115-184, 191-272, 279-357
- Need to test error paths, edge cases, date filtering logic

**`app/api/household-config/route.ts`** (16.51% → target 80%+)
- Uncovered: Lines 13-60, 67-109
- Need to test validation, update scenarios, error handling

### LOW PRIORITY (UI Components - 0% Coverage)

These components are currently untested but are lower priority than core business logic:

6. **Cost Breakdown Components**
   - `components/BreakdownChart.tsx` (0%)
   - `components/CostAllocationTable.tsx` (0%)
   - `components/CostBreakdownChart.tsx` (0%)

7. **Visualization Components**
   - `components/FloorComparisonChart.tsx` (0%)
   - `components/SeasonalPatternChart.tsx` (0%)
   - `components/WaterTemperatureChart.tsx` (0%)
   - `components/YearOverYearChart.tsx` (0%)

8. **Other Pages**
   - `app/costs/page.tsx` (0%)

---

## 🎯 Recommended Test Implementation Order

### Phase 1: Fix & Core Features (Target: 50% coverage)
1. ✅ Fix failing test in `meters/route.test.ts`
2. ✅ Create `__tests__/app/api/household-costs/route.test.ts` (HIGH IMPACT)
3. ✅ Expand `__tests__/components/PriceManagement.test.tsx` to 90%+ coverage
4. ✅ Improve `__tests__/app/api/price-config/route.test.ts` coverage to 80%+
5. ✅ Improve `__tests__/app/api/household-config/route.test.ts` coverage to 80%+

### Phase 2: User-Facing Features (Target: 60% coverage)
6. ✅ Create `__tests__/app/household-overview/page.test.tsx`
7. ✅ Create `__tests__/app/settings/page.test.tsx`

### Phase 3: Additional Components (Target: 70%+ coverage)
8. ✅ Test remaining chart components
9. ✅ Test costs page
10. ✅ Test utility type helpers and meter utilities

---

## 🛠️ Testing Utilities Already Available

### Mock Infrastructure
- ✅ `__tests__/mocks/influxdb.ts` - MockInfluxDB, MockQueryApi, MockWriteApi
- ✅ Point class mocking pattern (see existing tests)

### Test Patterns to Follow
```typescript
// API Route Testing
import { GET, POST } from '@/app/api/[route]/route';
import { NextRequest } from 'next/server';
import { MockInfluxDB } from '@/__tests__/mocks/influxdb';

// Component Testing
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock fetch globally
global.fetch = jest.fn();
```

---

## 📝 Coverage Targets by File Type

| File Type | Current Avg | Target | Priority |
|-----------|-------------|--------|----------|
| API Routes | 15% | 80% | HIGH |
| Type Helpers | 30% | 95% | HIGH |
| Pages | 0% | 70% | MEDIUM |
| Core Components | 41% | 85% | HIGH |
| Chart Components | 0% | 60% | LOW |

---

## 🚀 Quick Start for Next Session

```bash
# Run tests with coverage
npm test -- --coverage

# Run specific test file
npm test -- __tests__/app/api/household-costs/route.test.ts

# Run tests in watch mode
npm test -- --watch

# Run tests matching pattern
npm test -- --testNamePattern="household costs"
```

---

## 📌 Notes

- All new test files should follow the existing pattern in `__tests__/`
- Use the MockInfluxDB infrastructure for consistent mocking
- Focus on business logic coverage before UI component coverage
- Each API route should test: success paths, validation errors, database errors
- Each component should test: rendering, user interactions, loading states, error states

---

## Expected Coverage After Phase 1 (Estimates)

- **API Routes:** ~70% (up from 15%)
- **Components:** ~65% (up from 42%)
- **Type Helpers:** 100% (already there)
- **Overall:** ~55% (up from 24.21%)

## Expected Coverage After Phase 2 (Estimates)

- **Overall:** ~65% (up from 55%)

## Expected Coverage After Phase 3 (Estimates)

- **Overall:** ~75%+ (production-ready)
