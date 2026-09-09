"""Schemas for Historical Forecast Memory, Analogue Search, and Failure Fingerprints.

SIH26079: AI-Based Forecast Bust Detection for Medium-Range Weather Forecasts.
Strictly respects information boundaries at forecast cutoff T.
Forbids future observations, contemporaneous errors, and bust labels in query vectors.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ForecastCenterCoords(BaseModel):
    """Ensemble mean vortex center coordinates and central pressure."""

    latitude: float = Field(..., ge=-90.0, le=90.0, description="Vortex latitude in degrees North.")
    longitude: float = Field(..., ge=-180.0, le=360.0, description="Vortex longitude in degrees East.")
    pressure_hpa: Optional[float] = Field(None, ge=850.0, le=1050.0, description="Central MSLP in hPa.")


class ObservedCenterCoords(BaseModel):
    """Official IMD/RSMC best-track center coordinates and central pressure."""

    latitude: float = Field(..., ge=-90.0, le=90.0, description="Observed center latitude.")
    longitude: float = Field(..., ge=-180.0, le=360.0, description="Observed center longitude.")
    pressure_hpa: Optional[float] = Field(None, ge=850.0, le=1050.0, description="Observed MSLP in hPa.")


class ForecastStateQuery(BaseModel):
    """Query representation of a forecast state available at cutoff T.

    Strict Anti-Leakage Invariant:
    Accepts ONLY features available at forecast issuance.
    ConfigDict extra='forbid' strictly rejects any ground-truth fields
    (e.g., observed coordinates, track errors, bust labels, thresholds).
    """

    model_config = ConfigDict(extra="forbid")

    lead_hours: int = Field(..., ge=6, le=72, description="Forecast lead time in hours (6, 12, ..., 48).")
    ensemble_spread_km: float = Field(..., ge=0.0, le=1500.0, description="Scalar ensemble track spread in km.")
    major_axis_spread_km: Optional[float] = Field(None, ge=0.0, le=2000.0, description="Spread along major principal axis (km).")
    anisotropy_ratio: Optional[float] = Field(None, ge=0.5, le=20.0, description="Ratio of major to minor dispersion axes.")
    bimodality_coefficient: Optional[float] = Field(None, ge=0.0, le=1.0, description="Sarle's bimodality coefficient.")
    dominant_cluster_fraction: Optional[float] = Field(None, ge=0.0, le=1.0, description="Fraction in primary spatial cluster.")
    cluster_separation_km: Optional[float] = Field(None, ge=0.0, le=2000.0, description="Separation between multi-modal clusters (km).")
    spread_growth_km: Optional[float] = Field(None, ge=-500.0, le=500.0, description="Rate of spread change from prior lead (km).")
    trajectory_speed_kmh: Optional[float] = Field(None, ge=0.0, le=150.0, description="Vortex translation speed in km/h.")
    trajectory_curvature_deg: Optional[float] = Field(None, ge=0.0, le=360.0, description="Turning angle of forecast trajectory in degrees.")
    trajectory_instability_km: Optional[float] = Field(None, ge=0.0, le=1000.0, description="Trajectory wobble / displacement in km.")
    cycle_revision_distance_km: Optional[float] = Field(None, ge=0.0, le=2000.0, description="Displacement vs prior forecast cycle (km).")
    basin: Optional[str] = Field(None, description="Ocean basin (e.g. 'Bay of Bengal', 'Arabian Sea').")
    forecast_center: Optional[ForecastCenterCoords] = Field(None, description="Optional forecast vortex center.")


class FeatureDimensionComparison(BaseModel):
    """Detailed comparison along a single feature dimension between query and analogue."""

    dimension: str = Field(..., description="Feature name.")
    query_value: float = Field(..., description="Value in query state.")
    analogue_value: float = Field(..., description="Value in matched historical case.")
    reference_mean: float = Field(..., description="Historical reference archive mean.")
    reference_std: float = Field(..., description="Historical reference archive standard deviation.")
    delta_z_score: float = Field(..., description="Standardized difference (query_z - analogue_z).")
    feature_weight: float = Field(..., description="Weight applied in distance metric.")
    dimension_distance: float = Field(..., description="Weighted squared distance contribution.")


class VerifiedHistoricalOutcome(BaseModel):
    """Ground-truth verification outcome of a historical forecast case.

    Anti-Leakage Rule: Attached ONLY AFTER analogue retrieval.
    Never used in constructing candidate similarity representations.
    """

    verification_status: Literal["VERIFIED", "PENDING_VERIFICATION", "INSUFFICIENT_EVIDENCE"] = Field(
        ...,
        description="Explicit verification status tier.",
    )
    track_error_km: Optional[float] = Field(None, description="Continuous great-circle track error in km.")
    threshold_km: Optional[float] = Field(None, description="Authoritative tolerance threshold tau(lead) in km.")
    is_bust: Optional[bool] = Field(None, description="Whether track error exceeded tau(lead).")
    severity: Optional[str] = Field(None, description="Severity category: NORMAL, MODERATE, DEGRADED, SEVERE.")
    confidence_quadrant: Optional[str] = Field(None, description="Empirical reliability quadrant.")
    advance_warning_lead_hours: Optional[int] = Field(None, description="Advance warning lead time in hours.")
    observed_center: Optional[ObservedCenterCoords] = Field(None, description="Official best-track coordinates.")
    verification_horizon: Optional[str] = Field(None, description="Verification window (e.g. '+24h synoptic valid time').")


class FailureFingerprint(BaseModel):
    """Deterministic failure signature derived from verified historical evidence.

    Non-Causal Principle:
    Identifies observed forecast behaviour and historical patterns.
    Does NOT assert physical causation or causal mechanisms.
    """

    spread_regime: str = Field(..., description="Dispersion characterization (e.g. LOW_SPREAD_VULNERABLE, HIGH_SPREAD_DISPERSIVE).")
    geometric_dispersion: str = Field(..., description="Spatial geometry classification (e.g. STRONGLY_ELONGATED, MODERATE_ANISOTROPY).")
    cluster_structure: str = Field(..., description="Ensemble modality structure (e.g. BIFURCATED, COHERENT).")
    trajectory_behaviour: str = Field(..., description="Kinematic pattern (e.g. RAPID_TURNING, STABLE_TRANSLATION).")
    empirical_quadrant: str = Field(..., description="Diagnostic reliability quadrant.")
    observed_pattern_summary: str = Field(..., description="Scientifically guarded summary of observed forecast behaviour.")


class HistoricalAnalogueMatch(BaseModel):
    """Ranked historical forecast state match with post-retrieval verified outcome."""

    rank: int = Field(..., description="Similarity rank (1 = closest match).")
    case_id: str = Field(..., description="Unique historical case identifier e.g. 2023_MOCHA_00Z_plus24h.")
    storm_name: str = Field(..., description="Historical cyclone name e.g. MOCHA.")
    basin: str = Field(..., description="Ocean basin e.g. Bay of Bengal, Arabian Sea.")
    cycle_label: str = Field(..., description="Forecast initialization cycle e.g. MOCHA_00Z.")
    forecast_lead_hours: int = Field(..., description="Forecast lead time in hours.")
    initialization_time_utc: str = Field(..., description="Forecast cycle initialization timestamp.")
    forecast_valid_time_utc: str = Field(..., description="Synoptic valid time timestamp.")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Normalized similarity index (0 to 1.0).")
    similarity_percent: int = Field(..., ge=0, le=100, description="Similarity percentage integer.")
    standardized_distance: float = Field(..., ge=0.0, description="Standardized Euclidean distance d(x, y).")
    forecast_center: ForecastCenterCoords = Field(..., description="Forecast vortex center.")
    forecast_features: Dict[str, float] = Field(..., description="Measured forecast-state feature values.")
    dimension_breakdown: List[FeatureDimensionComparison] = Field(..., description="Per-dimension distance contributions.")
    verified_outcome: VerifiedHistoricalOutcome = Field(..., description="Real verified outcome attached post-retrieval.")
    failure_fingerprint: Optional[FailureFingerprint] = Field(None, description="Empirical failure signature if available.")
    provenance: Dict[str, str] = Field(..., description="Dual provenance: NCMRWF ensemble + IMD/RSMC best-track.")


class HistoricalMemorySearchRequest(BaseModel):
    """Request to search historical forecast memory."""

    model_config = ConfigDict(extra="forbid")

    query_state: Optional[ForecastStateQuery] = Field(
        None,
        description="Forecast state feature vector available at forecast cutoff.",
    )
    query_case_id: Optional[str] = Field(
        None,
        description="Optional ID of an existing case to query analogues for (e.g. '2023_MIDHILI_00Z_plus24h').",
    )
    top_k: int = Field(default=5, ge=1, le=20, description="Maximum number of historical analogues to retrieve.")
    lead_tolerance_hours: Optional[int] = Field(
        None,
        ge=0,
        le=48,
        description="Optional tolerance window around query lead (e.g. +/- 6h). None compares across all leads.",
    )
    basin_filter: Optional[str] = Field(
        None,
        description="Optional basin constraint (e.g. 'Bay of Bengal', 'Arabian Sea').",
    )
    exclude_same_storm: bool = Field(
        default=False,
        description="If True, excludes candidate records from the same storm to evaluate cross-event generalization.",
    )
    target_storm_name: Optional[str] = Field(
        None,
        description="Optional name of query storm to exclude when exclude_same_storm is True.",
    )


class HistoricalMemorySearchResponse(BaseModel):
    """Response containing retrieved historical analogues and verified evidence."""

    mode: Literal["HISTORICAL_MEMORY_SEARCH"] = "HISTORICAL_MEMORY_SEARCH"
    query_lead_hours: int
    query_features: Dict[str, float]
    total_reference_cases: int
    matched_analogues_count: int
    matches: List[HistoricalAnalogueMatch]
    reference_population_summary: Dict[str, Any]
    scientific_disclaimer: str = Field(
        default=(
            "Historical analogue matching identifies prior forecast states with similar ensemble dispersion "
            "and kinematic geometry. Historical similarity provides contextual evidence and does NOT "
            "guarantee an identical operational outcome."
        ),
        description="Mandatory scientific non-causal disclaimer.",
    )


class BustAtlasDetail(BaseModel):
    """Enhanced record in the ForecastGuard Cyclone Bust Atlas."""

    case_id: str
    storm_name: str
    cycle_label: str
    lead_hours: int
    valid_time_utc: str
    basin: str
    track_error_km: float
    threshold_km: float
    severity: str
    spread_km: float
    anisotropy_ratio: float
    bimodality_coefficient: float
    quadrant: str
    warning_status: str
    advance_warning_lead_hours: Optional[int]
    failure_fingerprint: FailureFingerprint
    forecast_center: ForecastCenterCoords
    observed_center: ObservedCenterCoords
    verification_status: Literal["VERIFIED", "PENDING_VERIFICATION", "INSUFFICIENT_EVIDENCE"] = "VERIFIED"
    provenance: Dict[str, str]
