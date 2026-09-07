import { useState, useMemo, useCallback } from 'react';
import type { DashboardEvent } from '../types/dashboard.ts';
import type { FilterCriteria } from '../types/filters.ts';
import { DEFAULT_FILTERS } from '../types/filters.ts';
import { applyFilters, isFilterActive, calculateKPIs, type KPIMetrics } from '../utils/filterLogic.ts';

export interface UseFiltersReturn {
  filters: FilterCriteria;
  filteredEvents: DashboardEvent[];
  kpis: KPIMetrics;
  isFiltered: boolean;
  setFilters: React.Dispatch<React.SetStateAction<FilterCriteria>>;
  toggleArrayFilter: <K extends keyof FilterCriteria>(
    key: K,
    value: FilterCriteria[K] extends (infer U)[] ? U : never
  ) => void;
  setFrpRange: (min: number, max: number) => void;
  setPersistenceOnly: (enabled: boolean) => void;
  resetFilters: () => void;
}

export function useFilters(events: DashboardEvent[]): UseFiltersReturn {
  const [filters, setFilters] = useState<FilterCriteria>(DEFAULT_FILTERS);

  // Toggle helper for array filters (adds if absent, removes if present)
  const toggleArrayFilter = useCallback(
    <K extends keyof FilterCriteria>(
      key: K,
      value: FilterCriteria[K] extends (infer U)[] ? U : never
    ) => {
      setFilters((prev) => {
        const currentList = (prev[key] as unknown as any[]) || [];
        const exists = currentList.includes(value);
        const updatedList = exists
          ? currentList.filter((item) => item !== value)
          : [...currentList, value];

        return {
          ...prev,
          [key]: updatedList,
        };
      });
    },
    []
  );

  const setFrpRange = useCallback((min: number, max: number) => {
    setFilters((prev) => ({
      ...prev,
      frpMin: min,
      frpMax: max,
    }));
  }, []);

  const setPersistenceOnly = useCallback((enabled: boolean) => {
    setFilters((prev) => ({
      ...prev,
      onlyPersistentHotspots: enabled,
    }));
  }, []);

  const resetFilters = useCallback(() => {
    setFilters(DEFAULT_FILTERS);
  }, []);

  // Compute filtered events deterministically
  const filteredEvents = useMemo(() => {
    return applyFilters(events, filters);
  }, [events, filters]);

  // Compute KPIs strictly from filtered events
  const kpis = useMemo(() => {
    return calculateKPIs(filteredEvents);
  }, [filteredEvents]);

  const isFiltered = useMemo(() => {
    return isFilterActive(filters);
  }, [filters]);

  return {
    filters,
    filteredEvents,
    kpis,
    isFiltered,
    setFilters,
    toggleArrayFilter,
    setFrpRange,
    setPersistenceOnly,
    resetFilters,
  };
}
