import React, { useState } from 'react';
import type { FilterCriteria } from '../../types/filters.ts';
import type {
  ProductionClass,
  ConfidenceTier,
  FirmsConfidence,
  FacilityTier,
  S2ChangeStatus,
} from '../../types/dashboard.ts';

export interface FilterPanelProps {
  filters: FilterCriteria;
  onToggleClass: (cls: ProductionClass) => void;
  onToggleMlConf: (tier: ConfidenceTier) => void;
  onToggleFirmsConf: (conf: FirmsConfidence) => void;
  onToggleLandcover: (lc: string) => void;
  onToggleFacilityTier: (tier: FacilityTier) => void;
  onToggleS2Status: (status: S2ChangeStatus) => void;
  onTogglePersistence: (enabled: boolean) => void;
  onSetFrpMax: (max: number) => void;
  onResetFilters: () => void;
  isFiltered: boolean;
  totalMatches: number;
}

const PRODUCTION_CLASSES: readonly ProductionClass[] = [
  'Industrial Thermal Activity',
  'Agricultural Burning',
  'Natural / Wildfire / Other',
];

const ML_CONFIDENCE_TIERS: readonly ConfidenceTier[] = ['HIGH', 'MEDIUM', 'LOW'];

const FIRMS_CONFIDENCES: readonly { value: FirmsConfidence; label: string }[] = [
  { value: 'h', label: 'High (h)' },
  { value: 'n', label: 'Nominal (n)' },
  { value: 'l', label: 'Low (l)' },
];

const LANDCOVER_OPTIONS: readonly string[] = [
  'Built-up',
  'Cropland',
  'Tree cover',
  'Shrubland',
  'Grassland',
  'Bare/sparse vegetation',
];

const FACILITY_TIER_OPTIONS: readonly { value: FacilityTier; label: string }[] = [
  { value: 'HIGHER_RELEVANCE', label: 'Higher Relevance (Metals, Chemical, Power)' },
  { value: 'CAUTION_LOWER_RELEVANCE', label: 'Caution Lower Relevance' },
  { value: 'GENERAL_CONTEXT', label: 'General Context' },
];

const S2_STATUS_OPTIONS: readonly { value: S2ChangeStatus; label: string }[] = [
  { value: 'SUCCESS', label: 'Analysis Succeeded (80 events)' },
  { value: 'MISSING_POST', label: 'Missing Post-Image' },
  { value: 'MISSING_PRE', label: 'Missing Pre-Image' },
  { value: 'CLOUD_REJECTED', label: 'Cloud Rejected' },
  { value: 'INSUFFICIENT_VALID_DATA', label: 'Insufficient Valid Data' },
];

export const FilterPanel: React.FC<FilterPanelProps> = ({
  filters,
  onToggleClass,
  onToggleMlConf,
  onToggleFirmsConf,
  onToggleLandcover,
  onToggleFacilityTier,
  onToggleS2Status,
  onTogglePersistence,
  onSetFrpMax,
  onResetFilters,
  isFiltered,
  totalMatches,
}) => {
  const [isOpen, setIsOpen] = useState(true);

  return (
    <aside className={`filter-sidebar ${isOpen ? 'open' : 'collapsed'}`}>
      <div className="filter-header">
        {isOpen && (
          <div className="filter-header-title">
            <h3>Multi-Facet Filters</h3>
            <span className="match-pill">{totalMatches} Events</span>
          </div>
        )}
        <div className="filter-header-actions">
          {isOpen && isFiltered && (
            <button type="button" className="reset-filter-btn" onClick={onResetFilters}>
              Reset
            </button>
          )}
          <button
            type="button"
            className="toggle-sidebar-btn"
            onClick={() => setIsOpen(!isOpen)}
            title={isOpen ? 'Collapse Filters' : 'Expand Filters'}
            aria-label={isOpen ? 'Collapse Filters' : 'Expand Filters'}
          >
            {isOpen ? '◀' : '▶'}
          </button>
        </div>
      </div>

      {isOpen && (
        <div className="filter-body">
          {/* Section 1: ML Predicted Class */}
          <div className="filter-section">
            <h4 className="section-title">ML Prediction Class</h4>
            <div className="checkbox-group">
              {PRODUCTION_CLASSES.map((cls) => (
                <label key={cls} className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={filters.classes.includes(cls)}
                    onChange={() => onToggleClass(cls)}
                  />
                  <span className={`class-indicator class-${cls.toLowerCase().replace(/[^a-z0-9]/g, '-')}`} />
                  <span className="label-text">{cls}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Section 2: ML Confidence Tier */}
          <div className="filter-section">
            <h4 className="section-title">ML Confidence Tier</h4>
            <div className="checkbox-group inline-group">
              {ML_CONFIDENCE_TIERS.map((tier) => (
                <label key={tier} className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={filters.mlConfidenceTiers.includes(tier)}
                    onChange={() => onToggleMlConf(tier)}
                  />
                  <span className={`tier-tag tier-${tier.toLowerCase()}`}>{tier}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Section 3: FIRMS Satellite Sensor Confidence */}
          <div className="filter-section">
            <h4 className="section-title">Satellite Sensor Certainty</h4>
            <div className="checkbox-group inline-group">
              {FIRMS_CONFIDENCES.map(({ value, label }) => (
                <label key={value} className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={filters.firmsConfidences.includes(value)}
                    onChange={() => onToggleFirmsConf(value)}
                  />
                  <span className="label-text">{label}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Section 4: Spatial Persistence */}
          <div className="filter-section">
            <h4 className="section-title">Spatial Persistence</h4>
            <label className="checkbox-label toggle-label">
              <input
                type="checkbox"
                checked={filters.onlyPersistentHotspots}
                onChange={(e) => onTogglePersistence(e.target.checked)}
              />
              <span className="label-text">
                Multi-day Persistent Hotspots
              </span>
            </label>
          </div>

          {/* Section 5: FRP Range Filter */}
          <div className="filter-section">
            <div className="frp-header">
              <h4 className="section-title">Max Fire Radiative Power (FRP)</h4>
              <span className="frp-value">{filters.frpMax} MW</span>
            </div>
            <input
              type="range"
              min="1"
              max="20"
              step="0.5"
              value={filters.frpMax}
              onChange={(e) => onSetFrpMax(parseFloat(e.target.value))}
              className="frp-slider"
            />
            <div className="slider-ticks">
              <span>1 MW</span>
              <span>10 MW</span>
              <span>20 MW</span>
            </div>
          </div>

          {/* Section 6: ESA WorldCover */}
          <div className="filter-section">
            <h4 className="section-title">WorldCover Land Surface</h4>
            <div className="checkbox-group">
              {LANDCOVER_OPTIONS.map((lc) => (
                <label key={lc} className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={filters.landcoverClasses.includes(lc)}
                    onChange={() => onToggleLandcover(lc)}
                  />
                  <span className="label-text">{lc}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Section 7: OSM Industrial Proximity Tier */}
          <div className="filter-section">
            <h4 className="section-title">OSM Proximity Relevance</h4>
            <div className="checkbox-group">
              {FACILITY_TIER_OPTIONS.map(({ value, label }) => (
                <label key={value} className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={filters.facilityTiers.includes(value)}
                    onChange={() => onToggleFacilityTier(value)}
                  />
                  <span className="label-text text-sm">{label}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Section 8: Sentinel-2 Optical Change Status */}
          <div className="filter-section">
            <h4 className="section-title">Sentinel-2 Optical Status</h4>
            <div className="checkbox-group">
              {S2_STATUS_OPTIONS.map(({ value, label }) => (
                <label key={value} className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={filters.s2Statuses.includes(value)}
                    onChange={() => onToggleS2Status(value)}
                  />
                  <span className="label-text text-sm">{label}</span>
                </label>
              ))}
            </div>
          </div>
        </div>
      )}
    </aside>
  );
};
