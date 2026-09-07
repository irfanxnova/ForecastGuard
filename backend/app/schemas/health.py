"""Health and Readiness response schemas."""

from typing import Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Schema for the API health check response."""

    status: str = Field(..., description="Service status", examples=["ok"])
    service: str = Field(..., description="Service identifier", examples=["ForecastGuard API"])
    version: str = Field(..., description="Application version", examples=["0.1.0"])
    environment: str = Field(..., description="Runtime environment", examples=["development"])


class ReadinessResponse(BaseModel):
    """Schema for the API readiness check response."""

    status: str = Field(..., description="Readiness status", examples=["ready"])
    service: str = Field(..., description="Service identifier", examples=["ForecastGuard API"])
    version: str = Field(..., description="Application version", examples=["0.1.0"])
    production_model: str = Field(..., description="Active production model ID")
    verified_dataset_loaded: bool = Field(..., description="Whether verified validation dataset is loaded")
    verified_leads_count: int = Field(..., description="Number of audited verified leads loaded")
