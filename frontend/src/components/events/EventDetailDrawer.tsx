import React, { useEffect } from 'react';
import type { DashboardEvent } from '../../types/dashboard.ts';
import { DetailSection } from './DetailSection.tsx';
import { ProbabilityBars } from './ProbabilityBars.tsx';
import { LivePredictionCard } from './LivePredictionCard.tsx';
import {
  formatCoord,
  formatFrp,
  formatKelvin,
  formatDistance,
  formatPercentage,
  formatNullable,
} from '../../utils/formatters.ts';

export interface EventDetailDrawerProps {
  event: DashboardEvent | null;
  onClose: () => void;
}

export const EventDetailDrawer: React.FC<EventDetailDrawerProps> = ({ event, onClose }) => {
  // Listen for Escape key to dismiss drawer
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [onClose]);

  if (!event) return null;

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

  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} aria-hidden="true" />

      <aside className="event-detail-drawer" aria-label="Event Details Inspector">
        {/* Drawer Header */}
        <div className="drawer-header">
          <div className="drawer-header-info">
            <span className="drawer-event-tag">THERMAL ANOMALY</span>
            <h2 className="drawer-title">{event.event_id}</h2>
            <div className="drawer-datetime">
              {event.acq_date} &bull; {String(event.acq_time).padStart(4, '0')} UTC
            </div>
          </div>
          <button
            type="button"
            className="drawer-close-btn"
            onClick={onClose}
            aria-label="Close detail drawer"
          >
            &times;
          </button>
        </div>

        {/* Drawer Scrollable Content */}
        <div className="drawer-content">
          {/* SECTION A: EVENT IDENTITY */}
          <DetailSection title="Event Identity" icon="📍">
            <div className="detail-grid">
              <div className="detail-item">
                <span className="detail-label">Event ID</span>
                <span className="detail-value font-mono">{event.event_id}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Acquisition Date & Time</span>
                <span className="detail-value">{event.acq_datetime || `${event.acq_date} ${event.acq_time}`}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Latitude</span>
                <span className="detail-value">{formatCoord(event.latitude)}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Longitude</span>
                <span className="detail-value">{formatCoord(event.longitude)}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Satellite / Instrument</span>
                <span className="detail-value">{event.satellite} / {event.instrument}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">FIRMS Detection Confidence</span>
                <span className={`detail-value badge-tier conf-${event.firms_confidence}`}>
                  {firmsConfLabel}
                </span>
              </div>
            </div>
          </DetailSection>

          {/* SECTION B: FIRMS THERMAL DETECTION */}
          <DetailSection title="FIRMS Thermal Detection" icon="🔥">
            <div className="detail-grid">
              <div className="detail-item highlight-item">
                <span className="detail-label">Fire Radiative Power (FRP)</span>
                <span className="detail-value text-frp">{formatFrp(event.frp)}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Brightness (I4 Channel)</span>
                <span className="detail-value">{formatKelvin(event.brightness)}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Brightness T31 (I5 Background)</span>
                <span className="detail-value">{formatKelvin(event.bright_t31)}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Day / Night Overpass</span>
                <span className="detail-value">
                  {event.daynight === 'D' ? '☀️ Daytime (D)' : '🌙 Nighttime (N)'}
                </span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Grid Active Days</span>
                <span className="detail-value">{event.grid_active_days} days</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Grid Detection Count</span>
                <span className="detail-value">{event.grid_detection_count} detections</span>
              </div>
              <div className="detail-item full-width">
                <span className="detail-label">Multi-day Persistent Hotspots</span>
                <span className="detail-value">
                  {event.persistent_location_flag === 1 ? (
                    <span className="tag-persistent">● Multi-day Persistent Thermal Source</span>
                  ) : (
                    <span className="tag-transient">Transient Anomaly</span>
                  )}
                </span>
              </div>
            </div>
          </DetailSection>

          {/* SECTION C: ML PREDICTION */}
          <DetailSection
            title="ML Prediction"
            icon="🧠"
            disclaimer="Prediction is an algorithmic ML estimate. It is not ground truth."
          >
            <div className="ml-prediction-card">
              <div className="ml-primary-badge">
                <span className="ml-primary-label">Predicted Class</span>
                <div className="ml-class-title">{event.predicted_class}</div>
              </div>

              <div className="ml-metrics-row">
                <div className="ml-metric-box">
                  <span className="metric-box-label">Winning Probability</span>
                  <span className="metric-box-value">{formatPercentage(event.max_probability)}</span>
                </div>
                <div className="ml-metric-box">
                  <span className="metric-box-label">ML Confidence</span>
                  <span className={`metric-box-value tier-${event.ml_confidence.toLowerCase()}`}>
                    {event.ml_confidence}
                  </span>
                </div>
              </div>

              <div className="ml-bars-wrapper">
                <span className="ml-bars-heading">Class Probability Distribution</span>
                <ProbabilityBars event={event} />
              </div>
            </div>

            {/* LIVE API INFERENCE EXTENSION */}
            <LivePredictionCard
              eventId={event.event_id}
              staticPredictedClass={event.predicted_class}
            />
          </DetailSection>

          {/* SECTION D: OSM INDUSTRIAL CONTEXT */}
          <DetailSection
            title="OSM Industrial Context"
            icon="🏭"
            disclaimer="OpenStreetMap (OSM) information provides geographic context and is not ground truth."
          >
            {event.osm_coverage_status === 'FAILED_TILE' ? (
              <div className="failed-tile-banner">
                ⚠️ OSM data was not retrieved for this area.
              </div>
            ) : (
              <div className="detail-grid">
                <div className="detail-item full-width">
                  <span className="detail-label">Nearest Facility Name</span>
                  <span className="detail-value font-semibold">
                    {formatNullable(event.nearest_facility_name)}
                  </span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Facility Type</span>
                  <span className="detail-value">{formatNullable(event.nearest_facility_type)}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Facility Category</span>
                  <span className="detail-value">{formatNullable(event.nearest_facility_category)}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Facility Relevance Tier</span>
                  <span className="detail-value">{formatNullable(event.nearest_facility_tier.replace(/_/g, ' '))}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Distance to Nearest Facility</span>
                  <span className="detail-value">{formatDistance(event.distance_to_facility_m)}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Distance to High-Relevance Facility</span>
                  <span className="detail-value">{formatDistance(event.distance_to_higher_relevance_m)}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Nearest High-Relevance Category</span>
                  <span className="detail-value">{formatNullable(event.nearest_hr_category)}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">OSM Coverage Status</span>
                  <span className="detail-value text-covered">{event.osm_coverage_status}</span>
                </div>
              </div>
            )}
          </DetailSection>

          {/* SECTION E: LAND COVER */}
          <DetailSection title="Land Cover Context" icon="🌍">
            <div className="detail-grid">
              <div className="detail-item">
                <span className="detail-label">ESA WorldCover Class</span>
                <span className="detail-value font-semibold">{formatNullable(event.landcover_class)}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">WorldCover Code</span>
                <span className="detail-value">{event.landcover_code}</span>
              </div>
            </div>
          </DetailSection>

          {/* SECTION F: SENTINEL-2 OPTICAL CONTEXT */}
          <DetailSection
            title="Sentinel-2 Optical Context"
            icon="🛰️"
            disclaimer="Sentinel-2 provides optical surface and change evidence; it is not a thermal sensor."
          >
            <div className="detail-grid">
              <div className="detail-item">
                <span className="detail-label">Pre-Fire Observation</span>
                <span className="detail-value">{formatNullable(event.pre_observation_status)}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Post-Fire Observation</span>
                <span className="detail-value">{formatNullable(event.post_observation_status)}</span>
              </div>
              <div className="detail-item full-width">
                <span className="detail-label">Change Analysis Status</span>
                <span className="detail-value font-semibold">{formatNullable(event.s2_change_status)}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Pre-Fire NDVI Mean</span>
                <span className="detail-value">
                  {event.s2_pre_ndvi_mean !== null ? event.s2_pre_ndvi_mean.toFixed(3) : 'Unavailable'}
                </span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Post-Fire NDVI Mean</span>
                <span className="detail-value">
                  {event.s2_post_ndvi_mean !== null ? event.s2_post_ndvi_mean.toFixed(3) : 'Unavailable'}
                </span>
              </div>
              <div className="detail-item">
                <span className="detail-label">NDVI Change (Post - Pre)</span>
                <span className="detail-value">{formatNullable(ndviDiff)}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Burn Severity (dNBR Mean)</span>
                <span className="detail-value">
                  {event.s2_dnbr_mean !== null ? event.s2_dnbr_mean.toFixed(3) : 'Unavailable'}
                </span>
              </div>
            </div>

            {event.s2_change_status !== 'SUCCESS' && (
              <div className="s2-unavailable-notice" data-testid="s2-unavailable-notice">
                <div className="s2-notice-title">Optical Imagery Context</div>
                <div className="s2-notice-text">
                  Optical imagery may be unavailable due to Sentinel-2 satellite revisit timing (5-day constellation cycle), cloud/quality filtering, or missing suitable cloud-free observation pairs. Sentinel-2 provides optical surface/change evidence rather than active thermal detection; unavailability of optical imagery does not indicate absence of fire activity.
                </div>
              </div>
            )}
          </DetailSection>

          {/* SECTION G: HUMAN VALIDATION */}
          <DetailSection title="Human Expert Ground Truth" icon="📋">
            {event.has_human_validation ? (
              <div className="detail-grid">
                <div className="detail-item">
                  <span className="detail-label">Human Validation Status</span>
                  <span className="detail-value badge-validated">{event.human_validation_status}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Validation Confidence</span>
                  <span className="detail-value">
                    {event.is_unambiguous_ground_truth
                      ? 'Unambiguous Ground Truth'
                      : 'Ambiguous / Requires Review'}
                  </span>
                </div>
                <div className="detail-item full-width">
                  <span className="detail-label">Expert Ground-Truth Class</span>
                  <span className="detail-value font-semibold text-human-class">
                    {formatNullable(event.human_ground_truth_class)}
                  </span>
                </div>
              </div>
            ) : (
              <div className="unvalidated-card">
                <div className="unvalidated-title">Not human validated</div>
                <div className="unvalidated-text">
                  This thermal event has not undergone independent expert ground-truth validation.
                  Displayed classifications reflect automated ML estimates.
                </div>
              </div>
            )}
          </DetailSection>

          {/* SECTION H: DATA PROVENANCE */}
          <DetailSection title="Data Provenance & Audit Trail" icon="🔒">
            <div className="detail-grid">
              <div className="detail-item full-width">
                <span className="detail-label">Model Version</span>
                <span className="detail-value font-mono text-xs">{event.model_version}</span>
              </div>
              <div className="detail-item full-width">
                <span className="detail-label">Model SHA-256 Digest</span>
                <span className="detail-value font-mono text-xs text-break">{event.model_sha256}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Data Source Version</span>
                <span className="detail-value font-mono text-xs">{event.data_source_version}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Inference Timestamp</span>
                <span className="detail-value text-xs">{event.inference_timestamp}</span>
              </div>
            </div>
          </DetailSection>
        </div>
      </aside>
    </>
  );
};
