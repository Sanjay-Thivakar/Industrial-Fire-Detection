import React from 'react';
import type { KPIMetrics } from '../../utils/filterLogic.ts';

export interface SummaryBarProps {
  kpis: KPIMetrics;
  totalDatasetEvents: number;
}

export const SummaryBar: React.FC<SummaryBarProps> = ({ kpis, totalDatasetEvents }) => {
  const isFiltered = kpis.totalShown !== totalDatasetEvents;

  return (
    <div className="summary-bar">
      <div className="kpi-card kpi-total">
        <span className="kpi-label">Events Shown</span>
        <div className="kpi-value-group">
          <span className="kpi-value">{kpis.totalShown}</span>
          {isFiltered && <span className="kpi-subtext">of {totalDatasetEvents}</span>}
        </div>
      </div>

      <div className="kpi-divider" />

      <div className="kpi-card kpi-industrial">
        <div className="kpi-header">
          <span className="kpi-dot dot-industrial" />
          <span className="kpi-label">Industrial Thermal</span>
        </div>
        <span className="kpi-value text-industrial">{kpis.industrialCount}</span>
      </div>

      <div className="kpi-card kpi-agricultural">
        <div className="kpi-header">
          <span className="kpi-dot dot-agricultural" />
          <span className="kpi-label">Agricultural Burning</span>
        </div>
        <span className="kpi-value text-agricultural">{kpis.agriculturalCount}</span>
      </div>

      <div className="kpi-card kpi-natural">
        <div className="kpi-header">
          <span className="kpi-dot dot-natural" />
          <span className="kpi-label">Natural / Wildfire</span>
        </div>
        <span className="kpi-value text-natural">{kpis.naturalCount}</span>
      </div>

      <div className="kpi-divider" />

      <div className="kpi-card kpi-high-conf">
        <span className="kpi-label">High ML Confidence</span>
        <span className="kpi-value text-high-conf">{kpis.highConfidenceCount}</span>
      </div>

      <div className="kpi-card kpi-frp">
        <span className="kpi-label">Avg FRP Intensity</span>
        <span className="kpi-value">{kpis.totalShown > 0 ? `${kpis.avgFrp} MW` : '—'}</span>
      </div>
    </div>
  );
};
