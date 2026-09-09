"""Schemas for Live Forecast Exploration, Provider Abstraction, and Capability Status."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class ForecastLocation(BaseModel):
    """Geographic location target for live forecast exploration."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Location display name e.g. 'Bay of Bengal Central'")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude in degrees North")
    longitude: float = Field(..., ge=-180.0, le=360.0, description="Longitude in degrees East")
    elevation_m: Optional[float] = Field(None, description="Surface elevation in meters")
    basin: Optional[str] = Field(None, description="Associated ocean basin or territory")


class DailyForecastStep(BaseModel):
    """Single-day prospective forecast telemetry at a specific lead horizon."""

    model_config = ConfigDict(extra="forbid")

    lead_day: str = Field(..., description="Forecast horizon label e.g. 'D+1', 'D+2'")
    lead_hours: int = Field(..., ge=24, le=240, description="Lead duration in hours (24, 48, ..., 240)")
    valid_time: str = Field(..., description="Forecast valid time in ISO 8601 UTC")
    temperature_max_c: Optional[float] = Field(None, description="Daily maximum 2m temperature in °C")
    temperature_min_c: Optional[float] = Field(None, description="Daily minimum 2m temperature in °C")
    precipitation_sum_mm: Optional[float] = Field(None, description="Accumulated daily precipitation in mm")
    wind_speed_max_kmh: Optional[float] = Field(None, description="Maximum surface wind speed in km/h")
    surface_pressure_hpa: Optional[float] = Field(None, description="Mean sea level / surface pressure in hPa")
    weather_description: Optional[str] = Field(None, description="Synoptic weather condition overview")
    is_validated_domain: bool = Field(
        ...,
        description="Whether this forecast step falls within the validated cyclone bust verification domain"
    )
    capability_status: Literal[
        "VALIDATED_CYCLONE_DOMAIN",
        "NOT_VALIDATED_FOR_THIS_INPUT_DOMAIN",
        "INSUFFICIENT_EVIDENCE",
    ] = Field(..., description="Operational capability classification")
    calibrated_bust_probability: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Calibrated bust probability (strictly None if not in validated domain)"
    )
    bust_probability_display: str = Field(
        ...,
        description="Formatted bust risk percentage or explicit 'NOT VALIDATED FOR THIS INPUT DOMAIN' notice"
    )
    reliability_state: Literal[
        "STABLE",
        "WATCH",
        "HIGH_RISK",
        "NOT_VALIDATED",
        "INSUFFICIENT_EVIDENCE",
    ] = Field(..., description="Operational reliability assessment state")
    reliability_score: Optional[int] = Field(
        None,
        ge=0,
        le=100,
        description="Operational reliability score index (0-100) if validated"
    )
    confidence_level: Optional[
        Literal["HIGH", "MODERATE", "LOW", "INSUFFICIENT"]
    ] = Field(None, description="Assessment confidence tier based on telemetry completeness and reference support")
    confidence_rationale: Optional[str] = Field(None, description="Factual operational rationale for confidence assessment")
    evidence_summary: str = Field(..., description="Non-causal associative evidence explanation")


class LiveForecastResponse(BaseModel):
    """Top-level response for live prospective forecast exploration."""

    model_config = ConfigDict(extra="forbid")

    provider_name: str = Field(..., description="Identified forecast data provider")
    provider_type: Literal[
        "PUBLIC_NWP_INTEGRATION",
        "NCMRWF_ARCHIVE_VALIDATED",
        "CUSTOM_INGESTION",
    ] = Field(..., description="Provider categorization")
    provider_attribution: str = Field(..., description="Factual provenance attribution statement")
    forecast_cycle: str = Field(..., description="Model initialization cycle in ISO 8601 UTC")
    location: ForecastLocation = Field(..., description="Target geographic coordinates and metadata")
    capability_status: Literal[
        "VALIDATED_CYCLONE_DOMAIN",
        "NOT_VALIDATED_FOR_THIS_INPUT_DOMAIN",
        "INSUFFICIENT_EVIDENCE",
    ] = Field(..., description="Operational capability classification")
    calibrated_bust_probability: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Headline calibrated bust probability (strictly None if not validated)"
    )
    bust_probability_display: str = Field(
        ...,
        description="Formatted bust risk percentage or explicit 'NOT VALIDATED FOR THIS INPUT DOMAIN'"
    )
    confidence_level: Optional[
        Literal["HIGH", "MODERATE", "LOW", "INSUFFICIENT"]
    ] = Field(None, description="Headline assessment confidence tier")
    confidence_rationale: Optional[str] = Field(None, description="Operational rationale for assessment confidence")
    forecast_steps: List[DailyForecastStep] = Field(
        ...,
        min_length=1,
        description="Prospective 10-day forecast steps (D+1 through D+10)"
    )
    capability_notice: str = Field(
        ...,
        description="Explicit capability disclaimer separating general NWP from validated cyclone bust models"
    )
    scientific_boundary_notice: str = Field(
        ...,
        description="Strict non-fabrication scientific boundary declaration"
    )
    evidence_summary: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Evidence summary rows and operational narrative if validated"
    )
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Audit and runtime metadata")
