from datetime import datetime, timezone
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
from backend.app.schemas.multimodel import (
    DataAuditSummaryResponse,
    MultiModelEvidenceRequest,
    MultiModelEvidenceResponse,
)
from backend.app.schemas.forecast_input import (
    ForecastAnalysisResponse,
    ForecastInputPayload,
    ForecastValidationResult,
)
from backend.app.services.inference_engine import production_engine
from backend.app.services.model_config import (
    M0_CLIMATOLOGY_METADATA,
    M1_SPREAD_ONLY_METADATA,
    RESEARCH_MODELS_CATALOG,
    asdict,
)
from backend.app.services.novelty_service import novelty_service
from backend.app.services.multimodel_service import multimodel_service
from backend.app.services.forecast_ingestion_service import forecast_ingestion_service

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
    "/multimodel/audit",
    response_model=DataAuditSummaryResponse,
    summary="NWP Multi-Model Archive Availability Audit",
    description=(
        "Returns authoritative audit of regional NWP forecast system availability in ForecastGuard. "
        "Reports operational status, resolution, historical coverage, missingness, and decision gate outcome."
    ),
)
async def get_multimodel_audit() -> DataAuditSummaryResponse:
    """Return NWP archive availability audit and decision gate status."""
    return multimodel_service.get_data_audit()


@router.post(
    "/multimodel/agreement",
    response_model=MultiModelEvidenceResponse,
    summary="Evaluate Multi-Model Forecast Agreement",
    description=(
        "Evaluates cross-model forecast agreement for prospective model fixes. "
        "Calculates pairwise great-circle separation and intensity disagreement. "
        "Returns INSUFFICIENT_EVIDENCE if fewer than 2 independent models are supplied."
    ),
)
async def assess_multimodel_agreement(request: MultiModelEvidenceRequest) -> MultiModelEvidenceResponse:
    """Evaluate cross-model agreement for independent model fixes."""
    try:
        return multimodel_service.evaluate_agreement(request)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Multi-model agreement evaluation failed: {str(exc)}",
        ) from exc


@router.post(
    "/upload",
    response_model=ForecastValidationResult,
    summary="Validate & Ingest Uploaded Forecast",
    description=(
        "Inspects an uploaded forecast payload (NCMRWF NEPS ensemble fixes). "
        "Validates cycle, lead time, coordinates, and ensemble member coverage without executing predictions."
    ),
)
async def upload_forecast(payload: Dict[str, Any]) -> ForecastValidationResult:
    """Validate raw uploaded forecast payload and report metadata / contract compliance."""
    _, validation = forecast_ingestion_service.validate_payload(payload)
    return validation


@router.post(
    "/analyze",
    response_model=ForecastAnalysisResponse,
    summary="Analyze Forecast Reliability (Core Operational Flow)",
    description=(
        "Executes the full ForecastGuard evidence pipeline on a validated forecast. "
        "Generates WHERE + WHEN + RISK + WHY breakdown. Classifies prospective forecasts as "
        "PENDING_VERIFICATION (never prematurely confirmed bust)."
    ),
)
async def analyze_forecast(payload: Dict[str, Any]) -> ForecastAnalysisResponse:
    """Analyze forecast reliability, generating WHERE, WHEN, RISK, and WHY evidence."""
    parsed, validation = forecast_ingestion_service.validate_payload(payload)
    if not validation.is_valid or parsed is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Forecast validation failed. Input does not satisfy ForecastGuard contract.",
                "errors": validation.errors,
            },
        )
    return forecast_ingestion_service.analyze_forecast(parsed)


@router.get(
    "/sample-forecasts",
    summary="Catalog of Real Verified NCMRWF Forecast Fixtures",
    description=(
        "Returns pre-built real forecast fixtures from verified North Indian Ocean archives "
        "(e.g. MICHAUNG +24h, BIPARJOY +18h, MIDHILI +30h) for 1-click testing and demonstration."
    ),
)
async def get_sample_forecasts() -> List[Dict[str, Any]]:
    """Return catalog of real forecast fixtures for rapid professor testing."""
    return forecast_ingestion_service.get_sample_forecasts()


@router.get(
    "/live-status",
    summary="Live NWP Telemetry Feed Availability Status",
    description=(
        "Reports availability of live authorized NCMRWF / IMD telemetry feeds. "
        "Reports LIVE DATA UNAVAILABLE when environment credentials are not present, "
        "recommending Forecast Upload or Historical Replay."
    ),
)
async def get_live_status() -> Dict[str, Any]:
    """Return live telemetry feed connection status and available alternatives."""
    return forecast_ingestion_service.get_live_feed_status()


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
        "multimodel_evidence": {
            "service": "MultiModelAgreementEngine",
            "decision_gate": "INSUFFICIENT_EVIDENCE",
            "operational_models": ["NCMRWF_NEPS"],
            "states": ["INSUFFICIENT_EVIDENCE", "AGREEMENT", "MODERATE_DISAGREEMENT", "HIGH_DISAGREEMENT"],
        },
        "operational_input": {
            "pipeline": "ForecastIngestionService",
            "supported_sources": ["NCMRWF_NEPS"],
            "verification_states": ["PENDING_VERIFICATION", "VERIFIED"],
        },
    }
