"""Schemas for Core Operational Forecast Input, Ingestion Validation, and Analysis."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class EnsembleMemberFix(BaseModel):
    """Vortex fix for an individual ensemble member."""

    member_id: int = Field(..., ge=1, le=100, description="Ensemble member identifier (1-11 for NEPS).")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Vortex latitude in degrees North.")
    longitude: float = Field(..., ge=-180.0, le=360.0, description="Vortex longitude in degrees East.")
    central_pressure_hpa: Optional[float] = Field(None, ge=800.0, le=1050.0, description="Minimum central MSLP in hPa.")

    model_config = ConfigDict(extra="forbid")

    @field_validator("latitude", "longitude")
    @classmethod
    def validate_finite_coords(cls, v: float) -> float:
        import math
        if math.isnan(v) or math.isinf(v):
            raise ValueError("Coordinate values must be finite numbers.")
        return v


class ObservedVerificationFix(BaseModel):
    """Ground-truth verification observation (optional, available only after observation time)."""

    observed_lat: float = Field(..., ge=-90.0, le=90.0)
    observed_lon: float = Field(..., ge=-180.0, le=360.0)
    observed_pressure_hpa: Optional[float] = Field(None, ge=800.0, le=1050.0)
    best_track_agency: Optional[str] = Field("IMD / RSMC New Delhi", description="Authoritative best-track agency")

    model_config = ConfigDict(extra="forbid")


class ForecastInputPayload(BaseModel):
    """Standard ForecastGuard real forecast input contract."""

    forecast_source: str = Field("NCMRWF_NEPS", description="NWP origin or ensemble system")
    cyclone_name: str = Field(..., description="Storm identifier or operational case name")
    forecast_cycle: datetime = Field(..., description="UTC forecast cycle initialization time")
    lead_hours: int = Field(..., ge=0, le=168, description="Forecast lead time in hours")
    valid_time: datetime = Field(..., description="Target forecast verification valid time")
    basin: str = Field("Bay of Bengal", description="Ocean basin: Bay of Bengal | Arabian Sea | North Indian Ocean")
    ensemble_members: List[EnsembleMemberFix] = Field(
        ...,
        min_length=1,
        description="List of ensemble member vortex center fixes (minimum 5 required for full dispersion analysis)",
    )
    deterministic_center: Optional[Dict[str, float]] = Field(
        None, description="Optional high-resolution deterministic center fix {latitude, longitude, mslp_hpa}"
    )
    observed_verification: Optional[ObservedVerificationFix] = Field(
        None, description="Post-event ground truth (if omitted, forecast is classified as PENDING_VERIFICATION)"
    )

    model_config = ConfigDict(extra="forbid")


class ForecastValidationResult(BaseModel):
    """Validation report returned upon inspecting an uploaded forecast."""

    is_valid: bool = Field(..., description="Whether the input satisfies ForecastGuard ingestion requirements")
    validation_status: Literal["PASS", "DEGRADED", "REJECTED"] = Field(..., description="Validation tier")
    errors: List[str] = Field(default_factory=list, description="Fatal blocking contract errors")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal data quality warnings")
    forecast_source: Optional[str] = None
    cyclone_name: Optional[str] = None
    forecast_cycle: Optional[str] = None
    lead_hours: Optional[int] = None
    valid_time: Optional[str] = None
    ensemble_members_count: int = Field(0, description="Count of valid ensemble member fixes detected")
    geographic_bounds: Optional[Dict[str, float]] = Field(
        None, description="Bounding box {min_lat, max_lat, min_lon, max_lon}"
    )
    supported_variables: List[str] = Field(default_factory=list)
    verification_mode: Literal["PROSPECTIVE_PENDING", "HISTORICAL_VERIFIED"] = Field(
        ..., description="Whether ground-truth observation is present or pending"
    )


class WhereAssessment(BaseModel):
    """WHERE dimension: spatial focus, centroid, and risk halo."""

    basin: str
    centroid_lat: float
    centroid_lon: float
    affected_region_label: str
    tolerance_radius_km: float
    dispersion_radius_km: float
    bounding_box: Dict[str, float]


class WhenAssessment(BaseModel):
    """WHEN dimension: timing, lead horizon, and failure window."""

    lead_hours: int
    forecast_cycle: str
    valid_time: str
    expected_failure_window: str
    expected_failure_window_desc: str


class WhyEvidence(BaseModel):
    """WHY dimension: ranked prospective evidence factors and analogues."""

    ensemble_spread_km: float
    ensemble_divergence_km: float
    anisotropy_ratio: float
    bimodality_coefficient: Optional[float] = None
    ood_representation_state: str
    ood_support_score: Optional[int] = None
    closest_historical_analogue: Optional[str] = None
    analogue_similarity_desc: Optional[str] = None
    ranked_factors: List[Dict[str, Any]] = Field(default_factory=list)


class ForecastAnalysisResponse(BaseModel):
    """Complete operational reliability assessment for an ingested forecast."""

    status: Literal["ok", "insufficient_data", "error"]
    reliability_state: str
    bust_risk_percent: Optional[int] = None
    reliability_score: Optional[int] = None
    verification_status: Literal["PENDING_VERIFICATION", "VERIFIED"]
    verification_detail: Optional[Dict[str, Any]] = None
    where: WhereAssessment
    when: WhenAssessment
    why: WhyEvidence
    data_quality: Dict[str, Any]
    provenance: Dict[str, Any]
    message: str
