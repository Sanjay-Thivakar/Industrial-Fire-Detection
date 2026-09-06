"""Deterministic unit and integration tests for Real Sentinel-2 CDSE Processing (Step 3C).

All tests use in-memory synthetic GeoTIFF byte streams and mocked network responses
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
from src.feature_engineering.sentinel2_real_processor import (
    parse_geotiff_bands,
    Sentinel2RealProcessor,
    STATUS_REAL_CDSE_SUCCESS,
    STATUS_AUTH_REQUIRED,
    STATUS_MISSING_PRODUCT,
    STATUS_PROCESSING_API_ERROR,
    STATUS_CORRUPT_RASTER,
    TARGET_BANDS,
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


class TestGeoTIFFParsing:
    """Tests for raw GeoTIFF unpacking, band assignment, and shape verification."""

    def test_parse_valid_geotiff(self):
        scl = np.full((50, 50), 4, dtype=np.uint16)
        b04 = np.full((50, 50), 800, dtype=np.uint16)
        b08 = np.full((50, 50), 3000, dtype=np.uint16)
        b11 = np.full((50, 50), 1500, dtype=np.uint16)
        b12 = np.full((50, 50), 900, dtype=np.uint16)

        data_bytes = _make_geotiff_bytes(scl, b04, b08, b11, b12)
        bands = parse_geotiff_bands(data_bytes, expected_shape=(50, 50))

        assert set(bands.keys()) == {"SCL", "B04", "B08", "B11", "B12"}
        assert bands["SCL"].shape == (50, 50)
        assert bands["SCL"].dtype == int
        assert bands["B04"].shape == (50, 50)
        assert bands["B04"].dtype == np.float64
        assert np.array_equal(bands["SCL"], scl)
        assert np.array_equal(bands["B08"], b08)

    def test_parse_empty_bytes_raises(self):
        with pytest.raises(ValueError, match="Empty raster"):
            parse_geotiff_bands(b"")

    def test_parse_corrupt_bytes_raises(self):
        with pytest.raises(ValueError, match="Failed to read"):
            parse_geotiff_bands(b"NOT_A_TIFF_HEADER")

    def test_parse_dimension_mismatch_raises(self):
        scl = np.full((30, 30), 4, dtype=np.uint16)
        b04 = np.full((30, 30), 800, dtype=np.uint16)
        b08 = np.full((30, 30), 3000, dtype=np.uint16)
        b11 = np.full((30, 30), 1500, dtype=np.uint16)
        b12 = np.full((30, 30), 900, dtype=np.uint16)

        data_bytes = _make_geotiff_bytes(scl, b04, b08, b11, b12)
        with pytest.raises(ValueError, match="dimensions"):
            parse_geotiff_bands(data_bytes, expected_shape=(50, 50))


class TestSentinel2RealProcessor:
    """Tests for end-to-end Step 3C pipeline behavior."""

    @pytest.fixture
    def mock_client_with_creds(self):
        client = Sentinel2ProcessingClient(client_id="test_id", client_secret="test_secret")
        return client

    @pytest.fixture
    def mock_client_no_creds(self):
        client = Sentinel2ProcessingClient(client_id=None, client_secret=None)
        return client

    def test_missing_observation_date_handling(self, mock_client_with_creds):
        processor = Sentinel2RealProcessor(processing_client=mock_client_with_creds)
        st, reason, feats, is_real = processor.process_single_observation(
            event_id="EV_01",
            latitude=11.18,
            longitude=79.10,
            observation_date=None,
            product_id=None,
            timing="pre",
        )
        assert st == STATUS_MISSING_PRODUCT
        assert "catalogue search" in reason
        assert feats is None
        assert is_real is False

    def test_unauthenticated_client_reports_auth_required(self, mock_client_no_creds):
        processor = Sentinel2RealProcessor(processing_client=mock_client_no_creds)
        st, reason, feats, is_real = processor.process_single_observation(
            event_id="EV_01",
            latitude=11.18,
            longitude=79.10,
            observation_date="2024-10-29T05:08:39Z",
            product_id="prod_123",
            timing="pre",
        )
        assert st == STATUS_AUTH_REQUIRED
        assert "credentials" in reason.lower()
        assert feats is None
        assert is_real is False

    def test_api_error_response_handling(self, mock_client_with_creds):
        with patch.object(mock_client_with_creds, "request_localized_patch") as mock_req:
            mock_req.return_value = {
                "success": False,
                "status": "PROCESSING_API_ERROR",
                "error_message": "Internal Server Error 500",
            }
            processor = Sentinel2RealProcessor(processing_client=mock_client_with_creds)
            st, reason, feats, is_real = processor.process_single_observation(
                event_id="EV_01",
                latitude=11.18,
                longitude=79.10,
                observation_date="2024-10-29T05:08:39Z",
                product_id="prod_123",
                timing="pre",
            )
            assert st == STATUS_PROCESSING_API_ERROR
            assert "500" in reason
            assert feats is None
            assert is_real is False

    def test_successful_observation_processing_with_mocked_cdse_geotiff(self, mock_client_with_creds):
        """Verify successful GeoTIFF parsing and Step 3A feature extraction on mocked CDSE response."""
        scl = np.full((50, 50), 4, dtype=np.uint16)  # 100% Vegetation
        scl[:10, :] = 9                             # 20% Cloud (SCL=9)
        b04 = np.full((50, 50), 800, dtype=np.uint16)
        b08 = np.full((50, 50), 3200, dtype=np.uint16)
        b11 = np.full((50, 50), 1600, dtype=np.uint16)
        b12 = np.full((50, 50), 800, dtype=np.uint16)

        tiff_bytes = _make_geotiff_bytes(scl, b04, b08, b11, b12)

        with patch.object(mock_client_with_creds, "request_localized_patch") as mock_req:
            mock_req.return_value = {
                "success": True,
                "status": "RETRIEVAL_SUCCESS",
                "data_bytes": tiff_bytes,
                "size_bytes": len(tiff_bytes),
            }

            processor = Sentinel2RealProcessor(processing_client=mock_client_with_creds)
            st, reason, feats, is_real = processor.process_single_observation(
                event_id="EV_01",
                latitude=11.18312,
                longitude=79.09965,
                observation_date="2024-10-29T05:08:39Z",
                product_id="prod_123",
                timing="pre",
            )

            assert st == STATUS_REAL_CDSE_SUCCESS
            assert reason == ""
            assert is_real is True
            assert feats is not None
            assert feats["s2_feature_status"] == "SUCCESS"
            # 80% valid surface (40 rows x 50 cols = 2000 pixels)
            assert feats["s2_spectral_valid_pixels"] == 2000
            assert feats["s2_spectral_valid_pct"] == 80.0
            # NDVI = (3200 - 800) / (3200 + 800) = 2400 / 4000 = 0.60
            assert pytest.approx(feats["s2_ndvi_mean"], rel=1e-5) == 0.60
            # NBR = (3200 - 800) / (3200 + 800) = 0.60
            assert pytest.approx(feats["s2_nbr_mean"], rel=1e-5) == 0.60
            # SWIR Ratio = 800 / 1600 = 0.50
            assert pytest.approx(feats["s2_swir_ratio_mean"], rel=1e-5) == 0.50

    def test_end_to_end_event_processing_with_mocked_cdse_data(self, mock_client_with_creds):
        """Verify full pre/post pipeline produces Step 3A features and Step 3B change features."""
        # Pre-event: Healthy vegetation (NDVI=0.60, NBR=0.60)
        scl_pre = np.full((50, 50), 4, dtype=np.uint16)
        b04_pre = np.full((50, 50), 800, dtype=np.uint16)
        b08_pre = np.full((50, 50), 3200, dtype=np.uint16)
        b11_pre = np.full((50, 50), 1600, dtype=np.uint16)
        b12_pre = np.full((50, 50), 800, dtype=np.uint16)
        pre_bytes = _make_geotiff_bytes(scl_pre, b04_pre, b08_pre, b11_pre, b12_pre)

        # Post-event: Disturbed surface (depressed NIR, elevated SWIR)
        scl_post = np.full((50, 50), 5, dtype=np.uint16)  # Bare/disturbed
        b04_post = np.full((50, 50), 1200, dtype=np.uint16)
        b08_post = np.full((50, 50), 1500, dtype=np.uint16)
        b11_post = np.full((50, 50), 2200, dtype=np.uint16)
        b12_post = np.full((50, 50), 1800, dtype=np.uint16)
        post_bytes = _make_geotiff_bytes(scl_post, b04_post, b08_post, b11_post, b12_post)

        with patch.object(mock_client_with_creds, "request_localized_patch") as mock_req:
            mock_req.side_effect = [
                {"success": True, "status": "RETRIEVAL_SUCCESS", "data_bytes": pre_bytes},
                {"success": True, "status": "RETRIEVAL_SUCCESS", "data_bytes": post_bytes},
            ]

            processor = Sentinel2RealProcessor(processing_client=mock_client_with_creds)
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
                "pre_product_name": "S2B_MSIL2A_pre",
                "pre_tile_id": "T44PKT",
                "selected_post_image_date": "2024-11-10T05:00:31Z",
                "post_product_id": "prod_post",
                "post_product_name": "S2A_MSIL2A_post",
                "post_tile_id": "T44PKT",
            })

            rec = processor.process_event(event_row)

            assert rec["processing_status"] == STATUS_REAL_CDSE_SUCCESS
            assert rec["is_real_cdse_data"] is True
            assert rec["s2_change_status"] == "SUCCESS"

            # Pre NDVI = 0.60, Post NDVI = (1500 - 1200) / (1500 + 1200) = 300 / 2700 = 0.1111
            expected_dndvi = (300.0 / 2700.0) - 0.60
            assert pytest.approx(rec["s2_dndvi_mean"], rel=1e-4) == expected_dndvi
            assert rec["s2_dndvi_mean"] < 0  # negative change
            assert pytest.approx(rec["s2_abs_dndvi_mean"], rel=1e-4) == abs(expected_dndvi)

            # Pre NBR = 0.60, Post NBR = (1500 - 1800) / (1500 + 1800) = -300 / 3300 = -0.0909
            expected_dnbr = (-300.0 / 3300.0) - 0.60
            assert pytest.approx(rec["s2_dnbr_mean"], rel=1e-4) == expected_dnbr

    def test_unauthenticated_prototype_events_halt_gracefully(self, mock_client_no_creds):
        """Verify that when credentials are not configured, prototype halts at authentication."""
        processor = Sentinel2RealProcessor(processing_client=mock_client_no_creds)
        df_in = pd.DataFrame([
            {
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
            },
            {
                "event_id": "FIRMS_TN_0087",
                "latitude": 11.18143,
                "longitude": 79.09660,
                "acquisition_date": "2024-12-04",
                "candidate_priority": "HIGH",
                "landcover_class": "Cropland",
                "frp": 1.08,
                "selected_pre_image_date": None,  # missing pre
                "pre_product_id": None,
                "selected_post_image_date": "2024-12-08T05:11:19Z",
                "post_product_id": "prod_post",
            },
        ])

        rec0 = processor.process_event(df_in.iloc[0])
        assert rec0["processing_status"] == STATUS_AUTH_REQUIRED
        assert rec0["is_real_cdse_data"] is False
        assert "credentials" in rec0["failure_reason"].lower()

        rec1 = processor.process_event(df_in.iloc[1])
        # Post requires auth, pre was missing from catalogue
        assert rec1["processing_status"] == STATUS_AUTH_REQUIRED
        assert rec1["pre_observation_status"] == STATUS_MISSING_PRODUCT
        assert rec1["post_observation_status"] == STATUS_AUTH_REQUIRED

    def test_all_output_keys_namespace_compliance(self, mock_client_with_creds):
        """All Sentinel-2 spectral and change keys must start with s2_."""
        scl = np.full((50, 50), 4, dtype=np.uint16)
        b04 = np.full((50, 50), 800, dtype=np.uint16)
        b08 = np.full((50, 50), 3000, dtype=np.uint16)
        b11 = np.full((50, 50), 1500, dtype=np.uint16)
        b12 = np.full((50, 50), 900, dtype=np.uint16)
        tiff_bytes = _make_geotiff_bytes(scl, b04, b08, b11, b12)

        with patch.object(mock_client_with_creds, "request_localized_patch") as mock_req:
            mock_req.return_value = {
                "success": True,
                "status": "RETRIEVAL_SUCCESS",
                "data_bytes": tiff_bytes,
            }

            processor = Sentinel2RealProcessor(processing_client=mock_client_with_creds)
            event_row = pd.Series({
                "event_id": "EV_TEST",
                "latitude": 11.0,
                "longitude": 79.0,
                "acquisition_date": "2024-11-04",
                "candidate_priority": "HIGH",
                "landcover_class": "Built-up",
                "frp": 1.0,
                "selected_pre_image_date": "2024-10-29",
                "selected_post_image_date": "2024-11-10",
            })
            rec = processor.process_event(event_row)

            # Check that change and spectral keys follow s2_ prefix convention
            s2_keys = [k for k in rec.keys() if k.startswith("s2_")]
            assert len(s2_keys) >= 40  # pre s3a + post s3a + change keys
            assert "s2_change_status" in rec
            assert "s2_dndvi_mean" in rec
            assert "s2_pre_ndvi_mean" in rec
            assert "s2_post_ndvi_mean" in rec
