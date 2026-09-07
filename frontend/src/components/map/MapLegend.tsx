import React from 'react';
import { CLASS_COLORS } from './EventMarker';
import type { ProductionClass } from '../../types/dashboard';

export interface MapLegendProps {
  totalEvents: number;
}

export const MapLegend: React.FC<MapLegendProps> = ({ totalEvents }) => {
  const classes: ProductionClass[] = [
    'Industrial Thermal Activity',
    'Agricultural Burning',
    'Natural / Wildfire / Other',
  ];

  return (
    <div className="map-legend">
      <div className="legend-header">
        <span className="legend-title">ML Prediction Classes</span>
        <span className="legend-count">{totalEvents} Events</span>
      </div>

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
                boxShadow: `0 0 6px ${CLASS_COLORS[cls]}88`,
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
  );
};
