import Papa from 'papaparse';
import { OFFICIAL_PRODUCTION_CLASSES } from '../types/dashboard.ts';
import type {
  DashboardEvent,
  ProductionClass,
  ConfidenceTier,
  FirmsConfidence,
  DayNight,
  OsmCoverageStatus,
  FacilityTier,
  ObservationStatus,
  S2ChangeStatus,
  HumanValidationStatus,
} from '../types/dashboard.ts';

export interface DataLoadResult {
  events: DashboardEvent[];
  error: string | null;
}

/**
 * Validates whether a string belongs to the official 3-class set.
 */
export function isValidProductionClass(val: unknown): val is ProductionClass {
  return typeof val === 'string' && (OFFICIAL_PRODUCTION_CLASSES as readonly string[]).includes(val);
}

/**
 * Parses raw CSV string or row object into a strongly-typed DashboardEvent.
 * Validates numeric fields and rejects malformed records.
 */
export function parseDashboardRow(raw: Record<string, any>, rowIndex: number): DashboardEvent {
  const event_id = String(raw.event_id || '').trim();
  if (!event_id) {
    throw new Error(`Row ${rowIndex}: Missing required event_id`);
  }

  const lat = parseFloat(raw.latitude);
  const lon = parseFloat(raw.longitude);

  if (isNaN(lat) || isNaN(lon)) {
    throw new Error(`Event ${event_id}: Invalid non-numeric coordinates (lat: ${raw.latitude}, lon: ${raw.longitude})`);
  }

  if (lat < 8.0 || lat > 14.0 || lon < 76.0 || lon > 81.5) {
    throw new Error(`Event ${event_id}: Coordinates out of Tamil Nadu bounds (lat: ${lat}, lon: ${lon})`);
  }

  const predicted_class = raw.predicted_class;
  if (!isValidProductionClass(predicted_class)) {
    throw new Error(`Event ${event_id}: Invalid predicted_class "${predicted_class}". Must be one of: ${OFFICIAL_PRODUCTION_CLASSES.join(', ')}`);
  }

  const parseNumber = (val: any, fieldName: string, defaultValue?: number): number => {
    if (val === null || val === undefined || val === '') {
      if (defaultValue !== undefined) return defaultValue;
      throw new Error(`Event ${event_id}: Missing required numeric field "${fieldName}"`);
    }
    const num = parseFloat(val);
    if (isNaN(num)) {
      throw new Error(`Event ${event_id}: Field "${fieldName}" is not a valid number ("${val}")`);
    }
    return num;
  };

  const parseNullableNumber = (val: any): number | null => {
    if (val === null || val === undefined || val === '' || val === 'N/A' || val === 'null') {
      return null;
    }
    const num = parseFloat(val);
    return isNaN(num) ? null : num;
  };

  const parseNullableString = (val: any): string | null => {
    if (val === null || val === undefined) return null;
    const s = String(val).trim();
    if (s === '' || s.toLowerCase() === 'null' || s.toLowerCase() === 'nan' || s.toLowerCase() === 'none') {
      return null;
    }
    return s;
  };

  const parseBool = (val: any): boolean => {
    if (typeof val === 'boolean') return val;
    const s = String(val).trim().toLowerCase();
    return s === 'true' || s === '1' || s === 'yes';
  };

  return {
    // Group A
    event_id,
    row_id: parseNumber(raw.row_id, 'row_id', rowIndex),
    acq_date: String(raw.acq_date || ''),
    acq_time: parseNumber(raw.acq_time, 'acq_time', 0),
    acq_datetime: String(raw.acq_datetime || ''),
    daynight: (raw.daynight === 'D' || raw.daynight === 'N' ? raw.daynight : 'D') as DayNight,

    // Group B
    latitude: lat,
    longitude: lon,

    // Group C
    satellite: String(raw.satellite || ''),
    instrument: String(raw.instrument || ''),
    firms_confidence: (raw.firms_confidence || 'n') as FirmsConfidence,
    frp: parseNumber(raw.frp, 'frp'),
    brightness: parseNumber(raw.brightness, 'brightness'),
    bright_t31: parseNumber(raw.bright_t31, 'bright_t31'),
    brightness_difference: parseNumber(raw.brightness_difference, 'brightness_difference'),
    is_day: parseNumber(raw.is_day, 'is_day', 1),
    is_stubble_burning_season: parseNumber(raw.is_stubble_burning_season, 'is_stubble_burning_season', 0),
    grid_detection_count: parseNumber(raw.grid_detection_count, 'grid_detection_count', 1),
    grid_active_days: parseNumber(raw.grid_active_days, 'grid_active_days', 1),
    persistent_location_flag: parseNumber(raw.persistent_location_flag, 'persistent_location_flag', 0),
    grid_total_frp: parseNumber(raw.grid_total_frp, 'grid_total_frp', 0),
    high_frp_flag_local: parseNumber(raw.high_frp_flag_local, 'high_frp_flag_local', 0),
    brightness_zscore_local: parseNumber(raw.brightness_zscore_local, 'brightness_zscore_local', 0),

    // Group D
    predicted_class,
    probability_agricultural_burning: parseNumber(raw.probability_agricultural_burning, 'probability_agricultural_burning'),
    probability_industrial_thermal_activity: parseNumber(raw.probability_industrial_thermal_activity, 'probability_industrial_thermal_activity'),
    probability_natural_wildfire_other: parseNumber(raw.probability_natural_wildfire_other, 'probability_natural_wildfire_other'),
    max_probability: parseNumber(raw.max_probability, 'max_probability'),
    ml_confidence: (raw.ml_confidence || 'MEDIUM') as ConfidenceTier,

    // Group E
    osm_coverage_status: (raw.osm_coverage_status || 'COVERED') as OsmCoverageStatus,
    nearest_facility_name: parseNullableString(raw.nearest_facility_name),
    nearest_facility_type: String(raw.nearest_facility_type || ''),
    nearest_facility_category: String(raw.nearest_facility_category || ''),
    nearest_facility_tier: (raw.nearest_facility_tier || 'GENERAL_CONTEXT') as FacilityTier,
    distance_to_facility_m: parseNumber(raw.distance_to_facility_m, 'distance_to_facility_m', 0),
    near_industrial_500m: parseNumber(raw.near_industrial_500m, 'near_industrial_500m', 0),
    near_industrial_1000m: parseNumber(raw.near_industrial_1000m, 'near_industrial_1000m', 0),
    near_industrial_2000m: parseNumber(raw.near_industrial_2000m, 'near_industrial_2000m', 0),
    nearest_hr_category: String(raw.nearest_hr_category || ''),
    nearest_hr_name: parseNullableString(raw.nearest_hr_name),
    distance_to_higher_relevance_m: parseNumber(raw.distance_to_higher_relevance_m, 'distance_to_higher_relevance_m', 0),

    // Group F
    landcover_code: parseNumber(raw.landcover_code, 'landcover_code', 0),
    landcover_class: String(raw.landcover_class || 'Unknown'),

    // Group G
    pre_observation_status: (raw.pre_observation_status || 'MISSING_PRODUCT') as ObservationStatus,
    post_observation_status: (raw.post_observation_status || 'MISSING_PRODUCT') as ObservationStatus,
    s2_change_status: (raw.s2_change_status || 'INSUFFICIENT_VALID_DATA') as S2ChangeStatus,
    selected_pre_image_date: parseNullableString(raw.selected_pre_image_date),
    selected_post_image_date: parseNullableString(raw.selected_post_image_date),
    s2_pre_feature_status: parseNullableString(raw.s2_pre_feature_status),
    s2_post_feature_status: parseNullableString(raw.s2_post_feature_status),
    s2_pre_ndvi_mean: parseNullableNumber(raw.s2_pre_ndvi_mean),
    s2_post_ndvi_mean: parseNullableNumber(raw.s2_post_ndvi_mean),
    s2_dnbr_mean: parseNullableNumber(raw.s2_dnbr_mean),

    // Group H
    has_human_validation: parseBool(raw.has_human_validation),
    human_validation_status: (raw.human_validation_status || 'UNREVIEWED') as HumanValidationStatus,
    human_ground_truth_class: parseNullableString(raw.human_ground_truth_class),
    is_unambiguous_ground_truth: parseBool(raw.is_unambiguous_ground_truth),

    // Group I
    inference_timestamp: String(raw.inference_timestamp || ''),
    model_version: String(raw.model_version || ''),
    model_sha256: String(raw.model_sha256 || ''),
    data_source_version: String(raw.data_source_version || ''),
  };
}

/**
 * Loads and validates the dashboard CSV dataset.
 * Performs runtime integrity checks:
 * 1. Exactly 633 events
 * 2. Unique event_id keys
 * 3. Valid numeric coordinates
 * 4. Strictly 3 official ML classes
 */
export async function loadDashboardEvents(csvUrl = '/data/dashboard_events_633.csv'): Promise<DataLoadResult> {
  try {
    const response = await fetch(csvUrl);
    if (!response.ok) {
      throw new Error(`Failed to fetch dashboard dataset from "${csvUrl}": HTTP ${response.status} ${response.statusText}`);
    }

    const csvText = await response.text();

    return new Promise((resolve) => {
      Papa.parse<Record<string, any>>(csvText, {
        header: true,
        dynamicTyping: false, // We control typed coercion explicitly
        skipEmptyLines: true,
        complete: (results) => {
          try {
            if (results.errors.length > 0) {
              const firstErr = results.errors[0];
              throw new Error(`CSV Parsing error at row ${firstErr.row}: ${firstErr.message}`);
            }

            const rawRows = results.data;
            if (rawRows.length !== 633) {
              throw new Error(`Integrity error: Expected exactly 633 events, but parsed ${rawRows.length} rows.`);
            }

            const seenIds = new Set<string>();
            const parsedEvents: DashboardEvent[] = [];

            for (let i = 0; i < rawRows.length; i++) {
              const event = parseDashboardRow(rawRows[i], i);
              if (seenIds.has(event.event_id)) {
                throw new Error(`Integrity error: Duplicate event_id "${event.event_id}" detected at row ${i + 1}`);
              }
              seenIds.add(event.event_id);
              parsedEvents.push(event);
            }

            resolve({
              events: parsedEvents,
              error: null,
            });
          } catch (err: any) {
            resolve({
              events: [],
              error: err.message || 'Unknown parsing error occurred.',
            });
          }
        },
        error: (err: Error) => {
          resolve({
            events: [],
            error: `PapaParse failure: ${err.message}`,
          });
        },
      });
    });
  } catch (err: any) {
    return {
      events: [],
      error: err.message || 'Failed to load dashboard CSV.',
    };
  }
}
