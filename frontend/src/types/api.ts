/**
 * TypeScript definitions for FastAPI ML Inference API integration.
 * Strictly aligned with src/api/main.py and outputs/phase_5c_api/ML_API_CONTRACT.md.
 */

import type { ProductionClass, ConfidenceTier } from './dashboard.ts';

/**
 * The canonical 36 baseline features required by the production Random Forest model.
 */
export interface Baseline36Features {
  // FIRMS Thermal Intensity (8)
  frp: number;
  brightness: number;
  bright_t31: number;
  brightness_difference: number;
  frp_brightness_ratio: number;
  log_frp: number;
  confidence_numeric: number;
  is_day: number;

  // FIRMS Persistence & Local Grid Anomaly (10)
  grid_detection_count: number;
  grid_active_days: number;
  persistent_location_flag: number;
  grid_total_frp: number;
  grid_brightness_mean: number;
  high_brightness_flag_local: number;
  high_frp_flag_local: number;
  brightness_zscore_local: number;
  frp_zscore_local: number;
  is_stubble_burning_season: number;

  // ESA WorldCover (1)
  landcover_code: number;

  // OpenStreetMap Spatial Proximity & Hierarchy Context (17)
  distance_to_facility_m: number;
  nearest_facility_type: string;
  nearest_facility_category: string;
  nearest_facility_tier: string;
  near_industrial_500m: number;
  near_industrial_1000m: number;
  near_industrial_2000m: number;
  near_industrial_5000m: number;
  near_industrial_10000m: number;
  distance_to_higher_relevance_m: number;
  nearest_hr_category: string;
  near_higher_relevance_500m: number;
  near_higher_relevance_1000m: number;
  near_higher_relevance_2000m: number;
  near_higher_relevance_5000m: number;
  near_higher_relevance_10000m: number;
  osm_coverage_status: string;
}

export type EventFeaturesLookup = Record<string, Baseline36Features>;

export interface PredictRequest {
  event_id?: string;
  features: Baseline36Features;
}

export interface ModelProvenance {
  version: string;
  sha256: string;
  architecture: string;
  training_samples: number;
  macro_f1_oof: number;
}

export interface PredictResponse {
  event_id?: string | null;
  predicted_class: ProductionClass;
  probabilities: {
    'Industrial Thermal Activity': number;
    'Agricultural Burning': number;
    'Natural / Wildfire / Other': number;
  };
  max_probability: number;
  ml_confidence: ConfidenceTier;
  confidence_scale: {
    HIGH: string;
    MEDIUM: string;
    LOW: string;
  };
  model: ModelProvenance;
  inference_timestamp: string;
  disclaimer: string;
}

export interface HealthResponse {
  status: string;
  model_loaded: boolean;
  model_version?: string;
  model_sha256?: string;
  required_features_count?: number;
  production_classes?: string[];
  api_version: string;
  timestamp: string;
  error?: string;
}

export interface ApiErrorDetail {
  code: string;
  message: string;
  details?: Record<string, any>;
}

export interface ApiErrorResponse {
  error: ApiErrorDetail;
}

export class ApiError extends Error {
  public readonly code: string;
  public readonly status: number;
  public readonly details: Record<string, any>;

  constructor(code: string, message: string, status: number, details: Record<string, any> = {}) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

/**
 * Default retry interval (10 seconds) for backend health check polling.
 */
export const DEFAULT_RETRY_INTERVAL_MS = 10000;
