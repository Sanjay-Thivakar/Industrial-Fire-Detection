/**
 * Formatting utilities for Industrial Fire Detection Dashboard & Event Drawer.
 */

export function formatCoord(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) return 'Unavailable';
  return `${val.toFixed(5)}°`;
}

export function formatFrp(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) return 'Unavailable';
  return `${val.toFixed(2)} MW`;
}

export function formatKelvin(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) return 'Unavailable';
  return `${val.toFixed(1)} K`;
}

export function formatDistance(meters: number | null | undefined): string {
  if (meters === null || meters === undefined || isNaN(meters)) return 'Unavailable';
  if (meters < 1000) {
    return `${Math.round(meters)} m`;
  }
  return `${(meters / 1000).toFixed(1)} km`;
}

export function formatPercentage(prob: number | null | undefined): string {
  if (prob === null || prob === undefined || isNaN(prob)) return 'Unavailable';
  return `${(prob * 100).toFixed(1)}%`;
}

export function formatNullable(val: unknown): string {
  if (val === null || val === undefined || val === '') return 'Unavailable';
  const s = String(val).trim();
  if (s.toLowerCase() === 'null' || s.toLowerCase() === 'nan' || s.toLowerCase() === 'n/a') {
    return 'Unavailable';
  }
  return s;
}
