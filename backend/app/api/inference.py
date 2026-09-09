"""API Router for Live Operational Inference and Model Governance."""

from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, status

from backend.app.schemas.inference import (
    LiveInferenceRequest,
    LiveInferenceResponse,
)
from backend.app.schemas.novelty import (
    NoveltyAssessmentResponse,
    ReferencePopulationMetadataResponse,
)
from backend.app.services.inference_engine import production_engine
from backend.app.services.model_config import (
    M0_CLIMATOLOGY_METADATA,
    M1_SPREAD_ONLY_METADATA,
    RESEARCH_MODELS_CATALOG,
    asdict,
)
from backend.app.services.novelty_service import novelty_service

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


@router.post(
    "/novelty",
    response_model=NoveltyAssessmentResponse,
    summary="Evaluate Forecast Representation & Novelty",
    description=(
        "Evaluates how well represented the current forecast state is by the historical "
        "population ForecastGuard was developed from. Returns deterministic representation "
        "state (WELL_REPRESENTED | LOW_SUPPORT | NOVEL_STATE | INSUFFICIENT_EVIDENCE), "
        "support distance, and abstention recommendation."
    ),
)
async def assess_novelty(request: LiveInferenceRequest) -> NoveltyAssessmentResponse:
    """Evaluate OOD representation and abstention guidance for a forecast state."""
    try:
        response = production_engine.evaluate(request)
        if response.novelty_assessment is not None:
            return response.novelty_assessment
        # Fallback if None
        return novelty_service.evaluate_novelty(response.features_extracted, len(request.ensemble_members))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Novelty evaluation failed: {str(exc)}",
        ) from exc


@router.get(
    "/reference-population",
    response_model=ReferencePopulationMetadataResponse,
    summary="Historical Reference Population Metadata",
    description=(
        "Returns audit metadata, sample counts, feature schema, cutoff date, "
        "and empirical quantile thresholds for the historical reference population."
    ),
)
async def get_reference_population() -> ReferencePopulationMetadataResponse:
    """Return historical reference population manifest and thresholds."""
    return novelty_service.get_reference_metadata()


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
        "ood_intelligence": {
            "service": "NoveltyDetector",
            "reference_id": "EXPANDED_CYCLONE_10CYCLES_77LEADS_MAY_NOV_2023",
            "states": ["WELL_REPRESENTED", "LOW_SUPPORT", "NOVEL_STATE", "INSUFFICIENT_EVIDENCE"],
        },
    }
