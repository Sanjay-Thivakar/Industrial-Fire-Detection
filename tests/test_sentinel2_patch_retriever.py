"""Deterministic unit tests for Sentinel-2 localized AOI retrieval and SCL quality screening.

All tests use synthetic arrays and mocked network calls with ZERO external dependencies.
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.data_ingestion.sentinel2_patch_retriever import (
    compute_localized_aoi_bbox,
    SCLQualityEvaluator,
    Sentinel2ProcessingClient,
    Sentinel2PatchRetriever,
)


class TestLocalizedAOIBoundingBox:
    """Tests for localized AOI bounding box calculation."""

    def test_compute_aoi_bbox_valid(self):
        lat, lon = 11.65394, 78.02792
        patch_size_m = 1000.0  # 1 km x 1 km
        min_lon, min_lat, max_lon, max_lat = compute_localized_aoi_bbox(lat, lon, patch_size_m)

        assert min_lon < lon < max_lon
        assert min_lat < lat < max_lat

        # Check approx span in degrees (~1000m / 111320m/deg ~ 0.00898 deg)
        lat_span = max_lat - min_lat
        assert 0.008 < lat_span < 0.010

    def test_compute_aoi_bbox_invalid_lat(self):
        with pytest.raises(ValueError, match="Latitude"):
            compute_localized_aoi_bbox(95.0, 78.0)

    def test_compute_aoi_bbox_invalid_lon(self):
        with pytest.raises(ValueError, match="Longitude"):
            compute_localized_aoi_bbox(11.0, 195.0)


class TestSCLQualityEvaluator:
    """Tests for separated SCL quality metrics and usability decision logic."""

    def test_clean_surface_usable(self):
        evaluator = SCLQualityEvaluator(min_valid_surface_pct=70.0, max_cloud_pct=20.0)
        # 50x50 pixels: 70% Vegetation (4), 30% Bare surface (5)
        arr = np.full((50, 50), 4, dtype=int)
        arr[:15, :] = 5

        metrics = evaluator.evaluate_scl(arr)
        assert metrics["total_pixels"] == 2500
        assert metrics["valid_surface_pixels"] == 2500
        assert metrics["valid_surface_pct"] == 100.0
        assert metrics["cloud_pixels"] == 0
        assert metrics["cloud_pct"] == 0.0
        assert metrics["usability_status"] == "USABLE"
        assert metrics["raw_scl_histogram"][4] == 1750
        assert metrics["raw_scl_histogram"][5] == 750

    def test_cloudy_aoi_rejected(self):
        evaluator = SCLQualityEvaluator(min_valid_surface_pct=70.0, max_cloud_pct=20.0)
        # 50x50 pixels: 50% Vegetation (4), 50% High probability cloud (9)
        arr = np.full((50, 50), 4, dtype=int)
        arr[:25, :] = 9

        metrics = evaluator.evaluate_scl(arr)
        assert metrics["cloud_pct"] == 50.0
        assert metrics["valid_surface_pct"] == 50.0
        assert metrics["usability_status"] == "REJECTED_LOCAL_CLOUD"
        assert "exceeds maximum allowable threshold" in metrics["decision_reason"]

    def test_cloud_shadow_tracked_separately(self):
        evaluator = SCLQualityEvaluator(min_valid_surface_pct=70.0, max_cloud_pct=20.0)
        # 50x50 pixels: 60% Vegetation (4), 40% Cloud Shadow (3)
        arr = np.full((50, 50), 4, dtype=int)
        arr[:20, :] = 3

        metrics = evaluator.evaluate_scl(arr)
        assert metrics["cloud_shadow_pixels"] == 1000
        assert metrics["cloud_shadow_pct"] == 40.0
        assert metrics["cloud_pct"] == 0.0
        assert metrics["usability_status"] == "REJECTED_CLOUD_SHADOW"

    def test_unclassified_class_7_not_valid_surface(self):
        """Verify SCL class 7 (Unclassified) is strictly NOT counted as valid surface."""
        evaluator = SCLQualityEvaluator(min_valid_surface_pct=70.0, max_cloud_pct=20.0)
        # 50x50 pixels: 100% Unclassified (7)
        arr = np.full((50, 50), 7, dtype=int)

        metrics = evaluator.evaluate_scl(arr)
        assert metrics["valid_surface_pixels"] == 0
        assert metrics["valid_surface_pct"] == 0.0
        assert metrics["unclassified_pixels"] == 2500
        assert metrics["unclassified_pct"] == 100.0
        assert metrics["usability_status"] == "REJECTED_LOW_VALID_SURFACE"

    def test_dark_area_class_2_preserved_separately(self):
        """Verify SCL class 2 (Dark Area) is preserved separately and not in valid surface."""
        evaluator = SCLQualityEvaluator()
        # 50x50 pixels: 50% Vegetation (4), 50% Dark Area (2)
        arr = np.full((50, 50), 4, dtype=int)
        arr[:25, :] = 2

        metrics = evaluator.evaluate_scl(arr)
        assert metrics["dark_area_pixels"] == 1250
        assert metrics["dark_area_pct"] == 50.0
        assert metrics["valid_surface_pixels"] == 1250
        assert metrics["valid_surface_pct"] == 50.0


class TestSentinel2ProcessingClient:
    """Tests for Sentinel Hub Processing API request construction and credential handling."""

    def test_build_process_payload(self):
        client = Sentinel2ProcessingClient(client_id="dummy", client_secret="dummy")
        bbox = (78.02, 11.65, 78.03, 11.66)
        payload = client.build_process_payload(
            bbox=bbox,
            date_str="2024-11-04T05:00:00Z",
            resolution_m=20.0,
            target_bands=["SCL", "B04", "B08", "B11", "B12"],
        )

        assert payload["input"]["bounds"]["bbox"] == list(bbox)
        assert payload["input"]["data"][0]["type"] == "sentinel-2-l2a"
        assert payload["input"]["data"][0]["dataFilter"]["timeRange"]["from"] == "2024-11-04T00:00:00Z"
        assert payload["input"]["data"][0]["dataFilter"]["timeRange"]["to"] == "2024-11-04T23:59:59Z"
        assert "width" in payload["output"]
        assert "height" in payload["output"]
        assert "SCL" in payload["evalscript"]
        assert "B11" in payload["evalscript"]

    def test_request_without_credentials_reports_auth_required(self):
        client = Sentinel2ProcessingClient(client_id=None, client_secret=None)
        bbox = (78.02, 11.65, 78.03, 11.66)
        res = client.request_localized_patch(bbox, "2024-11-04")

        assert res["success"] is False
        assert res["status"] == "AUTH_REQUIRED_FOR_PROCESSING"
        assert "credentials" in res["error_message"].lower()

    @patch("requests.Session.post")
    def test_request_with_mocked_success(self, mock_post):
        client = Sentinel2ProcessingClient(client_id="test_id", client_secret="test_secret")

        # Mock token response then processing response
        mock_token_resp = MagicMock()
        mock_token_resp.status_code = 200
        mock_token_resp.json.return_value = {"access_token": "mocked_jwt_token"}

        mock_proc_resp = MagicMock()
        mock_proc_resp.status_code = 200
        mock_proc_resp.content = b"MOCKED_TIFF_BYTES"

        mock_post.side_effect = [mock_token_resp, mock_proc_resp]

        bbox = (78.02, 11.65, 78.03, 11.66)
        res = client.request_localized_patch(bbox, "2024-11-04")

        assert res["success"] is True
        assert res["status"] == "RETRIEVAL_SUCCESS"
        assert res["size_bytes"] == len(b"MOCKED_TIFF_BYTES")


class TestSentinel2PatchRetriever:
    """Tests for end-to-end patch evaluation logic."""

    def test_missing_observation_evaluation(self):
        retriever = Sentinel2PatchRetriever()
        res = retriever.evaluate_event_observation(
            event_id="FIRMS_TN_0001",
            latitude=11.65,
            longitude=78.02,
            observation_date=None,
            product_id=None,
            product_name=None,
            tile_id=None,
            timing="pre",
        )

        assert res["retrieval_status"] == "MISSING_PRODUCT"
        assert res["scl_usability_status"] == "NOT_EVALUATED"
        assert res["total_pixels"] == 0

    def test_evaluation_without_credentials_graceful(self):
        client = Sentinel2ProcessingClient(client_id=None, client_secret=None)
        retriever = Sentinel2PatchRetriever(processing_client=client)

        res = retriever.evaluate_event_observation(
            event_id="FIRMS_TN_0001",
            latitude=11.65394,
            longitude=78.02792,
            observation_date="2024-10-29T05:08:39Z",
            product_id="prod-123",
            product_name="S2B_MSIL2A_...",
            tile_id="T43PHN",
            timing="pre",
        )

        assert res["retrieval_status"] == "AUTH_REQUIRED_FOR_PROCESSING"
        assert res["expected_dimensions"] == "50x50"
        assert res["bbox_wgs84"] is not None
        assert res["scl_usability_status"] == "NOT_EVALUATED"


class TestCDSETokenRefreshAndHandling:
    """Deterministic unit tests simulating CDSE OAuth2 token expiry and refresh behaviors."""

    def test_valid_token_cached_and_reused(self):
        """Simulate valid token: token is cached and reused within validity period without new network calls."""
        client = Sentinel2ProcessingClient(client_id="mock_id", client_secret="mock_sec")
        mock_token_resp = MagicMock()
        mock_token_resp.status_code = 200
        mock_token_resp.json.return_value = {"access_token": "valid_token_123", "expires_in": 1800}

        with patch.object(client.session, "post", return_value=mock_token_resp) as mock_post:
            ok, token = client.get_auth_token()
            assert ok is True
            assert token == "valid_token_123"
            assert client.is_token_valid() is True
            assert mock_post.call_count == 1

            # Second call should reuse valid token without network request
            ok2, token2 = client.get_auth_token()
            assert ok2 is True
            assert token2 == "valid_token_123"
            assert mock_post.call_count == 1

    def test_expired_token_automatically_refreshes(self):
        """Simulate expired token: when token expires past its epoch, get_auth_token automatically fetches fresh token."""
        client = Sentinel2ProcessingClient(client_id="mock_id", client_secret="mock_sec", token_safety_buffer_seconds=10.0)

        token_resp_1 = MagicMock(status_code=200)
        token_resp_1.json.return_value = {"access_token": "token_generation_1", "expires_in": 50}

        token_resp_2 = MagicMock(status_code=200)
        token_resp_2.json.return_value = {"access_token": "token_generation_2", "expires_in": 1800}

        with patch.object(client.session, "post", side_effect=[token_resp_1, token_resp_2]) as mock_post:
            base_time = 1000000.0
            with patch("time.time", return_value=base_time):
                ok, token = client.get_auth_token()
                assert ok is True
                assert token == "token_generation_1"
                assert mock_post.call_count == 1
                assert client.is_token_valid() is True

            # Advance time by 60s (past 50s expiry)
            with patch("time.time", return_value=base_time + 60.0):
                assert client.is_token_valid() is False
                ok2, token2 = client.get_auth_token()
                assert ok2 is True
                assert token2 == "token_generation_2"
                assert mock_post.call_count == 2
                assert client.is_token_valid() is True

    def test_token_refresh_before_expiry_via_buffer(self):
        """Simulate token refresh before expiry: safety buffer proactively refreshes near-expiration tokens."""
        client = Sentinel2ProcessingClient(client_id="mock_id", client_secret="mock_sec", token_safety_buffer_seconds=60.0)

        token_resp_1 = MagicMock(status_code=200)
        token_resp_1.json.return_value = {"access_token": "token_expiring_soon", "expires_in": 120}

        token_resp_2 = MagicMock(status_code=200)
        token_resp_2.json.return_value = {"access_token": "token_fresh", "expires_in": 1800}

        with patch.object(client.session, "post", side_effect=[token_resp_1, token_resp_2]) as mock_post:
            base_time = 1000000.0
            with patch("time.time", return_value=base_time):
                ok, token = client.get_auth_token()
                assert ok is True
                assert token == "token_expiring_soon"
                assert mock_post.call_count == 1

            # Advance time by 70s -> remaining time is 50s, which is within the 60s safety buffer
            with patch("time.time", return_value=base_time + 70.0):
                # Token has 50s left, buffer is 60s -> invalid
                assert client.is_token_valid() is False
                ok2, token2 = client.get_auth_token()
                assert ok2 is True
                assert token2 == "token_fresh"
                assert mock_post.call_count == 2

    def test_http_401_followed_by_successful_reauthentication_and_retry(self):
        """Simulate HTTP 401: invalidates cached token, obtains fresh token, retries request once successfully."""
        client = Sentinel2ProcessingClient(client_id="mock_id", client_secret="mock_sec")
        client.cached_token = "stale_token_xyz"
        client.token_expiry_epoch = 9999999999.0

        mock_401_resp = MagicMock(status_code=401, text='{"error":"invalid_token","error_description":"Token expired"}')
        mock_token_resp = MagicMock(status_code=200)
        mock_token_resp.json.return_value = {"access_token": "fresh_token_abc", "expires_in": 1800}
        mock_success_proc_resp = MagicMock(status_code=200, content=b"VALID_TIFF_BYTES")

        with patch.object(client.session, "post", side_effect=[mock_401_resp, mock_token_resp, mock_success_proc_resp]) as mock_post:
            bbox = (78.02, 11.65, 78.03, 11.66)
            res = client.request_localized_patch(bbox, "2024-11-04")

            assert res["success"] is True
            assert res["status"] == "RETRIEVAL_SUCCESS"
            assert res["data_bytes"] == b"VALID_TIFF_BYTES"
            assert client.cached_token == "fresh_token_abc"
            assert mock_post.call_count == 3

            # Verify the retried request had the updated Authorization header
            retried_call_kwargs = mock_post.call_args_list[2][1]
            assert retried_call_kwargs["headers"]["Authorization"] == "Bearer fresh_token_abc"

    def test_repeated_401_failure_stops_without_infinite_retry(self):
        """Simulate repeated 401 failure: retries exactly once then cleanly fails with PROCESSING_API_ERROR."""
        client = Sentinel2ProcessingClient(client_id="mock_id", client_secret="mock_sec")
        client.cached_token = "bad_token"
        client.token_expiry_epoch = 9999999999.0

        mock_401_resp1 = MagicMock(status_code=401, text='{"error":"invalid_token"}')
        mock_token_resp = MagicMock(status_code=200)
        mock_token_resp.json.return_value = {"access_token": "still_rejected_token", "expires_in": 1800}
        mock_401_resp2 = MagicMock(status_code=401, text='{"error":"unauthorized_account"}')

        with patch.object(client.session, "post", side_effect=[mock_401_resp1, mock_token_resp, mock_401_resp2]) as mock_post:
            bbox = (78.02, 11.65, 78.03, 11.66)
            res = client.request_localized_patch(bbox, "2024-11-04")

            assert res["success"] is False
            assert res["status"] == "PROCESSING_API_ERROR"
            assert "401" in res["error_message"]
            # Exactly 3 network calls (1 initial + 1 refresh + 1 retry). No infinite loop!
            assert mock_post.call_count == 3
            # Cached token should be invalidated so future calls don't keep using it
            assert client.cached_token is None

    def test_concurrent_token_refresh_thread_safety(self):
        """Verify that concurrent threads calling get_auth_token on an expired token do not make redundant requests."""
        import concurrent.futures

        client = Sentinel2ProcessingClient(client_id="mock_id", client_secret="mock_sec")
        mock_token_resp = MagicMock(status_code=200)
        mock_token_resp.json.return_value = {"access_token": "thread_safe_token", "expires_in": 1800}

        with patch.object(client.session, "post", return_value=mock_token_resp) as mock_post:
            def worker():
                return client.get_auth_token()

            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(worker) for _ in range(10)]
                results = [f.result() for f in futures]

            for ok, token in results:
                assert ok is True
                assert token == "thread_safe_token"

            # Only 1 POST was made across all 10 threads due to thread-safe lock
            assert mock_post.call_count == 1
