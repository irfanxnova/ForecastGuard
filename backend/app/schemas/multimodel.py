"""Pydantic schemas for Multi-Model Forecast Agreement & NWP Evidence."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ModelForecastFixInput(BaseModel):
    """Prospective vortex fix input from an individual NWP forecast model."""

    model_id: str = Field(..., description="Unique model identifier, e.g. NCMRWF_NEPS, ECMWF_IFS")
    center: str = Field(..., description="Operating meteorological centre name or abbreviation")
    initialization_time: datetime = Field(..., description="UTC cycle initialization timestamp")
    forecast_lead_hours: int = Field(..., ge=0, le=240, description="Forecast lead step in hours")
    valid_time: datetime = Field(..., description="Target valid verification timestamp")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Vortex latitude in degrees")
    longitude: float = Field(..., ge=-180.0, le=360.0, description="Vortex longitude in degrees")
    mslp_hpa: Optional[float] = Field(None, ge=800.0, le=1050.0, description="Central minimum MSLP in hPa")
    max_wind_kts: Optional[float] = Field(None, ge=0.0, le=250.0, description="Estimated maximum sustained wind in knots")

    model_config = ConfigDict(extra="forbid")

    @field_validator("latitude", "longitude")
    @classmethod
    def validate_finite_coords(cls, v: float) -> float:
        import math
        if math.isnan(v) or math.isinf(v):
            raise ValueError("Coordinate values must be finite numbers.")
        return v


class MultiModelEvidenceRequest(BaseModel):
    """Payload for evaluating cross-model forecast agreement."""

    models: List[ModelForecastFixInput] = Field(
        ...,
        description="List of model vortex fixes at identical valid times for cross-model agreement evaluation",
    )

    model_config = ConfigDict(extra="forbid")


class MultiModelEvidenceResponse(BaseModel):
    """Standardized output of cross-model forecast agreement assessment."""

    state: Literal["INSUFFICIENT_EVIDENCE", "AGREEMENT", "MODERATE_DISAGREEMENT", "HIGH_DISAGREEMENT"] = Field(
        ..., description="Categorical cross-system agreement state"
    )
    models_evaluated: List[str] = Field(..., description="List of model identifiers evaluated")
    available_model_count: int = Field(..., description="Number of distinct valid model inputs evaluated")
    valid_time: Optional[str] = Field(None, description="ISO-8601 target valid time evaluated")
    forecast_cycle: Optional[str] = Field(None, description="ISO-8601 reference forecast cycle")
    lead_hours: Optional[int] = Field(None, description="Forecast lead step in hours")
    mean_track_separation_km: Optional[float] = Field(None, description="Average pairwise track separation distance in km")
    max_track_separation_km: Optional[float] = Field(None, description="Maximum pairwise track separation distance in km")
    pairwise_separations_km: Dict[str, float] = Field(
        default_factory=dict, description="Pairwise separation distances in km between specific models"
    )
    mslp_disagreement_hpa: Optional[float] = Field(None, description="Maximum difference in central pressure across models in hPa")
    agreement_notice: str = Field(..., description="Human-readable decision-support and evidence disclosure notice")
    validation_status: str = Field(..., description="Operational validation maturity tier (INSUFFICIENT_EVIDENCE | EXPERIMENTAL)")
    is_abstention_recommended: bool = Field(..., description="Whether multi-model evidence recommends decision abstention")
    provenance: Dict[str, Any] = Field(..., description="Audit provenance, timestamps, thresholds, and governance metadata")


class NWPModelAuditResponse(BaseModel):
    """Audit descriptor for an individual NWP forecast system."""

    model_id: str
    center_name: str
    country_or_org: str
    tigge_origin: Optional[str]
    status: str
    resolution_horizontal: Optional[str]
    native_cadence: Optional[str]
    verified_cyclone_leads: int
    verified_cycles: int
    historical_coverage_start: Optional[str]
    historical_coverage_end: Optional[str]
    variables_available: List[str]
    missingness_notes: str


class DataAuditSummaryResponse(BaseModel):
    """Comprehensive summary of repository NWP archive availability."""

    total_models_cataloged: int
    available_operational_models: int
    missing_archive_models: int
    independent_cross_model_pairs: int
    decision_gate_status: str
    decision_gate_reason: str
    catalog: Dict[str, NWPModelAuditResponse]
