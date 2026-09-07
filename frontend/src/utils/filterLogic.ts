import type { DashboardEvent } from '../types/dashboard.ts';
import type { FilterCriteria } from '../types/filters.ts';

export interface KPIMetrics {
  totalShown: number;
  industrialCount: number;
  agriculturalCount: number;
  naturalCount: number;
  highConfidenceCount: number;
  avgFrp: number;
}

/**
 * Pure, deterministic filter function that returns a new array of matching events.
 * Does NOT mutate the input array.
 */
export function applyFilters(events: readonly DashboardEvent[], filters: FilterCriteria): DashboardEvent[] {
  return events.filter((event) => {
    // 1. ML Predicted Class Filter
    if (filters.classes.length > 0 && !filters.classes.includes(event.predicted_class)) {
      return false;
    }

    // 2. ML Confidence Tier Filter (HIGH / MEDIUM / LOW)
    if (filters.mlConfidenceTiers.length > 0 && !filters.mlConfidenceTiers.includes(event.ml_confidence)) {
      return false;
    }

    // 3. FIRMS Satellite Sensor Confidence Filter (h / n / l)
    if (filters.firmsConfidences.length > 0 && !filters.firmsConfidences.includes(event.firms_confidence)) {
      return false;
    }

    // 4. WorldCover Landcover Class Filter
    if (filters.landcoverClasses.length > 0 && !filters.landcoverClasses.includes(event.landcover_class)) {
      return false;
    }

    // 5. OSM Facility Proximity / Relevance Tier Filter
    if (filters.facilityTiers.length > 0 && !filters.facilityTiers.includes(event.nearest_facility_tier)) {
      return false;
    }

    // 6. Sentinel-2 Change Status Filter
    if (filters.s2Statuses.length > 0 && !filters.s2Statuses.includes(event.s2_change_status)) {
      return false;
    }

    // 7. Spatial Persistence (Multi-day Hotspot: persistent_location_flag === 1)
    if (filters.onlyPersistentHotspots && event.persistent_location_flag !== 1) {
      return false;
    }

    // 8. Fire Radiative Power (FRP) Range Filter
    if (event.frp < filters.frpMin || event.frp > filters.frpMax) {
      return false;
    }

    return true;
  });
}

/**
 * Determines whether any active filters are applied compared to default.
 */
export function isFilterActive(filters: FilterCriteria): boolean {
  return (
    filters.classes.length > 0 ||
    filters.mlConfidenceTiers.length > 0 ||
    filters.firmsConfidences.length > 0 ||
    filters.landcoverClasses.length > 0 ||
    filters.facilityTiers.length > 0 ||
    filters.s2Statuses.length > 0 ||
    filters.onlyPersistentHotspots ||
    filters.frpMin > 0 ||
    filters.frpMax < 20
  );
}

/**
 * Calculates summary KPI metrics based strictly on the filtered events.
 */
export function calculateKPIs(events: readonly DashboardEvent[]): KPIMetrics {
  if (events.length === 0) {
    return {
      totalShown: 0,
      industrialCount: 0,
      agriculturalCount: 0,
      naturalCount: 0,
      highConfidenceCount: 0,
      avgFrp: 0,
    };
  }

  let industrialCount = 0;
  let agriculturalCount = 0;
  let naturalCount = 0;
  let highConfidenceCount = 0;
  let totalFrp = 0;

  for (let i = 0; i < events.length; i++) {
    const e = events[i];
    if (e.predicted_class === 'Industrial Thermal Activity') industrialCount++;
    else if (e.predicted_class === 'Agricultural Burning') agriculturalCount++;
    else if (e.predicted_class === 'Natural / Wildfire / Other') naturalCount++;

    if (e.ml_confidence === 'HIGH') highConfidenceCount++;
    totalFrp += typeof e.frp === 'number' && !isNaN(e.frp) ? e.frp : 0;
  }

  return {
    totalShown: events.length,
    industrialCount,
    agriculturalCount,
    naturalCount,
    highConfidenceCount,
    avgFrp: parseFloat((totalFrp / events.length).toFixed(2)),
  };
}
