"""Health response schema."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Schema for the API health check response."""

    status: str = Field(..., description="Service status", examples=["ok"])
    service: str = Field(..., description="Service identifier", examples=["ForecastGuard API"])
    version: str = Field(..., description="Application version", examples=["0.1.0"])
    environment: str = Field(..., description="Runtime environment", examples=["development"])
