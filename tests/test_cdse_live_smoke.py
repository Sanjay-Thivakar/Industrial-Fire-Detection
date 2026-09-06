"""Optional live smoke test for CDSE OData API connectivity.

This test can be run manually to verify live network connectivity to the
Copernicus Data Space Ecosystem (CDSE) Catalogue endpoint.
It is marked with `pytest.mark.live_api` so that the default deterministic test suite
can skip or isolate it.
"""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from src.data_ingestion.sentinel2_client import Sentinel2Client


@pytest.mark.live_api
def test_cdse_live_connectivity_smoke():
    """Smoke check to test CDSE OData catalogue live query on a Tamil Nadu coordinate."""
    client = Sentinel2Client(timeout_seconds=25, max_retries=2)
    # Salem, Tamil Nadu coordinate
    lat, lon = 11.65394, 78.02792
    start_date = "2024-10-25T00:00:00.000Z"
    end_date = "2024-11-05T23:59:59.999Z"

    res = client.query_products(
        latitude=lat,
        longitude=lon,
        start_date_iso=start_date,
        end_date_iso=end_date,
        top=5,
    )

    print(f"\n[CDSE Live Smoke] Success: {res['success']}, Raw Count: {res.get('raw_count', 0)}")
    if not res["success"]:
        print(f"[CDSE Live Smoke] Error: {res.get('error_type')} - {res.get('error_message')}")

    # Verify response structure
    assert "success" in res
    assert "products" in res
    if res["success"]:
        assert len(res["products"]) > 0
        p0 = res["products"][0]
        assert "id" in p0
        assert "name" in p0
        assert "tile_id" in p0


if __name__ == "__main__":
    print("Executing CDSE Live Smoke Check...")
    test_cdse_live_connectivity_smoke()
    print("CDSE Live Smoke Check completed successfully!")
