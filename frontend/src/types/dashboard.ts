/**
 * Authoritative TypeScript Data Model for Industrial Fire Detection Dashboard.
 * Strictly aligned with outputs/phase_5b_dashboard/dashboard_events_633.csv (61 columns).
 */

export type ProductionClass =
  | 'Industrial Thermal Activity'
  | 'Agricultural Burning'
  | 'Natural / Wildfire / Other';

export type ConfidenceTier = 'HIGH' | 'MEDIUM' | 'LOW';

export type FirmsConfidence = 'h' | 'n' | 'l';

export type DayNight = 'D' | 'N';

export type OsmCoverageStatus = 'COVERED' | 'FAILED_TILE';

export type FacilityTier =
  | 'HIGHER_RELEVANCE'
  | 'CAUTION_LOWER_RELEVANCE'
  | 'GENERAL_CONTEXT'
  | 'NO_FACILITY_FOUND';

export type ObservationStatus =
  | 'REAL_CDSE_SUCCESS'
  | 'CLOUD_REJECTED'
  | 'MISSING_PRODUCT';

export type S2ChangeStatus =
  | 'SUCCESS'
  | 'MISSING_PRE'
  | 'MISSING_POST'
  | 'CLOUD_REJECTED'
  | 'INSUFFICIENT_VALID_DATA';

export type HumanValidationStatus = 'VERIFIED' | 'UNREVIEWED';

export interface DashboardEvent {
  // GROUP A — EVENT IDENTITY (6 fields)
  event_id: string;
  row_id: number;
  acq_date: string;
  acq_time: number;
  acq_datetime: string;
  daynight: DayNight;

  // GROUP B — LOCATION (2 fields)
  latitude: number;
  longitude: number;

  // GROUP C — FIRMS THERMAL EVIDENCE (15 fields)
  satellite: string;
  instrument: string;
  firms_confidence: FirmsConfidence;
  frp: number;
  brightness: number;
  bright_t31: number;
  brightness_difference: number;
  is_day: number;
  is_stubble_burning_season: number;
  grid_detection_count: number;
  grid_active_days: number;
  persistent_location_flag: number;
  grid_total_frp: number;
  high_frp_flag_local: number;
  brightness_zscore_local: number;

  // GROUP D — ML PREDICTION (6 fields)
  predicted_class: ProductionClass;
  probability_agricultural_burning: number;
  probability_industrial_thermal_activity: number;
  probability_natural_wildfire_other: number;
  max_probability: number;
  ml_confidence: ConfidenceTier;

  // GROUP E — OSM INDUSTRIAL CONTEXT (12 fields)
  osm_coverage_status: OsmCoverageStatus;
  nearest_facility_name: string | null;
  nearest_facility_type: string;
  nearest_facility_category: string;
  nearest_facility_tier: FacilityTier;
  distance_to_facility_m: number;
  near_industrial_500m: number;
  near_industrial_1000m: number;
  near_industrial_2000m: number;
  nearest_hr_category: string;
  nearest_hr_name: string | null;
  distance_to_higher_relevance_m: number;

  // GROUP F — WORLDCOVER (2 fields)
  landcover_code: number;
  landcover_class: string;

  // GROUP G — SENTINEL-2 (10 fields)
  pre_observation_status: ObservationStatus;
  post_observation_status: ObservationStatus;
  s2_change_status: S2ChangeStatus;
  selected_pre_image_date: string | null;
  selected_post_image_date: string | null;
  s2_pre_feature_status: string | null;
  s2_post_feature_status: string | null;
  s2_pre_ndvi_mean: number | null;
  s2_post_ndvi_mean: number | null;
  s2_dnbr_mean: number | null;

  // GROUP H — HUMAN VALIDATION (4 fields)
  has_human_validation: boolean;
  human_validation_status: HumanValidationStatus;
  human_ground_truth_class: string | null;
  is_unambiguous_ground_truth: boolean;

  // GROUP I — PROVENANCE (4 fields)
  inference_timestamp: string;
  model_version: string;
  model_sha256: string;
  data_source_version: string;
}

export const OFFICIAL_PRODUCTION_CLASSES: readonly ProductionClass[] = [
  'Industrial Thermal Activity',
  'Agricultural Burning',
  'Natural / Wildfire / Other',
] as const;
