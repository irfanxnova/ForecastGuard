"""FastAPI Router for Regional Reliability Intelligence (ForecastGuard V2).

Exposes canonical regional reliability assessments computed directly from
real NWP ensemble forecasts with strict anti-leakage invariants.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from backend.app.schemas.regional import (
    CanonicalRegionalAssessment,
    CycleComparison,
    RegionalAssessmentResponse,
    RegionalCaseSummary,
    RegionalFeatureCatalogItem,
    RegionalTimelineResponse,
    RegionalVerificationResponse,
    ReplayCaseResponse,
)
from backend.app.services.regional_service import regional_service

router = APIRouter(prefix="/regional", tags=["Regional Reliability Intelligence"])


@router.get(
    "/cases",
    response_model=List[RegionalCaseSummary],
    summary="Supported Regional Forecast Cases",
    description="Returns available real NWP forecast cases with validated GRIB datasets and supported horizons.",
)
async def list_cases() -> List[RegionalCaseSummary]:
    """List all supported forecast cases."""
    return regional_service.list_supported_cases()


@router.get(
    "/features",
    response_model=List[RegionalFeatureCatalogItem],
    summary="Regional Features Catalog",
    description=(
        "Returns the explicit catalog of genuine regional features evaluated by "
        "ForecastGuard V2, including scientific definitions, physical units, sources, "
        "audited status, and candidate model roles."
    ),
)
async def get_feature_catalog() -> List[RegionalFeatureCatalogItem]:
    """List all canonical regional features and metadata."""
    return regional_service.get_feature_catalog()


@router.get(
    "/assessment",
    response_model=RegionalAssessmentResponse,
    summary="Canonical Regional Reliability Assessment",
    description=(
        "Returns prospective regional reliability assessments across ForecastGuard "
        "predefined analytical regions for a given forecast case, lead horizon, and variable. "
        "Enforces strict anti-leakage guards and explicit insufficient evidence representations."
    ),
)
async def get_regional_assessment(
    case_id: str = Query(
        "MIDHILI_00Z",
        description="Forecast case identifier (e.g. 'MIDHILI_00Z', 'MICHAUNG_00Z', 'BIPARJOY_00Z')",
    ),
    lead_time: str = Query(
        "D+1",
        description="Forecast lead time horizon (e.g. 'D+1', 'D+2', '+18h', 'D+3', ..., 'D+10')",
    ),
    variable: Optional[str] = Query(
        None,
        description="Atmospheric variable name (e.g. 'Mean Sea Level Pressure (msl)')",
    ),
    as_of_cutoff: Optional[str] = Query(
        None,
        description="Replay cutoff time ISO 8601 UTC to enforce strict knowledge boundary (anti-leakage)",
    ),
    reveal_verification: bool = Query(
        True,
        description="Whether to reveal verification outcome at or before cutoff",
    ),
) -> RegionalAssessmentResponse:
    """Evaluate regional forecast reliability."""
    try:
        return regional_service.evaluate_regional_assessment(
            case_id=case_id,
            lead_time=lead_time,
            variable=variable,
            as_of_cutoff=as_of_cutoff,
            reveal_verification=reveal_verification,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Regional assessment evaluation error: {str(exc)}",
        ) from exc


@router.get(
    "/region/{region_id}",
    response_model=CanonicalRegionalAssessment,
    summary="Detailed Single-Region Reliability Assessment",
    description="Returns focused intelligence rail data for a single meteorological region.",
)
async def get_single_region_assessment(
    region_id: str,
    case_id: str = Query("MIDHILI_00Z", description="Forecast case ID"),
    lead_time: str = Query("D+1", description="Lead time horizon"),
    variable: Optional[str] = Query(None, description="Atmospheric variable"),
) -> CanonicalRegionalAssessment:
    """Return single region assessment object."""
    assessment_resp = await get_regional_assessment(
        case_id=case_id,
        lead_time=lead_time,
        variable=variable,
    )
    for reg in assessment_resp.regions:
        if reg.region_id.upper() == region_id.upper():
            return reg
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Region '{region_id}' not found in assessment response.",
    )


@router.get(
    "/verification/{case_id}",
    response_model=RegionalVerificationResponse,
    summary="Case Forecast-vs-Observation Verification",
    description="Returns ground-truth verification records from official IMD Best Track reports for the selected case.",
)
async def get_case_verification(case_id: str) -> RegionalVerificationResponse:
    """Return all verified ground-truth records for a forecast case."""
    try:
        return regional_service.get_case_verification(case_id=case_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification lookup error: {str(exc)}",
        ) from exc


@router.get(
    "/timeline/{case_id}",
    response_model=RegionalTimelineResponse,
    summary="6-Hourly Regional Reliability Evolution",
    description="Returns synoptic step-by-step reliability trajectory, state transitions, first actionable signal, and cycle comparisons.",
)
async def get_regional_timeline(
    case_id: str,
    region_id: Optional[str] = Query(None, description="Analytical region ID (defaults to primary affected region)"),
) -> RegionalTimelineResponse:
    """Retrieve full 6-hourly temporal reliability series for a region."""
    try:
        return regional_service.get_regional_timeline(case_id=case_id, region_id=region_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Timeline generation error: {str(exc)}",
        ) from exc


@router.get(
    "/replay/{case_id}",
    response_model=ReplayCaseResponse,
    summary="Historical Case Replay Session",
    description=(
        "Executes a deterministic historical replay stepping through synoptic cutoffs. "
        "Enforces strict knowledge boundaries where future observations remain locked."
    ),
)
async def get_case_replay(
    case_id: str,
    region_id: Optional[str] = Query(None, description="Focused analytical region ID"),
    reveal_verification: bool = Query(
        True,
        description="Whether to reveal verified ground-truth at or before the cutoff time",
    ),
) -> ReplayCaseResponse:
    """Retrieve chronological replay session for a forecast case."""
    try:
        return regional_service.get_case_replay(
            case_id=case_id,
            region_id=region_id,
            reveal_verification=reveal_verification,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Replay generation error: {str(exc)}",
        ) from exc


@router.get(
    "/comparison/{case_id}",
    response_model=Optional[CycleComparison],
    summary="Cycle-over-Cycle What Changed Comparison",
    description="Physical cycle-to-cycle comparison against consecutive runs on disk.",
)
async def get_cycle_comparison(
    case_id: str,
    region_id: Optional[str] = Query(None, description="Focused analytical region ID"),
) -> Optional[CycleComparison]:
    """Retrieve cycle-over-cycle comparison."""
    try:
        return regional_service.get_cycle_comparison(case_id=case_id, region_id=region_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cycle comparison error: {str(exc)}",
        ) from exc

