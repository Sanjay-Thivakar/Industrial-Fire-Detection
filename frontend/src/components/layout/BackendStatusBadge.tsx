import React, { useEffect, useState, useRef } from 'react';
import { checkHealth } from '../../services/apiClient.ts';
import { DEFAULT_RETRY_INTERVAL_MS } from '../../types/api.ts';
import type { HealthResponse } from '../../types/api.ts';

export { DEFAULT_RETRY_INTERVAL_MS };

export interface BackendStatusBadgeProps {
  retryIntervalMs?: number;
}

export const BackendStatusBadge: React.FC<BackendStatusBadgeProps> = ({
  retryIntervalMs = DEFAULT_RETRY_INTERVAL_MS,
}) => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [isOnline, setIsOnline] = useState<boolean>(false);

  // Guards against overlapping requests and unmount memory leaks
  const isMountedRef = useRef<boolean>(true);
  const isCheckingRef = useRef<boolean>(false);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const verifyBackendHealth = async (isInitial = false) => {
    if (isCheckingRef.current || !isMountedRef.current) {
      return;
    }

    isCheckingRef.current = true;
    if (isInitial) {
      setLoading(true);
    }

    // Abort previous in-flight request if any
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const data = await checkHealth(controller.signal);
      if (isMountedRef.current) {
        setHealth(data);
        setIsOnline(data.status === 'ok' && data.model_loaded);
        setLoading(false);
      }
    } catch {
      if (isMountedRef.current) {
        setIsOnline(false);
        setHealth(null);
        setLoading(false);
      }
    } finally {
      isCheckingRef.current = false;
    }
  };

  useEffect(() => {
    isMountedRef.current = true;

    // 1. Initial health check on mount
    verifyBackendHealth(true);

    // 2. Periodic retry timer (e.g. 10 seconds)
    timerRef.current = setInterval(() => {
      verifyBackendHealth(false);
    }, retryIntervalMs);

    return () => {
      isMountedRef.current = false;
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
    };
  }, [retryIntervalMs]);

  if (loading) {
    return (
      <div className="badge badge-backend-checking" aria-label="Checking ML Backend Status">
        <span className="status-dot dot-checking" />
        <span>Checking ML Backend...</span>
      </div>
    );
  }

  if (isOnline) {
    const apiVer = health?.api_version ? `(v${health.api_version})` : '';
    return (
      <div
        className="badge badge-backend-online"
        title={`ML Backend Online • Model: ${health?.model_version || 'Baseline RF'}`}
        aria-label="ML Backend Online"
      >
        <span className="status-dot dot-online" />
        <span>🟢 ML Backend: Online {apiVer}</span>
      </div>
    );
  }

  return (
    <div
      className="badge badge-backend-offline"
      title="FastAPI ML Inference Backend is unreachable or offline"
      aria-label="ML Backend Offline"
    >
      <span className="status-dot dot-offline" />
      <span>🔴 ML Backend: Offline</span>
    </div>
  );
};
