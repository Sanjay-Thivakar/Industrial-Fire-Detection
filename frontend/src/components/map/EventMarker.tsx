import React from 'react';
import { CircleMarker, Popup } from 'react-leaflet';
import type { DashboardEvent, ProductionClass } from '../../types/dashboard';

export interface EventMarkerProps {
  event: DashboardEvent;
  isSelected?: boolean;
  onSelect?: (event: DashboardEvent) => void;
  suppressPopup?: boolean;
}

export const CLASS_COLORS: Record<ProductionClass, string> = {
  'Industrial Thermal Activity': '#ef4444', // Crimson red
  'Agricultural Burning': '#f59e0b',        // Harvest amber
  'Natural / Wildfire / Other': '#10b981',  // Forest emerald
};

export const CONFIDENCE_BADGE_COLORS: Record<string, { bg: string; text: string }> = {
  HIGH: { bg: 'rgba(16, 185, 129, 0.2)', text: '#34d399' },
  MEDIUM: { bg: 'rgba(245, 158, 11, 0.2)', text: '#fbbf24' },
  LOW: { bg: 'rgba(239, 68, 68, 0.2)', text: '#f87171' },
};

export const EventMarker: React.FC<EventMarkerProps> = ({
  event,
  isSelected,
  onSelect,
  suppressPopup = false,
}) => {
  const color = CLASS_COLORS[event.predicted_class] || '#94a3b8';
  
  // Calculate dynamic radius scaled by FRP
  const radius = Math.min(10, Math.max(4, 3 + Math.sqrt(event.frp) * 1.2));
  
  const strokeColor = isSelected ? '#ffffff' : color;
  const strokeWeight = isSelected ? 3 : event.ml_confidence === 'HIGH' ? 2 : 1;
  const fillOpacity = isSelected ? 0.95 : 0.75;

  const eventHandlers = {
    click: () => {
      if (onSelect) {
        onSelect(event);
      }
    },
  };

  const confStyle = CONFIDENCE_BADGE_COLORS[event.ml_confidence] || CONFIDENCE_BADGE_COLORS.MEDIUM;

  return (
    <CircleMarker
      center={[event.latitude, event.longitude]}
      radius={radius}
      pathOptions={{
        color: strokeColor,
        fillColor: color,
        fillOpacity: fillOpacity,
        weight: strokeWeight,
      }}
      eventHandlers={eventHandlers}
    >
      {!suppressPopup && (
        <Popup className="event-marker-popup">
        <div style={{ padding: '4px', minWidth: '220px', color: '#0f172a', fontFamily: 'sans-serif' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
            <strong style={{ fontSize: '13px', color: '#0f172a' }}>{event.event_id}</strong>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 600,
                padding: '2px 6px',
                borderRadius: '4px',
                background: confStyle.bg,
                color: confStyle.text,
              }}
            >
              {event.ml_confidence}
            </span>
          </div>

          <div style={{ fontSize: '12px', marginBottom: '4px', color: '#475569' }}>
            <strong>Date/Time:</strong> {event.acq_date} {String(event.acq_time).padStart(4, '0')} UTC
          </div>

          <div style={{ fontSize: '12px', marginBottom: '4px', color: '#475569' }}>
            <strong>ML Class:</strong>{' '}
            <span style={{ color, fontWeight: 600 }}>{event.predicted_class}</span>
          </div>

          <div style={{ fontSize: '12px', marginBottom: '4px', color: '#475569' }}>
            <strong>Winning Prob:</strong> {(event.max_probability * 100).toFixed(1)}%
          </div>

          <div style={{ fontSize: '12px', marginBottom: '6px', color: '#475569' }}>
            <strong>Satellite Conf:</strong>{' '}
            <span style={{ textTransform: 'uppercase', fontWeight: 600 }}>
              {event.firms_confidence === 'h' ? 'High (h)' : event.firms_confidence === 'n' ? 'Nominal (n)' : 'Low (l)'}
            </span>
          </div>

          <div
            style={{
              fontSize: '10px',
              fontStyle: 'italic',
              color: '#64748b',
              borderTop: '1px solid #e2e8f0',
              paddingTop: '4px',
              marginTop: '4px',
            }}
          >
            Algorithmic ML estimate &bull; Not ground truth
          </div>
        </div>
      </Popup>
      )}
    </CircleMarker>
  );
};
