"""Deterministic unit and integration tests for CDSE Authentication and Real Smoke Test (Step 3D).

All tests use in-memory synthetic GeoTIFF byte streams and mocked network calls
with ZERO live CDSE network dependency.
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from rasterio.io import MemoryFile

from src.data_ingestion.sentinel2_patch_retriever import Sentinel2ProcessingClient
from src.feature_engineering.sentinel2_spectral import Sentinel2SpectralExtractor
from src.feature_engineering.sentinel2_change import Sentinel2ChangeFeatureCalculator
from src.feature_engineering.sentinel2_real_smoketest import (
    Sentinel2SmokeTester,
    STATUS_REAL_CDSE_SUCCESS,
    STATUS_AUTH_REQUIRED,
    STATUS_CLOUD_REJECTED,
    STATUS_MISSING_PRODUCT,
    STATUS_PROCESSING_API_ERROR,
    STATUS_PROCESSING_FAILED,
)


def _make_geotiff_bytes(
    scl_arr: np.ndarray,
    b04_arr: np.ndarray,
    b08_arr: np.ndarray,
    b11_arr: np.ndarray,
    b12_arr: np.ndarray,
) -> bytes:
    """Helper to generate in-memory 5-band GeoTIFF bytes matching CDSE API responses."""
    h, w = scl_arr.shape
    stack = np.stack([scl_arr, b04_arr, b08_arr, b11_arr, b12_arr]).astype(np.uint16)
    with MemoryFile() as memfile:
        with memfile.open(
            driver="GTiff",
            height=h,
            width=w,
            count=5,
            dtype="uint16",
        ) as dst:
            dst.write(stack)
        return memfile.read()


class TestCDSEAuthentication:
    """Tests for CDSE OAuth2 token exchange and credential handling."""

    def test_token_exchange_and_caching(self):
        client = Sentinel2ProcessingClient(client_id="test_client_id", client_secret="test_secret")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"access_token": "mocked_access_jwt_token_12345"}

        with patch.object(client.session, "post", return_value=mock_resp) as mock_post:
            ok, token = client.get_auth_token()
            assert ok is True
            assert token == "mocked_access_jwt_token_12345"
            assert client.cached_token == token
            assert mock_post.call_count == 1

            # Second call uses cached token without network request
            ok2, token2 = client.get_auth_token()
            assert ok2 is True
            assert token2 == token
            assert mock_post.call_count == 1

    def test_unauthenticated_client_rejects_without_network_call(self):
        client = Sentinel2ProcessingClient(client_id=None, client_secret=None)
        assert client.has_credentials() is False

        with patch.object(client.session, "post") as mock_post:
            ok, err = client.get_auth_token()
            assert ok is False
            assert "credentials" in err.lower()
            mock_post.assert_not_called()


class TestRealSmokeTester:
    """Tests for Sentinel2SmokeTester execution pipeline."""

    @pytest.fixture
    def authenticated_client(self):
        return Sentinel2ProcessingClient(client_id="mock_id", client_secret="mock_secret")

    @pytest.fixture
    def unauthenticated_client(self):
        return Sentinel2ProcessingClient(client_id=None, client_secret=None)

    def test_mocked_live_observation_success(self, authenticated_client):
        """Success criteria 1-6: Process actual multi-band GeoTIFF bytes through Step 3A."""
        scl = np.full((50, 50), 4, dtype=np.uint16)  # Vegetation
        b04 = np.full((50, 50), 750, dtype=np.uint16)
        b08 = np.full((50, 50), 3000, dtype=np.uint16)
        b11 = np.full((50, 50), 1500, dtype=np.uint16)
        b12 = np.full((50, 50), 750, dtype=np.uint16)
        tiff_bytes = _make_geotiff_bytes(scl, b04, b08, b11, b12)

        with patch.object(authenticated_client, "request_localized_patch") as mock_req:
            mock_req.return_value = {
                "success": True,
                "status": "RETRIEVAL_SUCCESS",
                "data_bytes": tiff_bytes,
                "size_bytes": len(tiff_bytes),
            }

            tester = Sentinel2SmokeTester(processing_client=authenticated_client)
            st, reason, s3a_feats, is_real, prov = tester.process_observation(
                event_id="FIRMS_TN_0007",
                latitude=11.18312,
                longitude=79.09965,
                observation_date="2024-10-29T05:08:39Z",
                product_id="prod_01",
                timing="pre",
            )

            assert st == STATUS_REAL_CDSE_SUCCESS
            assert reason == ""
            assert is_real is True
            assert s3a_feats is not None
            assert s3a_feats["s2_feature_status"] == "SUCCESS"
            assert s3a_feats["s2_spectral_valid_pixels"] == 2500
            assert s3a_feats["s2_spectral_valid_pct"] == 100.0

            # NDVI = (3000 - 750) / (3000 + 750) = 2250 / 3750 = 0.60
            assert pytest.approx(s3a_feats["s2_ndvi_mean"], rel=1e-5) == 0.60
            # NBR = (3000 - 750) / (3000 + 750) = 0.60
            assert pytest.approx(s3a_feats["s2_nbr_mean"], rel=1e-5) == 0.60
            # SWIR Ratio = 750 / 1500 = 0.50
            assert pytest.approx(s3a_feats["s2_swir_ratio_mean"], rel=1e-5) == 0.50

            # Verify provenance
            assert prov["pre_scl_valid_pixels"] == 2500
            assert prov["pre_scl_valid_pct"] == 100.0
            assert prov["pre_raster_dimensions"] == "50x50"
            assert "SCL" in prov["pre_bands_requested"]
            assert "B12" in prov["pre_bands_requested"]

    def test_mocked_end_to_end_event_success(self, authenticated_client):
        """Success criteria 7: Real pre/post features pass through Step 3B change calculation."""
        # Pre: Healthy vegetation (NDVI=0.60)
        scl_pre = np.full((50, 50), 4, dtype=np.uint16)
        b04_pre = np.full((50, 50), 750, dtype=np.uint16)
        b08_pre = np.full((50, 50), 3000, dtype=np.uint16)
        b11_pre = np.full((50, 50), 1500, dtype=np.uint16)
        b12_pre = np.full((50, 50), 750, dtype=np.uint16)
        pre_bytes = _make_geotiff_bytes(scl_pre, b04_pre, b08_pre, b11_pre, b12_pre)

        # Post: Surface disturbance (NDVI=(1600-1200)/(1600+1200)=400/2800=0.1429)
        scl_post = np.full((50, 50), 5, dtype=np.uint16)  # Bare/disturbed surface
        b04_post = np.full((50, 50), 1200, dtype=np.uint16)
        b08_post = np.full((50, 50), 1600, dtype=np.uint16)
        b11_post = np.full((50, 50), 2200, dtype=np.uint16)
        b12_post = np.full((50, 50), 1800, dtype=np.uint16)
        post_bytes = _make_geotiff_bytes(scl_post, b04_post, b08_post, b11_post, b12_post)

        with patch.object(authenticated_client, "request_localized_patch") as mock_req:
            mock_req.side_effect = [
                {"success": True, "status": "RETRIEVAL_SUCCESS", "data_bytes": pre_bytes},
                {"success": True, "status": "RETRIEVAL_SUCCESS", "data_bytes": post_bytes},
            ]

            tester = Sentinel2SmokeTester(processing_client=authenticated_client)
            event_row = pd.Series({
                "event_id": "FIRMS_TN_0007",
                "latitude": 11.18312,
                "longitude": 79.09965,
                "acquisition_date": "2024-11-04",
                "candidate_priority": "HIGH",
                "landcover_class": "Built-up",
                "frp": 1.23,
                "selected_pre_image_date": "2024-10-29T05:08:39Z",
                "pre_product_id": "prod_pre",
                "selected_post_image_date": "2024-11-10T05:00:31Z",
                "post_product_id": "prod_post",
            })

            rec = tester.run_event_smoketest(event_row)

            assert rec["smoketest_status"] == STATUS_REAL_CDSE_SUCCESS
            assert rec["is_real_cdse_data"] is True
            assert rec["s2_change_status"] == "SUCCESS"

            # Check dNDVI
            expected_dndvi = (400.0 / 2800.0) - 0.60
            assert pytest.approx(rec["s2_dndvi_mean"], rel=1e-4) == expected_dndvi
            assert rec["s2_dndvi_mean"] < 0
            assert pytest.approx(rec["s2_abs_dndvi_mean"], rel=1e-4) == abs(expected_dndvi)

    def test_cloud_rejected_observation(self, authenticated_client):
        """Observation with 100% Cloud SCL (class 9) is categorized as CLOUD_REJECTED."""
        scl_cloud = np.full((50, 50), 9, dtype=np.uint16)  # High probability cloud
        b04 = np.full((50, 50), 5000, dtype=np.uint16)
        b08 = np.full((50, 50), 6000, dtype=np.uint16)
        b11 = np.full((50, 50), 4000, dtype=np.uint16)
        b12 = np.full((50, 50), 3500, dtype=np.uint16)
        cloud_bytes = _make_geotiff_bytes(scl_cloud, b04, b08, b11, b12)

        with patch.object(authenticated_client, "request_localized_patch") as mock_req:
            mock_req.return_value = {
                "success": True,
                "status": "RETRIEVAL_SUCCESS",
                "data_bytes": cloud_bytes,
            }

            tester = Sentinel2SmokeTester(processing_client=authenticated_client)
            st, reason, feats, is_real, prov = tester.process_observation(
                event_id="EV_CLOUD",
                latitude=11.0,
                longitude=79.0,
                observation_date="2024-11-04",
                product_id="prod_c",
                timing="post",
            )

            assert st == STATUS_CLOUD_REJECTED
            assert "Valid surface pixel coverage too low" in reason
            assert is_real is True
            assert prov["post_scl_valid_pixels"] == 0

    def test_unauthenticated_client_stops_safely(self, unauthenticated_client):
        """When credentials are not configured, pipeline stops cleanly with AUTH_REQUIRED."""
        tester = Sentinel2SmokeTester(processing_client=unauthenticated_client)
        event_row = pd.Series({
            "event_id": "EV_NO_AUTH",
            "latitude": 11.0,
            "longitude": 79.0,
            "acquisition_date": "2024-11-04",
            "candidate_priority": "HIGH",
            "landcover_class": "Built-up",
            "selected_pre_image_date": "2024-10-29",
            "pre_product_id": "prod_pre",
            "selected_post_image_date": "2024-11-10",
            "post_product_id": "prod_post",
        })

        rec = tester.run_event_smoketest(event_row)
        assert rec["smoketest_status"] == STATUS_AUTH_REQUIRED
        assert rec["is_real_cdse_data"] is False
        assert "credentials" in rec["failure_reason"].lower()

    def test_processing_api_error_handling(self, authenticated_client):
        with patch.object(authenticated_client, "request_localized_patch") as mock_req:
            mock_req.return_value = {
                "success": False,
                "status": "PROCESSING_API_ERROR",
                "error_message": "Gateway Timeout 504",
            }
            tester = Sentinel2SmokeTester(processing_client=authenticated_client)
            event_row = pd.Series({
                "event_id": "EV_ERR",
                "latitude": 11.0,
                "longitude": 79.0,
                "acquisition_date": "2024-11-04",
                "selected_pre_image_date": "2024-10-29",
                "selected_post_image_date": "2024-11-10",
            })
            rec = tester.run_event_smoketest(event_row)
            assert rec["smoketest_status"] == STATUS_PROCESSING_API_ERROR
            assert "504" in rec["failure_reason"]
