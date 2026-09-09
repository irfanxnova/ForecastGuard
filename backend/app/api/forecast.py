"""API Router for Live Forecast Exploration and Operational Provider Abstraction."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from backend.app.schemas.forecast import ForecastLocation, LiveForecastResponse
from backend.app.services.forecast_provider import forecast_provider_service

router = APIRouter(prefix="/forecast", tags=["Live Forecast Exploration"])


@router.get(
    "/locations",
    response_model=List[ForecastLocation],
    summary="List Preset Geographic Locations",
    description="Returns vetted quick-select locations across maritime cyclone basins and urban sectors.",
)
async def list_forecast_locations() -> List[ForecastLocation]:
    """Retrieve list of preset geographic query targets."""
    return forecast_provider_service.get_preset_locations()


@router.get(
    "/live",
    response_model=LiveForecastResponse,
    summary="Retrieve Live 10-Day Medium-Range Forecast",
    description=(
        "Retrieves a real prospective 10-day medium-range forecast (D+1 to D+10) for target coordinates. "
        "Enforces strict scientific capability awareness: outputs real calibrated bust probabilities for "
        "supported tropical cyclone cases, and explicitly outputs 'NOT VALIDATED FOR THIS INPUT DOMAIN' "
        "for general coordinates or third-party feeds."
    ),
)
async def get_live_forecast(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Latitude in degrees North"),
    longitude: float = Query(..., ge=-180.0, le=360.0, description="Longitude in degrees East"),
    location_name: Optional[str] = Query(None, description="Optional display name"),
    case_id: Optional[str] = Query(None, description="Optional supported historical cyclone case ID e.g. 'MIDHILI_00Z'"),
) -> LiveForecastResponse:
    """Execute live forecast query with capability-aware reliability assessment."""
    try:
        return forecast_provider_service.get_live_forecast(
            latitude=latitude,
            longitude=longitude,
            location_name=location_name,
            preferred_case_id=case_id,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Live forecast retrieval failed: {str(exc)}",
        ) from exc
