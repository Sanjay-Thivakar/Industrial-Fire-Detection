import { useState, useEffect } from 'react';
import type { DashboardEvent } from '../types/dashboard';
import { loadDashboardEvents } from '../services/dataLoader';

export interface UseDashboardDataReturn {
  events: DashboardEvent[];
  loading: boolean;
  error: string | null;
}

export function useDashboardData(csvUrl = '/data/dashboard_events_633.csv'): UseDashboardDataReturn {
  const [events, setEvents] = useState<DashboardEvent[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function fetchData() {
      setLoading(true);
      setError(null);

      const result = await loadDashboardEvents(csvUrl);

      if (isMounted) {
        if (result.error) {
          setError(result.error);
          setEvents([]);
        } else {
          setEvents(result.events);
          setError(null);
        }
        setLoading(false);
      }
    }

    fetchData();

    return () => {
      isMounted = false;
    };
  }, [csvUrl]);

  return { events, loading, error };
}
