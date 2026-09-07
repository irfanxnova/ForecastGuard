"""Schemas for Live Operational Inference, Data Quality, and Provenance."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class EnsembleMemberInput(BaseModel):
    """Single ensemble member synoptic vortex fix."""

    model_config = ConfigDict(extra="forbid")

    member_id: int = Field(..., ge=0, le=100, description="Ensemble member identifier (1-11 for NEPS).")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Vortex center latitude in degrees North.")
    longitude: float = Field(..., ge=-180.0, le=360.0, description="Vortex center longitude in degrees East.")
    central_pressure_hpa: Optional[float] = Field(None, ge=850.0, le=1050.0, description="Central MSLP in hPa.")


class LiveInferenceRequest(BaseModel):
    """Strict Live Operational Inference Request.

    Accepts ONLY information available at forecast issuance.
    Strictly forbids any ground-truth observations, future verification errors,
    retrospective quadrants, or bust labels (ConfigDict extra='forbid').
    """

    model_config = ConfigDict(extra="forbid")

    forecast_source: str = Field(
        default="NCMRWF TIGGE",
        description="Originating NWP ensemble prediction system.",
    )
    forecast_cycle: str = Field(
        ...,
        description="Forecast initialization cycle in ISO 8601 UTC format (e.g., '2023-12-01T00:00:00Z').",
    )
    valid_time: str = Field(
        ...,
        description="Forecast valid time in ISO 8601 UTC format (e.g., '2023-12-02T00:00:00Z').",
    )
    lead_hours: int = Field(
        ...,
        ge=6,
        le=240,
        description="Forecast lead time in hours (6-hourly steps: 6, 12, 18, 24, ..., 48).",
    )
    variable: str = Field(
        default="Mean Sea Level Pressure (msl)",
        description="Atmospheric variable used for vortex tracking.",
    )
    deterministic_lat: Optional[float] = Field(
        None,
        ge=-90.0,
        le=90.0,
        description="Optional deterministic control run center latitude.",
    )
    deterministic_lon: Optional[float] = Field(
        None,
        ge=-180.0,
        le=360.0,
        description="Optional deterministic control run center longitude.",
    )
    ensemble_members: List[EnsembleMemberInput] = Field(
        ...,
        min_length=0,
        description="List of ensemble member vortex center coordinates at this lead.",
    )

    @field_validator("forecast_cycle", "valid_time")
    @classmethod
    def validate_utc_timestamp(cls, v: str) -> str:
        """Enforce standard ISO 8601 timestamp parsing."""
        try:
            # Normalize trailing Z for fromisoformat compatibility
            ts = v.replace("Z", "+00:00")
            dt = datetime.fromisoformat(ts)
            return dt.isoformat()
        except Exception as exc:
            raise ValueError(f"Invalid ISO 8601 timestamp: '{v}'. Expected format: YYYY-MM-DDTHH:MM:SSZ") from exc


class InferenceProvenance(BaseModel):
    """Truthful data provenance attached to every forecast assessment."""

    forecast_source: str = Field(..., description="NWP origin e.g. NCMRWF TIGGE")
    forecast_cycle: str = Field(..., description="Forecast initialization cycle in UTC")
    valid_time: str = Field(..., description="Forecast valid time in UTC")
    lead_time: str = Field(..., description="Formatted lead step e.g. +24h")
    ensemble_member_count: str = Field(..., description="Number of ingested ensemble members")
    variables_used: List[str] = Field(..., description="List of atmospheric parameters used")
    feature_version: str = Field(..., description="Feature schema version")
    model_name: str = Field(..., description="Active production model ID")
    model_version: str = Field(..., description="Active production model version")
    scientific_status: str = Field(..., description="Scientific status tier")
    processing_status: str = Field(..., description="DATA COMPLETE | DATA DEGRADED | DATA INSUFFICIENT")


class LiveInferenceResponse(BaseModel):
    """Structured response for Live Operational Inference."""

    status: Literal["ok", "insufficient_data"] = Field(..., description="Operational response status")
    data_quality: Literal["DATA COMPLETE", "DATA DEGRADED", "DATA INSUFFICIENT"] = Field(
        ..., description="Data completeness and quality indicator"
    )
    quality_detail: str = Field(..., description="Explanation of data quality status")
    reliability_state: Optional[Literal["STABLE", "WATCH", "VULNERABLE", "SEVERE", "DATA_INSUFFICIENT"]] = Field(
        None, description="Operational forecast reliability category"
    )
    bust_risk_percent: Optional[int] = Field(
        None, ge=0, le=100, description="Predicted prospective bust probability as percentage"
    )
    reliability_score: Optional[int] = Field(
        None, ge=0, le=100, description="Calibrated operational reliability index (100 - risk)"
    )
    message: str = Field(..., description="Primary operational summary message")
    features_extracted: Optional[Dict[str, float]] = Field(
        None, description="Tier A/B strictly prospective predictor features"
    )
    provenance: InferenceProvenance = Field(..., description="Complete audit provenance metadata")
