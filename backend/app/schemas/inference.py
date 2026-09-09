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
    confidence_breakdown: Optional["ConfidenceBreakdown"] = Field(
        None, description="Structured breakdown of evidence confidence across 5 defensible pillars"
    )
    structured_explanation: Optional["StructuredExplanation"] = Field(
        None, description="Deterministic structured explanations (WHY, WHAT CHANGED, WHY NOW)"
    )
    support_index: Optional[int] = Field(
        None, ge=0, le=100, description="Empirical support index [0-100] reflecting evidence completeness; NOT a probability"
    )
    provenance: InferenceProvenance = Field(..., description="Complete audit provenance metadata")


# Backward compatibility alias
ForecastAnalysisResponse = LiveInferenceResponse


# =========================================================================
# Medium-Range Reliability Timeline & Confidence System (Prompt 3/4)
# =========================================================================

class ConfidenceComponent(BaseModel):
    """Component of the structured evidence-confidence assessment."""

    model_config = ConfigDict(extra="forbid")

    status: str = Field(
        ...,
        description="Pillar status (e.g. COMPLETE, VALIDATED_DOMAIN, WELL_REPRESENTED, STRONG_CONSENSUS, VERIFIED_SOURCE)",
    )
    reason: str = Field(..., description="Empirical, non-causal rationale for this status")
    source: str = Field(..., description="Telemetry channel or evidence source")


class ConfidenceBreakdown(BaseModel):
    """Structured breakdown of evidence confidence across 5 defensible pillars."""

    model_config = ConfigDict(extra="forbid")

    data_coverage: ConfidenceComponent = Field(..., description="Completeness of ensemble members and fields")
    model_validation: ConfidenceComponent = Field(..., description="Regional and horizon calibration domain status")
    historical_representation: ConfidenceComponent = Field(..., description="Novelty distance to historical reference population")
    ensemble_support: ConfidenceComponent = Field(..., description="Ensemble dispersion and agreement level")
    provenance: ConfidenceComponent = Field(..., description="NWP origin and data lineage verification")


class StructuredExplanation(BaseModel):
    """Deterministic, non-causal structured explanations for operational decision support."""

    model_config = ConfigDict(extra="forbid")

    why: str = Field(..., description="Strongest currently available evidence supporting the assessment")
    what_changed: Optional[str] = Field(None, description="Meaningful sequential difference from prior forecast lead")
    why_now: str = Field(..., description="Why the system is flagging this state at this lead/cycle")


class TimelineLeadPoint(BaseModel):
    """Single lead-time point along the D+1 -> D+10 reliability timeline."""

    model_config = ConfigDict(extra="forbid")

    lead_name: str = Field(..., description="Lead day label e.g. D+1, D+2, ..., D+10")
    lead_hours: int = Field(..., ge=0, le=240, description="Lead time in hours")
    valid_time: str = Field(..., description="Forecast valid time in ISO 8601 UTC")
    reliability_state: Optional[
        Literal["STABLE", "WATCH", "VULNERABLE", "SEVERE", "DATA_INSUFFICIENT", "UNVALIDATED_DOMAIN"]
    ] = Field(None, description="Operational forecast reliability category")
    bust_probability: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Calibrated bust probability [0.0 - 1.0], or null if unvalidated"
    )
    probability_status: Literal["CALIBRATED", "NOT_VALIDATED", "INSUFFICIENT_EVIDENCE", "UNAVAILABLE"] = Field(
        ..., description="Status of bust probability calculation"
    )
    assessment_confidence: Literal["HIGH", "MODERATE", "LOW", "INSUFFICIENT"] = Field(
        ..., description="Confidence in assessment based on evidence completeness and validation support"
    )
    data_quality: Literal["DATA COMPLETE", "DATA DEGRADED", "DATA INSUFFICIENT"] = Field(
        ..., description="Data completeness and quality indicator"
    )
    evidence_strength: Literal["STRONG", "MODERATE", "WEAK", "INSUFFICIENT"] = Field(
        ..., description="Strength of available evidence"
    )
    validation_status: Literal["VALID", "PARTIAL", "NOT_VALIDATED", "INSUFFICIENT"] = Field(
        ..., description="Domain validation status for this lead"
    )
    support_index: Optional[int] = Field(
        None, ge=0, le=100, description="Empirical support index [0-100] reflecting evidence completeness; NOT a probability"
    )
    confidence_breakdown: ConfidenceBreakdown = Field(..., description="5-pillar structured confidence assessment")
    structured_explanation: StructuredExplanation = Field(..., description="Deterministic WHY / WHAT CHANGED / WHY NOW")
    evidence_summary: str = Field(..., description="Concise summary of available evidence")
    features_extracted: Optional[Dict[str, float]] = Field(None, description="Prospective feature values")
    feature_telemetry: Optional[List[FeatureTelemetryItem]] = Field(None, description="Audited feature telemetry")
    novelty_assessment: Optional[NoveltyAssessmentResponse] = Field(None, description="OOD representation and support")
    multimodel_evidence: Optional[MultiModelEvidenceResponse] = Field(None, description="Multi-model agreement evidence")


class RiskEvolution(BaseModel):
    """Evaluation of how reliability evolves across sequential forecast leads."""

    model_config = ConfigDict(extra="forbid")

    trajectory_state: Literal["IMPROVING", "STABLE", "DEGRADING", "MIXED", "INSUFFICIENT_EVIDENCE"] = Field(
        ..., description="Empirical trajectory trend across available sequential leads"
    )
    summary: str = Field(..., description="Non-causal explanation of risk evolution")
    evidence_basis: List[str] = Field(..., description="List of specific features and metrics underpinning the trend")
    lead_transitions: List[Dict[str, Any]] = Field(
        default_factory=list, description="Step-by-step transition delta records between leads"
    )


class MultiLeadForecastInput(BaseModel):
    """Canonical multi-lead forecast payload for medium-range timeline evaluation."""

    model_config = ConfigDict(extra="forbid")

    forecast_source: str = Field(
        default="NCMRWF TIGGE", description="Originating NWP ensemble prediction system."
    )
    model: Optional[str] = Field(
        default=None, description="NWP model or center identifier e.g. NCMRWF_NEPS, ECMWF_IFS."
    )
    forecast_cycle: str = Field(
        ..., description="Forecast initialization cycle in ISO 8601 UTC format."
    )
    variable: str = Field(
        default="Mean Sea Level Pressure (msl)", description="Atmospheric variable used for analysis."
    )
    units: Optional[str] = Field(default=None, description="Explicit physical units.")
    region: Optional[str] = Field(default=None, description="Target region or basin identifier.")
    leads: List[CanonicalForecastInput] = Field(
        ..., min_length=1, description="Chronological list of lead-step forecasts (D+1 through D+10)"
    )


class MediumRangeForecastAnalysisResponse(BaseModel):
    """Comprehensive Medium-Range Reliability Timeline and Confidence Assessment."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok", "partial_data", "insufficient_data", "not_validated"] = Field(
        ..., description="Overall operational response status"
    )
    forecast_source: str = Field(..., description="Originating NWP system")
    forecast_cycle: str = Field(..., description="Forecast cycle initialization in UTC")
    overall_assessment: Dict[str, Any] = Field(..., description="High-level operational overview across all horizons")
    timeline: List[TimelineLeadPoint] = Field(..., description="Chronological D+1 -> D+10 reliability timeline")
    risk_evolution: RiskEvolution = Field(..., description="Multi-lead trajectory evolution analysis")
    confidence: ConfidenceBreakdown = Field(..., description="Overall 5-pillar confidence breakdown")
    domain_identified: DomainIdentification = Field(..., description="Domain classification for this forecast")
    evidence_summary: Dict[str, Any] = Field(..., description="Synthesized evidence across available leads")
    provenance: InferenceProvenance = Field(..., description="Complete audit provenance metadata")


