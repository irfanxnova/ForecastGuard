"""Health and Readiness check API endpoints."""

from fastapi import APIRouter
from backend.app.config import settings
from backend.app.schemas.health import HealthResponse, ReadinessResponse
from backend.app.services.historical_service import historical_service
from backend.app.services.model_config import M1_SPREAD_ONLY_METADATA

router = APIRouter(tags=["Health & Readiness"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness check",
    description="Returns the runtime status of the ForecastGuard API service.",
)
async def get_health() -> HealthResponse:
    """Return application health and metadata."""
    return HealthResponse(
        status="ok",
        service=settings.service_name,
        version=settings.version,
        environment=settings.environment,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness check",
    description="Verifies that models, schemas, and historical datasets are loaded and ready to serve traffic.",
)
async def get_ready() -> ReadinessResponse:
    """Return operational readiness of inference engine and datasets."""
    cyclones = historical_service.list_cyclones()
    total_leads = sum(c.verified_leads_count for c in cyclones)
    return ReadinessResponse(
        status="ready",
        service=settings.service_name,
        version=settings.version,
        production_model=M1_SPREAD_ONLY_METADATA.model_name,
        verified_dataset_loaded=len(cyclones) > 0,
        verified_leads_count=total_leads,
    )
