"""Sentinel-2 historical imagery data access and matching component.

Uses exclusively the Copernicus Data Space Ecosystem (CDSE) Catalogue OData v1 API
to search and match Sentinel-2 Level-2A (S2MSI2A) observations for historical FIRMS events.

IMPORTANT DOMAIN NOTES:
1. Sentinel-2 is an optical multispectral sensor (VNIR/SWIR), NOT a thermal sensor.
   It does NOT detect active thermal plumes directly. It provides surface reflectance
   observations before and after fire events to enable historical surface-change,
   burn scar, vegetation change, and industrial facility context analysis.
2. The catalogue 'cloudCover' attribute is a product/tile-level aggregate estimate
   over the entire ~100x100 km Sentinel-2 granule, NOT a local pixel-level cloud mask.
   Fine-grained local pixel cloud masking (e.g. via Scene Classification Layer / SCL)
   must be handled in subsequent processing steps.
"""

import datetime
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

# Tile ID regex pattern for Sentinel-2 product names: e.g. _T43PHN_
TILE_ID_PATTERN = re.compile(r"_(T[0-9A-Z]{5})_")


class Sentinel2Client:
    """Client for Copernicus Data Space Ecosystem (CDSE) Catalogue OData API.
    
    Queries CDSE Catalogue OData v1 Products endpoint for Sentinel-2 L2A observations.
    Does NOT use third-party fallbacks. Reports explicit API_ERROR on connection failures.
    """

    DEFAULT_BASE_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1"

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout_seconds: int = 30,
        max_retries: int = 3,
        collection_name: str = "SENTINEL-2",
        target_product_type: str = "S2MSI2A",
    ):
        self.base_url = base_url.rstrip("/")
        self.products_url = f"{self.base_url}/Products"
        self.timeout = timeout_seconds
        self.max_retries = max_retries
        self.collection_name = collection_name
        self.target_product_type = target_product_type
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Industrial-Fire-AI-Sentinel2-Prototype/1.0"
        })

    @staticmethod
    def validate_coordinates(latitude: float, longitude: float) -> Tuple[bool, str]:
        """Validate WGS84 coordinates."""
        try:
            lat = float(latitude)
            lon = float(longitude)
        except (ValueError, TypeError):
            return False, f"Non-numeric coordinates: lat={latitude}, lon={longitude}"

        if not (-90.0 <= lat <= 90.0):
            return False, f"Latitude {lat} out of valid range [-90, 90]"
        if not (-180.0 <= lon <= 180.0):
            return False, f"Longitude {lon} out of valid range [-180, 180]"

        return True, ""

    def build_odata_filter(
        self,
        latitude: float,
        longitude: float,
        start_date_iso: str,
        end_date_iso: str,
        max_cloud_cover: Optional[float] = None,
    ) -> str:
        """Construct OData filter query for CDSE Catalogue."""
        # POINT(longitude latitude) format in WKT
        point_wkt = f"POINT({longitude:.6f} {latitude:.6f})"
        
        filter_parts = [
            f"Collection/Name eq '{self.collection_name}'",
            f"Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' and att/OData.CSC.StringAttribute/Value eq '{self.target_product_type}')",
            f"OData.CSC.Intersects(area=geography'SRID=4326;{point_wkt}')",
            f"ContentDate/Start ge {start_date_iso}",
            f"ContentDate/Start le {end_date_iso}",
        ]

        if max_cloud_cover is not None:
            filter_parts.append(
                f"Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' and att/OData.CSC.DoubleAttribute/Value le {float(max_cloud_cover):.2f})"
            )

        return " and ".join(filter_parts)

    def query_products(
        self,
        latitude: float,
        longitude: float,
        start_date_iso: str,
        end_date_iso: str,
        top: int = 50,
        max_cloud_cover: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Query CDSE OData Products catalogue for observations covering location and date range.
        
        Returns dictionary with keys:
            success (bool): True if HTTP 200 returned and parsed
            products (list): parsed product metadata items
            raw_count (int): number of products returned
            error_type (str, optional): API_ERROR, AUTH_FAILURE, INVALID_COORDINATES, etc.
            error_message (str, optional): detailed error description
        """
        valid, err_msg = self.validate_coordinates(latitude, longitude)
        if not valid:
            return {
                "success": False,
                "products": [],
                "raw_count": 0,
                "error_type": "INVALID_COORDINATES",
                "error_message": err_msg,
            }

        odata_filter = self.build_odata_filter(
            latitude=latitude,
            longitude=longitude,
            start_date_iso=start_date_iso,
            end_date_iso=end_date_iso,
            max_cloud_cover=max_cloud_cover,
        )

        params = {
            "$filter": odata_filter,
            "$orderby": "ContentDate/Start desc",
            "$top": top,
            "$expand": "Attributes",
        }

        last_error = ""
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.get(
                    self.products_url,
                    params=params,
                    timeout=self.timeout,
                )

                if response.status_code == 200:
                    data = response.json()
                    raw_items = data.get("value", [])
                    parsed = [self._parse_product_item(item) for item in raw_items]
                    return {
                        "success": True,
                        "products": parsed,
                        "raw_count": len(parsed),
                        "query_filter": odata_filter,
                    }

                if response.status_code in (401, 403):
                    return {
                        "success": False,
                        "products": [],
                        "raw_count": 0,
                        "error_type": "AUTH_FAILURE",
                        "error_message": f"Authentication/authorization rejected by CDSE (HTTP {response.status_code}): {response.text[:200]}",
                    }

                last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.warning("CDSE attempt %d/%d returned %s", attempt, self.max_retries, last_error)

            except requests.exceptions.Timeout as e:
                last_error = f"Network timeout ({self.timeout}s): {e}"
                logger.warning("CDSE attempt %d/%d timed out", attempt, self.max_retries)
            except requests.exceptions.RequestException as e:
                last_error = f"Network connection error: {e}"
                logger.warning("CDSE attempt %d/%d connection error: %s", attempt, self.max_retries, e)
            except Exception as e:
                last_error = f"Unexpected error during CDSE query: {e}"
                logger.exception("Unexpected error in CDSE query")

            if attempt < self.max_retries:
                time.sleep(1.0 * attempt)

        return {
            "success": False,
            "products": [],
            "raw_count": 0,
            "error_type": "API_ERROR",
            "error_message": last_error or "Max retries exceeded with CDSE",
        }

    def _parse_product_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structured Sentinel-2 metadata from CDSE OData product item."""
        product_id = item.get("Id")
        name = item.get("Name", "")
        content_date = item.get("ContentDate", {})
        start_date = content_date.get("Start", "")

        # Extract tile ID from name e.g. S2A_MSIL2A_20241103T050951_N0511_R019_T43PHN_...
        tile_id = ""
        tile_match = TILE_ID_PATTERN.search(name)
        if tile_match:
            tile_id = tile_match.group(1)

        # Parse cloud cover from Attributes
        cloud_cover = None
        for att in item.get("Attributes", []):
            if att.get("Name") == "cloudCover":
                val = att.get("Value")
                if val is not None:
                    try:
                        cloud_cover = float(val)
                    except (ValueError, TypeError):
                        pass
            elif att.get("Name") == "tileId" and not tile_id:
                tile_id = str(att.get("Value", ""))

        return {
            "id": product_id,
            "name": name,
            "content_date_start": start_date,
            "tile_id": tile_id,
            "cloud_cover": cloud_cover,
            "raw_item": item,
        }


class Sentinel2Matcher:
    """Matches FIRMS active fire events to historical Sentinel-2 L2A observations.
    
    Enforces disjoint temporal windows (excluding FIRMS acquisition date),
    deterministic 3-tier candidate ranking, and transparent status/reason reporting.
    """

    def __init__(
        self,
        client: Optional[Sentinel2Client] = None,
        pre_event_days: int = 15,
        post_event_days: int = 15,
        max_cloud_cover_percent: float = 40.0,
    ):
        self.client = client or Sentinel2Client()
        self.pre_event_days = pre_event_days
        self.post_event_days = post_event_days
        self.max_cloud_cover = max_cloud_cover_percent

    @staticmethod
    def parse_event_date(date_val: Any) -> datetime.date:
        """Parse various date formats into a standard datetime.date object."""
        if isinstance(date_val, datetime.date) and not isinstance(date_val, datetime.datetime):
            return date_val
        if isinstance(date_val, datetime.datetime):
            return date_val.date()
        
        date_str = str(date_val).strip()
        # Common ISO format YYYY-MM-DD
        if len(date_str) >= 10:
            return datetime.date.fromisoformat(date_str[:10])
        raise ValueError(f"Unable to parse date string: {date_val}")

    def compute_temporal_windows(
        self, event_date: datetime.date
    ) -> Tuple[datetime.date, datetime.date, datetime.date, datetime.date]:
        """Compute disjoint pre-event and post-event temporal windows.
        
        Strict rule:
        - PRE-EVENT: [event_date - pre_event_days, event_date - 1 day]
        - POST-EVENT: [event_date + 1 day, event_date + post_event_days]
        The event_date itself is strictly excluded from both windows.
        """
        pre_start = event_date - datetime.timedelta(days=self.pre_event_days)
        pre_end = event_date - datetime.timedelta(days=1)
        post_start = event_date + datetime.timedelta(days=1)
        post_end = event_date + datetime.timedelta(days=self.post_event_days)
        return pre_start, pre_end, post_start, post_end

    def rank_candidates(
        self,
        candidates: List[Dict[str, Any]],
        event_date: datetime.date,
        max_cloud_cover: float,
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        """Deterministic 3-tier candidate ranking.
        
        Ranking criteria:
        1. Smallest absolute day difference from FIRMS event date: |image_date - event_date|
        2. Lowest catalogue product/tile cloud-cover percentage
        3. ISO sensing timestamp descending (tie-breaker)
        
        Returns:
            (selected_product_or_None, selection_or_rejection_reason)
        """
        if not candidates:
            return None, "No observations found in catalogue for temporal window"

        # Separate into usable (within cloud threshold) vs cloud-rejected
        usable = []
        for c in candidates:
            cc = c.get("cloud_cover")
            # If cloud cover is None, treat cautiously or accept if unknown
            if cc is None or cc <= max_cloud_cover:
                usable.append(c)

        if not usable:
            min_cloud = min((c.get("cloud_cover") for c in candidates if c.get("cloud_cover") is not None), default=None)
            min_str = f"{min_cloud:.1f}%" if min_cloud is not None else "N/A"
            return (
                None,
                f"All {len(candidates)} observation(s) exceeded cloud threshold ({max_cloud_cover}%); lowest was {min_str}"
            )

        def sorting_key(item: Dict[str, Any]):
            start_str = item.get("content_date_start", "")
            try:
                dt = datetime.datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                obs_date = dt.date()
                timestamp = dt.timestamp()
            except Exception:
                obs_date = event_date
                timestamp = 0.0

            abs_day_diff = abs((obs_date - event_date).days)
            cloud_val = item.get("cloud_cover") if item.get("cloud_cover") is not None else 999.0
            return (abs_day_diff, cloud_val, -timestamp)

        sorted_candidates = sorted(usable, key=sorting_key)
        best = sorted_candidates[0]

        # Calculate exact day difference for description
        start_str = best.get("content_date_start", "")
        try:
            dt = datetime.datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            day_diff = (dt.date() - event_date).days
        except Exception:
            day_diff = 0

        cc_best = best.get("cloud_cover")
        cc_str = f"{cc_best:.1f}%" if cc_best is not None else "N/A"
        reason = (
            f"Selected observation {day_diff:+d} days from event "
            f"(tile cloud={cc_str}, candidate 1 of {len(usable)} usable)"
        )
        return best, reason

    def match_event(
        self,
        event_id: str,
        latitude: float,
        longitude: float,
        acquisition_date: Any,
    ) -> Dict[str, Any]:
        """Perform pre-event and post-event Sentinel-2 matching for a single FIRMS event."""
        # 1. Coordinate validation
        valid_coords, coord_err = Sentinel2Client.validate_coordinates(latitude, longitude)
        if not valid_coords:
            return self._build_result(
                event_id=event_id,
                lat=latitude,
                lon=longitude,
                acq_date=str(acquisition_date),
                status="INVALID_COORDINATES",
                failure_reason=coord_err,
                pre_prod=None,
                pre_reason=coord_err,
                post_prod=None,
                post_reason=coord_err,
            )

        # 2. Parse event date
        try:
            event_date = self.parse_event_date(acquisition_date)
        except Exception as e:
            return self._build_result(
                event_id=event_id,
                lat=latitude,
                lon=longitude,
                acq_date=str(acquisition_date),
                status="INVALID_DATE",
                failure_reason=f"Invalid acquisition date '{acquisition_date}': {e}",
                pre_prod=None,
                pre_reason="Invalid date",
                post_prod=None,
                post_reason="Invalid date",
            )

        # 3. Disjoint temporal windows (excluding event date)
        pre_start, pre_end, post_start, post_end = self.compute_temporal_windows(event_date)
        pre_start_iso = f"{pre_start.isoformat()}T00:00:00.000Z"
        pre_end_iso = f"{pre_end.isoformat()}T23:59:59.999Z"
        post_start_iso = f"{post_start.isoformat()}T00:00:00.000Z"
        post_end_iso = f"{post_end.isoformat()}T23:59:59.999Z"

        # 4. Query CDSE for Pre-event window
        pre_res = self.client.query_products(
            latitude=latitude,
            longitude=longitude,
            start_date_iso=pre_start_iso,
            end_date_iso=pre_end_iso,
        )

        if not pre_res["success"]:
            return self._build_result(
                event_id=event_id,
                lat=latitude,
                lon=longitude,
                acq_date=event_date.isoformat(),
                status="API_ERROR",
                failure_reason=f"Pre-event query CDSE error: {pre_res.get('error_message')}",
                pre_prod=None,
                pre_reason=pre_res.get("error_message", "API Error"),
                post_prod=None,
                post_reason="Aborted due to pre-event API error",
            )

        # 5. Query CDSE for Post-event window
        post_res = self.client.query_products(
            latitude=latitude,
            longitude=longitude,
            start_date_iso=post_start_iso,
            end_date_iso=post_end_iso,
        )

        if not post_res["success"]:
            return self._build_result(
                event_id=event_id,
                lat=latitude,
                lon=longitude,
                acq_date=event_date.isoformat(),
                status="API_ERROR",
                failure_reason=f"Post-event query CDSE error: {post_res.get('error_message')}",
                pre_prod=None,
                pre_reason="Pre-event query succeeded but post-event query failed",
                post_prod=None,
                post_reason=post_res.get("error_message", "API Error"),
            )

        # 6. Rank and select best observations
        pre_best, pre_reason = self.rank_candidates(
            pre_res["products"], event_date, self.max_cloud_cover
        )
        post_best, post_reason = self.rank_candidates(
            post_res["products"], event_date, self.max_cloud_cover
        )

        # 7. Determine overall selection status
        total_raw_pre = pre_res["raw_count"]
        total_raw_post = post_res["raw_count"]

        if pre_best is not None and post_best is not None:
            status = "SUCCESS_BOTH_FOUND"
            failure_reason = ""
        elif pre_best is not None and post_best is None:
            status = "SUCCESS_PRE_ONLY"
            failure_reason = f"Post-event image unavailable: {post_reason}"
        elif pre_best is None and post_best is not None:
            status = "SUCCESS_POST_ONLY"
            failure_reason = f"Pre-event image unavailable: {pre_reason}"
        else:
            # Neither found
            if total_raw_pre > 0 and total_raw_post > 0:
                status = "CLOUDY_ALL_DATES"
                failure_reason = f"Images existed ({total_raw_pre} pre, {total_raw_post} post) but all exceeded cloud threshold of {self.max_cloud_cover}%"
            elif total_raw_pre == 0 and total_raw_post == 0:
                status = "NO_USABLE_IMAGE"
                failure_reason = "No Sentinel-2 observations found in either pre-event or post-event catalogue window"
            else:
                status = "NO_USABLE_IMAGE"
                failure_reason = f"Pre: {pre_reason}; Post: {post_reason}"

        return self._build_result(
            event_id=event_id,
            lat=latitude,
            lon=longitude,
            acq_date=event_date.isoformat(),
            status=status,
            failure_reason=failure_reason,
            pre_prod=pre_best,
            pre_reason=pre_reason,
            post_prod=post_best,
            post_reason=post_reason,
            raw_pre_products=pre_res["products"],
            raw_post_products=post_res["products"],
        )

    def _build_result(
        self,
        event_id: str,
        lat: float,
        lon: float,
        acq_date: str,
        status: str,
        failure_reason: str,
        pre_prod: Optional[Dict[str, Any]],
        pre_reason: str,
        post_prod: Optional[Dict[str, Any]],
        post_reason: str,
        raw_pre_products: Optional[List[Dict[str, Any]]] = None,
        raw_post_products: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Build normalized output record adhering to exact specification."""
        # Event date as datetime.date if possible
        try:
            ev_date = datetime.date.fromisoformat(acq_date[:10])
        except Exception:
            ev_date = None

        # Pre metadata
        pre_id = pre_prod.get("id") if pre_prod else None
        pre_name = pre_prod.get("name") if pre_prod else None
        pre_tile = pre_prod.get("tile_id") if pre_prod else None
        pre_date_str = pre_prod.get("content_date_start") if pre_prod else None
        pre_cloud = pre_prod.get("cloud_cover") if pre_prod else None

        pre_days = None
        if pre_date_str and ev_date:
            try:
                p_dt = datetime.datetime.fromisoformat(pre_date_str.replace("Z", "+00:00"))
                pre_days = (p_dt.date() - ev_date).days
            except Exception:
                pass

        # Post metadata
        post_id = post_prod.get("id") if post_prod else None
        post_name = post_prod.get("name") if post_prod else None
        post_tile = post_prod.get("tile_id") if post_prod else None
        post_date_str = post_prod.get("content_date_start") if post_prod else None
        post_cloud = post_prod.get("cloud_cover") if post_prod else None

        post_days = None
        if post_date_str and ev_date:
            try:
                p_dt = datetime.datetime.fromisoformat(post_date_str.replace("Z", "+00:00"))
                post_days = (p_dt.date() - ev_date).days
            except Exception:
                pass

        return {
            "event_id": event_id,
            "latitude": lat,
            "longitude": lon,
            "acquisition_date": acq_date,
            "selected_pre_image_date": pre_date_str,
            "selected_post_image_date": post_date_str,
            "pre_days_from_event": pre_days,
            "post_days_from_event": post_days,
            "pre_tile_id": pre_tile,
            "post_tile_id": post_tile,
            "pre_cloud_cover": pre_cloud,
            "post_cloud_cover": post_cloud,
            "pre_product_name": pre_name,
            "post_product_name": post_name,
            "pre_product_id": pre_id,
            "post_product_id": post_id,
            "selection_status": status,
            "failure_reason": failure_reason,
            "pre_selection_reason": pre_reason,
            "post_selection_reason": post_reason,
            # Cache items for reproduction
            "_raw_pre_count": len(raw_pre_products) if raw_pre_products else 0,
            "_raw_post_count": len(raw_post_products) if raw_post_products else 0,
        }
