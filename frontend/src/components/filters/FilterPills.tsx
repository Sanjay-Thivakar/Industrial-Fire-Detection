import React from 'react';
import type { FilterCriteria } from '../../types/filters.ts';
import type { ProductionClass, ConfidenceTier, FirmsConfidence, FacilityTier, S2ChangeStatus } from '../../types/dashboard.ts';

export interface FilterPillsProps {
  filters: FilterCriteria;
  onRemoveClass: (cls: ProductionClass) => void;
  onRemoveMlConf: (conf: ConfidenceTier) => void;
  onRemoveFirmsConf: (conf: FirmsConfidence) => void;
  onRemoveLandcover: (lc: string) => void;
  onRemoveFacilityTier: (tier: FacilityTier) => void;
  onRemoveS2Status: (status: S2ChangeStatus) => void;
  onRemovePersistence: () => void;
  onResetFrp: () => void;
  onClearAll: () => void;
  isFiltered: boolean;
}

const getClassModifier = (cls: ProductionClass): string => {
  switch (cls) {
    case 'Industrial Thermal Activity':
      return 'pill-class-industrial';
    case 'Agricultural Burning':
      return 'pill-class-agricultural';
    case 'Natural / Wildfire / Other':
      return 'pill-class-natural';
    default:
      return '';
  }
};

export const FilterPills: React.FC<FilterPillsProps> = ({
  filters,
  onRemoveClass,
  onRemoveMlConf,
  onRemoveFirmsConf,
  onRemoveLandcover,
  onRemoveFacilityTier,
  onRemoveS2Status,
  onRemovePersistence,
  onResetFrp,
  onClearAll,
  isFiltered,
}) => {
  if (!isFiltered) return null;

  return (
    <div className="filter-pills-bar">
      <div className="pills-scroll-container">
        {filters.classes.map((cls) => (
          <span key={`class-${cls}`} className={`filter-pill pill-class ${getClassModifier(cls)}`}>
            <span>Class: {cls}</span>
            <button type="button" className="pill-remove-btn" onClick={() => onRemoveClass(cls)}>
              &times;
            </button>
          </span>
        ))}

        {filters.mlConfidenceTiers.map((tier) => (
          <span key={`ml-conf-${tier}`} className="filter-pill pill-ml-conf">
            <span>ML Conf: {tier}</span>
            <button type="button" className="pill-remove-btn" onClick={() => onRemoveMlConf(tier)}>
              &times;
            </button>
          </span>
        ))}

        {filters.firmsConfidences.map((conf) => (
          <span key={`firms-conf-${conf}`} className="filter-pill pill-firms-conf">
            <span>Satellite: {conf === 'h' ? 'High' : conf === 'n' ? 'Nominal' : 'Low'}</span>
            <button type="button" className="pill-remove-btn" onClick={() => onRemoveFirmsConf(conf)}>
              &times;
            </button>
          </span>
        ))}

        {filters.onlyPersistentHotspots && (
          <span className="filter-pill pill-persistence">
            <span>Multi-day Hotspots Only</span>
            <button type="button" className="pill-remove-btn" onClick={onRemovePersistence}>
              &times;
            </button>
          </span>
        )}

        {(filters.frpMin > 0 || filters.frpMax < 20) && (
          <span className="filter-pill pill-frp">
            <span>FRP: {filters.frpMin} - {filters.frpMax} MW</span>
            <button type="button" className="pill-remove-btn" onClick={onResetFrp}>
              &times;
            </button>
          </span>
        )}

        {filters.facilityTiers.map((tier) => (
          <span key={`fac-tier-${tier}`} className="filter-pill pill-facility">
            <span>OSM Tier: {tier.replace(/_/g, ' ')}</span>
            <button type="button" className="pill-remove-btn" onClick={() => onRemoveFacilityTier(tier)}>
              &times;
            </button>
          </span>
        ))}

        {filters.landcoverClasses.map((lc) => (
          <span key={`lc-${lc}`} className="filter-pill pill-landcover">
            <span>Land: {lc}</span>
            <button type="button" className="pill-remove-btn" onClick={() => onRemoveLandcover(lc)}>
              &times;
            </button>
          </span>
        ))}

        {filters.s2Statuses.map((s2) => (
          <span key={`s2-${s2}`} className="filter-pill pill-s2">
            <span>S2: {s2}</span>
            <button type="button" className="pill-remove-btn" onClick={() => onRemoveS2Status(s2)}>
              &times;
            </button>
          </span>
        ))}

        <button type="button" className="clear-all-pills-btn" onClick={onClearAll}>
          Clear all
        </button>
      </div>
    </div>
  );
};
