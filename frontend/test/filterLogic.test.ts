import { describe, it } from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';
import Papa from 'papaparse';
import { parseDashboardRow } from '../src/services/dataLoader.ts';
import { applyFilters, calculateKPIs, isFilterActive } from '../src/utils/filterLogic.ts';
import { DEFAULT_FILTERS, type FilterCriteria } from '../src/types/filters.ts';
import type { DashboardEvent } from '../src/types/dashboard.ts';

describe('Multi-Facet Filter & Analytics Logic Tests', () => {
  // Load full 633 dataset once for the test suite
  const csvPath = path.resolve(process.cwd(), 'public/data/dashboard_events_633.csv');
  const csvContent = fs.readFileSync(csvPath, 'utf-8');
  const parsed = Papa.parse<Record<string, any>>(csvContent, { header: true, skipEmptyLines: true });
  const allEvents: DashboardEvent[] = parsed.data.map((r, i) => parseDashboardRow(r, i));

  assert.strictEqual(allEvents.length, 633, 'Precondition: Must load exactly 633 events');

  it('1. No filters applied returns all 633 events', () => {
    const result = applyFilters(allEvents, DEFAULT_FILTERS);
    assert.strictEqual(result.length, 633);
    assert.strictEqual(isFilterActive(DEFAULT_FILTERS), false);
  });

  it('2. Filters accurately by single ML predicted class', () => {
    const industrialFilters: FilterCriteria = {
      ...DEFAULT_FILTERS,
      classes: ['Industrial Thermal Activity'],
    };
    const industrialEvents = applyFilters(allEvents, industrialFilters);
    assert.strictEqual(industrialEvents.length, 261);
    assert.strictEqual(industrialEvents.every((e) => e.predicted_class === 'Industrial Thermal Activity'), true);

    const agriFilters: FilterCriteria = {
      ...DEFAULT_FILTERS,
      classes: ['Agricultural Burning'],
    };
    const agriEvents = applyFilters(allEvents, agriFilters);
    assert.strictEqual(agriEvents.length, 287);
    assert.strictEqual(agriEvents.every((e) => e.predicted_class === 'Agricultural Burning'), true);

    const naturalFilters: FilterCriteria = {
      ...DEFAULT_FILTERS,
      classes: ['Natural / Wildfire / Other'],
    };
    const naturalEvents = applyFilters(allEvents, naturalFilters);
    assert.strictEqual(naturalEvents.length, 85);
    assert.strictEqual(naturalEvents.every((e) => e.predicted_class === 'Natural / Wildfire / Other'), true);
  });

  it('3. Filters accurately by multiple categorical criteria (ML class + ML confidence + Sensor confidence)', () => {
    const multiFilters: FilterCriteria = {
      ...DEFAULT_FILTERS,
      classes: ['Industrial Thermal Activity'],
      mlConfidenceTiers: ['HIGH'],
      firmsConfidences: ['n'],
    };
    const filtered = applyFilters(allEvents, multiFilters);
    assert.strictEqual(filtered.length, 180);
    assert.strictEqual(
      filtered.every(
        (e) =>
          e.predicted_class === 'Industrial Thermal Activity' &&
          e.ml_confidence === 'HIGH' &&
          e.firms_confidence === 'n'
      ),
      true
    );
  });

  it('4. Filters accurately by Fire Radiative Power (FRP) numeric range', () => {
    const frpFilters: FilterCriteria = {
      ...DEFAULT_FILTERS,
      frpMin: 2.0,
      frpMax: 5.0,
    };
    const filtered = applyFilters(allEvents, frpFilters);
    assert.strictEqual(filtered.length > 0, true);
    assert.strictEqual(filtered.every((e) => e.frp >= 2.0 && e.frp <= 5.0), true);
  });

  it('5. Filters accurately by spatial persistence (multi-day hotspot flag)', () => {
    const persistenceFilters: FilterCriteria = {
      ...DEFAULT_FILTERS,
      onlyPersistentHotspots: true,
    };
    const filtered = applyFilters(allEvents, persistenceFilters);
    assert.strictEqual(filtered.length > 0, true);
    assert.strictEqual(filtered.every((e) => e.persistent_location_flag === 1), true);
  });

  it('6. Combines multiple complex filters (Persistence + WorldCover + OSM Tier)', () => {
    const combinedFilters: FilterCriteria = {
      ...DEFAULT_FILTERS,
      landcoverClasses: ['Built-up'],
      facilityTiers: ['HIGHER_RELEVANCE'],
      onlyPersistentHotspots: true,
    };
    const filtered = applyFilters(allEvents, combinedFilters);
    assert.strictEqual(filtered.length > 0, true);
    assert.strictEqual(
      filtered.every(
        (e) =>
          e.landcover_class === 'Built-up' &&
          e.nearest_facility_tier === 'HIGHER_RELEVANCE' &&
          e.persistent_location_flag === 1
      ),
      true
    );
  });

  it('7. Resetting filters restores the complete 633-event array', () => {
    const narrowedFilters: FilterCriteria = {
      ...DEFAULT_FILTERS,
      classes: ['Natural / Wildfire / Other'],
      onlyPersistentHotspots: true,
    };
    const narrowed = applyFilters(allEvents, narrowedFilters);
    assert.strictEqual(narrowed.length < 633, true);

    const reset = applyFilters(allEvents, DEFAULT_FILTERS);
    assert.strictEqual(reset.length, 633);
  });

  it('8. Zero-result filter returns an empty array cleanly without crashing', () => {
    const impossibleFilters: FilterCriteria = {
      ...DEFAULT_FILTERS,
      frpMin: 999.0, // Dataset max is ~16.84 MW
    };
    const filtered = applyFilters(allEvents, impossibleFilters);
    assert.strictEqual(filtered.length, 0);

    const kpis = calculateKPIs(filtered);
    assert.strictEqual(kpis.totalShown, 0);
    assert.strictEqual(kpis.industrialCount, 0);
    assert.strictEqual(kpis.agriculturalCount, 0);
    assert.strictEqual(kpis.naturalCount, 0);
    assert.strictEqual(kpis.highConfidenceCount, 0);
    assert.strictEqual(kpis.avgFrp, 0);
  });

  it('9. KPI calculations are strictly computed from filtered events', () => {
    const industrialFilters: FilterCriteria = {
      ...DEFAULT_FILTERS,
      classes: ['Industrial Thermal Activity'],
    };
    const industrialEvents = applyFilters(allEvents, industrialFilters);
    const kpis = calculateKPIs(industrialEvents);

    assert.strictEqual(kpis.totalShown, 261);
    assert.strictEqual(kpis.industrialCount, 261);
    assert.strictEqual(kpis.agriculturalCount, 0);
    assert.strictEqual(kpis.naturalCount, 0);

    // Verify avgFrp calculation
    const expectedSum = industrialEvents.reduce((acc, e) => acc + e.frp, 0);
    const expectedAvg = parseFloat((expectedSum / 261).toFixed(2));
    assert.strictEqual(kpis.avgFrp, expectedAvg);
  });

  it('10. Immutability check: Filtering never mutates the original dataset array or its objects', () => {
    const snapshotBefore = JSON.stringify(allEvents.slice(0, 5));
    const filters: FilterCriteria = {
      ...DEFAULT_FILTERS,
      classes: ['Agricultural Burning'],
      frpMin: 3.0,
      onlyPersistentHotspots: true,
    };

    applyFilters(allEvents, filters);

    assert.strictEqual(allEvents.length, 633, 'Original array length must remain 633');
    const snapshotAfter = JSON.stringify(allEvents.slice(0, 5));
    assert.strictEqual(snapshotBefore, snapshotAfter, 'Original array elements must remain unchanged');
  });
});
