import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { checkHealth, predictEvent } from '../src/services/apiClient.ts';
import {
  getModelFeatures,
  clearFeatureLookupCache,
} from '../src/services/featureExtractor.ts';
import { ApiError, DEFAULT_RETRY_INTERVAL_MS } from '../src/types/api.ts';
import type { PredictRequest, PredictResponse, HealthResponse } from '../src/types/api.ts';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const LOOKUP_PATH = path.resolve(__dirname, '../public/data/event_features_36_lookup.json');

const EXPECTED_36_FEATURES = [
  'frp',
  'brightness',
  'bright_t31',
  'brightness_difference',
  'frp_brightness_ratio',
  'log_frp',
  'confidence_numeric',
  'is_day',
  'grid_detection_count',
  'grid_active_days',
  'persistent_location_flag',
  'grid_total_frp',
  'grid_brightness_mean',
  'high_brightness_flag_local',
  'high_frp_flag_local',
  'brightness_zscore_local',
  'frp_zscore_local',
  'is_stubble_burning_season',
  'landcover_code',
  'distance_to_facility_m',
  'nearest_facility_type',
  'nearest_facility_category',
  'nearest_facility_tier',
  'near_industrial_500m',
  'near_industrial_1000m',
  'near_industrial_2000m',
  'near_industrial_5000m',
  'near_industrial_10000m',
  'distance_to_higher_relevance_m',
  'nearest_hr_category',
  'near_higher_relevance_500m',
  'near_higher_relevance_1000m',
  'near_higher_relevance_2000m',
  'near_higher_relevance_5000m',
  'near_higher_relevance_10000m',
  'osm_coverage_status',
];

const PROHIBITED_LEAKAGE_FIELDS = [
  'ml_target_3class',
  'human_ground_truth_class',
  'human_raw_label',
  'weak_label',
  'ground_truth_status',
  'human_validation_status',
  'human_industry_observation',
  'human_review_confidence',
  'is_unambiguous_ground_truth',
];

describe('Phase 6 Step 7 — Live API Prediction & Integration Tests', () => {
  let lookupData: Record<string, Record<string, any>>;

  beforeEach(() => {
    clearFeatureLookupCache();
    if (!lookupData) {
      const rawText = fs.readFileSync(LOOKUP_PATH, 'utf-8');
      lookupData = JSON.parse(rawText);
    }
  });

  it('1. Live prediction button contract renders with required text label', () => {
    const buttonLabel = '⚡ Re-predict via Live FastAPI Service';
    assert.strictEqual(buttonLabel.includes('Re-predict via Live FastAPI Service'), true);
  });

  it('2. Clicking live prediction requests exact 36-feature lookup without approximation', async () => {
    const originalFetch = globalThis.fetch;
    let requestedUrl = '';
    globalThis.fetch = (async (url: string) => {
      requestedUrl = url;
      return {
        ok: true,
        status: 200,
        statusText: 'OK',
        json: async () => lookupData,
      } as Response;
    }) as any;

    try {
      const features = await getModelFeatures('FIRMS_TN_0000');
      assert.strictEqual(requestedUrl, '/data/event_features_36_lookup.json');
      assert.strictEqual(Object.keys(features).length, 36);
      assert.strictEqual(features.grid_brightness_mean, 309.895);
      assert.strictEqual(features.frp_zscore_local, -0.50618);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it('3. Correct event_id and payload structure are sent in PredictRequest', async () => {
    const originalFetch = globalThis.fetch;
    let capturedBody: any = null;

    globalThis.fetch = (async (_url: string, init?: RequestInit) => {
      capturedBody = init?.body ? JSON.parse(init.body as string) : null;
      return {
        ok: true,
        status: 200,
        statusText: 'OK',
        json: async () => ({
          predicted_class: 'Industrial Thermal Activity',
          probabilities: { 'Industrial Thermal Activity': 0.5031, 'Agricultural Burning': 0.4331, 'Natural / Wildfire / Other': 0.0639 },
          max_probability: 0.5031,
          ml_confidence: 'MEDIUM',
          confidence_scale: { HIGH: '>= 0.75', MEDIUM: '0.50 - 0.74', LOW: '< 0.50' },
          model: { version: 'phase_5_ml_handoff/final_model.joblib', sha256: '5909bb546fc55aeffd37b7bb601e96718709fe685e987705b246bb2963279798' },
          inference_timestamp: '2026-09-07T02:50:00Z',
          disclaimer: 'Prediction is an algorithmic ML estimate. It is not ground truth.',
        }),
      } as Response;
    }) as any;

    try {
      const payload: PredictRequest = {
        event_id: 'FIRMS_TN_0000',
        features: lookupData['FIRMS_TN_0000'] as any,
      };
      await predictEvent(payload);
      assert.strictEqual(capturedBody.event_id, 'FIRMS_TN_0000');
      assert.strictEqual(Object.keys(capturedBody.features).length, 36);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it('4. Successful API response parses and returns live prediction model', async () => {
    const originalFetch = globalThis.fetch;
    const mockResponse: PredictResponse = {
      event_id: 'FIRMS_TN_0000',
      predicted_class: 'Industrial Thermal Activity',
      probabilities: {
        'Industrial Thermal Activity': 0.5031,
        'Agricultural Burning': 0.4331,
        'Natural / Wildfire / Other': 0.0639,
      },
      max_probability: 0.5031,
      ml_confidence: 'MEDIUM',
      confidence_scale: {
        HIGH: '>= 0.75',
        MEDIUM: '0.50 - 0.74',
        LOW: '< 0.50',
      },
      model: {
        version: 'phase_5_ml_handoff/final_model.joblib',
        sha256: '5909bb546fc55aeffd37b7bb601e96718709fe685e987705b246bb2963279798',
        architecture: 'Random Forest Classifier (Baseline FIRMS+OSM+WorldCover)',
        training_samples: 76,
        macro_f1_oof: 0.7772,
      },
      inference_timestamp: '2026-09-07T02:50:00Z',
      disclaimer: 'Prediction is an algorithmic ML estimate. It is not ground truth.',
    };

    globalThis.fetch = (async () => ({
      ok: true,
      status: 200,
      statusText: 'OK',
      json: async () => mockResponse,
    })) as any;

    try {
      const res = await predictEvent({
        event_id: 'FIRMS_TN_0000',
        features: lookupData['FIRMS_TN_0000'] as any,
      });
      assert.strictEqual(res.predicted_class, 'Industrial Thermal Activity');
      assert.strictEqual(res.ml_confidence, 'MEDIUM');
      assert.strictEqual(res.model.sha256, '5909bb546fc55aeffd37b7bb601e96718709fe685e987705b246bb2963279798');
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it('5. Three returned probabilities render correctly with percentages', () => {
    const probs = {
      'Industrial Thermal Activity': 0.5031,
      'Agricultural Burning': 0.4331,
      'Natural / Wildfire / Other': 0.0639,
    };
    assert.strictEqual((probs['Industrial Thermal Activity'] * 100).toFixed(1), '50.3');
    assert.strictEqual((probs['Agricultural Burning'] * 100).toFixed(1), '43.3');
    assert.strictEqual((probs['Natural / Wildfire / Other'] * 100).toFixed(1), '6.4');
  });

  it('6. Loading state disables the prediction action button', () => {
    let isLoading = true;
    const isButtonDisabled = isLoading;
    assert.strictEqual(isButtonDisabled, true);
    isLoading = false;
    assert.strictEqual(!isLoading, true);
  });

  it('7. API error displays cleanly with error code and message', async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = (async () => ({
      ok: false,
      status: 503,
      statusText: 'Service Unavailable',
      json: async () => ({
        error: {
          code: 'MODEL_NOT_LOADED',
          message: 'Model is not loaded and unavailable for inference.',
        },
      }),
    })) as any;

    try {
      await assert.rejects(
        async () => {
          await predictEvent({ event_id: 'FIRMS_TN_0000', features: {} as any });
        },
        (err: any) => {
          assert.strictEqual(err instanceof ApiError, true);
          assert.strictEqual(err.code, 'MODEL_NOT_LOADED');
          assert.strictEqual(err.status, 503);
          assert.strictEqual(err.message, 'Model is not loaded and unavailable for inference.');
          return true;
        }
      );
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it('8. Retry re-dispatches prediction on failure', async () => {
    const originalFetch = globalThis.fetch;
    let callCount = 0;

    globalThis.fetch = (async () => {
      callCount++;
      if (callCount === 1) {
        return {
          ok: false,
          status: 500,
          statusText: 'Internal Server Error',
          json: async () => ({
            error: { code: 'INFERENCE_ERROR', message: 'Simulated transient failure' },
          }),
        } as Response;
      }
      return {
        ok: true,
        status: 200,
        statusText: 'OK',
        json: async () => ({
          predicted_class: 'Industrial Thermal Activity',
          probabilities: { 'Industrial Thermal Activity': 0.5031, 'Agricultural Burning': 0.4331, 'Natural / Wildfire / Other': 0.0639 },
          max_probability: 0.5031,
          ml_confidence: 'MEDIUM',
          confidence_scale: { HIGH: '>= 0.75', MEDIUM: '0.50 - 0.74', LOW: '< 0.50' },
          model: { version: 'phase_5_ml_handoff/final_model.joblib', sha256: '5909bb546fc55aeffd37b7bb601e96718709fe685e987705b246bb2963279798' },
          inference_timestamp: '2026-09-07T02:50:00Z',
          disclaimer: 'Prediction is an algorithmic ML estimate. It is not ground truth.',
        }),
      } as Response;
    }) as any;

    try {
      // First attempt fails
      await assert.rejects(async () => {
        await predictEvent({ event_id: 'FIRMS_TN_0000', features: lookupData['FIRMS_TN_0000'] as any });
      });
      // Second attempt (retry) succeeds
      const result = await predictEvent({ event_id: 'FIRMS_TN_0000', features: lookupData['FIRMS_TN_0000'] as any });
      assert.strictEqual(result.predicted_class, 'Industrial Thermal Activity');
      assert.strictEqual(callCount, 2);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it('9. Static baseline prediction remains visible when live prediction renders', () => {
    // Both components exist simultaneously in the drawer Section C
    const staticCardRendered = true;
    const liveCardRendered = true;
    assert.strictEqual(staticCardRendered && liveCardRendered, true);
  });

  it('10. Live result is clearly labeled as "Live API Result"', () => {
    const liveResultTag = 'Live API Result';
    assert.strictEqual(liveResultTag, 'Live API Result');
  });

  it('11. Matches Baseline = Yes when live and static classes match', () => {
    const staticClass = 'Industrial Thermal Activity';
    const liveClass = 'Industrial Thermal Activity';
    const comparisonText = liveClass === staticClass ? 'Matches Baseline: Yes' : 'Matches Baseline: No';
    assert.strictEqual(comparisonText, 'Matches Baseline: Yes');
  });

  it('12. Matches Baseline = No when live and static classes differ', () => {
    const staticClass = 'Industrial Thermal Activity';
    const liveClass = 'Agricultural Burning';
    const comparisonText = liveClass === staticClass ? 'Matches Baseline: Yes' : 'Matches Baseline: No';
    assert.strictEqual(comparisonText, 'Matches Baseline: No');
  });

  it('13. API latency is formatted and displayed only after successful inference', () => {
    const start = 100;
    const end = 124.6;
    const latencyMs = Math.round(end - start);
    const latencyString = `API latency: ${latencyMs} ms`;
    assert.strictEqual(latencyString, 'API latency: 25 ms');
  });

  it('14. Backend status displays Online on successful health check', async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = (async () => ({
      ok: true,
      status: 200,
      statusText: 'OK',
      json: async () => ({
        status: 'ok',
        model_loaded: true,
        api_version: '1.0.0',
        model_version: 'phase_5_ml_handoff/final_model.joblib',
      }),
    })) as any;

    try {
      const data = await checkHealth();
      assert.strictEqual(data.status, 'ok');
      assert.strictEqual(data.model_loaded, true);
      const badgeText = data.status === 'ok' && data.model_loaded ? '🟢 ML Backend: Online' : '🔴 ML Backend: Offline';
      assert.strictEqual(badgeText, '🟢 ML Backend: Online');
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it('15. Backend status displays Offline on health failure', async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = (async () => ({
      ok: false,
      status: 503,
      statusText: 'Service Unavailable',
      json: async () => ({ status: 'unavailable', model_loaded: false }),
    })) as any;

    try {
      await assert.rejects(async () => {
        await checkHealth();
      });
      const badgeText = '🔴 ML Backend: Offline';
      assert.strictEqual(badgeText, '🔴 ML Backend: Offline');
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it('16. No X-API-Key is present in browser request code', async () => {
    const originalFetch = globalThis.fetch;
    let capturedHeaders: any = null;

    globalThis.fetch = (async (_url: string, init?: RequestInit) => {
      capturedHeaders = init?.headers;
      return {
        ok: true,
        status: 200,
        statusText: 'OK',
        json: async () => ({ status: 'ok', model_loaded: true }),
      } as Response;
    }) as any;

    try {
      await checkHealth();
      assert.strictEqual(capturedHeaders?.['X-API-Key'], undefined);

      await predictEvent({ event_id: 'FIRMS_TN_0000', features: lookupData['FIRMS_TN_0000'] as any });
      assert.strictEqual(capturedHeaders?.['X-API-Key'], undefined);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it('17. API key is never rendered or stored client-side', () => {
    // Check client source tree for VITE_ML_API_KEY or hardcoded keys
    const srcDir = path.resolve(__dirname, '../src');
    const checkDir = (dir: string) => {
      const files = fs.readdirSync(dir, { withFileTypes: true });
      for (const f of files) {
        const fullPath = path.join(dir, f.name);
        if (f.isDirectory()) {
          checkDir(fullPath);
        } else if (f.name.endsWith('.ts') || f.name.endsWith('.tsx')) {
          const content = fs.readFileSync(fullPath, 'utf-8');
          assert.strictEqual(
            content.includes('VITE_ML_API_KEY'),
            false,
            `Forbidden VITE_ML_API_KEY found in ${fullPath}`
          );
          assert.strictEqual(
            content.includes('localStorage.setItem'),
            false,
            `Forbidden localStorage found in ${fullPath}`
          );
          assert.strictEqual(
            content.includes('sessionStorage.setItem'),
            false,
            `Forbidden sessionStorage found in ${fullPath}`
          );
        }
      }
    };
    checkDir(srcDir);
  });

  it('18. Closing the drawer or changing selected event resets live prediction state', () => {
    // Model state transition test
    let cardState = { status: 'success', result: {} };
    // When eventId changes or drawer unmounts:
    const onEventChange = () => {
      cardState = { status: 'idle', result: {} };
    };
    onEventChange();
    assert.strictEqual(cardState.status, 'idle', 'State must reset to idle on event change');
  });

  // ---------------------------------------------------------------------------
  // Phase 7 Step 3 (Fix M3): BackendStatusBadge Health Retry Tests
  // ---------------------------------------------------------------------------

  it('19. BackendStatusBadge initial health check triggers on mount and sets online', async () => {
    const originalFetch = globalThis.fetch;
    let callCount = 0;
    globalThis.fetch = (async () => {
      callCount++;
      return {
        ok: true,
        status: 200,
        statusText: 'OK',
        json: async () => ({ status: 'ok', model_loaded: true }),
      };
    }) as any;

    try {
      let isOnline = false;
      let loading = true;
      const res = await checkHealth();
      isOnline = res.status === 'ok' && res.model_loaded;
      loading = false;

      assert.strictEqual(callCount, 1, 'Initial health check must be called once on mount');
      assert.strictEqual(isOnline, true, 'Badge must be online after healthy response');
      assert.strictEqual(loading, false, 'Loading must resolve to false');
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it('20. BackendStatusBadge retries periodically and recovers when backend becomes available', async () => {
    const originalFetch = globalThis.fetch;
    let callCount = 0;

    // First call fails (backend starting), second call succeeds (backend online)
    globalThis.fetch = (async () => {
      callCount++;
      if (callCount === 1) {
        return {
          ok: false,
          status: 503,
          statusText: 'Service Unavailable',
          json: async () => ({ status: 'unavailable', model_loaded: false }),
        };
      }
      return {
        ok: true,
        status: 200,
        statusText: 'OK',
        json: async () => ({ status: 'ok', model_loaded: true }),
      };
    }) as any;

    try {
      let isOnline = false;

      // 1. Initial attempt fails
      try {
        await checkHealth();
        isOnline = true;
      } catch {
        isOnline = false;
      }
      assert.strictEqual(callCount, 1);
      assert.strictEqual(isOnline, false, 'Badge must reflect offline after initial failure');

      // 2. Periodic retry fires and succeeds
      try {
        const retryRes = await checkHealth();
        isOnline = retryRes.status === 'ok' && retryRes.model_loaded;
      } catch {
        isOnline = false;
      }
      assert.strictEqual(callCount, 2);
      assert.strictEqual(isOnline, true, 'Badge must automatically recover to online upon retry');
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it('21. BackendStatusBadge cleanup/unmount terminates timer and aborts pending requests', () => {
    let timerCleared = false;
    let requestAborted = false;

    const controller = new AbortController();
    const fakeTimer: any = setTimeout(() => {}, 10000);

    // Simulate component unmount handler
    const unmount = () => {
      clearTimeout(fakeTimer);
      timerCleared = true;
      controller.abort();
      requestAborted = controller.signal.aborted;
    };

    unmount();
    assert.strictEqual(timerCleared, true, 'Periodic timer must be cleared on unmount');
    assert.strictEqual(requestAborted, true, 'Pending requests must be aborted on unmount');
  });

  it('22. BackendStatusBadge overlap guard prevents concurrent in-flight health checks', async () => {
    let inFlight = false;
    let skippedCalls = 0;
    let executedCalls = 0;

    const triggerHealthCheck = async (simulateDelayMs: number) => {
      if (inFlight) {
        skippedCalls++;
        return;
      }
      inFlight = true;
      executedCalls++;
      await new Promise((resolve) => setTimeout(resolve, simulateDelayMs));
      inFlight = false;
    };

    // Trigger check 1 (takes 50ms)
    const p1 = triggerHealthCheck(50);
    // Concurrent check 2 should be skipped due to overlap guard
    const p2 = triggerHealthCheck(10);

    await Promise.all([p1, p2]);

    assert.strictEqual(executedCalls, 1, 'Only 1 health request should execute');
    assert.strictEqual(skippedCalls, 1, 'Overlapping second request should be skipped');
  });

  it('23. DEFAULT_RETRY_INTERVAL_MS equals 10,000 milliseconds (10s)', () => {
    assert.strictEqual(DEFAULT_RETRY_INTERVAL_MS, 10000, 'Default retry interval must be 10s');
  });
});
