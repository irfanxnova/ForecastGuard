"""Schemas for Historical Replay, Verified Cyclone Cases, and Bust Atlas."""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class CycloneSummary(BaseModel):
    """Summary of a historical tropical cyclone in the verified dataset."""

    storm_id: str = Field(..., description="Unique storm identifier e.g. 2023_MOCHA")
    storm_name: str = Field(..., description="Cyclone official name e.g. MOCHA")
    basin: str = Field(..., description="Ocean basin e.g. Bay of Bengal, Arabian Sea")
    season_year: int = Field(..., description="Year of cyclone activity")
    cycles_count: int = Field(..., description="Number of evaluated NCMRWF forecast cycles")
    cycles: List[str] = Field(..., description="Cycle labels available for replay")
    verified_leads_count: int = Field(..., description="Number of exact verified 6-hourly fixes")
    contemporaneous_busts_count: int = Field(..., description="Number of leads exceeding tau(lead)")
    mean_track_error_km: float = Field(..., description="Mean continuous track error in km")


class ReplayLeadPoint(BaseModel):
    """Single verified forecast lead in historical replay sequence (+06h to +48h)."""

    lead_hours: int = Field(..., description="Lead time in hours (6, 12, ..., 48)")
    lead_formatted: str = Field(..., description="Formatted lead string e.g. +24h")
    valid_time_utc: str = Field(..., description="Synoptic valid time in ISO 8601 UTC")
    forecast_center: Dict[str, float] = Field(..., description="Ensemble mean vortex center (lat, lon, pressure_hpa)")
    observed_center: Dict[str, float] = Field(..., description="Official IMD/RSMC best-track center (lat, lon, pressure_hpa)")
    track_error_km: float = Field(..., description="Continuous great-circle track error in km")
    threshold_km: float = Field(..., description="Authoritative tolerance threshold tau(lead) in km")
    is_bust: bool = Field(..., description="Whether track error exceeds tau(lead)")
    severity: Literal["NORMAL", "MODERATE", "DEGRADED", "SEVERE"] = Field(..., description="Severity category")
    ensemble_spread_km: float = Field(..., description="Scalar ensemble track spread in km")
    ensemble_divergence_km: float = Field(..., description="Displacement of ensemble mean from control/origin in km")
    prospective_bust_risk_percent: Optional[int] = Field(None, description="Prospective bust risk predicted by M1")
    reliability_score: int = Field(..., description="Operational reliability index (0-100)")
    reliability_state: Literal["STABLE", "WATCH", "VULNERABLE", "SEVERE"] = Field(..., description="Reliability state")
    retrospective_confidence_quadrant: str = Field(..., description="Retrospective verification quadrant")


class HistoricalReplayResponse(BaseModel):
    """Full historical replay response for a selected cyclone and cycle."""

    mode: Literal["HISTORICAL_REPLAY"] = Field(
        default="HISTORICAL_REPLAY",
        description="Explicitly labelled historical research/verification mode.",
    )
    storm_id: str
    storm_name: str
    basin: str
    cycle_label: str
    initialization_time_utc: str
    total_leads: int
    leads: List[ReplayLeadPoint]
    continuous_error_summary: Dict[str, float]
    provenance: Dict[str, str] = Field(
        ...,
        description="Dual provenance: NCMRWF TIGGE ensemble forecast + Official IMD/RSMC Best Track.",
    )


class BustAtlasRecord(BaseModel):
    """Curated record in the ForecastGuard Cyclone Bust Atlas."""

    storm_name: str
    cycle_label: str
    lead_hours: int
    valid_time_utc: str
    track_error_km: float
    threshold_km: float
    severity: str
    spread_km: float
    quadrant: str
    failure_type: str
    description: str
