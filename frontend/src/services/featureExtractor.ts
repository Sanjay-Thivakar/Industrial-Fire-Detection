/**
 * Authoritative 36-Feature Lookup Service.
 *
 * Retrieves canonical production features directly from the authoritative
 * Phase 4B/4C dataset lookup table (event_features_36_lookup.json).
 *
 * Integrity Guarantees:
 * - Never calculates or approximates Category C features (grid_brightness_mean, frp_zscore_local).
 * - Never includes ground-truth labels or ML target columns (target-leakage-free).
 * - Caches lookup data in memory after initial fetch.
 * - Throws a descriptive error if an unknown event_id is requested.
 */

import type { Baseline36Features, EventFeaturesLookup } from '../types/api.ts';

let cachedLookup: EventFeaturesLookup | null = null;
let fetchPromise: Promise<EventFeaturesLookup> | null = null;

/**
 * Loads and caches the authoritative 36-feature lookup table.
 */
export async function loadFeatureLookup(
  url = '/data/event_features_36_lookup.json'
): Promise<EventFeaturesLookup> {
  if (cachedLookup) {
    return cachedLookup;
  }

  if (fetchPromise) {
    return fetchPromise;
  }

  fetchPromise = (async () => {
    try {
      const res = await fetch(url);
      if (!res.ok) {
        throw new Error(
          `Failed to load authoritative feature lookup from "${url}": HTTP ${res.status} ${res.statusText}`
        );
      }
      const data = (await res.json()) as EventFeaturesLookup;
      cachedLookup = data;
      return data;
    } finally {
      fetchPromise = null;
    }
  })();

  return fetchPromise;
}

/**
 * Retrieves the exact 36 baseline features for a specific event_id.
 *
 * @param eventId The event identifier (e.g. 'FIRMS_TN_0000')
 * @param lookupUrl Optional URL override for tests or alternate environments
 * @returns Exactly the 36 canonical features required by the production model
 */
export async function getModelFeatures(
  eventId: string,
  lookupUrl = '/data/event_features_36_lookup.json'
): Promise<Baseline36Features> {
  if (!eventId || typeof eventId !== 'string') {
    throw new Error(`Invalid event_id provided: "${eventId}"`);
  }

  const lookup = await loadFeatureLookup(lookupUrl);
  const features = lookup[eventId];

  if (!features) {
    throw new Error(
      `Event "${eventId}" not found in authoritative 36-feature lookup (total known events: ${
        Object.keys(lookup).length
      }).`
    );
  }

  return features;
}

/**
 * Clears the in-memory cache (primarily for unit test isolation).
 */
export function clearFeatureLookupCache(): void {
  cachedLookup = null;
  fetchPromise = null;
}
