"""Canonical Regional Assessment Schemas for ForecastGuard V2.

Strict adherence to AGENTS.md:
- No hardcoded scientific values
- No fabricated probabilities or fake live data
- Explicit representation of unavailable/insufficient evidence
- Preserves chronological train/validation/test separation and strict anti-leakage invariants
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class DominantEvidenceItem(BaseModel):
    """Single genuine computed physical/statistical evidence signal."""

    model_config = ConfigDict(extra="forbid")

    signal_id: str = Field(..., description="Unique identifier for the evidence factor e.g. 'ensemble_spread'")
    rank: str = Field(..., description="Rank string e.g. '01', '02'")
    title: str = Field(..., description="Human-readable title e.g. 'Ensemble Spread Dispersion'")
    description: str = Field(..., description="Factual description of the computed evidence")
    level: Literal["LOW", "MODERATE", "HIGH", "CRITICAL", "UNAVAILABLE"] = Field(
        ..., description="Severity level of this evidence signal"
    )
    metric_value: Optional[float] = Field(None, description="Scalar metric value if genuinely computed")
    metric_unit: Optional[str] = Field(None, description="Physical or statistical unit (e.g. 'Pa', 'mm', 'km')")


class RegionalProvenance(BaseModel):
    """Auditable data and model provenance for regional reliability assessments."""

    model_config = ConfigDict(extra="forbid")

    forecast_source: str = Field(..., description="Originating NWP system e.g. 'NCMRWF TIGGE'")
    forecast_cycle: str = Field(..., description="Initialization timestamp in ISO 8601 UTC")
    valid_time: str = Field(..., description="Forecast valid timestamp in ISO 8601 UTC")
    lead_time: str = Field(..., description="Lead time label e.g. 'D+1', 'D+2'")
    lead_hours: int = Field(..., description="Forecast lead in hours e.g. 24, 48")
    ensemble_member_count: int = Field(..., description="Number of ingested ensemble members")
    grid_cells_in_region: int = Field(..., description="Number of valid GRIB grid points within this region")
    variable: str = Field(..., description="Evaluated variable shortName e.g. 'msl', 'tp', '2t'")
    model_name: str = Field(..., description="Model identifier e.g. 'M1_SpreadOnly'")
    model_version: str = Field(..., description="Model version e.g. '1.0.0'")
    feature_version: str = Field(..., description="Feature schema version e.g. '1.0.0'")
    prediction_cutoff: str = Field(..., description="Strict prospective cutoff timestamp")
    data_quality_tier: Literal["DATA COMPLETE", "DATA DEGRADED", "DATA INSUFFICIENT"] = Field(
        ..., description="Quality control classification"
    )


class RegionalFeatureCatalogItem(BaseModel):
    """Explicit descriptor and value for a genuine computed regional feature."""

    model_config = ConfigDict(extra="forbid")

    feature_name: str = Field(..., description="Canonical name of feature e.g. 'regional_mean_spread'")
    definition: str = Field(..., description="Scientific definition of the feature calculation")
    units: str = Field(..., description="Physical or statistical units e.g. 'Pa', 'hours', 'dimensionless'")
    source: str = Field(..., description="Source telemetry or algorithm")
    is_validated: bool = Field(..., description="Whether feature calculation code is verified and audited")
    model_role: str = Field(..., description="Role in candidate or production reliability evaluation")
    current_value: Optional[float] = Field(None, description="Scalar numerical value if computed for this region")


class RegionalVerificationDetail(BaseModel):
    """Ground-truth forecast-versus-observation verification detail for a region."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(..., description="Forecast case identifier")
    storm_name: str = Field(..., description="Storm name")
    lead_hours: int = Field(..., description="Forecast lead time in hours")
    lead_label: str = Field(..., description="Lead time label e.g. 'D+1', 'D+2'")
    valid_time: str = Field(..., description="Verification valid timestamp in ISO 8601 UTC")
    region_id: str = Field(..., description="Analytical region identifier")
    region_name: str = Field(..., description="Analytical region name")
    forecast_lat: float = Field(..., description="Forecast vortex center latitude")
    forecast_lon: float = Field(..., description="Forecast vortex center longitude")
    forecast_pressure_hpa: float = Field(..., description="Forecast central pressure in hPa")
    observed_lat: float = Field(..., description="Observed center latitude (IMD Best Track)")
    observed_lon: float = Field(..., description="Observed center longitude (IMD Best Track)")
    observed_pressure_hpa: float = Field(..., description="Observed central pressure in hPa")
    track_error_km: float = Field(..., description="Observed forecast track displacement error in km")
    pressure_error_hpa: float = Field(..., description="Central pressure discrepancy in hPa")
    threshold_km: float = Field(..., description="Operational bust error threshold in km")
    is_bust: bool = Field(..., description="Whether track error exceeded operational bust threshold")
    severity: Literal["NORMAL", "MODERATE", "DEGRADED", "SEVERE"] = Field(
        ..., description="Observed verification severity"
    )
    provenance: str = Field(..., description="Ground truth authority and data provenance")
class EnsembleIntelligenceSummary(BaseModel):
    """Ensemble intelligence summary for structured evidence."""

    model_config = ConfigDict(extra="forbid")

    state: Literal["COHERENT", "SPREADING", "MULTI_BRANCH", "FRAGMENTED", "INSUFFICIENT_EVIDENCE"] = Field(
        ..., description="Categorical ensemble dispersion state"
    )
    state_description: str = Field(..., description="Explainable description of ensemble state")
    member_count: int = Field(..., description="Number of ingested ensemble members")
    mean_spread: Optional[float] = Field(None, description="Spatial spread across members")
    spread_unit: str = Field("km", description="Spread measurement unit (e.g. 'km' or 'Pa')")
    coherence_score: Optional[float] = Field(None, description="Non-dimensional consensus score in [0.0, 1.0]")
    anisotropy_ratio: Optional[float] = Field(None, description="Major-to-minor principal axis spread ratio")
    bimodality_coefficient: Optional[float] = Field(None, description="Sarle's bimodality coefficient along major axis")
    dominant_cluster_fraction: Optional[float] = Field(None, description="Fraction of members in dominant cluster")
    cluster_separation: Optional[float] = Field(None, description="Distance between cluster centroids")
    pairwise_disagreement: Optional[float] = Field(None, description="Mean pairwise member discrepancy")
    status: Literal["COMPLETE", "PARTIAL", "INSUFFICIENT"] = Field("COMPLETE", description="Ensemble telemetry status")


class TrajectoryIntelligenceSummary(BaseModel):
    """Forecast trajectory intelligence summary for structured evidence."""

    model_config = ConfigDict(extra="forbid")

    state: Literal["STABLE_PERSISTENT", "PROGRESSIVE_DRIFT", "OSCILLATING_JUMPY", "RAPID_REVISION", "INSUFFICIENT_EVIDENCE"] = Field(
        ..., description="Categorical trajectory stability state"
    )
    state_description: str = Field(..., description="Explainable description of trajectory state")
    has_prior_cycle: bool = Field(False, description="Whether consecutive prior cycle was available on disk")
    reference_cycle: Optional[str] = Field(None, description="Prior cycle initialization timestamp ISO")
    cycle_revision_distance_km: Optional[float] = Field(None, description="Cycle-to-cycle revision distance at identical valid time")
    cycle_spread_shift_km: Optional[float] = Field(None, description="Change in ensemble spread between cycles")
    revision_rate_kmh: Optional[float] = Field(None, description="Cycle displacement rate in km/h")
    trajectory_speed_kmh: Optional[float] = Field(None, description="Translation speed between leads in km/h")
    trajectory_curvature_deg: Optional[float] = Field(None, description="Heading change curvature in degrees")
    spread_growth_rate: Optional[float] = Field(None, description="Spread change rate across leads")
    trajectory_instability_km: Optional[float] = Field(None, description="Step distance jitter in km")
    status: Literal["COMPLETE", "PARTIAL", "UNAVAILABLE", "INSUFFICIENT"] = Field("COMPLETE", description="Trajectory telemetry status")


class EnvironmentalIntelligenceSummary(BaseModel):
    """Environmental conditioning intelligence summary for structured evidence."""

    model_config = ConfigDict(extra="forbid")

    state: Literal[
        "SYMMETRIC_DEEP_PRESSURE_STRUCTURE",
        "MARGINAL_PRESSURE_STRUCTURE",
        "ASYMMETRIC_WEAK_PRESSURE_STRUCTURE",
        "INSUFFICIENT_EVIDENCE",
    ] = Field(..., description="Categorical environmental state derived strictly from surface MSLP pressure structure")
    state_description: str = Field(..., description="Explainable description of environmental pressure structure")
    pressure_depth_hpa: Optional[float] = Field(None, description="Environmental pressure depth in hPa (annulus vs center)")
    pressure_gradient_hpa_per_100km: Optional[float] = Field(None, description="Radial environmental pressure gradient (hPa / 100 km)")
    gradient_asymmetry_hpa_per_100km: Optional[float] = Field(None, description="Annulus directional pressure asymmetry (hPa / 100 km)")
    gradient_trend_hpa_per_100km: Optional[float] = Field(None, description="Change in radial gradient across lead steps (hPa / 100 km)")
    core_pressure_hpa: Optional[float] = Field(None, description="Central minimum MSLP in hPa")
    peripheral_pressure_hpa: Optional[float] = Field(None, description="Mean peripheral pressure in hPa across outer annulus [300, 600] km")
    upper_air_shear_status: Literal["AVAILABLE", "UNAVAILABLE", "INSUFFICIENT_EVIDENCE"] = Field(
        "UNAVAILABLE", description="Availability of 850-200 hPa deep layer shear (UNAVAILABLE in local archive)"
    )
    mid_level_humidity_status: Literal["AVAILABLE", "UNAVAILABLE", "INSUFFICIENT_EVIDENCE"] = Field(
        "UNAVAILABLE", description="Availability of 700-500 hPa relative humidity (UNAVAILABLE in local archive)"
    )
    sst_status: Literal["AVAILABLE", "UNAVAILABLE", "INSUFFICIENT_EVIDENCE"] = Field(
        "UNAVAILABLE", description="Availability of sea surface temperature (UNAVAILABLE in local archive)"
    )
    validation_status: Literal["VALIDATED", "EXPERIMENTAL", "INSUFFICIENT_EVIDENCE"] = Field(
        "EXPERIMENTAL", description="Scientific validation status (EXPERIMENTAL; A0 remains operational baseline per Rule 11)"
    )
    provenance: str = Field(..., description="Provenance of environmental field")
    scientific_provenance_note: str = Field(
        "Derived from NCMRWF NEPS ensemble MSLP pressure-gradient geometry. NOT a direct measurement of vertical wind shear, upper-air wind, or humidity.",
        description="Explicit provenance note clarifying that this diagnostic is derived from surface MSLP and is NOT a direct measurement of vertical wind shear.",
    )
    status: Literal["COMPLETE", "PARTIAL", "UNAVAILABLE", "INSUFFICIENT"] = Field(
        "COMPLETE", description="Telemetry status"
    )


class TopAnalogueSummary(BaseModel):
    """Top-ranked historical forecast state analogue."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(..., description="Analogue unique case ID")
    storm_name: str = Field(..., description="Analogue cyclone name")
    cycle_label: str = Field(..., description="Initialization cycle")
    forecast_lead_hours: int = Field(..., description="Forecast lead hours")
    similarity_percent: int = Field(..., ge=0, le=100, description="Similarity percentage")
    standardized_distance: float = Field(..., ge=0.0, description="Standardized distance")
    verified_status: str = Field(..., description="Ground truth verification status")
    track_error_km: Optional[float] = Field(None, description="Verified track error in km")
    threshold_km: Optional[float] = Field(None, description="Tolerance threshold in km")
    is_bust: Optional[bool] = Field(None, description="Whether analogue experienced forecast bust")
    spread_regime: Optional[str] = Field(None, description="Empirical spread regime")
    failure_summary: Optional[str] = Field(None, description="Observed analogue outcome summary")


class HistoricalMemorySummary(BaseModel):
    """Historical forecast memory intelligence summary for structured evidence."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["AVAILABLE", "INSUFFICIENT_EVIDENCE", "UNAVAILABLE"] = Field(
        "AVAILABLE", description="Historical memory query status"
    )
    total_reference_cases: int = Field(..., description="Total verified historical records in memory")
    matched_count: int = Field(..., description="Number of candidate analogues evaluated")
    top_analogue: Optional[TopAnalogueSummary] = Field(None, description="Highest similarity analogue match")
    analogue_summary_text: str = Field(..., description="Contextual summary of historical matches")
    disclaimer: str = Field(
        "Historical similarity provides contextual evidence and does NOT guarantee an identical operational outcome.",
        description="Scientific non-causal disclaimer",
    )


class RepresentationSupportSummary(BaseModel):
    """Novelty and reference support intelligence summary for structured evidence."""

    model_config = ConfigDict(extra="forbid")

    representation_state: Literal["WELL_REPRESENTED", "LOW_SUPPORT", "NOVEL_STATE", "INSUFFICIENT_EVIDENCE"] = Field(
        ..., description="Deterministic representation state relative to historical reference population"
    )
    support_score: int = Field(..., ge=0, le=100, description="Historical representation index (0-100)")
    novelty_score: float = Field(..., ge=0.0, le=1.0, description="Empirical novelty percentile ranking (0.0-1.0)")
    distance_to_reference: Optional[float] = Field(None, description="Standardized distance to k=3 nearest reference neighbours")
    nearest_reference_distance: Optional[float] = Field(None, description="Standardized distance to closest reference sample")
    reference_population_size: int = Field(..., description="Historical reference population count (n=77)")
    abstention_recommended: bool = Field(..., description="Whether system advises abstaining from high-confidence reliance")
    abstention_reason: Optional[str] = Field(None, description="Rationale when abstention is recommended")
    status_message: str = Field(..., description="Decision-support summary message")
    decision_rule: str = Field(
        "Novelty indicates statistical distance from historical reference population; novelty != forecast failure.",
        description="Scientific non-causal firewall rule",
    )


class MultiModelEvidenceSummary(BaseModel):
    """Multi-model NWP cross-center agreement intelligence summary for structured evidence."""

    model_config = ConfigDict(extra="forbid")

    state: Literal["INSUFFICIENT_EVIDENCE", "AGREEMENT", "MODERATE_DISAGREEMENT", "HIGH_DISAGREEMENT"] = Field(
        "INSUFFICIENT_EVIDENCE", description="Cross-system agreement state"
    )
    models_evaluated: List[str] = Field(
        default_factory=lambda: ["NCMRWF_NEPS (origin=dems)"],
        description="List of NWP forecast systems evaluated"
    )
    available_model_count: int = Field(1, description="Number of operational models with valid data")
    independent_nwp_centers_count: int = Field(1, description="Number of distinct independent NWP operational centers")
    notice: str = Field(
        "NCMRWF NEPS (origin=dems) is the sole operational NWP system in the validated local archive. Secondary global models (ECMWF, UKMO, NCEP) have zero historical overlap. Multi-model consensus is unavailable.",
        description="Factual audit disclosure of archive availability"
    )
    is_abstention_recommended: bool = Field(False, description="Whether abstention is advised due to model disagreement")
    validation_status: Literal["INSUFFICIENT_EVIDENCE", "EXPERIMENTAL"] = Field(
        "INSUFFICIENT_EVIDENCE", description="Validation tier of cross-model consensus"
    )


class StructuredEvidenceObject(BaseModel):
    """Canonical structured evidence object backing regional reliability assessments."""

    model_config = ConfigDict(extra="forbid")

    ensemble: EnsembleIntelligenceSummary
    trajectory: TrajectoryIntelligenceSummary
    environmental: Optional[EnvironmentalIntelligenceSummary] = Field(
        None, description="Environmental conditioning intelligence summary"
    )
    historical_memory: Optional[HistoricalMemorySummary] = Field(
        None, description="Historical forecast memory analogue summary"
    )
    representation: Optional[RepresentationSupportSummary] = Field(
        None, description="OOD representation and support summary"
    )
    multimodel: Optional[MultiModelEvidenceSummary] = Field(
        None, description="Multi-model NWP evidence summary"
    )
    trend: Literal["increasing", "decreasing", "stable", "unavailable"]
    why_now: str = Field(..., description="Deterministic attribution explaining current reliability health")
    what_changed: str = Field(..., description="Deterministic delta narrative comparing to prior cycle/lead")
    evidence_status: Literal["COMPLETE", "PARTIAL", "UNAVAILABLE", "INSUFFICIENT"] = Field(
        ..., description="Overall status of evidence"
    )
    evidence_strength: Literal["HIGH", "MODERATE", "LOW", "INSUFFICIENT_EVIDENCE"] = Field(
        ..., description="Evidence confidence strength"
    )
    source_provenance: str = Field(..., description="Auditable data and model provenance")


class CanonicalRegionalAssessment(BaseModel):
    """Canonical Regional Reliability Assessment Object.

    Standardized contract consumed identically by backend services, REST API,
    and frontend Command Center.
    """

    model_config = ConfigDict(extra="forbid")

    region_id: str = Field(..., description="Predefined region ID e.g. 'MAR_BOB', 'IND_ENE', 'IND_CEN'")
    region_name: str = Field(..., description="Predefined analytical region name e.g. 'Bay of Bengal Basin'")
    forecast_cycle: str = Field(..., description="Forecast initialization cycle in ISO 8601 UTC")
    valid_time: str = Field(..., description="Valid verification time in ISO 8601 UTC")
    lead_time: str = Field(..., description="Lead time formatted string e.g. 'D+1'")
    lead_hours: int = Field(..., ge=0, le=240, description="Lead time in hours e.g. 24")
    variable: str = Field(..., description="Variable evaluated e.g. 'Mean Sea Level Pressure (msl)'")
    
    # Model Semantics & Calibration Transparency (Priorities 1 & 4)
    model_status: Literal["VALIDATED", "CANDIDATE", "INSUFFICIENT_EVIDENCE"] = Field(
        ...,
        description="Scientific status of model for this task. V2 regional output is CANDIDATE pending independent calibration.",
    )
    calibration_status: Literal["CALIBRATED", "UNCALIBRATED_CANDIDATE", "NOT_AVAILABLE"] = Field(
        ...,
        description="Calibration state. Regional candidate output is UNCALIBRATED_CANDIDATE (zero fabricated calibration).",
    )
    raw_model_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Raw prospective vulnerability score in [0.0, 1.0] before empirical regional calibration.",
    )
    calibrated_bust_probability: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Calibrated probability of bust in [0.0, 1.0]. Strictly None until regional calibration population is established.",
    )

    # Operational outputs consumed by Command Center
    bust_probability: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Raw candidate vulnerability index in [0.0, 1.0]. None if unsupported/outside domain.",
    )
    reliability_score: Optional[int] = Field(
        None,
        ge=0,
        le=100,
        description="Operational reliability index in [0, 100] derived from candidate score. None if unsupported.",
    )
    reliability_state: Literal[
        "STABLE", "WATCH", "DEGRADING", "HIGH_RISK", "INSUFFICIENT_EVIDENCE"
    ] = Field(..., description="Categorical operational reliability status")
    
    trend: Literal["increasing", "decreasing", "stable", "unavailable"] = Field(
        ..., description="Qualitative reliability vulnerability trend compared to previous lead"
    )
    trend_description: Optional[str] = Field(
        None, description="Factual description of the computed trend"
    )

    assessment_confidence: Literal["HIGH", "MODERATE", "LOW", "INSUFFICIENT_EVIDENCE"] = Field(
        ..., description="Confidence in assessment based on ensemble coverage and data completeness"
    )
    evidence_status: Literal["COMPLETE", "PARTIAL", "UNAVAILABLE", "INSUFFICIENT"] = Field(
        ..., description="Status of evidence underlying the evaluation"
    )
    
    dominant_evidence: List[DominantEvidenceItem] = Field(
        default_factory=list,
        description="List of genuine computed physical signals. Empty if unavailable.",
    )
    
    regional_features: List[RegionalFeatureCatalogItem] = Field(
        default_factory=list,
        description="Explicit breakdown of all genuine computed regional features with definitions, units, and model roles.",
    )

    provenance: RegionalProvenance = Field(
        ..., description="Full traceable provenance record"
    )
    
    verification_status: Literal["VERIFIED", "PENDING_VERIFICATION", "UNVERIFIED"] = Field(
        ..., description="Verification status against ground truth observation"
    )
    verification_detail: Optional[RegionalVerificationDetail] = Field(
        None,
        description="Audited ground-truth forecast-versus-observation verification detail if verified",
    )
    
    domain_coverage_percent: float = Field(
        ..., ge=0.0, le=100.0, description="Percentage of regional area covered by forecast grid"
    )
    status_message: str = Field(
        ..., description="Operational summary message explaining reliability state or data limitation"
    )
    ensemble_state: Optional[
        Literal["COHERENT", "SPREADING", "MULTI_BRANCH", "FRAGMENTED", "INSUFFICIENT_EVIDENCE"]
    ] = Field(None, description="Categorical ensemble dispersion state")
    trajectory_state: Optional[
        Literal["STABLE_PERSISTENT", "PROGRESSIVE_DRIFT", "OSCILLATING_JUMPY", "RAPID_REVISION", "INSUFFICIENT_EVIDENCE"]
    ] = Field(None, description="Categorical trajectory stability state")
    environmental_state: Optional[
        Literal[
            "SYMMETRIC_DEEP_PRESSURE_STRUCTURE",
            "MARGINAL_PRESSURE_STRUCTURE",
            "ASYMMETRIC_WEAK_PRESSURE_STRUCTURE",
            "INSUFFICIENT_EVIDENCE",
        ]
    ] = Field(None, description="Categorical environmental state derived strictly from surface MSLP pressure structure")
    structured_evidence: Optional[StructuredEvidenceObject] = Field(
        None, description="Deterministic structured evidence object answering Why and What Changed"
    )
    historical_memory: Optional[HistoricalMemorySummary] = Field(
        None, description="Historical forecast memory analogue summary"
    )
    representation: Optional[RepresentationSupportSummary] = Field(
        None, description="OOD representation and support summary"
    )
    multimodel: Optional[MultiModelEvidenceSummary] = Field(
        None, description="Multi-model NWP evidence summary"
    )



class RegionalCaseSummary(BaseModel):
    """Summary of a supported forecast case available for regional assessment."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(..., description="Unique case ID e.g. 'MIDHILI_00Z'")
    storm_name: Optional[str] = Field(None, description="Associated tropical cyclone name if applicable")
    basin: str = Field(..., description="Macro ocean basin e.g. 'Bay of Bengal', 'Arabian Sea', 'Pan-India'")
    forecast_cycle: str = Field(..., description="Forecast initialization cycle in ISO 8601 UTC")
    available_leads: List[str] = Field(..., description="List of validated available leads e.g. ['D+1', 'D+2']")
    unsupported_leads: List[str] = Field(
        ..., description="List of unsupported leads in D+1..D+10 e.g. ['D+3', ..., 'D+10']"
    )
    available_variables: List[str] = Field(..., description="Available atmospheric variables e.g. ['msl']")
    supported_regions: List[str] = Field(..., description="Region IDs with real grid coverage in this case")
    unsupported_regions: List[str] = Field(..., description="Region IDs outside domain coverage")
    description: str = Field(..., description="Operational narrative of this forecast case")


class RegionalAssessmentResponse(BaseModel):
    """Top-level response envelope for the Regional Reliability API."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    forecast_cycle: str
    valid_time: str
    lead_time: str
    lead_hours: int
    variable: str
    available_leads: List[str]
    unsupported_leads: List[str]
    is_horizon_supported: bool
    regions: List[CanonicalRegionalAssessment]
    supported_regions_count: int
    unsupported_regions_count: int
    data_quality: str
    system_overview: str


class RegionalVerificationResponse(BaseModel):
    """Top-level response envelope for Forecast-vs-Observation verification."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    storm_name: str
    forecast_cycle: str
    records: List[RegionalVerificationDetail]
    verified_leads_count: int
    bust_count: int
    data_source: str


class StateTransitionEvent(BaseModel):
    """Deterministic reliability state transition event in temporal trajectory."""

    model_config = ConfigDict(extra="forbid")

    transition_id: str = Field(..., description="Unique event identifier e.g. 'MIDHILI_STABLE_TO_WATCH_18H'")
    lead_hours: int = Field(..., description="Lead time in hours at which transition was detected")
    valid_time: str = Field(..., description="Valid timestamp in ISO 8601 UTC")
    from_state: str = Field(..., description="Prior reliability state")
    to_state: str = Field(..., description="New reliability state")
    probability_delta: float = Field(..., description="Numerical probability delta across transition")
    severity_direction: Literal["DEGRADING", "IMPROVING", "STABLE"] = Field(
        ..., description="Direction of reliability health shift"
    )
    trigger_reason: str = Field(..., description="Physical or statistical reason for state transition")


class FirstActionableSignal(BaseModel):
    """Earliest actionable alert signal with rigorous warning lead duration."""

    model_config = ConfigDict(extra="forbid")

    alert_triggered: bool = Field(..., description="Whether alert criterion was crossed")
    signal_cutoff_iso: Optional[str] = Field(None, description="Forecast cycle or cutoff time when alert fired")
    signal_lead_hours: Optional[int] = Field(None, description="Forecast lead duration at alert point")
    trigger_state: Optional[str] = Field(None, description="Reliability state that triggered alert")
    trigger_probability: Optional[float] = Field(None, description="Calibrated bust probability at alert point")
    downstream_failure_time_iso: Optional[str] = Field(None, description="Valid time of first verified downstream failure")
    downstream_failure_lead_hours: Optional[int] = Field(None, description="Lead duration of first verified bust")
    warning_lead_hours: Optional[float] = Field(
        None, description="Exact warning lead time in hours (failure_time minus alert_time)"
    )
    warning_lead_label: Optional[str] = Field(None, description="Human-readable warning lead e.g. '24.0h Warning Lead'")
    narrative: str = Field(..., description="Auditable narrative explaining signal detection and advance lead")


class KnowledgeBoundaryStatus(BaseModel):
    """Strict temporal boundary separating available knowledge from locked future."""

    model_config = ConfigDict(extra="forbid")

    cutoff_iso: str = Field(..., description="Prediction cutoff timestamp in ISO 8601 UTC")
    elapsed_hours: int = Field(..., description="Hours elapsed since cycle initialization")
    available_observations_count: int = Field(..., description="Number of unlocked verified observations")
    future_observations_locked_count: int = Field(..., description="Number of strictly locked future observations")
    future_information_locked: bool = Field(..., description="True if any future observations remain locked")
    unlocked_valid_times: List[str] = Field(default_factory=list, description="Unlocked observation valid timestamps")
    locked_valid_times: List[str] = Field(default_factory=list, description="Withheld future observation timestamps")
    boundary_statement: str = Field(..., description="Explicit human-readable boundary status statement")


class CycleComparison(BaseModel):
    """Truthful comparison across consecutive forecast cycles ('What Changed?')."""

    model_config = ConfigDict(extra="forbid")

    prior_cycle_iso: Optional[str] = Field(None, description="Previous forecast cycle initialization time")
    current_cycle_iso: str = Field(..., description="Current forecast cycle initialization time")
    region_id: str = Field(..., description="Evaluated analytical region")
    target_lead_hours: int = Field(..., description="Target lead time for cycle comparison")
    risk_change: Optional[float] = Field(None, description="Change in risk probability/score")
    risk_trend: Literal["increasing", "decreasing", "stable", "unavailable"] = Field(
        ..., description="Qualitative direction of risk change across cycles"
    )
    state_change: Optional[str] = Field(None, description="State shift e.g. 'STABLE -> DEGRADING'")
    mean_spread_pa_change: Optional[float] = Field(None, description="Change in regional mean spread (Pa)")
    peak_spread_pa_change: Optional[float] = Field(None, description="Change in peak localized spread anomaly (Pa)")
    summary_narrative: str = Field(..., description="Auditable narrative describing what changed across cycles")


class RegionalTimelineStep(BaseModel):
    """Discrete synoptic time step in a regional reliability evolution series."""

    model_config = ConfigDict(extra="forbid")

    lead_hours: int = Field(..., description="Forecast lead duration in hours")
    lead_label: str = Field(..., description="Formatted lead label e.g. '+6h', 'D+1'")
    valid_time: str = Field(..., description="Valid verification timestamp in ISO 8601 UTC")
    raw_model_score: Optional[float] = Field(None, description="Candidate raw dispersion score")
    calibrated_bust_probability: Optional[float] = Field(None, description="Calibrated bust probability")
    reliability_score: Optional[int] = Field(None, description="Reliability index in [0, 100]")
    reliability_state: str = Field(..., description="Categorical reliability state")
    trend: str = Field(..., description="Trajectory trend from previous step")
    model_status: str = Field(..., description="Model status e.g. 'VALIDATED' or 'CANDIDATE'")
    calibration_status: str = Field(..., description="Calibration status e.g. 'CALIBRATED'")
    verification_status: str = Field(..., description="'VERIFIED' if observed, 'PENDING_VERIFICATION' if prospective")
    verification_detail: Optional[RegionalVerificationDetail] = Field(
        None, description="Matched ground truth detail if unlocked and verified"
    )
    is_alert_active: bool = Field(..., description="True if alert criteria are met at this step")
    ensemble_state: Optional[str] = Field(None, description="Categorical ensemble state at this step")
    trajectory_state: Optional[str] = Field(None, description="Categorical trajectory state at this step")
    environmental_state: Optional[str] = Field(None, description="Categorical environmental state at this step")
    historical_analogue_id: Optional[str] = Field(None, description="ID of closest historical analogue")
    historical_similarity_percent: Optional[int] = Field(None, description="Similarity percentage of closest analogue")
    representation_state: Optional[str] = Field(None, description="Representation state at this step")
    support_score: Optional[int] = Field(None, description="Representation support score (0-100)")
    multi_model_state: Optional[str] = Field(None, description="Multi-model agreement state at this step")


class RegionalTimelineResponse(BaseModel):
    """Full temporal reliability evolution series for a region and case."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    region_id: str
    region_name: str
    forecast_cycle: str
    steps: List[RegionalTimelineStep]
    state_transitions: List[StateTransitionEvent]
    first_actionable_signal: Optional[FirstActionableSignal]
    cycle_comparison: Optional[CycleComparison]


class ReplayStepDetail(BaseModel):
    """Complete snapshot of application state at a specific replay cutoff."""

    model_config = ConfigDict(extra="forbid")

    step_index: int = Field(..., description="Zero-based replay step index")
    cutoff_time: str = Field(..., description="Cutoff timestamp in ISO 8601 UTC")
    elapsed_hours: int = Field(..., description="Hours elapsed from initialization")
    label: str = Field(..., description="Step label e.g. 'T+0h (Cycle Init)'")
    lead_hours: int = Field(..., description="Active forecast lead evaluated at this step")
    lead_label: str = Field(..., description="Active lead label e.g. '+18h', 'D+1'")
    knowledge_boundary: KnowledgeBoundaryStatus = Field(..., description="Strict past vs future boundary")
    focused_region_assessment: CanonicalRegionalAssessment = Field(..., description="Assessment for focused region")
    all_regional_assessments: List[CanonicalRegionalAssessment] = Field(
        ..., description="Assessments for all predefined regions"
    )
    unlocked_verifications: List[RegionalVerificationDetail] = Field(
        ..., description="Ground-truth records available at this cutoff"
    )
    first_actionable_signal: Optional[FirstActionableSignal] = Field(
        None, description="Earliest actionable signal if detected by this cutoff"
    )
    active_event: Optional[str] = Field(None, description="Event notification banner if triggered at this step")


class ReplayCaseResponse(BaseModel):
    """Top-level container for a complete historical replay session."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    storm_name: str
    basin: str
    forecast_cycle: str
    total_steps: int
    available_cutoffs: List[str]
    steps: List[ReplayStepDetail]
    first_actionable_signal: Optional[FirstActionableSignal]
    overall_verification_summary: str
