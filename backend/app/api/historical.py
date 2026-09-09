"""API Router for Historical Replay, Verified Cyclone Cases, and Bust Atlas."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from backend.app.schemas.historical import (
    BustAtlasRecord,
    CycloneSummary,
    HistoricalReplayResponse,
)
from backend.app.schemas.historical_memory import (
    BustAtlasDetail,
    HistoricalMemorySearchRequest,
    HistoricalMemorySearchResponse,
)
from backend.app.services.historical_memory_service import historical_memory_service
from backend.app.services.historical_service import historical_service

router = APIRouter(prefix="/historical", tags=["Historical Replay & Verification"])


@router.get(
    "/cyclones",
    response_model=List[CycloneSummary],
    summary="List Historical Tropical Cyclones",
    description="Returns all 6 audited cyclones (MOCHA, BIPARJOY, TEJ, HAMOON, MIDHILI, MICHAUNG) and available cycles.",
)
async def list_cyclones() -> List[CycloneSummary]:
    """List available historical cyclone cases."""
    return historical_service.list_cyclones()


@router.get(
    "/replay/{storm_name}",
    response_model=HistoricalReplayResponse,
    summary="Historical Forecast Replay",
    description=(
        "Retrieves lead-by-lead (+06h to +48h) historical forecast trajectory, "
        "ensemble evidence, continuous track error, and official IMD/RSMC best-track verification."
    ),
)
async def get_cyclone_replay(
    storm_name: str,
    cycle_label: Optional[str] = Query(None, description="Specific cycle label e.g. MICHAUNG_00Z"),
) -> HistoricalReplayResponse:
    """Retrieve historical replay sequence."""
    replay = historical_service.get_replay(storm_name, cycle_label)
    if replay is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Historical case for storm '{storm_name}' not found in verified dataset.",
        )
    return replay


@router.get(
    "/bust-atlas",
    response_model=List[BustAtlasRecord],
    summary="Forecast Bust Atlas",
    description="Returns verified forecast failure records and false-confidence cases.",
)
async def get_bust_atlas() -> List[BustAtlasRecord]:
    """Retrieve curated Cyclone Bust Atlas records."""
    return historical_service.get_bust_atlas()


@router.get(
    "/bust-atlas/detail",
    response_model=List[BustAtlasDetail],
    summary="Detailed Forecast Bust Atlas",
    description="Returns comprehensive Bust Atlas records with failure fingerprints, observed coordinates, and thresholds.",
)
async def get_bust_atlas_detail(
    storm_name: Optional[str] = Query(None, description="Filter by storm name e.g. MOCHA"),
    severity: Optional[str] = Query(None, description="Filter by severity: DEGRADED, SEVERE"),
    quadrant: Optional[str] = Query(None, description="Filter by reliability quadrant"),
) -> List[BustAtlasDetail]:
    """Retrieve detailed Bust Atlas records with failure fingerprints."""
    return historical_memory_service.get_bust_atlas_records(
        storm_name=storm_name,
        severity=severity,
        quadrant=quadrant,
    )


@router.post(
    "/memory/search",
    response_model=HistoricalMemorySearchResponse,
    summary="Search Historical Forecast Memory",
    description=(
        "Searches verified historical archive for nearest forecast-state analogues using "
        "strictly anti-leakage forecast predictors available at cutoff T. "
        "Ground-truth verification outcomes are attached only post-retrieval."
    ),
)
async def search_historical_memory(
    request: HistoricalMemorySearchRequest,
) -> HistoricalMemorySearchResponse:
    """Execute deterministic historical memory analogue search."""
    try:
        return historical_memory_service.search_analogues(request)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/memory/analogue/{case_id}",
    summary="Historical Analogue Case Details",
    description="Retrieves full historical forecast state and verified outcome for a specific case ID.",
)
async def get_analogue_detail(case_id: str):
    """Retrieve single historical analogue case by ID."""
    rec = historical_memory_service.get_analogue_by_id(case_id)
    if rec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Historical case ID '{case_id}' not found in verified archive.",
        )
    fingerprint = historical_memory_service.build_failure_fingerprint(rec)
    return {
        "case_id": case_id,
        "storm_name": rec["storm_name"],
        "basin": rec["basin"],
        "cycle_label": rec["cycle_label"],
        "forecast_lead_hours": rec["forecast_lead_hours"],
        "initialization_time": rec["initialization_time"],
        "forecast_valid_time": rec["forecast_valid_time"],
        "forecast_center": {
            "latitude": rec["forecast_lat"],
            "longitude": rec["forecast_lon"],
            "pressure_hpa": rec.get("forecast_pressure_hpa"),
        },
        "verified_outcome": {
            "verification_status": "VERIFIED",
            "observed_latitude": rec["observed_lat"],
            "observed_longitude": rec["observed_lon"],
            "observed_pressure_hpa": rec.get("observed_pressure_hpa"),
            "track_error_km": rec["track_error_km"],
            "threshold_km": rec["threshold_km"],
            "is_bust": bool(rec["bust_label"] == 1),
            "severity": rec.get("severity"),
            "confidence_quadrant": rec.get("confidence_quadrant"),
        },
        "failure_fingerprint": fingerprint.model_dump(),
        "provenance": {
            "forecast_source": "NCMRWF NEPS 11-member ensemble",
            "verification_source": "Official IMD/RSMC Best Tracks",
        },
    }


@router.get(
    "/fingerprint/{storm_name}",
    summary="Storm Failure Fingerprint",
    description="Retrieves the diagnostic failure signature and observed forecast behaviour for a given storm.",
)
async def get_storm_fingerprint(storm_name: str):
    """Retrieve storm failure fingerprint summary."""
    res = historical_memory_service.get_storm_failure_fingerprint(storm_name)
    if res.get("status") == "INSUFFICIENT_EVIDENCE":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=res["message"],
        )
    return res

