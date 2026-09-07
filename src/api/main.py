




"""Industrial Fire Detection - Machine Learning Inference API.

FastAPI service exposing Phase 5 production ML model inference.
Compliant with outputs/phase_5c_api/ML_API_CONTRACT.md.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Header, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.models.predict import (
    CONFIDENCE_TIERS,
    DEFAULT_MODEL_PATH,
    PRODUCTION_CLASSES,
    REQUIRED_FEATURES,
    TARGET_LEAKAGE_FIELDS,
    load_production_model,
    predict_event,
)

logger = logging.getLogger("IndustrialFireDetectionAPI")

# API Configuration and Environment Constants
API_VERSION = "1.0.0"
DEFAULT_API_KEY = "test-api-key-phase5c"
API_KEY = os.environ.get("ML_API_KEY", os.environ.get("API_KEY", DEFAULT_API_KEY))

# CORS Configuration
DEFAULT_CORS_ORIGINS: List[str] = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:4173",
    "http://localhost:4173",
]
raw_cors_origins = os.environ.get("CORS_ALLOWED_ORIGINS", "").strip()
CORS_ORIGINS: List[str] = (
    [o.strip() for o in raw_cors_origins.split(",") if o.strip()]
    if raw_cors_origins
    else DEFAULT_CORS_ORIGINS
)

EXPECTED_MODEL_SHA256 = "5909bb546fc55aeffd37b7bb601e96718709fe685e987705b246bb2963279798"
MODEL_VERSION_IDENTIFIER = "phase_5_ml_handoff/final_model.joblib"
MODEL_ARCHITECTURE = "Random Forest Classifier (Baseline FIRMS+OSM+WorldCover)"
MODEL_TRAINING_SAMPLES = 76
MODEL_MACRO_F1_OOF = 0.7772

CONFIDENCE_SCALE = {
    "HIGH": ">= 0.75",
    "MEDIUM": "0.50 - 0.74",
    "LOW": "< 0.50",
}

DISCLAIMER_TEXT = "Prediction is an algorithmic ML estimate. It is not ground truth."

NUMERIC_FLOAT_FEATURES = {
    "frp",
    "brightness",
    "bright_t31",
    "brightness_difference",
    "frp_brightness_ratio",
    "log_frp",
    "grid_total_frp",
    "grid_brightness_mean",
    "brightness_zscore_local",
    "frp_zscore_local",
    "distance_to_facility_m",
    "distance_to_higher_relevance_m",
}

INTEGER_FEATURES = {
    "confidence_numeric",
    "is_day",
    "grid_detection_count",
    "grid_active_days",
    "persistent_location_flag",
    "high_brightness_flag_local",
    "high_frp_flag_local",
    "is_stubble_burning_season",
    "landcover_code",
    "near_industrial_500m",
    "near_industrial_1000m",
    "near_industrial_2000m",
    "near_industrial_5000m",
    "near_industrial_10000m",
    "near_higher_relevance_500m",
    "near_higher_relevance_1000m",
    "near_higher_relevance_2000m",
    "near_higher_relevance_5000m",
    "near_higher_relevance_10000m",
}

CATEGORICAL_FEATURES = {
    "nearest_facility_type",
    "nearest_facility_category",
    "nearest_facility_tier",
    "nearest_hr_category",
    "osm_coverage_status",
}

# Runtime application state
app_state: Dict[str, Any] = {
    "model_loaded": False,
    "model_sha256": None,
    "model_path": None,
    "model_error": None,
}


def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA-256 digest of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def error_response(
    code: str,
    message: str,
    status_code: int,
    details: Optional[Dict[str, Any]] = None,
) -> JSONResponse:
    """Construct a contract-compliant error response."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details if details is not None else {},
            }
        },
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the FastAPI application.

    Pre-loads the production ML model and verifies integrity at startup.
    """
    try:
        model = load_production_model()
        # Locate the resolved artifact path
        target_path = DEFAULT_MODEL_PATH
        if not target_path.exists():
            target_path = (
                Path(__file__).resolve().parent.parent.parent
                / "outputs"
                / "phase_5_ml_handoff"
                / "final_model.joblib"
            )

        if target_path.exists():
            sha256_hash = calculate_sha256(target_path)
            app_state["model_loaded"] = True
            app_state["model_sha256"] = sha256_hash
            app_state["model_path"] = str(target_path)
            app_state["model_error"] = None
            logger.info("Production model loaded successfully. SHA-256: %s", sha256_hash)
        else:
            app_state["model_loaded"] = False
            app_state["model_error"] = "Model artifact not found at expected path."
            logger.error(app_state["model_error"])
    except Exception as exc:
        app_state["model_loaded"] = False
        app_state["model_error"] = str(exc)
        logger.exception("Failed to load production model at startup.")

    yield


# FastAPI Application instance
app = FastAPI(
    title="Industrial Fire Detection - ML Inference API",
    description="Backend ML inference API for 3-class thermal anomaly classification",
    version=API_VERSION,
    lifespan=lifespan,
)

# CORS Middleware Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["X-API-Key", "Content-Type", "Accept"],
)


# Exception Handlers for Contract-Compliant Error Envelope
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Map Pydantic/FastAPI validation errors to contract-compliant error structures."""
    errors = exc.errors()

    for err in errors:
        err_type = err.get("type", "")
        loc = err.get("loc", ())

        # 1. Invalid JSON body
        if err_type == "json_invalid" or "json" in err_type:
            return error_response(
                code="INVALID_JSON",
                message="Request body is not valid JSON.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # 2. Missing features object
        if loc == ("body", "features") and err_type == "missing":
            return error_response(
                code="MISSING_FEATURES_OBJECT",
                message="Request body must contain a 'features' object.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # 3. Features not a dictionary/object
        if loc == ("body", "features") and "dict" in err_type:
            return error_response(
                code="MISSING_FEATURES_OBJECT",
                message="'features' must be a JSON object.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

    return error_response(
        code="VALIDATION_ERROR",
        message="Request validation failed.",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        details={"validation_errors": errors},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle standard Starlette / FastAPI HTTPExceptions."""
    code = "HTTP_ERROR"
    if exc.status_code == status.HTTP_404_NOT_FOUND:
        code = "NOT_FOUND"
    elif exc.status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
        code = "METHOD_NOT_ALLOWED"

    return error_response(
        code=code,
        message=str(exc.detail),
        status_code=exc.status_code,
    )


# Pydantic Schemas
class PredictRequest(BaseModel):
    """Contract-compliant request model for thermal event prediction."""

    event_id: Optional[str] = Field(
        default=None,
        description="Optional caller-supplied identifier, echoed in the response.",
    )
    features: Dict[str, Any] = Field(
        ...,
        description="Dictionary containing strictly the 36 baseline ML features.",
    )


class ModelProvenance(BaseModel):
    """Model provenance metadata included in prediction responses."""

    version: str
    sha256: str
    architecture: str
    training_samples: int
    macro_f1_oof: float


class PredictResponse(BaseModel):
    """Contract-compliant response model for thermal event prediction."""

    event_id: Optional[str] = None
    predicted_class: str
    probabilities: Dict[str, float]
    max_probability: float
    ml_confidence: str
    confidence_scale: Dict[str, str]
    model: ModelProvenance
    inference_timestamp: str
    disclaimer: str


class HealthResponse(BaseModel):
    """Contract-compliant response model for API health check."""

    status: str
    model_loaded: bool
    model_version: Optional[str] = None
    model_sha256: Optional[str] = None
    required_features_count: Optional[int] = None
    production_classes: Optional[List[str]] = None
    api_version: str
    timestamp: str
    error: Optional[str] = None


# Endpoints
@app.get("/api/v1/health", response_model=HealthResponse, response_model_exclude_none=True)
async def health_check():
    """Liveness and model readiness endpoint.

    Public endpoint — no authentication required.
    Returns 200 OK when model is loaded, or 503 if unavailable.
    """
    current_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if not app_state["model_loaded"]:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unavailable",
                "model_loaded": False,
                "error": app_state.get("model_error") or "Model artifact not found at expected path.",
                "timestamp": current_time,
            },
        )

    return HealthResponse(
        status="ok",
        model_loaded=True,
        model_version=MODEL_VERSION_IDENTIFIER,
        model_sha256=app_state.get("model_sha256") or EXPECTED_MODEL_SHA256,
        required_features_count=len(REQUIRED_FEATURES),
        production_classes=PRODUCTION_CLASSES,
        api_version=API_VERSION,
        timestamp=current_time,
    )


@app.post("/api/v1/predict", response_model=PredictResponse)
async def predict(
    payload: PredictRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """Generate 3-class thermal anomaly classification for a single event.

    Requires valid X-API-Key header.
    Validates features against leakage and schema completeness.
    """
    # 1. Authentication
    if x_api_key is None:
        return error_response(
            code="MISSING_API_KEY",
            message="Missing required X-API-Key header.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    expected_key = os.environ.get("ML_API_KEY", os.environ.get("API_KEY", DEFAULT_API_KEY))
    if x_api_key != expected_key:
        return error_response(
            code="INVALID_API_KEY",
            message="Invalid API key provided.",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    # 2. Model readiness check
    if not app_state["model_loaded"]:
        return error_response(
            code="MODEL_NOT_LOADED",
            message="Model is not loaded and unavailable for inference.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    features = payload.features

    # 3. Target leakage guard
    present_leakage = [col for col in TARGET_LEAKAGE_FIELDS if col in features]
    if present_leakage:
        return error_response(
            code="LEAKAGE_FIELD_DETECTED",
            message="Ground-truth fields must not be passed as inference features.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={"leakage_fields_detected": present_leakage},
        )

    # 4. Check for missing required features
    missing_features = [f for f in REQUIRED_FEATURES if f not in features]
    if missing_features:
        return error_response(
            code="MISSING_REQUIRED_FEATURES",
            message=f"Missing {len(missing_features)} required feature(s) for production model.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={
                "missing": missing_features,
                "total_required": len(REQUIRED_FEATURES),
                "total_provided": len(features),
            },
        )

    # 5. Type validation and coercion
    clean_features: Dict[str, Any] = {}
    invalid_fields: List[str] = []

    for name, val in features.items():
        if name not in REQUIRED_FEATURES:
            continue

        try:
            if name in NUMERIC_FLOAT_FEATURES:
                if val is None or isinstance(val, (bool, str)):
                    # Try string conversion if string represents number
                    if isinstance(val, str):
                        clean_features[name] = float(val)
                    else:
                        invalid_fields.append(name)
                else:
                    clean_features[name] = float(val)

            elif name in INTEGER_FEATURES:
                if val is None or isinstance(val, bool):
                    invalid_fields.append(name)
                elif isinstance(val, str):
                    clean_features[name] = int(val)
                elif isinstance(val, (int, float)):
                    if float(val).is_integer():
                        clean_features[name] = int(val)
                    else:
                        invalid_fields.append(name)
                else:
                    invalid_fields.append(name)

            elif name in CATEGORICAL_FEATURES:
                if val is None:
                    invalid_fields.append(name)
                else:
                    clean_features[name] = str(val)
            else:
                clean_features[name] = val
        except (ValueError, TypeError):
            invalid_fields.append(name)

    if invalid_fields:
        return error_response(
            code="INVALID_FEATURE_TYPE",
            message="One or more feature values have invalid types or cannot be coerced.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={"invalid_fields": sorted(list(set(invalid_fields)))},
        )

    # 6. Execute inference using predict_event()
    try:
        raw_result = predict_event(clean_features)
    except ValueError as val_err:
        return error_response(
            code="VALIDATION_ERROR",
            message=str(val_err),
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    except Exception as exc:
        logger.exception("Unexpected inference error.")
        return error_response(
            code="INFERENCE_ERROR",
            message="An error occurred during model inference.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"error_detail": str(exc)},
        )

    # 7. Formulate contract response
    timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return PredictResponse(
        event_id=payload.event_id,
        predicted_class=raw_result["prediction"],
        probabilities=raw_result["probabilities"],
        max_probability=raw_result["max_probability"],
        ml_confidence=raw_result["confidence"],
        confidence_scale=CONFIDENCE_SCALE,
        model=ModelProvenance(
            version=MODEL_VERSION_IDENTIFIER,
            sha256=app_state.get("model_sha256") or EXPECTED_MODEL_SHA256,
            architecture=MODEL_ARCHITECTURE,
            training_samples=MODEL_TRAINING_SAMPLES,
            macro_f1_oof=MODEL_MACRO_F1_OOF,
        ),
        inference_timestamp=timestamp_str,
        disclaimer=DISCLAIMER_TEXT,
    )
