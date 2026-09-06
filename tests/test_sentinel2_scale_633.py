"""Deterministic unit and integration tests for Scaled Sentinel-2 Real Processing (Step 3E).

All tests use in-memory synthetic GeoTIFF byte streams and mocked network calls
with ZERO live CDSE network dependency.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from rasterio.io import MemoryFile

from src.data_ingestion.sentinel2_patch_retriever import Sentinel2ProcessingClient
from src.feature_engineering.sentinel2_scale_processor import (
    Sentinel2ScaleProcessor,
    STATUS_REAL_CDSE_SUCCESS,
    STATUS_PARTIAL_PRE_ONLY,
    STATUS_PARTIAL_POST_ONLY,
    STATUS_CLOUD_REJECTED,
    STATUS_AUTH_REQUIRED,
    STATUS_MISSING_PRODUCT,
)


def _make_geotiff_bytes(
    scl_arr: np.ndarray,
    b04_arr: np.ndarray,
    b08_arr: np.ndarray,
    b11_arr: np.ndarray,
    b12_arr: np.ndarray,
) -> bytes:
    """Generate in-memory 5-band GeoTIFF bytes matching CDSE API responses."""
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


class TestScaledSentinel2Processing:
    """Tests for Sentinel2ScaleProcessor scaling logic."""

    @pytest.fixture
    def authoritative_df(self):
        csv_path = Path("outputs/ground_truth_investigation/validation_candidates_v2.csv")
        assert csv_path.exists(), f"Authoritative dataset not found at {csv_path}"
        df = pd.read_csv(csv_path)
        return df

    def test_authoritative_dataset_integrity(self, authoritative_df):
        """Verify authoritative FIRMS dataset matches 633 unique events requirement."""
        assert len(authoritative_df) == 633
        assert authoritative_df["event_id"].nunique() == 633
        assert not authoritative_df["event_id"].isnull().any()
        assert not authoritative_df["latitude"].isnull().any()
        assert not authoritative_df["longitude"].isnull().any()
        assert not authoritative_df["acq_date"].isnull().any()

    def test_unauthenticated_scaling_preserves_rows_and_reports_auth_required(self, authoritative_df, tmp_path, monkeypatch):
        """Verify that without credentials, all rows are preserved with AUTH_REQUIRED and no synthetic data."""
        monkeypatch.delenv("CDSE_CLIENT_ID", raising=False)
        monkeypatch.delenv("CDSE_CLIENT_SECRET", raising=False)
        client = Sentinel2ProcessingClient(client_id=None, client_secret=None)
        processor = Sentinel2ScaleProcessor(processing_client=client)

        sample_subset = authoritative_df.iloc[:5].copy()
        df_out = processor.process_all_events(sample_subset, output_dir=tmp_path, resume=False)

        assert len(df_out) == 5
        assert (df_out["processing_status"] == STATUS_AUTH_REQUIRED).all()
        assert (df_out["is_real_cdse_data"] == False).all()
        assert "credentials" in df_out["failure_reason"].iloc[0].lower()

        # Verify output files
        assert (tmp_path / "sentinel2_real_633_events.csv").exists()
        assert (tmp_path / "SENTINEL2_633_PROCESSING_REPORT.md").exists()

    def test_mocked_live_scaling_batch_statuses(self, tmp_path):
        """Verify mock successful CDSE responses produce REAL_CDSE_SUCCESS, PARTIAL, and CLOUD_REJECTED."""
        client = Sentinel2ProcessingClient(client_id="mock_id", client_secret="mock_secret")

        # Create valid vegetation patch
        scl_veg = np.full((50, 50), 4, dtype=np.uint16)
        b04 = np.full((50, 50), 800, dtype=np.uint16)
        b08 = np.full((50, 50), 3000, dtype=np.uint16)
        b11 = np.full((50, 50), 1500, dtype=np.uint16)
        b12 = np.full((50, 50), 800, dtype=np.uint16)
        veg_bytes = _make_geotiff_bytes(scl_veg, b04, b08, b11, b12)

        # Create cloud patch
        scl_cloud = np.full((50, 50), 9, dtype=np.uint16)
        cloud_bytes = _make_geotiff_bytes(scl_cloud, b04, b08, b11, b12)

        # Test events
        events = pd.DataFrame([
            {
                "event_id": "EV_FULL",
                "latitude": 11.0,
                "longitude": 79.0,
                "acq_date": "2024-11-04",
                "selected_pre_image_date": "2024-10-29",
                "selected_post_image_date": "2024-11-10",
            },
            {
                "event_id": "EV_PRE_ONLY",
                "latitude": 11.1,
                "longitude": 79.1,
                "acq_date": "2024-11-05",
                "selected_pre_image_date": "2024-10-30",
                "selected_post_image_date": None,  # missing post
            },
            {
                "event_id": "EV_POST_CLOUD",
                "latitude": 11.2,
                "longitude": 79.2,
                "acq_date": "2024-11-06",
                "selected_pre_image_date": "2024-10-31",
                "selected_post_image_date": "2024-11-12",
            },
            {
                "event_id": "EV_NO_PROD",
                "latitude": 11.3,
                "longitude": 79.3,
                "acq_date": "2024-11-07",
                "selected_pre_image_date": None,
                "selected_post_image_date": None,
            },
        ])

        with patch.object(client, "request_localized_patch") as mock_req:
            # Responses:
            # EV_FULL: pre veg, post veg
            # EV_PRE_ONLY: pre veg (post is None)
            # EV_POST_CLOUD: pre veg, post cloud
            mock_req.side_effect = [
                {"success": True, "status": "RETRIEVAL_SUCCESS", "data_bytes": veg_bytes},
                {"success": True, "status": "RETRIEVAL_SUCCESS", "data_bytes": veg_bytes},
                {"success": True, "status": "RETRIEVAL_SUCCESS", "data_bytes": veg_bytes},
                {"success": True, "status": "RETRIEVAL_SUCCESS", "data_bytes": veg_bytes},
                {"success": True, "status": "RETRIEVAL_SUCCESS", "data_bytes": cloud_bytes},
            ]

            processor = Sentinel2ScaleProcessor(processing_client=client)
            with patch.object(processor.matcher, "match_event", return_value={"selected_pre_image_date": None, "selected_post_image_date": None}):
                df_out = processor.process_all_events(events, output_dir=tmp_path, resume=False)

            assert len(df_out) == 4
            assert df_out.loc[df_out["event_id"] == "EV_FULL", "processing_status"].iloc[0] == STATUS_REAL_CDSE_SUCCESS
            assert df_out.loc[df_out["event_id"] == "EV_PRE_ONLY", "processing_status"].iloc[0] == STATUS_PARTIAL_PRE_ONLY
            assert df_out.loc[df_out["event_id"] == "EV_POST_CLOUD", "processing_status"].iloc[0] == STATUS_PARTIAL_PRE_ONLY
            assert df_out.loc[df_out["event_id"] == "EV_POST_CLOUD", "post_observation_status"].iloc[0] == STATUS_CLOUD_REJECTED
            assert df_out.loc[df_out["event_id"] == "EV_NO_PROD", "processing_status"].iloc[0] == STATUS_MISSING_PRODUCT

    def test_resumable_caching(self, tmp_path):
        """Verify that cached events are loaded from disk without re-processing."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        # Pre-populate cache for EV_CACHED
        cached_record = {
            "event_id": "EV_CACHED",
            "processing_status": STATUS_REAL_CDSE_SUCCESS,
            "is_real_cdse_data": True,
            "s2_dndvi_mean": -0.25,
        }
        with open(cache_dir / "EV_CACHED.json", "w") as f:
            json.dump(cached_record, f)

        client = Sentinel2ProcessingClient(client_id="mock_id", client_secret="mock_secret")
        processor = Sentinel2ScaleProcessor(processing_client=client, cache_dir=cache_dir)

        events = pd.DataFrame([{"event_id": "EV_CACHED"}])
        with patch.object(client, "request_localized_patch") as mock_req:
            df_out = processor.process_all_events(events, output_dir=tmp_path, resume=True)
            mock_req.assert_not_called()  # Reused from cache!
            assert len(df_out) == 1
            assert df_out["event_id"].iloc[0] == "EV_CACHED"
            assert df_out["processing_status"].iloc[0] == STATUS_REAL_CDSE_SUCCESS
            assert df_out["s2_dndvi_mean"].iloc[0] == -0.25

    def test_all_output_keys_namespace_compliance(self, tmp_path, monkeypatch):
        """Verify all Sentinel-2 features start with s2_ and NaN is used for missing stats."""
        monkeypatch.delenv("CDSE_CLIENT_ID", raising=False)
        monkeypatch.delenv("CDSE_CLIENT_SECRET", raising=False)
        client = Sentinel2ProcessingClient(client_id=None, client_secret=None)
        processor = Sentinel2ScaleProcessor(processing_client=client)

        events = pd.DataFrame([{
            "event_id": "EV_TEST",
            "latitude": 11.0,
            "longitude": 79.0,
            "acq_date": "2024-11-04",
        }])

        df_out = processor.process_all_events(events, output_dir=tmp_path, resume=False)
        rec = df_out.iloc[0].to_dict()

        # All numerical S2 columns must be NaN, not fabricated 0
        assert np.isnan(rec["s2_dndvi_mean"])
        assert np.isnan(rec["s2_dnbr_mean"])
        assert np.isnan(rec["s2_pre_ndvi_mean"])
        assert np.isnan(rec["s2_post_ndvi_mean"])

        # Check that S2 columns adhere to s2_ namespace
        s2_keys = [k for k in rec.keys() if k.startswith("s2_")]
        assert len(s2_keys) >= 40

    def test_runner_source_integrity_and_preflight(self, authoritative_df, tmp_path):
        """Verify run_sentinel2_scale_633 pre-flight integrity verification and SHA256 stability."""
        from src.feature_engineering.run_sentinel2_scale_633 import (
            verify_source_integrity,
            verify_output_integrity,
            compute_file_sha256,
        )

        source_path = Path("outputs/ground_truth_investigation/validation_candidates_v2.csv")
        df_checked, sha256_val = verify_source_integrity(source_path)
        assert len(df_checked) == 633
        assert df_checked["event_id"].nunique() == 633
        assert len(sha256_val) == 64

    def test_runner_manifest_schema_and_tracking(self, tmp_path):
        """Verify execution manifest records required fields and updates incrementally."""
        cache_dir = tmp_path / ".cache"
        cache_dir.mkdir()

        client = Sentinel2ProcessingClient(client_id="mock_id", client_secret="mock_secret")
        processor = Sentinel2ScaleProcessor(processing_client=client, cache_dir=cache_dir)

        events = pd.DataFrame([
            {"event_id": "EV_01", "latitude": 11.0, "longitude": 78.0, "acq_date": "2024-11-01", "candidate_priority": "HIGH", "landcover_class": "Built-up", "frp": 2.0},
            {"event_id": "EV_02", "latitude": 12.0, "longitude": 79.0, "acq_date": "2024-11-02", "candidate_priority": "LOW", "landcover_class": "Cropland", "frp": 1.0},
        ])

        with patch.object(processor.matcher, "match_event", return_value={"selected_pre_image_date": None, "selected_post_image_date": None}):
            df_out = processor.process_all_events(
                events_df=events,
                output_dir=tmp_path,
                resume=True,
                csv_filename="test_events.csv",
                manifest_filename="test_manifest.csv",
            )

        manifest_file = tmp_path / "test_manifest.csv"
        assert manifest_file.exists()
        m_df = pd.read_csv(manifest_file)

        # Check required fields from requirement 12
        required_manifest_fields = [
            "event_id",
            "processing_status",
            "pre_event_status",
            "post_event_status",
            "is_real_cdse_data",
            "processing_timestamp",
            "error_category",
        ]
        for field in required_manifest_fields:
            assert field in m_df.columns, f"Required manifest field '{field}' missing"

        assert len(m_df) == 2
        assert set(m_df["event_id"]) == {"EV_01", "EV_02"}

    def test_runner_resumability_skips_completed_events(self, tmp_path):
        """Verify that running with resume skips cached events and processes only uncompleted ones."""
        cache_dir = tmp_path / ".cache"
        cache_dir.mkdir()

        # Simulate EV_01 already completed in cache
        cached_ev01 = {
            "event_id": "EV_01",
            "processing_status": STATUS_REAL_CDSE_SUCCESS,
            "pre_observation_status": STATUS_REAL_CDSE_SUCCESS,
            "post_observation_status": STATUS_REAL_CDSE_SUCCESS,
            "is_real_cdse_data": True,
            "processing_timestamp": "2026-09-05T12:00:00Z",
            "error_category": "",
            "s2_dndvi_mean": 0.05,
        }
        with open(cache_dir / "EV_01.json", "w") as f:
            json.dump(cached_ev01, f)

        client = Sentinel2ProcessingClient(client_id="mock_id", client_secret="mock_secret")
        processor = Sentinel2ScaleProcessor(processing_client=client, cache_dir=cache_dir)

        events = pd.DataFrame([
            {"event_id": "EV_01", "latitude": 11.0, "longitude": 78.0, "acq_date": "2024-11-01"},
            {"event_id": "EV_02", "latitude": 12.0, "longitude": 79.0, "acq_date": "2024-11-02"},
        ])

        with patch.object(processor, "process_event", wraps=processor.process_event) as mock_proc:
            with patch.object(processor.matcher, "match_event", return_value={"selected_pre_image_date": None, "selected_post_image_date": None}):
                df_out = processor.process_all_events(
                    events_df=events,
                    output_dir=tmp_path,
                    resume=True,
                    csv_filename="resumed_events.csv",
                    manifest_filename="resumed_manifest.csv",
                )

            # process_event must ONLY be called once (for EV_02), EV_01 was resumed from cache!
            assert mock_proc.call_count == 1
            assert mock_proc.call_args[0][0]["event_id"] == "EV_02"

            assert len(df_out) == 2
            assert df_out.loc[df_out["event_id"] == "EV_01", "s2_dndvi_mean"].iloc[0] == 0.05
            assert df_out["event_id"].nunique() == 2  # No duplicate records

