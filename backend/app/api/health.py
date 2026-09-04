"""Health check API endpoint."""

from fastapi import APIRouter
from backend.app.config import settings
from backend.app.schemas.health import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns the truthful runtime status of the ForecastGuard API service.",
)
async def get_health() -> HealthResponse:
    """Return application health and metadata."""
    return HealthResponse(
        status="ok",
        service=settings.service_name,
        version=settings.version,
        environment=settings.environment,
    )
