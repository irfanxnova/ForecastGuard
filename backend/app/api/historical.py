"""API Router for Historical Replay, Verified Cyclone Cases, and Bust Atlas."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from backend.app.schemas.historical import (
    BustAtlasRecord,
    CycloneSummary,
    HistoricalReplayResponse,
)
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
