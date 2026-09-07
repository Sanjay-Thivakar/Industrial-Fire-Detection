import type {
  ProductionClass,
  ConfidenceTier,
  FirmsConfidence,
  FacilityTier,
  S2ChangeStatus,
} from './dashboard.ts';

export interface FilterCriteria {
  // 1. ML Predicted Class (multiselect; empty = all)
  classes: ProductionClass[];

  // 2. ML Confidence Tier (HIGH, MEDIUM, LOW)
  mlConfidenceTiers: ConfidenceTier[];

  // 3. NASA FIRMS Satellite Sensor Confidence (h, n, l)
  firmsConfidences: FirmsConfidence[];

  // 4. ESA WorldCover Landcover Class
  landcoverClasses: string[];

  // 5. OSM Industrial Context / Proximity Tier
  facilityTiers: FacilityTier[];

  // 6. Sentinel-2 Change Status
  s2Statuses: S2ChangeStatus[];

  // 7. Spatial Persistence (Multi-day Hotspot: persistent_location_flag === 1)
  onlyPersistentHotspots: boolean;

  // 8. Fire Radiative Power (FRP) Minimum & Maximum in Megawatts (MW)
  frpMin: number;
  frpMax: number;
}

export const DEFAULT_FILTERS: FilterCriteria = {
  classes: [],
  mlConfidenceTiers: [],
  firmsConfidences: [],
  landcoverClasses: [],
  facilityTiers: [],
  s2Statuses: [],
  onlyPersistentHotspots: false,
  frpMin: 0,
  frpMax: 20, // Dataset max is 16.84 MW
};
