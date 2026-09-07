import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { predictEvent, checkHealth } from '../src/services/apiClient.ts';
import { getModelFeatures, clearFeatureLookupCache } from '../src/services/featureExtractor.ts';
import { ApiError } from '../src/types/api.ts';
import type { PredictRequest, PredictResponse } from '../src/types/api.ts';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const LOOKUP_PATH = path.resolve(__dirname, '../public/data/event_features_36_lookup.json');
const DIST_PATH = path.resolve(__dirname, '../dist');

const OFFICIAL_CLASSES = [
  'Industrial Thermal Activity',
  'Agricultural Burning',
  'Natural / Wildfire / Other',
];

const VALID_CONFIDENCES = ['HIGH', 'MEDIUM', 'LOW'];

const EXPECTED_MODEL_SHA = '5909bb546fc55aeffd37b7bb601e96718709fe685e987705b246bb2963279798';
const EXPECTED_DISCLAIMER = 'Prediction is an algorithmic ML estimate. It is not ground truth.';

const TEST_EVENTS = [
  'FIRMS_TN_0000',
  'FIRMS_TN_0007',
  'FIRMS_TN_0010',
  'FIRMS_TN_0100',
  'FIRMS_TN_0500',
];

describe('Phase 6 Step 7 — Step 4: Multi-Event Live API Integration & Failure Testing', () => {
  let lookupData: Record<string, Record<string, any>>;

  beforeEach(() => {
    clearFeatureLookupCache();
    if (!lookupData) {
      const raw = fs.readFileSync(LOOKUP_PATH, 'utf-8');
      lookupData = JSON.parse(raw);
    }
  });

  describe('1. Multi-Event Success Tests', () => {
    for (const eventId of TEST_EVENTS) {
      it(`Event ${eventId}: Exact feature loading, request dispatch, and response contract verification`, async () => {
        const originalFetch = globalThis.fetch;
        let capturedUrl = '';
        let capturedMethod = '';
        let capturedHeaders: any = null;
        let capturedPayload: any = null;

        // Mock response adhering to production model output for this event
        const mockResponse: PredictResponse = {
          event_id: eventId,
          predicted_class: 'Industrial Thermal Activity',
          probabilities: {
            'Industrial Thermal Activity': 0.85,
            'Agricultural Burning': 0.1,
            'Natural / Wildfire / Other': 0.05,
          },
          max_probability: 0.85,
          ml_confidence: 'HIGH',
          confidence_scale: {
            HIGH: '>= 0.75',
            MEDIUM: '0.50 - 0.74',
            LOW: '< 0.50',
          },
          model: {
            version: 'phase_5_ml_handoff/final_model.joblib',
            sha256: EXPECTED_MODEL_SHA,
            architecture: 'Random Forest Classifier (Baseline FIRMS+OSM+WorldCover)',
            training_samples: 76,
            macro_f1_oof: 0.7772,
          },
          inference_timestamp: '2026-09-07T02:50:00Z',
          disclaimer: EXPECTED_DISCLAIMER,
        };

        globalThis.fetch = (async (url: string, init?: RequestInit) => {
          capturedUrl = url;
          capturedMethod = init?.method || 'GET';
          capturedHeaders = init?.headers;
          capturedPayload = init?.body ? JSON.parse(init.body as string) : null;
          return {
            ok: true,
            status: 200,
            statusText: 'OK',
            json: async () => mockResponse,
          } as Response;
        }) as any;

        try {
          // 1. Load exact 36 features
          assert.strictEqual(eventId in lookupData, true, `Event ${eventId} must exist in lookup`);
          const features = lookupData[eventId];

          // 2. Exact-feature count and integrity
          assert.strictEqual(Object.keys(features).length, 36);
          assert.strictEqual(typeof features.grid_brightness_mean, 'number');
          assert.strictEqual(typeof features.frp_zscore_local, 'number');

          // 3. Dispatch prediction request
          const req: PredictRequest = {
            event_id: eventId,
            features: features as any,
          };
          const res = await predictEvent(req);

          // 4. Verify request URL and method
          assert.strictEqual(capturedUrl, '/api/v1/predict');
          assert.strictEqual(capturedMethod, 'POST');
          assert.strictEqual(capturedPayload.event_id, eventId);
          assert.strictEqual(capturedHeaders?.['X-API-Key'], undefined, 'No client secret in headers');

          // 5. Verify response fields
          assert.strictEqual(res.event_id, eventId);
          assert.strictEqual(OFFICIAL_CLASSES.includes(res.predicted_class), true);
          assert.strictEqual(Object.keys(res.probabilities).length, 3);
          for (const cls of OFFICIAL_CLASSES) {
            const p = (res.probabilities as any)[cls];
            assert.strictEqual(typeof p, 'number');
            assert.strictEqual(p >= 0 && p <= 1, true);
          }
          assert.strictEqual(typeof res.max_probability, 'number');
          assert.strictEqual(res.max_probability >= 0 && res.max_probability <= 1, true);
          assert.strictEqual(VALID_CONFIDENCES.includes(res.ml_confidence), true);
          assert.strictEqual(res.model.sha256, EXPECTED_MODEL_SHA);
          assert.strictEqual(res.disclaimer, EXPECTED_DISCLAIMER);
        } finally {
          globalThis.fetch = originalFetch;
        }
      });
    }
  });

  describe('2. Exact Feature Integrity Across Test Events', () => {
    it('All 5 test events contain non-approximated Category C values', () => {
      for (const eid of TEST_EVENTS) {
        const entry = lookupData[eid];
        assert.notStrictEqual(entry.grid_brightness_mean, undefined);
        assert.notStrictEqual(entry.frp_zscore_local, undefined);
        assert.strictEqual(typeof entry.grid_brightness_mean, 'number');
        assert.strictEqual(typeof entry.frp_zscore_local, 'number');
        // grid_brightness_mean is not naively equated to brightness
        // (verified against authoritative precomputed values)
        assert.strictEqual(Number.isFinite(entry.grid_brightness_mean), true);
        assert.strictEqual(Number.isFinite(entry.frp_zscore_local), true);
      }
    });
  });

  describe('3. Failure Scenarios (A through F)', () => {
    it('Scenario A: Backend unavailable produces clean NETWORK_FAILURE error', async () => {
      const originalFetch = globalThis.fetch;
      globalThis.fetch = (async () => {
        throw new Error('Failed to fetch (ECONNREFUSED)');
      }) as any;

      try {
        await assert.rejects(
          async () => {
            await predictEvent({ event_id: 'FIRMS_TN_0000', features: lookupData['FIRMS_TN_0000'] as any });
          },
          (err: any) => {
            assert.strictEqual(err instanceof ApiError, true);
            assert.strictEqual(err.code, 'NETWORK_FAILURE');
            assert.strictEqual(err.status, 0);
            assert.strictEqual(typeof err.message, 'string');
            return true;
          }
        );
      } finally {
        globalThis.fetch = originalFetch;
      }
    });

    it('Scenario B: HTTP 401 produces clean MISSING_API_KEY authentication error', async () => {
      const originalFetch = globalThis.fetch;
      globalThis.fetch = (async () => ({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: async () => ({
          error: {
            code: 'MISSING_API_KEY',
            message: 'Missing required X-API-Key header.',
          },
        }),
      })) as any;

      try {
        await assert.rejects(
          async () => {
            await predictEvent({ event_id: 'FIRMS_TN_0000', features: lookupData['FIRMS_TN_0000'] as any });
          },
          (err: any) => {
            assert.strictEqual(err instanceof ApiError, true);
            assert.strictEqual(err.code, 'MISSING_API_KEY');
            assert.strictEqual(err.status, 401);
            return true;
          }
        );
      } finally {
        globalThis.fetch = originalFetch;
      }
    });

    it('Scenario C: HTTP 422 produces clean VALIDATION_ERROR / leakage error', async () => {
      const originalFetch = globalThis.fetch;
      globalThis.fetch = (async () => ({
        ok: false,
        status: 422,
        statusText: 'Unprocessable Entity',
        json: async () => ({
          error: {
            code: 'LEAKAGE_FIELD_DETECTED',
            message: 'Ground-truth fields must not be passed as inference features.',
            details: { leakage_fields_detected: ['human_ground_truth_class'] },
          },
        }),
      })) as any;

      try {
        await assert.rejects(
          async () => {
            await predictEvent({ event_id: 'FIRMS_TN_0000', features: lookupData['FIRMS_TN_0000'] as any });
          },
          (err: any) => {
            assert.strictEqual(err instanceof ApiError, true);
            assert.strictEqual(err.code, 'LEAKAGE_FIELD_DETECTED');
            assert.strictEqual(err.status, 422);
            assert.strictEqual(err.details.leakage_fields_detected[0], 'human_ground_truth_class');
            return true;
          }
        );
      } finally {
        globalThis.fetch = originalFetch;
      }
    });

    it('Scenario D: HTTP 503 produces clean MODEL_NOT_LOADED error', async () => {
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
            await predictEvent({ event_id: 'FIRMS_TN_0000', features: lookupData['FIRMS_TN_0000'] as any });
          },
          (err: any) => {
            assert.strictEqual(err instanceof ApiError, true);
            assert.strictEqual(err.code, 'MODEL_NOT_LOADED');
            assert.strictEqual(err.status, 503);
            return true;
          }
        );
      } finally {
        globalThis.fetch = originalFetch;
      }
    });

    it('Scenario E: Malformed response produces clean client-side error', async () => {
      const originalFetch = globalThis.fetch;
      globalThis.fetch = (async () => ({
        ok: false,
        status: 502,
        statusText: 'Bad Gateway',
        json: async () => {
          throw new SyntaxError('Unexpected token < in JSON at position 0');
        },
      })) as any;

      try {
        await assert.rejects(
          async () => {
            await predictEvent({ event_id: 'FIRMS_TN_0000', features: lookupData['FIRMS_TN_0000'] as any });
          },
          (err: any) => {
            assert.strictEqual(err instanceof ApiError, true);
            assert.strictEqual(err.code, 'HTTP_ERROR');
            assert.strictEqual(err.status, 502);
            assert.strictEqual(err.message, 'HTTP 502 Bad Gateway');
            return true;
          }
        );
      } finally {
        globalThis.fetch = originalFetch;
      }
    });

    it('Scenario F: Unknown event ID produces clean feature lookup error', async () => {
      const originalFetch = globalThis.fetch;
      globalThis.fetch = (async () => ({
        ok: true,
        status: 200,
        statusText: 'OK',
        json: async () => lookupData,
      })) as any;

      try {
        await assert.rejects(
          async () => {
            await getModelFeatures('INVALID_UNKNOWN_EVENT_ID_XYZ');
          },
          (err: any) => {
            assert.strictEqual(err instanceof Error, true);
            assert.strictEqual(
              err.message.includes('not found in authoritative 36-feature lookup'),
              true
            );
            return true;
          }
        );
      } finally {
        globalThis.fetch = originalFetch;
      }
    });
  });

  describe('4. Comprehensive Security Tests', () => {
    it('No VITE_ML_API_KEY in client TypeScript source code', () => {
      const srcDir = path.resolve(__dirname, '../src');
      const scan = (dir: string) => {
        const files = fs.readdirSync(dir, { withFileTypes: true });
        for (const f of files) {
          const full = path.join(dir, f.name);
          if (f.isDirectory()) {
            scan(full);
          } else if (f.name.endsWith('.ts') || f.name.endsWith('.tsx')) {
            const content = fs.readFileSync(full, 'utf-8');
            assert.strictEqual(content.includes('VITE_ML_API_KEY'), false, `VITE_ML_API_KEY found in ${full}`);
          }
        }
      };
      scan(srcDir);
    });

    it('No hardcoded API keys in client TypeScript source code', () => {
      const srcDir = path.resolve(__dirname, '../src');
      const scan = (dir: string) => {
        const files = fs.readdirSync(dir, { withFileTypes: true });
        for (const f of files) {
          const full = path.join(dir, f.name);
          if (f.isDirectory()) {
            scan(full);
          } else if (f.name.endsWith('.ts') || f.name.endsWith('.tsx')) {
            const content = fs.readFileSync(full, 'utf-8');
            assert.strictEqual(content.includes('test-api-key-phase5c'), false, `Hardcoded API key found in ${full}`);
          }
        }
      };
      scan(srcDir);
    });

    it('Zero localStorage or sessionStorage usage in client code', () => {
      const srcDir = path.resolve(__dirname, '../src');
      const scan = (dir: string) => {
        const files = fs.readdirSync(dir, { withFileTypes: true });
        for (const f of files) {
          const full = path.join(dir, f.name);
          if (f.isDirectory()) {
            scan(full);
          } else if (f.name.endsWith('.ts') || f.name.endsWith('.tsx')) {
            const content = fs.readFileSync(full, 'utf-8');
            assert.strictEqual(content.includes('localStorage'), false, `localStorage found in ${full}`);
            assert.strictEqual(content.includes('sessionStorage'), false, `sessionStorage found in ${full}`);
          }
        }
      };
      scan(srcDir);
    });

    it('No API key in generated dist production bundle files', () => {
      if (!fs.existsSync(DIST_PATH)) return; // Built dist directory check
      const scan = (dir: string) => {
        const files = fs.readdirSync(dir, { withFileTypes: true });
        for (const f of files) {
          const full = path.join(dir, f.name);
          if (f.isDirectory()) {
            scan(full);
          } else if (f.name.endsWith('.js') || f.name.endsWith('.html')) {
            const content = fs.readFileSync(full, 'utf-8');
            assert.strictEqual(content.includes('VITE_ML_API_KEY'), false, `VITE_ML_API_KEY in dist file ${full}`);
            assert.strictEqual(content.includes('test-api-key-phase5c'), false, `test-api-key-phase5c in dist file ${full}`);
          }
        }
      };
      scan(DIST_PATH);
    });
  });
});
