import React, { useState, useEffect } from 'react';
import { useDashboardData } from './hooks/useDashboardData.ts';
import { useFilters } from './hooks/useFilters.ts';
import { FireMap } from './components/map/FireMap.tsx';
import { SummaryBar } from './components/layout/SummaryBar.tsx';
import { FilterPanel } from './components/filters/FilterPanel.tsx';
import { FilterPills } from './components/filters/FilterPills.tsx';
import { EventDetailDrawer } from './components/events/EventDetailDrawer.tsx';
import { BackendStatusBadge } from './components/layout/BackendStatusBadge.tsx';
import { DemoQuickPicks } from './components/layout/DemoQuickPicks.tsx';
import type { DashboardEvent } from './types/dashboard.ts';

export default function App(): React.ReactElement {
  const { events, loading, error } = useDashboardData('/data/dashboard_events_633.csv');
  const [selectedEvent, setSelectedEvent] = useState<DashboardEvent | null>(null);
  const [quickPickNotice, setQuickPickNotice] = useState<string | null>(null);

  const {
    filters,
    filteredEvents,
    kpis,
    isFiltered,
    toggleArrayFilter,
    setFrpRange,
    setPersistenceOnly,
    resetFilters,
  } = useFilters(events);

  // Requirement 4: If selected event is no longer in filteredEvents when filters change, close drawer automatically
  useEffect(() => {
    if (selectedEvent) {
      const stillPresent = filteredEvents.some((e) => e.event_id === selectedEvent.event_id);
      if (!stillPresent) {
        setSelectedEvent(null);
      }
    }
  }, [filteredEvents, selectedEvent]);

  if (loading) {
    return (
      <div className="state-container">
        <div className="spinner" />
        <h2>Loading Tamil Nadu Thermal Events...</h2>
        <p style={{ color: '#9ca3af', fontSize: '0.875rem', marginTop: '0.5rem' }}>
          Parsing authoritative 633-event dataset &bull; Phase 5B Production Baseline
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="state-container">
        <div className="error-card">
          <div className="error-title">Dataset Loading / Integrity Error</div>
          <div className="error-message">{error}</div>
          <button
            type="button"
            onClick={() => window.location.reload()}
            style={{
              padding: '0.5rem 1rem',
              background: '#ef4444',
              color: '#ffffff',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontWeight: 600,
            }}
          >
            Retry Loading
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="app-layout">
      {/* 1. Global Header */}
      <header className="app-header">
        <div className="header-brand">
          <div className="header-title-group">
            <h1>Industrial Fire Detection &amp; Classification System</h1>
            <div className="header-subtitle">
              Interactive Multi-Modal GIS Dashboard &bull; Smart India Hackathon
            </div>
          </div>
        </div>

        <DemoQuickPicks
          events={events}
          filteredEvents={filteredEvents}
          selectedEventId={selectedEvent?.event_id || null}
          onSelectEvent={setSelectedEvent}
          onResetFilters={resetFilters}
          onNotice={setQuickPickNotice}
        />

        <div className="header-stats">
          <BackendStatusBadge />
          <div className={`badge ${isFiltered ? 'badge-amber' : 'badge-green'}`}>
            <span className="pulse-dot" />
            <span>
              {isFiltered ? `Showing: ${filteredEvents.length} of ${events.length}` : `Dataset Active: ${events.length} Events`}
            </span>
          </div>
          <div className="badge badge-blue">
            <span>Random Forest (3 ML Classes)</span>
          </div>
        </div>
      </header>

      {/* Demo Quick-Pick Filter Notice Banner */}
      {quickPickNotice && (
        <div className="quick-pick-notice-bar">
          <span className="notice-icon">⚡</span>
          <span className="notice-text">{quickPickNotice}</span>
          <button
            type="button"
            className="notice-dismiss-btn"
            onClick={() => setQuickPickNotice(null)}
            aria-label="Dismiss notice"
          >
            &times;
          </button>
        </div>
      )}

      {/* 2. Real-Time Analytics / KPI Bar */}
      <SummaryBar kpis={kpis} totalDatasetEvents={events.length} />

      {/* 3. Active Filter Pills */}
      <FilterPills
        filters={filters}
        onRemoveClass={(cls) => toggleArrayFilter('classes', cls)}
        onRemoveMlConf={(conf) => toggleArrayFilter('mlConfidenceTiers', conf)}
        onRemoveFirmsConf={(conf) => toggleArrayFilter('firmsConfidences', conf)}
        onRemoveLandcover={(lc) => toggleArrayFilter('landcoverClasses', lc)}
        onRemoveFacilityTier={(tier) => toggleArrayFilter('facilityTiers', tier)}
        onRemoveS2Status={(status) => toggleArrayFilter('s2Statuses', status)}
        onRemovePersistence={() => setPersistenceOnly(false)}
        onResetFrp={() => setFrpRange(0, 20)}
        onClearAll={resetFilters}
        isFiltered={isFiltered}
      />

      {/* 4. Workspace: Filter Sidebar + Interactive Map + Event Detail Drawer */}
      <div className="workspace-container">
        <FilterPanel
          filters={filters}
          onToggleClass={(cls) => toggleArrayFilter('classes', cls)}
          onToggleMlConf={(tier) => toggleArrayFilter('mlConfidenceTiers', tier)}
          onToggleFirmsConf={(conf) => toggleArrayFilter('firmsConfidences', conf)}
          onToggleLandcover={(lc) => toggleArrayFilter('landcoverClasses', lc)}
          onToggleFacilityTier={(tier) => toggleArrayFilter('facilityTiers', tier)}
          onToggleS2Status={(status) => toggleArrayFilter('s2Statuses', status)}
          onTogglePersistence={setPersistenceOnly}
          onSetFrpMax={(max) => setFrpRange(0, max)}
          onResetFilters={resetFilters}
          isFiltered={isFiltered}
          totalMatches={filteredEvents.length}
        />

        <main className="map-viewport">
          <FireMap
            events={filteredEvents}
            selectedEventId={selectedEvent?.event_id}
            onSelectEvent={setSelectedEvent}
            isDrawerOpen={selectedEvent !== null}
          />

          {/* Zero Result Overlay */}
          {filteredEvents.length === 0 && (
            <div className="zero-result-overlay">
              <div className="zero-result-card">
                <div className="zero-result-icon">🔍</div>
                <h3>No events match the selected filters</h3>
                <p>Try clearing some filter criteria or widening the FRP threshold.</p>
                <button type="button" className="zero-result-reset-btn" onClick={resetFilters}>
                  Reset All Filters
                </button>
              </div>
            </div>
          )}

          {/* Slide-Over Event Detail Drawer */}
          <EventDetailDrawer
            event={selectedEvent}
            onClose={() => setSelectedEvent(null)}
          />
        </main>
      </div>
    </div>
  );
}
