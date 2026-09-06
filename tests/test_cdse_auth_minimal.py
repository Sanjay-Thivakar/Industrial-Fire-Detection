"""Minimal live authentication test for Copernicus Data Space Ecosystem (CDSE) OAuth2.

Requirements:
1. Read CDSE_CLIENT_ID and CDSE_CLIENT_SECRET from environment variables only.
2. Do NOT print either credential or the access token.
3. Request an OAuth2 access token from the CDSE Sentinel Hub authentication endpoint.
4. Report only:
   - whether authentication succeeded or failed
   - HTTP status code
   - a short safe error message if it failed
5. Do not modify the existing Phase 3E processing logic.
6. Do not run the 633-event pipeline.
"""

import os
import sys
from pathlib import Path
import requests

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_ingestion.sentinel2_patch_retriever import Sentinel2ProcessingClient


def test_cdse_oauth2_authentication():
    """Execute minimal CDSE OAuth2 authentication test."""
    client_id = os.environ.get("CDSE_CLIENT_ID")
    client_secret = os.environ.get("CDSE_CLIENT_SECRET")

    if not client_id or not client_secret:
        return {
            "success": False,
            "status_code": None,
            "error_message": "Environment variables CDSE_CLIENT_ID and/or CDSE_CLIENT_SECRET not configured.",
        }

    token_url = Sentinel2ProcessingClient.DEFAULT_TOKEN_URL

    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }

    try:
        resp = requests.post(token_url, data=payload, timeout=30)
        status_code = resp.status_code

        if status_code == 200:
            token_json = resp.json()
            if "access_token" in token_json and token_json["access_token"]:
                return {
                    "success": True,
                    "status_code": status_code,
                    "error_message": None,
                }
            else:
                return {
                    "success": False,
                    "status_code": status_code,
                    "error_message": "HTTP 200 received but access_token field missing in response.",
                }
        else:
            safe_msg = f"HTTP {status_code}"
            try:
                err_data = resp.json()
                safe_desc = err_data.get("error_description") or err_data.get("error")
                if safe_desc:
                    safe_msg = f"{safe_msg}: {safe_desc}"
            except Exception:
                safe_text = resp.text[:120].strip()
                if safe_text:
                    safe_msg = f"{safe_msg}: {safe_text}"
            return {
                "success": False,
                "status_code": status_code,
                "error_message": safe_msg,
            }
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "status_code": None,
            "error_message": "Connection timed out connecting to CDSE token endpoint.",
        }
    except Exception as e:
        return {
            "success": False,
            "status_code": None,
            "error_message": f"Network / connection error: {type(e).__name__}",
        }


def main():
    result = test_cdse_oauth2_authentication()
    status_str = "SUCCEEDED" if result["success"] else "FAILED"
    print(f"Authentication: {status_str}")
    print(f"HTTP Status Code: {result['status_code']}")
    if not result["success"]:
        print(f"Error Message: {result['error_message']}")

    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
