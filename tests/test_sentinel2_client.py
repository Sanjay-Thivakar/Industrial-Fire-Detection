"""Deterministic unit tests for Sentinel-2 CDSE client and matcher.

All tests are 100% mocked and deterministic with ZERO external network dependencies.
"""

import datetime
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.data_ingestion.sentinel2_client import (
    Sentinel2Client,
    Sentinel2Matcher,
)


class TestSentinel2Client:
    """Tests for Sentinel2Client query construction and error handling."""

    def test_coordinate_validation(self):
        # Valid
        valid, msg = Sentinel2Client.validate_coordinates(11.65, 78.02)
        assert valid is True
        assert msg == ""

        # Invalid latitude
        valid, msg = Sentinel2Client.validate_coordinates(95.0, 78.02)
        assert valid is False
        assert "Latitude" in msg

        # Invalid longitude
        valid, msg = Sentinel2Client.validate_coordinates(11.65, 185.0)
        assert valid is False
        assert "Longitude" in msg

        # Non-numeric
        valid, msg = Sentinel2Client.validate_coordinates("invalid", 78.02)
        assert valid is False
        assert "Non-numeric" in msg

    def test_odata_filter_construction(self):
        client = Sentinel2Client(
            collection_name="SENTINEL-2",
            target_product_type="S2MSI2A",
        )
        query = client.build_odata_filter(
            latitude=11.65394,
            longitude=78.02792,
            start_date_iso="2024-10-15T00:00:00.000Z",
            end_date_iso="2024-10-31T23:59:59.999Z",
            max_cloud_cover=35.0,
        )
        assert "Collection/Name eq 'SENTINEL-2'" in query
        assert "productType" in query and "S2MSI2A" in query
        assert "POINT(78.027920 11.653940)" in query
        assert "ContentDate/Start ge 2024-10-15T00:00:00.000Z" in query
        assert "ContentDate/Start le 2024-10-31T23:59:59.999Z" in query
        assert "cloudCover" in query and "35.00" in query

    @patch("requests.Session.get")
    def test_query_products_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {
                    "Id": "prod-123",
                    "Name": "S2A_MSIL2A_20241029T050839_N0511_R019_T43PHN_20241029T073358.SAFE",
                    "ContentDate": {"Start": "2024-10-29T05:08:39.024Z"},
                    "Attributes": [
                        {"Name": "cloudCover", "Value": 18.5},
                        {"Name": "productType", "Value": "S2MSI2A"},
                    ],
                }
            ]
        }
        mock_get.return_value = mock_response

        client = Sentinel2Client()
        res = client.query_products(11.65, 78.02, "2024-10-15T00:00:00Z", "2024-10-31T23:59:59Z")
        assert res["success"] is True
        assert len(res["products"]) == 1
        prod = res["products"][0]
        assert prod["id"] == "prod-123"
        assert prod["tile_id"] == "T43PHN"
        assert prod["cloud_cover"] == 18.5

    @patch("requests.Session.get")
    def test_query_products_auth_failure(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_get.return_value = mock_response

        client = Sentinel2Client(max_retries=1)
        res = client.query_products(11.65, 78.02, "2024-10-15T00:00:00Z", "2024-10-31T23:59:59Z")
        assert res["success"] is False
        assert res["error_type"] == "AUTH_FAILURE"

    @patch("requests.Session.get")
    def test_query_products_network_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection aborted")

        client = Sentinel2Client(max_retries=1)
        res = client.query_products(11.65, 78.02, "2024-10-15T00:00:00Z", "2024-10-31T23:59:59Z")
        assert res["success"] is False
        assert res["error_type"] == "API_ERROR"
        assert "Connection aborted" in res["error_message"]


class TestSentinel2Matcher:
    """Tests for Sentinel2Matcher temporal windows, candidate ranking, and output structure."""

    def test_disjoint_temporal_windows_exclude_event_date(self):
        matcher = Sentinel2Matcher(pre_event_days=15, post_event_days=15)
        event_date = datetime.date(2024, 11, 10)
        pre_start, pre_end, post_start, post_end = matcher.compute_temporal_windows(event_date)

        # Pre-event: [Nov 10 - 15 days = Oct 26, Nov 10 - 1 day = Nov 09]
        assert pre_start == datetime.date(2024, 10, 26)
        assert pre_end == datetime.date(2024, 11, 9)

        # Post-event: [Nov 10 + 1 day = Nov 11, Nov 10 + 15 days = Nov 25]
        assert post_start == datetime.date(2024, 11, 11)
        assert post_end == datetime.date(2024, 11, 25)

        # Crucial check: event_date is NOT inside pre or post window
        assert pre_end < event_date < post_start

    def test_deterministic_candidate_ranking_proximity_over_cloud(self):
        """Verify candidate ranking prefers temporal proximity over distant low-cloud images."""
        matcher = Sentinel2Matcher()
        event_date = datetime.date(2024, 11, 10)

        # Candidate A: 2 days before event, cloud 25%
        # Candidate B: 12 days before event, cloud 2%
        # Candidate C: 2 days before event, cloud 15%
        candidates = [
            {
                "id": "A",
                "content_date_start": "2024-11-08T05:00:00.000Z",
                "cloud_cover": 25.0,
            },
            {
                "id": "B",
                "content_date_start": "2024-10-29T05:00:00.000Z",
                "cloud_cover": 2.0,
            },
            {
                "id": "C",
                "content_date_start": "2024-11-08T05:00:00.000Z",
                "cloud_cover": 15.0,
            },
        ]

        best, reason = matcher.rank_candidates(candidates, event_date, max_cloud_cover=40.0)
        # C should win over B (temporal proximity: 2 days vs 12 days)
        # C should win over A (cloud cover: 15% vs 25%)
        assert best is not None
        assert best["id"] == "C"
        assert "-2 days from event" in reason
        assert "15.0%" in reason

    def test_candidate_ranking_all_cloudy(self):
        """When all candidates exceed max_cloud_cover, none is selected and reason is recorded."""
        matcher = Sentinel2Matcher()
        event_date = datetime.date(2024, 11, 10)
        candidates = [
            {"id": "A", "content_date_start": "2024-11-08T05:00:00.000Z", "cloud_cover": 75.0},
            {"id": "B", "content_date_start": "2024-11-05T05:00:00.000Z", "cloud_cover": 60.0},
        ]
        best, reason = matcher.rank_candidates(candidates, event_date, max_cloud_cover=40.0)
        assert best is None
        assert "exceeded cloud threshold (40.0%)" in reason
        assert "lowest was 60.0%" in reason

    def test_match_event_success_both_found(self):
        """Test end-to-end match_event when both pre and post images are found."""
        mock_client = MagicMock()
        mock_client.validate_coordinates.return_value = (True, "")

        # Pre query returns an observation
        mock_client.query_products.side_effect = [
            {
                "success": True,
                "products": [
                    {
                        "id": "pre-1",
                        "name": "S2A_MSIL2A_20241108_T43PHN",
                        "content_date_start": "2024-11-08T05:10:00.000Z",
                        "tile_id": "T43PHN",
                        "cloud_cover": 12.0,
                    }
                ],
                "raw_count": 1,
            },
            {
                "success": True,
                "products": [
                    {
                        "id": "post-1",
                        "name": "S2B_MSIL2A_20241113_T43PHN",
                        "content_date_start": "2024-11-13T05:10:00.000Z",
                        "tile_id": "T43PHN",
                        "cloud_cover": 5.0,
                    }
                ],
                "raw_count": 1,
            },
        ]

        matcher = Sentinel2Matcher(client=mock_client)
        res = matcher.match_event("FIRMS_TN_0001", 11.65394, 78.02792, "2024-11-10")

        assert res["selection_status"] == "SUCCESS_BOTH_FOUND"
        assert res["pre_product_id"] == "pre-1"
        assert res["post_product_id"] == "post-1"
        assert res["pre_days_from_event"] == -2
        assert res["post_days_from_event"] == 3
        assert res["pre_cloud_cover"] == 12.0
        assert res["post_cloud_cover"] == 5.0
        assert "pre_selection_reason" in res
        assert "post_selection_reason" in res
        assert res["failure_reason"] == ""

    def test_match_event_api_error_no_silent_fallback(self):
        """Verify API_ERROR is raised and preserved without silent fallback."""
        mock_client = MagicMock()
        mock_client.validate_coordinates.return_value = (True, "")
        mock_client.query_products.return_value = {
            "success": False,
            "error_type": "API_ERROR",
            "error_message": "CDSE service 503 Unavailable",
            "products": [],
            "raw_count": 0,
        }

        matcher = Sentinel2Matcher(client=mock_client)
        res = matcher.match_event("FIRMS_TN_0001", 11.65394, 78.02792, "2024-11-10")

        assert res["selection_status"] == "API_ERROR"
        assert "503 Unavailable" in res["failure_reason"]
        assert res["selected_pre_image_date"] is None
        assert res["selected_post_image_date"] is None

    def test_match_event_invalid_coordinates(self):
        matcher = Sentinel2Matcher()
        res = matcher.match_event("FIRMS_TN_0001", 999.0, 78.02792, "2024-11-10")
        assert res["selection_status"] == "INVALID_COORDINATES"
        assert "Latitude" in res["failure_reason"]
