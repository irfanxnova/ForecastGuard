"""Schemas for Canonical Forecast Input, Reliability Analysis, and Audit Provenance."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.schemas.novelty import NoveltyAssessmentResponse
from backend.app.schemas.multimodel import MultiModelEvidenceResponse


class EnsembleMemberInput(BaseModel):
    """Single ensemble member synoptic vortex fix."""

    model_config = ConfigDict(extra="forbid")

    member_id: int = Field(..., ge=0, le=100, description="Ensemble member identifier (1-11 for NEPS).")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Vortex center latitude in degrees North.")
    longitude: float = Field(..., ge=-180.0, le=360.0, description="Vortex center longitude in degrees East.")
    central_pressure_hpa: Optional[float] = Field(None, ge=850.0, le=1050.0, description="Central MSLP in hPa.")


class CanonicalForecastInput(BaseModel):
    """Canonical Forecast Input Contract for ForecastGuard Reliability Analysis.

    Accepts ONLY information available at forecast issuance.
    Strictly forbids any ground-truth observations, future verification errors,
    retrospective quadrants, or bust labels (ConfigDict extra='forbid').
    """

    model_config = ConfigDict(extra="forbid")

    forecast_source: str = Field(
        default="NCMRWF TIGGE",
        description="Originating NWP ensemble prediction system or telemetry feed.",
    )
    model: Optional[str] = Field(
        default=None,
        description="NWP model or center identifier e.g. NCMRWF_NEPS, ECMWF_IFS.",
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
        ge=0,
        le=240,
        description="Forecast lead time in hours (e.g. 6, 12, 18, 24, 48, ..., 240).",
    )
    variable: str = Field(
        default="Mean Sea Level Pressure (msl)",
        description="Atmospheric variable used for analysis (e.g. msl, tp, 2t).",
    )
    units: Optional[str] = Field(
        default=None,
        description="Explicit physical units of the forecast variable (e.g. hPa, Pa, mm, K).",
    )
    latitude: Optional[float] = Field(
        default=None,
        ge=-90.0,
        le=90.0,
        description="Target forecast latitude in degrees North.",
    )
    longitude: Optional[float] = Field(
        default=None,
        ge=-180.0,
        le=360.0,
        description="Target forecast longitude in degrees East.",
    )
    region: Optional[str] = Field(
        default=None,
        description="Target region or basin identifier (e.g. MAR_BOB, Bay of Bengal, MAR_AS).",
    )
    value: Optional[float] = Field(
        default=None,
        description="Optional scalar forecast value at the target coordinate.",
    )
    forecast_field_reference: Optional[str] = Field(
        default=None,
        description="Field or grid parameter reference in NWP catalog.",
    )
    deterministic_lat: Optional[float] = Field(
        default=None,
        ge=-90.0,
        le=90.0,
        description="Optional deterministic control run center latitude.",
    )
    deterministic_lon: Optional[float] = Field(
        default=None,
        ge=-180.0,
        le=360.0,
        description="Optional deterministic control run center longitude.",
    )
    ensemble_members: List[EnsembleMemberInput] = Field(
        default_factory=list,
        description="List of ensemble member vortex center coordinates at this lead.",
    )
    grid_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional grid geometry specifications (ni, nj, bounds, resolution).",
    )
    resolution: Optional[str] = Field(
        default=None,
        description="NWP model spatial resolution (e.g. '0.12°', '12 km').",
    )
    forecast_file_reference: Optional[str] = Field(
        default=None,
        description="Path or identifier of uploaded/referenced forecast file.",
    )
    provenance_info: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional issuance-time metadata dictionary.",
    )

    @field_validator("forecast_cycle", "valid_time")
    @classmethod
    def validate_utc_timestamp(cls, v: str) -> str:
        """Enforce standard ISO 8601 timestamp parsing."""
        try:
            ts = v.replace("Z", "+00:00")
            dt = datetime.fromisoformat(ts)
            return dt.isoformat()
        except Exception as exc:
            raise ValueError(f"Invalid ISO 8601 timestamp: '{v}'. Expected format: YYYY-MM-DDTHH:MM:SSZ") from exc

    @field_validator("units")
    @classmethod
    def validate_units(cls, v: Optional[str]) -> Optional[str]:
        """Validate physical units without silent interpretation of unknown units."""
        if v is None:
            return None
        allowed = {"hpa", "pa", "mm", "k", "c", "m/s", "knots", "kts", "degrees", "dimensionless", "%"}
        clean = v.strip().lower()
        if clean not in allowed and not any(u in clean for u in allowed):
            raise ValueError(f"Unknown or unsupported unit: '{v}'. Expected standard meteorological units: hPa, Pa, mm, K, knots, m/s.")
        return v


# Backward compatibility alias
LiveInferenceRequest = CanonicalForecastInput


class FeatureTelemetryItem(BaseModel):
    """Audited prospective feature telemetry item."""

    name: str = Field(..., description="Canonical meteorological feature identifier")
    value: float = Field(..., description="Computed numerical value")
    unit: str = Field(..., description="Standard physical measurement unit")
    source: str = Field(..., description="Telemetry source or derivation method")
    availability: Literal["AVAILABLE", "DEGRADED", "UNAVAILABLE"] = Field("AVAILABLE")
    validation_status: Literal["VALIDATED", "UNVALIDATED", "EXPERIMENTAL"] = Field("VALIDATED")


class DomainIdentification(BaseModel):
    """Meteorological spatial, temporal, and variable domain classification."""

    basin: str = Field(..., description="Identified oceanic/atmospheric basin")
    region: Optional[str] = Field(None, description="Regional identifier or meteorological zone")
    lead_classification: str = Field(..., description="SHORT_RANGE | MEDIUM_RANGE | EXTENDED_RANGE")
    is_validated_domain: bool = Field(..., description="Whether calibrated bust probability is validated for this domain")
    validation_notes: str = Field(..., description="Domain limitation or calibration explanation")


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
    """Structured response for Live Operational Inference & Reliability Analysis."""

    status: Literal["ok", "insufficient_data", "unsupported", "not_validated"] = Field(
        ..., description="Operational response status"
    )
    validation_status: Literal["VALID", "PARTIAL", "INSUFFICIENT", "NOT_SUPPORTED", "NOT_VALIDATED"] = Field(
        default="VALID", description="Input QC and validation status"
    )
    data_quality: Literal["DATA COMPLETE", "DATA DEGRADED", "DATA INSUFFICIENT"] = Field(
        ..., description="Data completeness and quality indicator"
    )
    quality_detail: str = Field(..., description="Explanation of data quality status")
    domain_identified: Optional[DomainIdentification] = Field(
        default=None, description="Domain spatial, temporal, and calibration classification"
    )
    reliability_state: Optional[Literal["STABLE", "WATCH", "VULNERABLE", "SEVERE", "DATA_INSUFFICIENT", "UNVALIDATED_DOMAIN"]] = Field(
        None, description="Operational forecast reliability category"
    )
    bust_probability: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Real calibrated forecast bust probability [0.0 - 1.0], or null if unvalidated domain"
    )
    probability_status: Literal["CALIBRATED", "NOT_VALIDATED", "INSUFFICIENT_EVIDENCE"] = Field(
        default="CALIBRATED", description="Status of bust probability calculation"
    )
    confidence_status: Literal["HIGH", "MODERATE", "LOW", "INSUFFICIENT"] = Field(
        default="HIGH", description="Confidence in assessment based on evidence completeness and OOD support"
    )
    bust_risk_percent: Optional[int] = Field(
        None, ge=0, le=100, description="Predicted prospective bust probability as percentage, or null if unvalidated"
    )
    reliability_score: Optional[int] = Field(
        None, ge=0, le=100, description="Calibrated operational reliability index (100 - risk), or null if unvalidated"
    )
    message: str = Field(..., description="Primary operational summary message")
    features_extracted: Optional[Dict[str, float]] = Field(
        None, description="Tier A/B strictly prospective predictor features"
    )
    feature_telemetry: Optional[List[FeatureTelemetryItem]] = Field(
        None, description="Audited feature telemetry records with units and validation status"
    )
    ensemble_evidence: Optional[Dict[str, Any]] = Field(
        None, description="Detailed ensemble dispersion and geometry evidence"
    )
    trajectory_evidence: Optional[Dict[str, Any]] = Field(
        None, description="Trajectory stability and revision persistence evidence"
    )
    environmental_evidence: Optional[Dict[str, Any]] = Field(
        None, description="Environmental conditioning evidence"
    )
    historical_memory_evidence: Optional[Dict[str, Any]] = Field(
        None, description="Analogous historical cyclone sequences from verified repository memory"
    )
    novelty_assessment: Optional[NoveltyAssessmentResponse] = Field(
        None, description="OOD representation, support status, and abstention intelligence"
    )
    multimodel_evidence: Optional[MultiModelEvidenceResponse] = Field(
        None, description="Cross-model forecast agreement, NWP consensus dispersion, and availability evidence"
    )
    model_status: str = Field(
        default="PRIMARY_MACHINE_BASELINE",
        description="Active production model scientific tier",
    )
    calibration_status: str = Field(
        default="CALIBRATED",
        description="CALIBRATED | NOT_VALIDATED | UNCALIBRATED_CANDIDATE",
    )
    verification_status: Literal["PENDING_VERIFICATION"] = Field(
        default="PENDING_VERIFICATION",
        description="Strict prospective status: ground truth is withheld/pending",
    )
    provenance: InferenceProvenance = Field(..., description="Complete audit provenance metadata")


# Backward compatibility alias
ForecastAnalysisResponse = LiveInferenceResponse

