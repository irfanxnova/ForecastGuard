"""ForecastGuard Novelty & Representation Backend Service.

Provides live operational novelty evaluation, support scoring, and reference metadata.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional

from backend.app.schemas.novelty import (
    NoveltyAssessmentResponse,
    ReferencePopulationMetadataResponse,
)
from scientific.ml.novelty import (
    REFERENCE_METADATA,
    NoveltyAssessment,
    NoveltyDetector,
    novelty_detector,
)


class NoveltyService:
    """Service encapsulating the scientific novelty and abstention intelligence engine."""

    def __init__(self, detector: Optional[NoveltyDetector] = None) -> None:
        self.detector = detector or novelty_detector

    def evaluate_novelty(
        self,
        features: Optional[Dict[str, float]],
        member_count: int,
    ) -> NoveltyAssessmentResponse:
        """Evaluate representation state and support distance for a forecast state."""
        assessment: NoveltyAssessment = self.detector.evaluate(
            features=features,
            ensemble_member_count=member_count,
        )

        dist_val = (
            None
            if (assessment.distance is None or math.isnan(assessment.distance))
            else assessment.distance
        )
        nearest_dist_val = (
            None
            if (
                assessment.nearest_reference_distance is None
                or math.isnan(assessment.nearest_reference_distance)
            )
            else assessment.nearest_reference_distance
        )

        return NoveltyAssessmentResponse(
            representation_state=assessment.representation_state.value,
            novelty_score=assessment.novelty_score,
            support_score=assessment.support_score,
            distance=dist_val,
            nearest_reference_distance=nearest_dist_val,
            reference_population_size=assessment.reference_population_size,
            feature_coverage=assessment.feature_coverage,
            coverage_ratio=assessment.coverage_ratio,
            abstention_recommended=assessment.abstention_recommended,
            abstention_reason=assessment.abstention_reason,
            status=assessment.status,
            message=assessment.message,
            provenance=assessment.provenance,
        )

    def get_reference_metadata(self) -> ReferencePopulationMetadataResponse:
        """Retrieve audit metadata of the historical reference population."""
        return ReferencePopulationMetadataResponse(
            reference_id=REFERENCE_METADATA["reference_id"],
            reference_period=REFERENCE_METADATA["reference_period"],
            cutoff_timestamp_utc=REFERENCE_METADATA["cutoff_timestamp_utc"],
            historical_storms=REFERENCE_METADATA["historical_storms"],
            historical_cycles_count=REFERENCE_METADATA["historical_cycles_count"],
            sample_count=REFERENCE_METADATA["sample_count"],
            feature_names=REFERENCE_METADATA["feature_names"],
            normalization_method=REFERENCE_METADATA["normalization_method"],
            k_nearest_neighbors=REFERENCE_METADATA["k_nearest_neighbors"],
            threshold_q75_well_represented=REFERENCE_METADATA["threshold_q75_well_represented"],
            threshold_q95_novel_state=REFERENCE_METADATA["threshold_q95_novel_state"],
            provenance_description=REFERENCE_METADATA["provenance_description"],
        )


novelty_service = NoveltyService()
