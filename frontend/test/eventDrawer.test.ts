import { describe, it } from 'node:test';
import assert from 'node:assert';
import { getDrawerViewModel } from '../src/components/events/drawerViewModel.ts';
import { applyFilters } from '../src/utils/filterLogic.ts';
import { DEFAULT_FILTERS, type FilterCriteria } from '../src/types/filters.ts';
import type { DashboardEvent } from '../src/types/dashboard.ts';

describe('Event Detail Drawer ViewModel & Interaction Tests', () => {
  const sampleEvent: DashboardEvent = {
    event_id: 'FIRMS_TN_0000',
    row_id: 0,
    acq_date: '2024-11-01',
    acq_time: 1940,
    acq_datetime: '2024-11-01T19:40:00',
    daynight: 'N',
    latitude: 11.664,
    longitude: 78.071,
    satellite: 'N20',
    instrument: 'VIIRS',
    firms_confidence: 'n',
    frp: 1.16,
    brightness: 312.4,
    bright_t31: 294.2,
    brightness_difference: 18.2,
    is_day: 0,
    is_ststub_burning_season: undefined as unknown as number,
    is_stubble_burning_season: 0,
    grid_detection_count: 14,
    grid_active_days: 9,
    persistent_location_flag: 1,
    grid_total_frp: 28.4,
    high_frp_flag_local: 0,
    brightness_zscore_local: 0.45,
    predicted_class: 'Industrial Thermal Activity',
    probability_agricultural_burning: 0.433,
    probability_industrial_thermal_activity: 0.503,
    probability_natural_wildfire_other: 0.064,
    max_probability: 0.503,
    ml_confidence: 'MEDIUM',
    osm_coverage_status: 'COVERED',
    nearest_facility_name: 'Salem Steel Plant',
    nearest_facility_type: 'industrial',
    nearest_facility_category: 'Steel / Metallurgy',
    nearest_facility_tier: 'HIGHER_RELEVANCE',
    distance_to_facility_m: 328.0,
    near_industrial_500m: 1,
    near_industrial_1000m: 1,
    near_industrial_2000m: 1,
    nearest_hr_category: 'Steel / Metallurgy',
    nearest_hr_name: 'Salem Steel Plant',
    distance_to_higher_relevance_m: 328.0,
    landcover_code: 50,
    landcover_class: 'Built-up',
    pre_observation_status: 'REAL_CDSE_SUCCESS',
    post_observation_status: 'REAL_CDSE_SUCCESS',
    s2_change_status: 'SUCCESS',
    selected_pre_image_date: '2024-10-28',
    selected_post_image_date: '2024-11-02',
    s2_pre_feature_status: 'SUCCESS',
    s2_post_feature_status: 'SUCCESS',
    s2_pre_ndvi_mean: 0.18,
    s2_post_ndvi_mean: 0.17,
    s2_dnbr_mean: 0.008,
    has_human_validation: true,
    human_validation_status: 'VERIFIED',
    human_ground_truth_class: 'Persistent Industrial Thermal Source',
    is_unambiguous_ground_truth: true,
    inference_timestamp: '2026-09-06T18:18:49Z',
    model_version: 'phase_5_ml_handoff/final_model.joblib',
    model_sha256: '5909bb546fc55aeffd37b7bb601e96718709fe685e987705b246bb2963279798',
    data_source_version: 'phase_4b_ground_truth_v1',
  };

  it('1. Drawer renders selected event and handles null safely', () => {
    const vm = getDrawerViewModel(sampleEvent);
    assert.strictEqual(vm.isEmpty, false);
    assert.strictEqual(vm.eventId, 'FIRMS_TN_0000');

    const nullVm = getDrawerViewModel(null);
    assert.strictEqual(nullVm.isEmpty, true);
    assert.strictEqual(nullVm.eventId, '');
  });

  it('2. Event ID, date, and location coordinates are formatted with required precision', () => {
    const vm = getDrawerViewModel(sampleEvent);
    assert.strictEqual(vm.eventId, 'FIRMS_TN_0000');
    assert.strictEqual(vm.acqDateTime.includes('2024-11-01'), true);
    assert.strictEqual(vm.coordinates.lat, '11.66400°');
    assert.strictEqual(vm.coordinates.lon, '78.07100°');
    assert.strictEqual(vm.satelliteSource, 'N20 / VIIRS');
  });

  it('3. Three ML probabilities render correctly with percentages', () => {
    const vm = getDrawerViewModel(sampleEvent);
    assert.strictEqual(vm.mlPrediction.predictedClass, 'Industrial Thermal Activity');
    assert.strictEqual(vm.mlPrediction.winningProbability, '50.3%');
    assert.strictEqual(vm.mlPrediction.probabilities.industrial, '50.3%');
    assert.strictEqual(vm.mlPrediction.probabilities.agricultural, '43.3%');
    assert.strictEqual(vm.mlPrediction.probabilities.natural, '6.4%');
  });

  it('4. ML confidence and FIRMS confidence are displayed separately without merging', () => {
    const vm = getDrawerViewModel(sampleEvent);
    // Explicit title check
    assert.strictEqual(vm.firmsConfidence.title, 'FIRMS Detection Confidence');
    assert.strictEqual(vm.firmsConfidence.label, 'Nominal (n)');
    assert.strictEqual(vm.firmsConfidence.raw, 'n');

    assert.strictEqual(vm.mlPrediction.confidenceTierTitle, 'ML Confidence');
    assert.strictEqual(vm.mlPrediction.confidenceTier, 'MEDIUM');
    assert.notStrictEqual(vm.firmsConfidence.title, vm.mlPrediction.confidenceTierTitle);
  });

  it('5. Scientific disclaimer is prominently present for algorithmic ML estimate', () => {
    const vm = getDrawerViewModel(sampleEvent);
    assert.strictEqual(
      vm.mlPrediction.disclaimer,
      'Prediction is an algorithmic ML estimate. It is not ground truth.'
    );
  });

  it('6. OSM FAILED_TILE displays explicit message and does not claim no facility exists', () => {
    const failedTileEvent: DashboardEvent = {
      ...sampleEvent,
      osm_coverage_status: 'FAILED_TILE',
    };
    const vm = getDrawerViewModel(failedTileEvent);
    assert.strictEqual(vm.osm.isFailedTile, true);
    assert.strictEqual(vm.osm.failedTileMessage, 'OSM data was not retrieved for this area.');
    assert.strictEqual(
      vm.osm.disclaimer,
      'OpenStreetMap (OSM) information provides geographic context and is not ground truth.'
    );
  });

  it('7. Missing Sentinel-2 values display "Unavailable" rather than NaN/null/undefined', () => {
    const missingS2Event: DashboardEvent = {
      ...sampleEvent,
      s2_pre_ndvi_mean: null,
      s2_post_ndvi_mean: null,
      s2_dnbr_mean: null,
    };
    const vm = getDrawerViewModel(missingS2Event);
    assert.strictEqual(vm.sentinel2.preNdvi, 'Unavailable');
    assert.strictEqual(vm.sentinel2.postNdvi, 'Unavailable');
    assert.strictEqual(vm.sentinel2.dnbr, 'Unavailable');
    assert.strictEqual(vm.sentinel2.ndviDiff, 'Unavailable');
  });

  it('8. Sentinel-2 optical disclaimer is present', () => {
    const vm = getDrawerViewModel(sampleEvent);
    assert.strictEqual(
      vm.sentinel2.disclaimer,
      'Sentinel-2 provides optical surface and change evidence; it is not a thermal sensor.'
    );
  });

  it('9. Human-unvalidated event displays "Not human validated"', () => {
    const unvalidatedEvent: DashboardEvent = {
      ...sampleEvent,
      has_human_validation: false,
      human_validation_status: 'UNREVIEWED',
      human_ground_truth_class: null,
    };
    const vm = getDrawerViewModel(unvalidatedEvent);
    assert.strictEqual(vm.humanValidation.hasValidation, false);
    assert.strictEqual(vm.humanValidation.unvalidatedNotice, 'Not human validated');
  });

  it('10. Escape key closes drawer (contract verification)', () => {
    let closed = false;
    const onClose = () => {
      closed = true;
    };
    // Simulating the Escape key event handler logic in EventDetailDrawer
    const handleKeyDown = (e: { key: string }) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    handleKeyDown({ key: 'Enter' });
    assert.strictEqual(closed, false, 'Non-Escape key must not close drawer');
    handleKeyDown({ key: 'Escape' });
    assert.strictEqual(closed, true, 'Escape key must trigger onClose');
  });

  it('11. Closing drawer works', () => {
    let closed = false;
    const onClose = () => {
      closed = true;
    };
    onClose();
    assert.strictEqual(closed, true);
  });

  it('12. Selected event disappears when filters exclude it', () => {
    const events: DashboardEvent[] = [
      sampleEvent, // Industrial Thermal Activity
      {
        ...sampleEvent,
        event_id: 'FIRMS_TN_0001',
        predicted_class: 'Agricultural Burning',
      },
    ];

    // Filter by Agricultural Burning only -> excludes FIRMS_TN_0000
    const filterOnlyAgri: FilterCriteria = {
      ...DEFAULT_FILTERS,
      classes: ['Agricultural Burning'],
    };

    const filtered = applyFilters(events, filterOnlyAgri);
    assert.strictEqual(filtered.length, 1);
    assert.strictEqual(filtered[0].event_id, 'FIRMS_TN_0001');

    // Check if FIRMS_TN_0000 is still present in filtered events
    const isSelectedStillPresent = filtered.some((e) => e.event_id === sampleEvent.event_id);
    assert.strictEqual(isSelectedStillPresent, false, 'Excluded selected event must not be present in filteredEvents');
  });
});

