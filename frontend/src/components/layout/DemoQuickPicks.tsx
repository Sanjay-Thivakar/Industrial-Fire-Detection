import React from 'react';
import type { DashboardEvent } from '../../types/dashboard.ts';
import { DEMO_QUICK_PICK_EVENTS } from '../../utils/quickPickEvents.ts';
export type { DemoEventDef } from '../../utils/quickPickEvents.ts';
export { DEMO_QUICK_PICK_EVENTS };

export interface DemoQuickPicksProps {
  events: DashboardEvent[];
  filteredEvents: DashboardEvent[];
  selectedEventId: string | null;
  onSelectEvent: (event: DashboardEvent) => void;
  onResetFilters?: () => void;
  onNotice?: (message: string | null) => void;
}

export const DemoQuickPicks: React.FC<DemoQuickPicksProps> = ({
  events,
  filteredEvents,
  selectedEventId,
  onSelectEvent,
  onResetFilters,
  onNotice,
}) => {
  const handleSelect = (eventId: string) => {
    const target = events.find((e) => e.event_id === eventId);
    if (!target) return;

    const isHiddenByFilters = !filteredEvents.some((e) => e.event_id === eventId);
    if (isHiddenByFilters) {
      if (onResetFilters) {
        onResetFilters();
      }
      if (onNotice) {
        onNotice(`Active filters were reset to display demo event ${eventId} on the map.`);
      }
    } else {
      if (onNotice) {
        onNotice(null);
      }
    }

    onSelectEvent(target);
  };

  return (
    <div className="demo-quick-picks" role="region" aria-label="Demo Quick Picks">
      <div className="quick-pick-header">
        <span className="quick-pick-icon">⚡</span>
        <span className="quick-pick-title">Demo Quick Picks:</span>
      </div>
      <div className="quick-pick-list">
        {DEMO_QUICK_PICK_EVENTS.map((item) => {
          const isSelected = selectedEventId === item.id;
          const isFilteredOut = !filteredEvents.some((e) => e.event_id === item.id);

          return (
            <button
              key={item.id}
              type="button"
              className={`quick-pick-btn ${isSelected ? 'active' : ''} ${
                isFilteredOut ? 'filtered-out' : ''
              }`}
              onClick={() => handleSelect(item.id)}
              title={`${item.id} • ${item.name} (${item.expectedClass})${
                isFilteredOut
                  ? ' • Currently hidden by active filters (click to reset filters and view)'
                  : ''
              }`}
              aria-label={`Select demo event ${item.id} - ${item.name}`}
            >
              <span className="quick-pick-id">{item.id}</span>
              <span className="quick-pick-name">{item.name}</span>
              {isFilteredOut && (
                <span className="quick-pick-hidden-badge" title="Hidden by current filters">
                  Filtered
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
};
