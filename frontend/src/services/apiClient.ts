/**
 * Typed API client for Industrial Fire Detection FastAPI ML Service.
 *
 * Security Architecture:
 * - Uses relative URLs (/api/v1/...) matching origin.
 * - ZERO secrets or API keys are stored, referenced, or transmitted from client code.
 * - In local development, Vite dev proxy injects the server-side X-API-Key.
 * - In production, an API gateway or reverse proxy injects the X-API-Key.
 */

import { ApiError } from '../types/api.ts';
import type {
  HealthResponse,
  PredictRequest,
  PredictResponse,
  ApiErrorResponse,
} from '../types/api.ts';

const HEALTH_ENDPOINT = '/api/v1/health';
const PREDICT_ENDPOINT = '/api/v1/predict';

/**
 * Parses response body and throws a typed ApiError if not OK.
 */
async function handleResponse<T>(res: Response): Promise<T> {
  if (res.ok) {
    return (await res.json()) as T;
  }

  let errorCode = 'HTTP_ERROR';
  let errorMessage = `HTTP ${res.status} ${res.statusText}`;
  let errorDetails: Record<string, any> = {};

  try {
    const errorJson = (await res.json()) as ApiErrorResponse;
    if (errorJson?.error) {
      errorCode = errorJson.error.code || errorCode;
      errorMessage = errorJson.error.message || errorMessage;
      errorDetails = errorJson.error.details || {};
    }
  } catch {
    // Response body is not JSON, use HTTP status text
  }

  throw new ApiError(errorCode, errorMessage, res.status, errorDetails);
}

/**
 * Checks liveness and model readiness of the FastAPI backend.
 * Public endpoint; requires no authentication.
 */
export async function checkHealth(signal?: AbortSignal): Promise<HealthResponse> {
  try {
    const res = await fetch(HEALTH_ENDPOINT, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
      signal,
    });

    return await handleResponse<HealthResponse>(res);
  } catch (err: any) {
    if (err instanceof ApiError) {
      throw err;
    }
    throw new ApiError(
      'NETWORK_FAILURE',
      err?.message || 'Failed to connect to ML Backend service.',
      0
    );
  }
}

/**
 * Dispatches a single thermal event prediction request to the FastAPI service.
 * Does NOT attach an X-API-Key header; header injection is handled by the server-side proxy.
 */
export async function predictEvent(
  request: PredictRequest,
  signal?: AbortSignal
): Promise<PredictResponse> {
  try {
    const res = await fetch(PREDICT_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify(request),
      signal,
    });

    return await handleResponse<PredictResponse>(res);
  } catch (err: any) {
    if (err instanceof ApiError) {
      throw err;
    }
    throw new ApiError(
      'NETWORK_FAILURE',
      err?.message || 'Network failure communicating with prediction API.',
      0
    );
  }
}
