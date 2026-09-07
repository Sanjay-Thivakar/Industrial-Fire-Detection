import React, { useMemo, useEffect } from 'react';
import { MapContainer, TileLayer, useMap } from 'react-leaflet';
import type { DashboardEvent } from '../../types/dashboard';
import { EventMarker } from './EventMarker';
import { MapLegend } from './MapLegend';

export interface FireMapProps {
  events: DashboardEvent[];
  selectedEventId?: string | null;
  onSelectEvent?: (event: DashboardEvent) => void;
  isDrawerOpen?: boolean;
}

interface MapPanControllerProps {
  selectedEvent: DashboardEvent | null;
  isDrawerOpen: boolean;
}

export const MapPanController: React.FC<MapPanControllerProps> = ({ selectedEvent, isDrawerOpen }) => {
  const map = useMap();

  useEffect(() => {
    if (selectedEvent) {
      // 1. Suppress and close any active Leaflet popups to prevent double-popup clutter
      map.closePopup();

      // 2. Smoothly center/pan to selected marker without aggressive animation
      map.panTo([selectedEvent.latitude, selectedEvent.longitude], {
        animate: true,
        duration: 0.4,
      });
    }
  }, [selectedEvent, isDrawerOpen, map]);

  return null;
};

export const FireMap: React.FC<FireMapProps> = ({
  events,
  selectedEventId,
  onSelectEvent,
  isDrawerOpen = false,
}) => {
  // Compute initial center from actual dataset events if available, or default to Tamil Nadu centroid
  const center = useMemo<[number, number]>(() => {
    if (events.length === 0) return [11.1271, 78.6569];
    const sumLat = events.reduce((acc, e) => acc + e.latitude, 0);
    const sumLon = events.reduce((acc, e) => acc + e.longitude, 0);
    return [sumLat / events.length, sumLon / events.length];
  }, [events]);

  const selectedEvent = useMemo(() => {
    if (!selectedEventId) return null;
    return events.find((e) => e.event_id === selectedEventId) || null;
  }, [events, selectedEventId]);

  const shouldSuppressPopup = Boolean(selectedEventId || isDrawerOpen);

  return (
    <div className="fire-map-container">
      <MapContainer
        center={center}
        zoom={7}
        minZoom={6}
        maxZoom={15}
        scrollWheelZoom={true}
        preferCanvas={true} // High-performance canvas rendering for 633 markers
        className="leaflet-map-canvas"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />

        <MapPanController selectedEvent={selectedEvent} isDrawerOpen={shouldSuppressPopup} />

        {events.map((event) => (
          <EventMarker
            key={event.event_id}
            event={event}
            isSelected={event.event_id === selectedEventId}
            onSelect={onSelectEvent}
            suppressPopup={shouldSuppressPopup}
          />
        ))}
      </MapContainer>

      <MapLegend totalEvents={events.length} />
    </div>
  );
};
