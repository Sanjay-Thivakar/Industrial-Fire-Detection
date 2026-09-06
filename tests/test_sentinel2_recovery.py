"""Deterministic unit tests for the Sentinel-2 Processing API Failure Recovery Runner.

All tests use mocks with ZERO live network calls.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from src.feature_engineering.run_sentinel2_recovery import (
    retry_single_observation_with_backoff,
    recover_single_event,
    STATUS_REAL_CDSE_SUCCESS,
    STATUS_CLOUD_REJECTED,
    STATUS_MISSING_PRODUCT,
    STATUS_PROCESSING_API_ERROR,
)


class TestSentinel2RecoveryLogic:
    """Tests for targeted recovery and backoff behavior."""

    def test_backoff_succeeds_on_first_attempt(self):
        processor = MagicMock()
        processor.process_single_observation.return_value = (
            STATUS_REAL_CDSE_SUCCESS,
            "",
            {"s2_ndvi_mean": 0.45},
            True,
            {"pre_spectral_valid_pct": 100.0},
        )

        st, err, s3a, is_real, prov, attempts = retry_single_observation_with_backoff(
            processor=processor,
            event_id="TEST_001",
            latitude=11.0,
            longitude=79.0,
            observation_date="2024-11-04",
            product_id="prod_01",
            timing="pre",
            max_attempts=3,
            initial_backoff=0.01,
            pacing_seconds=0.0,
        )

        assert st == STATUS_REAL_CDSE_SUCCESS
        assert is_real is True
        assert attempts == 1
        assert processor.process_single_observation.call_count == 1

    def test_backoff_retries_transient_error_and_succeeds(self):
        processor = MagicMock()
        # First call fails with 500 API error, second call succeeds
        processor.process_single_observation.side_effect = [
            (STATUS_PROCESSING_API_ERROR, "HTTP 502 Bad Gateway", None, False, {}),
            (STATUS_REAL_CDSE_SUCCESS, "", {"s2_ndvi_mean": 0.50}, True, {}),
        ]

        st, err, s3a, is_real, prov, attempts = retry_single_observation_with_backoff(
            processor=processor,
            event_id="TEST_002",
            latitude=11.0,
            longitude=79.0,
            observation_date="2024-11-04",
            product_id="prod_01",
            timing="pre",
            max_attempts=3,
            initial_backoff=0.01,
            pacing_seconds=0.0,
        )

        assert st == STATUS_REAL_CDSE_SUCCESS
        assert is_real is True
        assert attempts == 2
        assert processor.process_single_observation.call_count == 2

    def test_backoff_exhausts_retries_and_returns_failure(self):
        processor = MagicMock()
        # All 3 calls fail with 500 API error
        processor.process_single_observation.return_value = (
            STATUS_PROCESSING_API_ERROR, "HTTP 500 Gateway Timeout", None, False, {}
        )

        st, err, s3a, is_real, prov, attempts = retry_single_observation_with_backoff(
            processor=processor,
            event_id="TEST_003",
            latitude=11.0,
            longitude=79.0,
            observation_date="2024-11-04",
            product_id="prod_01",
            timing="pre",
            max_attempts=3,
            initial_backoff=0.01,
            pacing_seconds=0.0,
        )

        assert st == STATUS_PROCESSING_API_ERROR
        assert is_real is False
        assert attempts == 3
        assert processor.process_single_observation.call_count == 3

    def test_recover_single_event_preserves_unretried_window(self):
        """When retry_post=False, post window is not retried and existing MISSING_PRODUCT is preserved."""
        processor = MagicMock()
        # Pre succeeds
        processor.process_single_observation.return_value = (
            STATUS_REAL_CDSE_SUCCESS, "", {"s2_ndvi_mean": 0.60}, True, {"pre_spectral_valid_pct": 100.0}
        )
        processor.change_calculator.compute_change_features.return_value = {
            "s2_change_status": "POST_UNAVAILABLE",
            "s2_dndvi_mean": np.nan,
        }

        retry_row = pd.Series({
            "event_id": "TEST_004",
            "retry_pre": True,
            "retry_post": False,
        })

        base_record = {
            "event_id": "TEST_004",
            "latitude": 11.5,
            "longitude": 79.5,
            "selected_pre_image_date": "2024-11-01",
            "pre_product_id": "prod_pre",
            "selected_post_image_date": None,
            "post_product_id": None,
            "post_observation_status": STATUS_MISSING_PRODUCT,
            "post_observation_failure_reason": "No usable post product matched",
        }

        rec, manifest_row = recover_single_event(
            processor=processor,
            retry_row=retry_row,
            base_cache_record=base_record,
            pacing_seconds=0.0,
        )

        # Only 1 call made for pre; post was never queried
        assert processor.process_single_observation.call_count == 1
        assert manifest_row["retry_pre_attempted"] is True
        assert manifest_row["retry_post_attempted"] is False
        assert manifest_row["pre_status"] == STATUS_REAL_CDSE_SUCCESS
        assert manifest_row["post_status"] == STATUS_MISSING_PRODUCT
        assert rec["processing_status"] == "PARTIAL_PRE_ONLY"
        assert rec["is_real_cdse_data"] is True
