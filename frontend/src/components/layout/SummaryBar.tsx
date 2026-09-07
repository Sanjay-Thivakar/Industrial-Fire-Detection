import React from 'react';
import type { KPIMetrics } from '../../utils/filterLogic.ts';

export interface SummaryBarProps {
  kpis: KPIMetrics;
  totalDatasetEvents: number;
}

export const SummaryBar: React.FC<SummaryBarProps> = ({ kpis, totalDatasetEvents }) => {
  const isFiltered = kpis.totalShown !== totalDatasetEvents;

  return (
    <div className="summary-bar" role="region" aria-label="Dataset Summary Metrics">
      {/* 1. Total Events */}
      <div className="kpi-card kpi-item kpi-total">
        <span className="kpi-label">Events:</span>
        <div className="kpi-value-group">
          <span className="kpi-value">{kpis.totalShown}</span>
          {isFiltered && <span className="kpi-subtext">of {totalDatasetEvents}</span>}
        </div>
      </div>

      <div className="kpi-divider" />

      {/* 2. Industrial Thermal */}
      <div className="kpi-card kpi-item kpi-industrial">
        <span className="kpi-dot dot-industrial" />
        <span className="kpi-label">Industrial:</span>
        <span className="kpi-value text-industrial">{kpis.industrialCount}</span>
      </div>

      <div className="kpi-divider" />

      {/* 3. Agricultural Burning */}
      <div className="kpi-card kpi-item kpi-agricultural">
        <span className="kpi-dot dot-agricultural" />
        <span className="kpi-label">Agricultural:</span>
        <span className="kpi-value text-agricultural">{kpis.agriculturalCount}</span>
      </div>

      <div className="kpi-divider" />

      {/* 4. Natural / Wildfire */}
      <div className="kpi-card kpi-item kpi-natural">
        <span className="kpi-dot dot-natural" />
        <span className="kpi-label">Natural:</span>
        <span className="kpi-value text-natural">{kpis.naturalCount}</span>
      </div>

      <div className="kpi-divider" />

      {/* 5. High ML Confidence */}
      <div className="kpi-card kpi-item kpi-high-conf">
        <span className="kpi-label">High Conf:</span>
        <span className="kpi-value text-high-conf">{kpis.highConfidenceCount}</span>
      </div>

      <div className="kpi-divider" />

      {/* 6. Avg FRP Intensity */}
      <div className="kpi-card kpi-item kpi-frp">
        <span className="kpi-label">Avg FRP:</span>
        <span className="kpi-value">{kpis.totalShown > 0 ? `${kpis.avgFrp} MW` : '—'}</span>
      </div>
    </div>
  );
};
