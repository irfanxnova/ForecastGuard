"""Schemas for OOD Representation, Novelty Detection, and Abstention Intelligence."""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


RepresentationStateLiteral = Literal[
    "WELL_REPRESENTED",
    "LOW_SUPPORT",
    "NOVEL_STATE",
    "INSUFFICIENT_EVIDENCE",
]


class NoveltyAssessmentResponse(BaseModel):
    """Structured response for OOD Representation and Novelty Assessment."""

    model_config = ConfigDict(extra="forbid")

    representation_state: RepresentationStateLiteral = Field(
        ...,
        description=(
            "Deterministic representation state relative to historical reference population "
            "(WELL_REPRESENTED | LOW_SUPPORT | NOVEL_STATE | INSUFFICIENT_EVIDENCE)."
        ),
    )
    novelty_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Empirical percentile distance ranking against reference population [0.0, 1.0].",
    )
    support_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Calibrated historical representation index [0, 100], where 100 = maximum support.",
    )
    distance: Optional[float] = Field(
        None,
        description="Mean standardized Euclidean distance to k=3 nearest reference neighbours.",
    )
    nearest_reference_distance: Optional[float] = Field(
        None,
        description="Standardized Euclidean distance to closest single reference sample.",
    )
    reference_population_size: int = Field(
        ...,
        description="Number of historical forecast states in reference population (n=77).",
    )
    feature_coverage: Dict[str, bool] = Field(
        ...,
        description="Presence indicator for each required reference feature.",
    )
    coverage_ratio: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Fraction of required reference features available [0.0, 1.0].",
    )
    abstention_recommended: bool = Field(
        ...,
        description=(
            "Whether ForecastGuard recommends abstaining from high-confidence reliance "
            "due to inadequate historical representation or missing evidence."
        ),
    )
    abstention_reason: Optional[str] = Field(
        None,
        description="Detailed rationale when abstention is recommended.",
    )
    status: str = Field(
        ...,
        description="SUPPORT_CONFIRMED | PROCEED_WITH_CAUTION | CAUTION_NOVEL_STATE | ABSTAIN_INSUFFICIENT_EVIDENCE",
    )
    message: str = Field(
        ...,
        description="Human-readable decision-support summary of representation status.",
    )
    provenance: Dict[str, Any] = Field(
        ...,
        description="Audit trail of reference cutoff, feature definitions, and thresholds.",
    )


class ReferencePopulationMetadataResponse(BaseModel):
    """Audit metadata for ForecastGuard's historical reference population."""

    model_config = ConfigDict(extra="forbid")

    reference_id: str = Field(..., description="Unique identifier of reference dataset.")
    reference_period: str = Field(..., description="Date range of reference forecast cycles.")
    cutoff_timestamp_utc: str = Field(..., description="Strict cutoff timestamp in UTC.")
    historical_storms: List[str] = Field(..., description="List of cyclone events in reference.")
    historical_cycles_count: int = Field(..., description="Number of verified forecast cycles.")
    sample_count: int = Field(..., description="Number of 6-hourly forecast lead states.")
    feature_names: List[str] = Field(..., description="Features used for state representation.")
    normalization_method: str = Field(..., description="Mathematical scaling method.")
    k_nearest_neighbors: int = Field(..., description="k parameter for local density estimation.")
    threshold_q75_well_represented: float = Field(..., description="Q75 boundary threshold.")
    threshold_q95_novel_state: float = Field(..., description="Q95 boundary threshold.")
    provenance_description: str = Field(..., description="Detailed provenance narrative.")
