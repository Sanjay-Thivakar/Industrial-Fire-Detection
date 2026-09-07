import React from 'react';
import type { DashboardEvent } from '../../types/dashboard.ts';
import { CLASS_COLORS } from '../map/EventMarker.tsx';
import { formatPercentage } from '../../utils/formatters.ts';

export interface ProbabilityBarsProps {
  event: DashboardEvent;
}

export const ProbabilityBars: React.FC<ProbabilityBarsProps> = ({ event }) => {
  const classesData = [
    {
      name: 'Industrial Thermal Activity' as const,
      prob: event.probability_industrial_thermal_activity,
      color: CLASS_COLORS['Industrial Thermal Activity'],
    },
    {
      name: 'Agricultural Burning' as const,
      prob: event.probability_agricultural_burning,
      color: CLASS_COLORS['Agricultural Burning'],
    },
    {
      name: 'Natural / Wildfire / Other' as const,
      prob: event.probability_natural_wildfire_other,
      color: CLASS_COLORS['Natural / Wildfire / Other'],
    },
  ];

  return (
    <div className="probability-bars-container">
      {classesData.map(({ name, prob, color }) => {
        const isWinning = event.predicted_class === name;
        const percentWidth = Math.min(100, Math.max(0, prob * 100));

        return (
          <div key={name} className={`prob-row ${isWinning ? 'winning-row' : ''}`}>
            <div className="prob-label-group">
              <span className="prob-name">
                <span className="prob-indicator-dot" style={{ backgroundColor: color }} />
                {name}
                {isWinning && <span className="winning-tag">PREDICTED</span>}
              </span>
              <span className="prob-value" style={{ color: isWinning ? color : '#cbd5e1' }}>
                {formatPercentage(prob)}
              </span>
            </div>

            <div className="prob-track">
              <div
                className="prob-fill"
                style={{
                  width: `${percentWidth}%`,
                  backgroundColor: color,
                  boxShadow: isWinning ? `0 0 8px ${color}88` : 'none',
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
};
