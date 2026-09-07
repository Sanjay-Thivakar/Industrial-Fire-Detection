import React, { useState, useEffect } from 'react';
import { getModelFeatures } from '../../services/featureExtractor.ts';
import { predictEvent } from '../../services/apiClient.ts';
import { CLASS_COLORS } from '../map/EventMarker.tsx';
import { formatPercentage } from '../../utils/formatters.ts';
import { ApiError } from '../../types/api.ts';
import type { PredictResponse } from '../../types/api.ts';
import type { ProductionClass } from '../../types/dashboard.ts';

export interface LivePredictionCardProps {
  eventId: string;
  staticPredictedClass: string;
}

type CardState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; result: PredictResponse; latencyMs: number }
  | { status: 'error'; code: string; message: string };

export const LivePredictionCard: React.FC<LivePredictionCardProps> = ({
  eventId,
  staticPredictedClass,
}) => {
  const [state, setState] = useState<CardState>({ status: 'idle' });

  // Reset live prediction state whenever the selected event changes
  useEffect(() => {
    setState({ status: 'idle' });
  }, [eventId]);

  const handlePredict = async () => {
    setState({ status: 'loading' });
    const startTime = performance.now();

    try {
      // Step 1: Retrieve exact 36 baseline features from authoritative lookup (no approximation)
      const features = await getModelFeatures(eventId);

      // Step 2: Dispatch request to FastAPI via Vite proxy (zero browser keys)
      const result = await predictEvent({
        event_id: eventId,
        features,
      });

      const latencyMs = Math.round(performance.now() - startTime);

      setState({
        status: 'success',
        result,
        latencyMs,
      });
    } catch (err: any) {
      let code = 'INFERENCE_ERROR';
      let message = 'An unexpected error occurred during live prediction.';

      if (err instanceof ApiError) {
        code = err.code;
        message = err.message;
      } else if (err?.message) {
        message = err.message;
      }

      setState({
        status: 'error',
        code,
        message,
      });
    }
  };

  return (
    <div className="live-prediction-section">
      <div className="live-prediction-header">
        <span className="live-badge-tag">FASTAPI MICROSERVICE</span>
        <h4 className="live-section-title">Live ML Inference Engine</h4>
      </div>

      {state.status === 'idle' && (
        <div className="live-idle-box">
          <p className="live-idle-desc">
            Re-evaluate this thermal event in real time against the production Random Forest model
            via the FastAPI backend.
          </p>
          <button
            type="button"
            className="btn-live-predict"
            onClick={handlePredict}
            aria-label="Re-predict via Live FastAPI Service"
          >
            ⚡ Re-predict via Live FastAPI Service
          </button>
        </div>
      )}

      {state.status === 'loading' && (
        <div className="live-loading-box">
          <div className="mini-spinner" />
          <span>Running live prediction…</span>
          <button type="button" className="btn-live-predict disabled" disabled>
            ⚡ Re-predict via Live FastAPI Service
          </button>
        </div>
      )}

      {state.status === 'error' && (
        <div className="live-error-box">
          <div className="live-error-header">
            <span className="live-error-icon">⚠️</span>
            <span className="live-error-title">Inference Failed</span>
          </div>
          <div className="live-error-code">Code: {state.code}</div>
          <p className="live-error-message">{state.message}</p>
          <button
            type="button"
            className="btn-retry-predict"
            onClick={handlePredict}
            aria-label="Retry live prediction"
          >
            🔄 Retry Live Prediction
          </button>
        </div>
      )}

      {state.status === 'success' && (
        <div className="live-result-card">
          <div className="live-result-header">
            <div className="live-result-pill">
              <span className="pulse-dot-live" />
              <span>Live API Result</span>
            </div>
            <div
              className={`live-match-indicator ${
                state.result.predicted_class === staticPredictedClass ? 'match-yes' : 'match-no'
              }`}
            >
              {state.result.predicted_class === staticPredictedClass
                ? 'Matches Baseline: Yes'
                : 'Matches Baseline: No'}
            </div>
          </div>

          <div className="live-class-banner">
            <div className="live-class-label">API Predicted Class</div>
            <div className="live-class-name">{state.result.predicted_class}</div>
          </div>

          <div className="live-metrics-row">
            <div className="live-metric-item">
              <span className="live-metric-label">Max Probability</span>
              <span className="live-metric-val font-mono">
                {formatPercentage(state.result.max_probability)}
              </span>
            </div>
            <div className="live-metric-item">
              <span className="live-metric-label">ML Confidence</span>
              <span
                className={`live-metric-val tier-${state.result.ml_confidence.toLowerCase()}`}
              >
                {state.result.ml_confidence}
              </span>
            </div>
            <div className="live-metric-item">
              <span className="live-metric-label">Inference Latency</span>
              <span className="live-metric-val font-mono text-cyan">
                API latency: {state.latencyMs} ms
              </span>
            </div>
          </div>

          {/* Three class probability bars */}
          <div className="live-bars-container">
            <div className="live-bars-title">Live Probability Distribution:</div>
            {(
              [
                'Industrial Thermal Activity',
                'Agricultural Burning',
                'Natural / Wildfire / Other',
              ] as const
            ).map((className: ProductionClass) => {
              const prob = state.result.probabilities[className] ?? 0;
              const isWinning = state.result.predicted_class === className;
              const color = CLASS_COLORS[className];
              const percentWidth = Math.min(100, Math.max(0, prob * 100));

              return (
                <div key={className} className={`prob-row ${isWinning ? 'winning-row' : ''}`}>
                  <div className="prob-label-group">
                    <span className="prob-name">
                      <span className="prob-indicator-dot" style={{ backgroundColor: color }} />
                      {className}
                      {isWinning && <span className="winning-tag">LIVE PREDICTION</span>}
                    </span>
                    <span
                      className="prob-value"
                      style={{ color: isWinning ? color : '#cbd5e1' }}
                    >
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

          {/* Live Provenance Details */}
          <div className="live-provenance-meta">
            <div>
              <span className="meta-label">Inference Timestamp:</span>{' '}
              <span className="meta-val">{state.result.inference_timestamp}</span>
            </div>
            <div>
              <span className="meta-label">Model Version:</span>{' '}
              <span className="meta-val font-mono">{state.result.model.version}</span>
            </div>
            <div>
              <span className="meta-label">Model SHA-256:</span>{' '}
              <span className="meta-val font-mono text-xs">{state.result.model.sha256}</span>
            </div>
          </div>

          {/* Mandatory Scientific Disclaimer */}
          <div className="live-disclaimer">
            ⚠️ {state.result.disclaimer || 'Prediction is an algorithmic ML estimate. It is not ground truth.'}
          </div>

          <div className="live-actions-bar">
            <button
              type="button"
              className="btn-live-repredict"
              onClick={handlePredict}
              aria-label="Re-run live prediction"
            >
              🔄 Re-run Live Prediction
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
