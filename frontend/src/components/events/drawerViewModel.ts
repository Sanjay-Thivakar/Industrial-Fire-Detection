import type { DashboardEvent } from '../../types/dashboard.ts';
import {
  formatCoord,
  formatFrp,
  formatKelvin,
  formatDistance,
  formatPercentage,
  formatNullable,
} from '../../utils/formatters.ts';

export interface DrawerViewModel {
  isEmpty: boolean;
  eventId: string;
  acqDateTime: string;
  coordinates: {
    lat: string;
    lon: string;
  };
  satelliteSource: string;
  firmsConfidence: {
    title: string;
    label: string;
    raw: string;
  };
  thermal: {
    frp: string;
    brightness: string;
    brightT31: string;
    dayNight: string;
    activeDays: string;
    detectionCount: string;
    isPersistent: boolean;
  };
  mlPrediction: {
    predictedClass: string;
    winningProbability: string;
    confidenceTierTitle: string;
    confidenceTier: string;
    disclaimer: string;
    probabilities: {
      industrial: string;
      agricultural: string;
      natural: string;
    };
  };
  osm: {
    coverageStatus: string;
    isFailedTile: boolean;
    failedTileMessage: string;
    disclaimer: string;
    facilityName: string;
    facilityType: string;
    facilityCategory: string;
    facilityTier: string;
    distanceFacility: string;
    distanceHigherRelevance: string;
    nearestHrCategory: string;
  };
  landcover: {
    className: string;
    code: number;
  };
  sentinel2: {
    preStatus: string;
    postStatus: string;
    changeStatus: string;
    preNdvi: string;
    postNdvi: string;
    ndviDiff: string;
    dnbr: string;
    disclaimer: string;
    isUnavailable: boolean;
    unavailableExplanation: string;
  };
  humanValidation: {
    hasValidation: boolean;
    unvalidatedNotice: string;
    status: string;
    groundTruthClass: string;
    certainty: string;
  };
  provenance: {
    modelVersion: string;
    modelSha256: string;
    dataSourceVersion: string;
    timestamp: string;
  };
}

export function getDrawerViewModel(event: DashboardEvent | null): DrawerViewModel {
  if (!event) {
    return {
      isEmpty: true,
      eventId: '',
      acqDateTime: '',
      coordinates: { lat: 'Unavailable', lon: 'Unavailable' },
      satelliteSource: '',
      firmsConfidence: { title: 'FIRMS Detection Confidence', label: 'Unavailable', raw: '' },
      thermal: { frp: '', brightness: '', brightT31: '', dayNight: '', activeDays: '', detectionCount: '', isPersistent: false },
      mlPrediction: {
        predictedClass: '',
        winningProbability: '',
        confidenceTierTitle: 'ML Confidence',
        confidenceTier: '',
        disclaimer: 'Prediction is an algorithmic ML estimate. It is not ground truth.',
        probabilities: { industrial: '', agricultural: '', natural: '' },
      },
      osm: {
        coverageStatus: '',
        isFailedTile: false,
        failedTileMessage: 'OSM data was not retrieved for this area.',
        disclaimer: 'OpenStreetMap (OSM) information provides geographic context and is not ground truth.',
        facilityName: 'Unavailable',
        facilityType: 'Unavailable',
        facilityCategory: 'Unavailable',
        facilityTier: 'Unavailable',
        distanceFacility: 'Unavailable',
        distanceHigherRelevance: 'Unavailable',
        nearestHrCategory: 'Unavailable',
      },
      landcover: { className: 'Unavailable', code: 0 },
      sentinel2: {
        preStatus: 'Unavailable',
        postStatus: 'Unavailable',
        changeStatus: 'Unavailable',
        preNdvi: 'Unavailable',
        postNdvi: 'Unavailable',
        ndviDiff: 'Unavailable',
        dnbr: 'Unavailable',
        disclaimer: 'Sentinel-2 provides optical surface and change evidence; it is not a thermal sensor.',
        isUnavailable: true,
        unavailableExplanation:
          'Optical imagery may be unavailable due to satellite revisit timing (5-day constellation cycle), cloud/quality filtering, or missing suitable cloud-free observation pairs. Sentinel-2 provides optical surface/change evidence rather than active thermal detection; unavailability does not indicate absence of fire activity.',
      },
      humanValidation: {
        hasValidation: false,
        unvalidatedNotice: 'Not human validated',
        status: 'UNREVIEWED',
        groundTruthClass: 'Unavailable',
        certainty: 'Unavailable',
      },
      provenance: { modelVersion: '', modelSha256: '', dataSourceVersion: '', timestamp: '' },
    };
  }

  const firmsConfLabel =
    event.firms_confidence === 'h'
      ? 'High (h)'
      : event.firms_confidence === 'n'
      ? 'Nominal (n)'
      : 'Low (l)';

  const ndviDiff =
    event.s2_post_ndvi_mean !== null && event.s2_pre_ndvi_mean !== null
      ? (event.s2_post_ndvi_mean - event.s2_pre_ndvi_mean).toFixed(3)
      : null;

  return {
    isEmpty: false,
    eventId: event.event_id,
    acqDateTime: event.acq_datetime || `${event.acq_date} ${event.acq_time}`,
    coordinates: {
      lat: formatCoord(event.latitude),
      lon: formatCoord(event.longitude),
    },
    satelliteSource: `${event.satellite} / ${event.instrument}`,
    firmsConfidence: {
      title: 'FIRMS Detection Confidence',
      label: firmsConfLabel,
      raw: event.firms_confidence,
    },
    thermal: {
      frp: formatFrp(event.frp),
      brightness: formatKelvin(event.brightness),
      brightT31: formatKelvin(event.bright_t31),
      dayNight: event.daynight === 'D' ? '☀️ Daytime (D)' : '🌙 Nighttime (N)',
      activeDays: `${event.grid_active_days} days`,
      detectionCount: `${event.grid_detection_count} detections`,
      isPersistent: event.persistent_location_flag === 1,
    },
    mlPrediction: {
      predictedClass: event.predicted_class,
      winningProbability: formatPercentage(event.max_probability),
      confidenceTierTitle: 'ML Confidence',
      confidenceTier: event.ml_confidence,
      disclaimer: 'Prediction is an algorithmic ML estimate. It is not ground truth.',
      probabilities: {
        industrial: formatPercentage(event.probability_industrial_thermal_activity),
        agricultural: formatPercentage(event.probability_agricultural_burning),
        natural: formatPercentage(event.probability_natural_wildfire_other),
      },
    },
    osm: {
      coverageStatus: event.osm_coverage_status,
      isFailedTile: event.osm_coverage_status === 'FAILED_TILE',
      failedTileMessage: 'OSM data was not retrieved for this area.',
      disclaimer: 'OpenStreetMap (OSM) information provides geographic context and is not ground truth.',
      facilityName: formatNullable(event.nearest_facility_name),
      facilityType: formatNullable(event.nearest_facility_type),
      facilityCategory: formatNullable(event.nearest_facility_category),
      facilityTier: formatNullable(event.nearest_facility_tier.replace(/_/g, ' ')),
      distanceFacility: formatDistance(event.distance_to_facility_m),
      distanceHigherRelevance: formatDistance(event.distance_to_higher_relevance_m),
      nearestHrCategory: formatNullable(event.nearest_hr_category),
    },
    landcover: {
      className: formatNullable(event.landcover_class),
      code: event.landcover_code,
    },
    sentinel2: {
      preStatus: formatNullable(event.pre_observation_status),
      postStatus: formatNullable(event.post_observation_status),
      changeStatus: formatNullable(event.s2_change_status),
      preNdvi: event.s2_pre_ndvi_mean !== null ? event.s2_pre_ndvi_mean.toFixed(3) : 'Unavailable',
      postNdvi: event.s2_post_ndvi_mean !== null ? event.s2_post_ndvi_mean.toFixed(3) : 'Unavailable',
      ndviDiff: formatNullable(ndviDiff),
      dnbr: event.s2_dnbr_mean !== null ? event.s2_dnbr_mean.toFixed(3) : 'Unavailable',
      disclaimer: 'Sentinel-2 provides optical surface and change evidence; it is not a thermal sensor.',
      isUnavailable: event.s2_change_status !== 'SUCCESS',
      unavailableExplanation:
        event.s2_change_status !== 'SUCCESS'
          ? 'Optical imagery may be unavailable due to satellite revisit timing (5-day constellation cycle), cloud/quality filtering, or missing suitable cloud-free observation pairs. Sentinel-2 provides optical surface/change evidence rather than active thermal detection; unavailability does not indicate absence of fire activity.'
          : '',
    },
    humanValidation: {
      hasValidation: event.has_human_validation,
      unvalidatedNotice: 'Not human validated',
      status: event.human_validation_status,
      groundTruthClass: formatNullable(event.human_ground_truth_class),
      certainty: event.is_unambiguous_ground_truth ? 'Unambiguous Ground Truth' : 'Ambiguous / Requires Review',
    },
    provenance: {
      modelVersion: event.model_version,
      modelSha256: event.model_sha256,
      dataSourceVersion: event.data_source_version,
      timestamp: event.inference_timestamp,
    },
  };
}
