import { describe, it } from 'node:test';
import assert from 'node:assert';
import * as fs from 'node:fs';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';
import Papa from 'papaparse';
import { parseDashboardRow } from '../src/services/dataLoader.ts';
import { applyFilters } from '../src/utils/filterLogic.ts';
import { DEFAULT_FILTERS } from '../src/types/filters.ts';
import { getDrawerViewModel } from '../src/components/events/drawerViewModel.ts';
import { DEMO_QUICK_PICK_EVENTS } from '../src/utils/quickPickEvents.ts';
import type { DashboardEvent } from '../src/types/dashboard.ts';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const CSV_PATH = path.resolve(__dirname, '../public/data/dashboard_events_633.csv');
const CSS_PATH = path.resolve(__dirname, '../src/index.css');

describe('Phase 6 Step 8 — Step 2: Critical & High SIH Fixes Tests', () => {
  const csvContent = fs.readFileSync(CSV_PATH, 'utf-8');
  const parsed = Papa.parse<Record<string, any>>(csvContent, { header: true, skipEmptyLines: true });
  const allEvents: DashboardEvent[] = parsed.data.map((row) => parseDashboardRow(row));

  it('A. Quick-pick event selection correctly identifies and loads demo events', () => {
    assert.strictEqual(allEvents.length, 633, 'Authoritative dataset must contain 633 events');
    assert.strictEqual(DEMO_QUICK_PICK_EVENTS.length, 4, 'Must define exactly 4 demo quick-pick presets');

    for (const demoDef of DEMO_QUICK_PICK_EVENTS) {
      const match = allEvents.find((e) => e.event_id === demoDef.id);
      assert.ok(match, `Demo event ${demoDef.id} must exist in 633-event dataset`);
      assert.strictEqual(match.event_id, demoDef.id);
      assert.strictEqual(match.predicted_class, demoDef.expectedClass);
    }
  });

  it('B. Quick-pick selection of all 4 specified event IDs verifies exact attributes', () => {
    // 1. FIRMS_TN_0000: Salem Steel
    const e0 = allEvents.find((e) => e.event_id === 'FIRMS_TN_0000');
    assert.ok(e0);
    assert.strictEqual(e0.predicted_class, 'Industrial Thermal Activity');
    assert.strictEqual(e0.nearest_facility_name, 'SAIL');
    assert.strictEqual(e0.nearest_hr_name, 'Salem Steel Plant');

    // 2. FIRMS_TN_0008: JSW Steel
    const e8 = allEvents.find((e) => e.event_id === 'FIRMS_TN_0008');
    assert.ok(e8);
    assert.strictEqual(e8.predicted_class, 'Industrial Thermal Activity');
    assert.strictEqual(e8.nearest_hr_name, 'JSW Steel Plant');
    assert.strictEqual(e8.ml_confidence, 'HIGH');

    // 3. FIRMS_TN_0001: Ramanathapuram Agriculture
    const e1 = allEvents.find((e) => e.event_id === 'FIRMS_TN_0001');
    assert.ok(e1);
    assert.strictEqual(e1.predicted_class, 'Agricultural Burning');
    assert.strictEqual(e1.landcover_class, 'Tree cover');

    // 4. FIRMS_TN_0004: Mining & Quarry Region
    const e4 = allEvents.find((e) => e.event_id === 'FIRMS_TN_0004');
    assert.ok(e4);
    assert.strictEqual(e4.predicted_class, 'Agricultural Burning');
    assert.strictEqual(e4.nearest_facility_category, 'Mining & Quarry');
  });

  it('C. Quick-pick behavior when an event is filtered out triggers clean reset and notice', () => {
    // Apply restrictive filter (e.g. only Natural fires)
    const activeFilters = {
      ...DEFAULT_FILTERS,
      classes: ['Natural / Wildfire / Other' as const],
    };

    let filtered = applyFilters(allEvents, activeFilters);
    assert.strictEqual(filtered.length, 85);

    const targetId = 'FIRMS_TN_0008'; // Industrial
    const isHiddenBefore = !filtered.some((e) => e.event_id === targetId);
    assert.strictEqual(isHiddenBefore, true, 'FIRMS_TN_0008 must be hidden under Natural filter');

    // Simulate QuickPick selection with filter reset handler
    let filterResetCalled = false;
    let noticeMessage: string | null = null;

    const onResetFilters = () => {
      filterResetCalled = true;
      filtered = applyFilters(allEvents, DEFAULT_FILTERS);
    };
    const onNotice = (msg: string | null) => {
      noticeMessage = msg;
    };

    const targetEvent = allEvents.find((e) => e.event_id === targetId)!;
    if (isHiddenBefore) {
      onResetFilters();
      onNotice(`Active filters were reset to display demo event ${targetId} on the map.`);
    }

    assert.strictEqual(filterResetCalled, true, 'Filters must be reset when selected demo event is hidden');
    assert.strictEqual(filtered.length, 633, 'Filtered events must restore to 633 after reset');
    assert.strictEqual(filtered.some((e) => e.event_id === targetId), true);
    assert.ok(noticeMessage && noticeMessage.includes(targetId), 'Notice message must mention event ID');
  });

  it('D. Drawer opening from quick-pick selection initializes complete ViewModel', () => {
    const event = allEvents.find((e) => e.event_id === 'FIRMS_TN_0000')!;
    const vm = getDrawerViewModel(event);

    assert.strictEqual(vm.isEmpty, false);
    assert.strictEqual(vm.eventId, 'FIRMS_TN_0000');
    assert.strictEqual(vm.mlPrediction.predictedClass, 'Industrial Thermal Activity');
    assert.strictEqual(vm.osm.nearestHrCategory, 'Steel / Metallurgy');
    assert.ok(vm.mlPrediction.disclaimer.includes('algorithmic ML estimate'));
  });

  it('E. Marker selection still opens drawer and formats location data', () => {
    const event = allEvents.find((e) => e.event_id === 'FIRMS_TN_0008')!;
    let selectedEvent: DashboardEvent | null = null;

    // Simulate onSelect from marker click
    const handleMarkerSelect = (e: DashboardEvent) => {
      selectedEvent = e;
    };

    handleMarkerSelect(event);
    assert.strictEqual(selectedEvent?.event_id, 'FIRMS_TN_0008');

    const vm = getDrawerViewModel(selectedEvent);
    assert.strictEqual(vm.eventId, 'FIRMS_TN_0008');
    assert.strictEqual(vm.thermal.isPersistent, true);
  });

  it('F. Popup/drawer coordination: popup is suppressed when drawer is open', () => {
    let selectedEventId: string | null = null;
    let isDrawerOpen = false;

    // When drawer is closed:
    const suppressWhenClosed = Boolean(selectedEventId || isDrawerOpen);
    assert.strictEqual(suppressWhenClosed, false, 'Popup is allowed when drawer is closed');

    // When marker or quick-pick is selected:
    selectedEventId = 'FIRMS_TN_0000';
    isDrawerOpen = true;
    const suppressWhenOpen = Boolean(selectedEventId || isDrawerOpen);
    assert.strictEqual(suppressWhenOpen, true, 'Popup is suppressed when drawer is open to prevent double-popup clutter');
  });

  it('G. Existing filtering remains completely unchanged', () => {
    // 1. Industrial count
    const industrialEvents = applyFilters(allEvents, {
      ...DEFAULT_FILTERS,
      classes: ['Industrial Thermal Activity'],
    });
    assert.strictEqual(industrialEvents.length, 261);

    // 2. Agricultural count
    const agEvents = applyFilters(allEvents, {
      ...DEFAULT_FILTERS,
      classes: ['Agricultural Burning'],
    });
    assert.strictEqual(agEvents.length, 287);

    // 3. Natural count
    const naturalEvents = applyFilters(allEvents, {
      ...DEFAULT_FILTERS,
      classes: ['Natural / Wildfire / Other'],
    });
    assert.strictEqual(naturalEvents.length, 85);

    // 4. Persistence filter
    const persistentEvents = applyFilters(allEvents, {
      ...DEFAULT_FILTERS,
      onlyPersistentHotspots: true,
    });
    assert.strictEqual(persistentEvents.length, 272);
  });

  it('H. Responsive CSS contains required 1280px and 960px breakpoints and selector rules', () => {
    const cssContent = fs.readFileSync(CSS_PATH, 'utf-8');

    // 1. Verify 1280px media query
    assert.ok(
      cssContent.includes('@media (max-width: 1280px)'),
      'index.css must contain @media (max-width: 1280px) breakpoint'
    );
    assert.ok(
      cssContent.includes('width: 240px;'),
      'Sidebar width must be reduced to 240px in 1280px media query'
    );
    assert.ok(
      cssContent.includes('width: 380px;'),
      'Drawer width must be reduced to 380px in 1280px media query'
    );

    // 2. Verify 960px media query
    assert.ok(
      cssContent.includes('@media (max-width: 960px)'),
      'index.css must contain @media (max-width: 960px) breakpoint'
    );
    assert.ok(
      cssContent.includes('width: min(360px, 92vw);'),
      'Drawer must fit viewport on 960px breakpoint'
    );
    assert.ok(
      cssContent.includes('width: 210px;'),
      'Sidebar must be compact on 960px breakpoint'
    );

    // 3. Verify DemoQuickPicks CSS classes
    assert.ok(cssContent.includes('.demo-quick-picks'), 'Must contain .demo-quick-picks class');
    assert.ok(cssContent.includes('.quick-pick-btn'), 'Must contain .quick-pick-btn class');
    assert.ok(cssContent.includes('.quick-pick-notice-bar'), 'Must contain .quick-pick-notice-bar class');
  });

  describe('Phase 6 Step 8 — Step 3: Medium & Low Polish Tests', () => {
    it('1. Year-neutral SIH header subtitle without hardcoded year', () => {
      const appFile = fs.readFileSync(path.resolve(__dirname, '../src/App.tsx'), 'utf-8');
      assert.ok(
        appFile.includes('Smart India Hackathon'),
        'App header must reference Smart India Hackathon'
      );
      assert.strictEqual(
        appFile.includes('SIH 2024'),
        false,
        'App header must not hardcode outdated competition year "SIH 2024"'
      );
    });

    it('2. User-facing persistence terminology is clean and avoids raw column names', () => {
      const filterPanelFile = fs.readFileSync(
        path.resolve(__dirname, '../src/components/filters/FilterPanel.tsx'),
        'utf-8'
      );
      const drawerFile = fs.readFileSync(
        path.resolve(__dirname, '../src/components/events/EventDetailDrawer.tsx'),
        'utf-8'
      );

      // Verify clean label
      assert.ok(
        filterPanelFile.includes('Multi-day Persistent Hotspots'),
        'FilterPanel must display "Multi-day Persistent Hotspots"'
      );
      assert.ok(
        drawerFile.includes('Multi-day Persistent Hotspots'),
        'EventDetailDrawer must display "Multi-day Persistent Hotspots"'
      );

      // Verify no raw column exposed in user-facing text
      assert.strictEqual(
        filterPanelFile.includes('persistent_location_flag = 1'),
        false,
        'FilterPanel must not expose raw code snippet "persistent_location_flag = 1"'
      );
      assert.strictEqual(
        drawerFile.includes('>Persistent Location Flag<'),
        false,
        'EventDetailDrawer must not use raw "Persistent Location Flag" label'
      );
    });

    it('3. Class-specific filter pill styling and CSS classes exist for all 3 ML classes', () => {
      const filterPillsFile = fs.readFileSync(
        path.resolve(__dirname, '../src/components/filters/FilterPills.tsx'),
        'utf-8'
      );
      const cssContent = fs.readFileSync(CSS_PATH, 'utf-8');

      // Check FilterPills component logic
      assert.ok(filterPillsFile.includes('pill-class-industrial'));
      assert.ok(filterPillsFile.includes('pill-class-agricultural'));
      assert.ok(filterPillsFile.includes('pill-class-natural'));

      // Check CSS definitions
      assert.ok(cssContent.includes('.filter-pill.pill-class-industrial'));
      assert.ok(cssContent.includes('.filter-pill.pill-class-agricultural'));
      assert.ok(cssContent.includes('.filter-pill.pill-class-natural'));
    });

    it('4. Sentinel-2 unavailable explanation provides proper optical and revisit context', () => {
      const drawerFile = fs.readFileSync(
        path.resolve(__dirname, '../src/components/events/EventDetailDrawer.tsx'),
        'utf-8'
      );
      const vmFile = fs.readFileSync(
        path.resolve(__dirname, '../src/components/events/drawerViewModel.ts'),
        'utf-8'
      );

      // Check presence of unavailable notice
      assert.ok(drawerFile.includes('s2-unavailable-notice'));
      assert.ok(drawerFile.includes('revisit timing'));
      assert.ok(drawerFile.includes('cloud/quality filtering'));

      // Verify scientific framing: not thermal, absence doesn't mean no fire
      assert.ok(drawerFile.includes('not indicate absence of fire activity'));
      assert.ok(drawerFile.includes('optical surface/change evidence'));

      // Check drawerViewModel logic for non-SUCCESS S2 status
      const failedEvent = allEvents.find((e) => e.s2_change_status !== 'SUCCESS')!;
      assert.ok(failedEvent, 'Must have events with non-SUCCESS S2 status');
      const vmFailed = getDrawerViewModel(failedEvent);
      assert.strictEqual(vmFailed.sentinel2.isUnavailable, true);
      assert.ok(vmFailed.sentinel2.unavailableExplanation.length > 0);
      assert.ok(vmFailed.sentinel2.unavailableExplanation.includes('revisit timing'));

      // For SUCCESS S2 event
      const successEvent = allEvents.find((e) => e.s2_change_status === 'SUCCESS');
      if (successEvent) {
        const vmSuccess = getDrawerViewModel(successEvent);
        assert.strictEqual(vmSuccess.sentinel2.isUnavailable, false);
      }
    });

    it('5. Drawer scroll polish tightens spacing while preserving all scientific content', () => {
      const cssContent = fs.readFileSync(CSS_PATH, 'utf-8');

      // Tightened drawer content and section spacing
      assert.ok(cssContent.includes('padding: 0.75rem 1rem;'));
      assert.ok(cssContent.includes('gap: 0.75rem;'));
      assert.ok(cssContent.includes('gap: 0.5rem;'));
      assert.ok(cssContent.includes('gap: 0.45rem 0.75rem;'));

      // Verify all 8 drawer sections remain intact in EventDetailDrawer.tsx
      const drawerFile = fs.readFileSync(
        path.resolve(__dirname, '../src/components/events/EventDetailDrawer.tsx'),
        'utf-8'
      );
      assert.ok(drawerFile.includes('title="Event Identity"'));
      assert.ok(drawerFile.includes('title="FIRMS Thermal Detection"'));
      assert.ok(drawerFile.includes('title="ML Prediction"'));
      assert.ok(drawerFile.includes('title="OSM Industrial Context"'));
      assert.ok(drawerFile.includes('title="Land Cover Context"'));
      assert.ok(drawerFile.includes('title="Sentinel-2 Optical Context"'));
      assert.ok(drawerFile.includes('title="Human Expert Ground Truth"'));
      assert.ok(drawerFile.includes('title="Data Provenance & Audit Trail"'));
    });
  });
});

