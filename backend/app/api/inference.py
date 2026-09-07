"""API Router for Live Operational Inference and Model Governance."""

from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, status

from backend.app.schemas.inference import (
    LiveInferenceRequest,
    LiveInferenceResponse,
)
from backend.app.services.inference_engine import production_engine
from backend.app.services.model_config import (
    M0_CLIMATOLOGY_METADATA,
    M1_SPREAD_ONLY_METADATA,
    RESEARCH_MODELS_CATALOG,
    asdict,
)

router = APIRouter(prefix="/inference", tags=["Live Operational Inference"])


@router.post(
    "/predict",
    response_model=LiveInferenceResponse,
    summary="Live Forecast Reliability Assessment",
    description=(
        "Executes deterministic prospective forecast bust detection using strictly "
        "issuance-time forecast telemetry (NCMRWF NEPS ensemble spread & geometry). "
        "Enforces strict anti-leakage guards; rejects any historical verification inputs."
    ),
)
async def predict_reliability(request: LiveInferenceRequest) -> LiveInferenceResponse:
    """Execute live deterministic inference."""
    try:
        return production_engine.evaluate(request)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Inference evaluation failed: {str(exc)}",
        ) from exc


@router.get(
    "/model-info",
    summary="Active Production Model & Governance Metadata",
    description="Returns versioned metadata, training provenance, and research candidate status.",
)
async def get_model_info() -> Dict[str, Any]:
    """Return model governance and metadata."""
    return {
        "production_model": asdict(M1_SPREAD_ONLY_METADATA),
        "reference_baseline": asdict(M0_CLIMATOLOGY_METADATA),
        "research_catalog": RESEARCH_MODELS_CATALOG,
        "authoritative_bust_threshold": "tau(lead) = 90.0 * (1.0 + 0.008 * lead) km",
        "governance_rule": "M1 is the primary machine baseline. Complex models (M2, M3, M6) are provisional research candidates.",
    }
