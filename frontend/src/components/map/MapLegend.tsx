import React, { useState } from 'react';
import { CLASS_COLORS } from './EventMarker';
import type { ProductionClass } from '../../types/dashboard';

export interface MapLegendProps {
  totalEvents: number;
}

export const MapLegend: React.FC<MapLegendProps> = ({ totalEvents }) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(true);

  const classes: ProductionClass[] = [
    'Industrial Thermal Activity',
    'Agricultural Burning',
    'Natural / Wildfire / Other',
  ];

  return (
    <div
      className={`map-legend ${isExpanded ? 'expanded' : 'minimized'}`}
      onClick={!isExpanded ? () => setIsExpanded(true) : undefined}
      role={!isExpanded ? 'button' : undefined}
      tabIndex={!isExpanded ? 0 : undefined}
      onKeyDown={
        !isExpanded
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                setIsExpanded(true);
              }
            }
          : undefined
      }
      aria-label={!isExpanded ? 'Map Legend (minimized, click or press Enter to expand)' : undefined}
    >
      <div className="legend-header">
        <div className="legend-header-left">
          <span className="legend-title">ML Prediction Classes</span>
          <span className="legend-count">{totalEvents} Events</span>
        </div>
        <button
          type="button"
          className="legend-toggle-btn"
          onClick={(e) => {
            e.stopPropagation();
            setIsExpanded((prev) => !prev);
          }}
          aria-label={isExpanded ? 'Minimize map legend' : 'Expand map legend'}
          aria-expanded={isExpanded}
        >
          {isExpanded ? '▼' : '▲'}
        </button>
      </div>

      {isExpanded && (
        <div className="legend-body">
          <div className="legend-subtitle">
            Algorithmic Random Forest predictions. Not ground-truth labels.
          </div>

          <div className="legend-items">
            {classes.map((cls) => (
              <div key={cls} className="legend-item">
                <span
                  className="legend-dot"
                  style={{
                    backgroundColor: CLASS_COLORS[cls],
                    boxShadow: `0 0 5px ${CLASS_COLORS[cls]}88`,
                  }}
                />
                <span className="legend-label">{cls}</span>
              </div>
            ))}
          </div>

          <div className="legend-footer">
            <div className="legend-footer-item">
              <span className="legend-size-icon" />
              <span>Marker radius scales with Fire Radiative Power (FRP)</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
