import { describe, it } from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';
import Papa from 'papaparse';
import { parseDashboardRow, isValidProductionClass } from '../src/services/dataLoader.ts';
import { OFFICIAL_PRODUCTION_CLASSES } from '../src/types/dashboard.ts';

describe('Data Loader & Integrity Verification Tests', () => {
  const baseValidRow = {
    event_id: 'FIRMS_TN_0000',
    row_id: '0',
    acq_date: '2024-11-01',
    acq_time: '1940',
    acq_datetime: '2024-11-01T19:40:00',
    daynight: 'N',
    latitude: '11.664',
    longitude: '78.071',
    satellite: 'N20',
    instrument: 'VIIRS',
    firms_confidence: 'h',
    frp: '1.16',
    brightness: '312.4',
    bright_t31: '294.2',
    brightness_difference: '18.2',
    is_day: '0',
    is_stubble_burning_season: '0',
    grid_detection_count: '14',
    grid_active_days: '9',
    persistent_location_flag: '1',
    grid_total_frp: '28.4',
    high_frp_flag_local: '0',
    brightness_zscore_local: '0.45',
    predicted_class: 'Industrial Thermal Activity',
    probability_agricultural_burning: '0.433',
    probability_industrial_thermal_activity: '0.503',
    probability_natural_wildfire_other: '0.064',
    max_probability: '0.503',
    ml_confidence: 'MEDIUM',
    osm_coverage_status: 'COVERED',
    nearest_facility_name: 'Salem Steel Plant',
    nearest_facility_type: 'industrial',
    nearest_facility_category: 'Steel / Metallurgy',
    nearest_facility_tier: 'HIGHER_RELEVANCE',
    distance_to_facility_m: '328.0',
    near_industrial_500m: '1',
    near_industrial_1000m: '1',
    near_industrial_2000m: '1',
    nearest_hr_category: 'Steel / Metallurgy',
    nearest_hr_name: 'Salem Steel Plant',
    distance_to_higher_relevance_m: '328.0',
    landcover_code: '50',
    landcover_class: 'Built-up',
    pre_observation_status: 'REAL_CDSE_SUCCESS',
    post_observation_status: 'REAL_CDSE_SUCCESS',
    s2_change_status: 'SUCCESS',
    selected_pre_image_date: '2024-10-28',
    selected_post_image_date: '2024-11-02',
    s2_pre_feature_status: 'SUCCESS',
    s2_post_feature_status: 'SUCCESS',
    s2_pre_ndvi_mean: '0.18',
    s2_post_ndvi_mean: '0.17',
    s2_dnbr_mean: '0.008',
    has_human_validation: 'True',
    human_validation_status: 'VERIFIED',
    human_ground_truth_class: 'Persistent Industrial Thermal Source',
    is_unambiguous_ground_truth: 'True',
    inference_timestamp: '2026-09-06T18:18:49Z',
    model_version: 'phase_5_ml_handoff/final_model.joblib',
    model_sha256: '5909bb546fc55aeffd37b7bb601e96718709fe685e987705b246bb2963279798',
    data_source_version: 'phase_4b_ground_truth_v1',
  };

  it('1. Successfully parses a valid dashboard row into typed values', () => {
    const event = parseDashboardRow(baseValidRow, 0);
    assert.strictEqual(event.event_id, 'FIRMS_TN_0000');
    assert.strictEqual(event.latitude, 11.664);
    assert.strictEqual(event.longitude, 78.071);
    assert.strictEqual(event.frp, 1.16);
    assert.strictEqual(event.predicted_class, 'Industrial Thermal Activity');
    assert.strictEqual(event.max_probability, 0.503);
    assert.strictEqual(event.ml_confidence, 'MEDIUM');
    assert.strictEqual(event.firms_confidence, 'h');
    assert.strictEqual(event.has_human_validation, true);
    assert.strictEqual(event.is_unambiguous_ground_truth, true);
  });

  it('2. Enforces the official 3 ML classes and validates class helper', () => {
    assert.strictEqual(isValidProductionClass('Industrial Thermal Activity'), true);
    assert.strictEqual(isValidProductionClass('Agricultural Burning'), true);
    assert.strictEqual(isValidProductionClass('Natural / Wildfire / Other'), true);
    assert.strictEqual(isValidProductionClass('Persistent Industrial Source'), false);
    assert.strictEqual(isValidProductionClass('Forest Fire'), false);
    assert.strictEqual(isValidProductionClass('Unknown Class'), false);
  });

  it('3. Rejects rows with invalid or non-official ML classes', () => {
    const invalidClassRow = { ...baseValidRow, predicted_class: 'Invalid Class Heuristic' };
    assert.throws(
      () => parseDashboardRow(invalidClassRow, 1),
      /Invalid predicted_class "Invalid Class Heuristic"/
    );
  });

  it('4. Rejects rows with non-numeric or missing coordinates', () => {
    const nanCoordRow = { ...baseValidRow, latitude: 'not-a-number' };
    assert.throws(
      () => parseDashboardRow(nanCoordRow, 2),
      /Invalid non-numeric coordinates/
    );
  });

  it('5. Rejects coordinates outside of Tamil Nadu bounds', () => {
    const outOfBoundsRow = { ...baseValidRow, latitude: '25.500', longitude: '85.000' };
    assert.throws(
      () => parseDashboardRow(outOfBoundsRow, 3),
      /Coordinates out of Tamil Nadu bounds/
    );
  });

  it('6. Rejects missing event_id', () => {
    const missingIdRow = { ...baseValidRow, event_id: '' };
    assert.throws(
      () => parseDashboardRow(missingIdRow, 4),
      /Missing required event_id/
    );
  });

  it('7. Handles nullable fields gracefully without fabrication', () => {
    const nullRow = {
      ...baseValidRow,
      nearest_facility_name: '',
      nearest_hr_name: 'null',
      s2_dnbr_mean: 'N/A',
      human_ground_truth_class: '',
    };
    const event = parseDashboardRow(nullRow, 5);
    assert.strictEqual(event.nearest_facility_name, null);
    assert.strictEqual(event.nearest_hr_name, null);
    assert.strictEqual(event.s2_dnbr_mean, null);
    assert.strictEqual(event.human_ground_truth_class, null);
  });

  it('8. Verifies authoritative CSV: exactly 633 unique rows, valid coords, valid 3 ML classes', () => {
    const csvPath = path.resolve(process.cwd(), 'public/data/dashboard_events_633.csv');
    assert.strictEqual(fs.existsSync(csvPath), true, 'dashboard_events_633.csv must exist in public/data/');

    const csvContent = fs.readFileSync(csvPath, 'utf-8');
    const parsed = Papa.parse<Record<string, any>>(csvContent, {
      header: true,
      skipEmptyLines: true,
    });

    assert.strictEqual(parsed.errors.length, 0, 'CSV parsing should have zero errors');
    assert.strictEqual(parsed.data.length, 633, 'Expected exactly 633 events');

    const seenIds = new Set<string>();
    const classCounts: Record<string, number> = {
      'Industrial Thermal Activity': 0,
      'Agricultural Burning': 0,
      'Natural / Wildfire / Other': 0,
    };

    parsed.data.forEach((rawRow, idx) => {
      const event = parseDashboardRow(rawRow, idx);

      // Check unique IDs
      assert.strictEqual(seenIds.has(event.event_id), false, `Duplicate ID: ${event.event_id}`);
      seenIds.add(event.event_id);

      // Check coordinates
      assert.strictEqual(event.latitude >= 8.0 && event.latitude <= 14.0, true);
      assert.strictEqual(event.longitude >= 76.0 && event.longitude <= 81.5, true);

      // Check ML class
      assert.strictEqual((OFFICIAL_PRODUCTION_CLASSES as readonly string[]).includes(event.predicted_class), true);
      classCounts[event.predicted_class]++;
    });

    assert.strictEqual(seenIds.size, 633, 'Total unique event IDs must be 633');
    assert.strictEqual(
      classCounts['Industrial Thermal Activity'] +
        classCounts['Agricultural Burning'] +
        classCounts['Natural / Wildfire / Other'],
      633
    );

    console.log('Class distribution in authoritative dataset:');
    console.log(classCounts);
  });
});
