"""ForecastGuard Scientific Novelty, Support, and Abstention Intelligence Engine.

Provides an isolated, interpretable representation and support intelligence layer answering:
"How well represented is the current forecast state by the historical
population ForecastGuard was developed from?"

Strict scientific boundaries:
- Forecast risk != novelty.
- Ensemble uncertainty != forecast error.
- Low support != forecast bust.
- NOVEL_STATE indicates novelty strictly relative to ForecastGuard's mathematical reference
  population; it does NOT claim that the atmosphere itself is unprecedented.

Deterministic Representation States:
- WELL_REPRESENTED: Forecast state lies within the dense historical reference distribution.
- LOW_SUPPORT: Forecast state lies in a sparse region of the historical reference distribution.
- NOVEL_STATE: Forecast state lies outside the empirical reference envelope (extrapolation risk).
- INSUFFICIENT_EVIDENCE: Ensemble telemetry is missing, degraded below threshold, or corrupted.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


class RepresentationState(str, Enum):
    """Deterministic forecast representation state relative to historical reference."""

    WELL_REPRESENTED = "WELL_REPRESENTED"
    LOW_SUPPORT = "LOW_SUPPORT"
    NOVEL_STATE = "NOVEL_STATE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


# ---------------------------------------------------------------------------
# Precomputed Reference Population Matrix (10 cycles, 77 verified leads, May-Nov 2023)
# Fitted strictly before the chronological evaluation cutoff (2023-11-17T00:00:00Z).
# Features: [forecast_lead_hours, ensemble_spread_km, ensemble_divergence_km, anisotropy_ratio]
# ---------------------------------------------------------------------------

REFERENCE_FEATURES = [
    "forecast_lead_hours",
    "ensemble_spread_km",
    "ensemble_divergence_km",
    "anisotropy_ratio",
]

REFERENCE_SCALER_MEAN: List[float] = [
    26.337662337662337,
    99.38610389610386,
    368.49571428571414,
    2.3009090909090917,
]

REFERENCE_SCALER_STD: List[float] = [
    13.5432068461717,
    30.519532011009336,
    126.43109829744256,
    0.9541874653380562,
]

# Empirical quantiles of leave-one-out k=3 NN distance on reference population (n=77)
REFERENCE_DISTANCE_Q50: float = 0.6298
REFERENCE_DISTANCE_Q75: float = 0.8406  # Boundary: WELL_REPRESENTED -> LOW_SUPPORT
REFERENCE_DISTANCE_Q90: float = 1.1160
REFERENCE_DISTANCE_Q95: float = 1.3601  # Boundary: LOW_SUPPORT -> NOVEL_STATE
REFERENCE_DISTANCE_Q99: float = 1.6684
REFERENCE_DISTANCE_MAX: float = 1.7509
REFERENCE_DISTANCE_MIN: float = 0.3866

# Reference Population Manifest
REFERENCE_METADATA: Dict[str, Any] = {
    "reference_id": "EXPANDED_CYCLONE_10CYCLES_77LEADS_MAY_NOV_2023",
    "reference_period": "2023-05-10T00:00:00Z to 2023-11-16T00:00:00Z",
    "cutoff_timestamp_utc": "2023-11-17T00:00:00Z",
    "historical_storms": ["MOCHA", "BIPARJOY", "TEJ", "HAMOON", "MIDHILI"],
    "historical_cycles_count": 10,
    "sample_count": 77,
    "feature_names": REFERENCE_FEATURES,
    "normalization_method": "Z-score Standardization (Reference Population Only)",
    "k_nearest_neighbors": 3,
    "threshold_q75_well_represented": REFERENCE_DISTANCE_Q75,
    "threshold_q95_novel_state": REFERENCE_DISTANCE_Q95,
    "provenance_description": (
        "Constructed strictly from 77 pre-issuance forecast lead states across 10 verified "
        "training cycles of NCMRWF NEPS forecasts (ECMWF origin=dems, 11 members). Excludes "
        "all verification observations, future forecast cycles, and the unseen test storm MICHAUNG."
    ),
}

# Audited 77 reference vectors in unstandardized feature space:
# [lead_hours, spread_km, divergence_km, anisotropy_ratio]
HISTORICAL_REFERENCE_RECORDS: List[List[float]] = [
    [6.0, 113.33, 389.98, 1.969],
    [12.0, 113.11, 401.45, 1.826],
    [18.0, 104.47, 420.54, 1.212],
    [24.0, 95.79, 354.61, 1.536],
    [30.0, 80.41, 318.03, 1.601],
    [36.0, 110.65, 450.97, 1.881],
    [42.0, 120.58, 431.91, 1.398],
    [48.0, 145.0, 508.56, 1.39],
    [6.0, 129.63, 558.67, 2.151],
    [12.0, 114.58, 585.61, 2.75],
    [18.0, 86.35, 279.49, 1.511],
    [24.0, 72.69, 218.9, 1.381],
    [30.0, 83.76, 276.06, 1.579],
    [36.0, 87.39, 316.55, 1.772],
    [42.0, 84.91, 286.09, 1.561],
    [48.0, 88.95, 333.15, 1.896],
    [6.0, 56.62, 214.08, 1.76],
    [12.0, 55.33, 246.32, 2.845],
    [18.0, 59.08, 256.51, 2.522],
    [24.0, 68.9, 255.67, 2.216],
    [30.0, 72.49, 292.5, 1.931],
    [36.0, 78.98, 306.11, 1.774],
    [42.0, 84.35, 287.5, 1.856],
    [48.0, 100.12, 341.29, 1.896],
    [6.0, 89.51, 506.29, 4.355],
    [12.0, 102.06, 523.73, 3.566],
    [18.0, 107.28, 527.79, 3.581],
    [24.0, 112.34, 564.06, 3.215],
    [30.0, 124.91, 562.49, 2.451],
    [36.0, 127.4, 494.97, 2.493],
    [42.0, 130.54, 551.34, 3.215],
    [48.0, 140.64, 620.72, 3.701],
    [6.0, 63.92, 265.23, 1.624],
    [12.0, 76.59, 301.58, 1.442],
    [18.0, 90.28, 334.27, 1.818],
    [24.0, 106.55, 371.0, 2.352],
    [30.0, 120.18, 414.84, 2.865],
    [36.0, 134.31, 422.46, 2.717],
    [42.0, 143.99, 425.12, 2.631],
    [48.0, 159.31, 447.73, 2.602],
    [6.0, 61.07, 177.62, 1.506],
    [12.0, 69.5, 237.05, 1.106],
    [18.0, 68.48, 262.72, 1.532],
    [24.0, 71.68, 312.09, 1.944],
    [30.0, 91.88, 366.96, 2.002],
    [36.0, 122.49, 425.97, 2.235],
    [42.0, 136.36, 411.19, 1.945],
    [48.0, 145.7, 420.23, 1.734],
    [6.0, 43.21, 117.72, 1.507],
    [12.0, 57.36, 177.7, 1.602],
    [18.0, 62.57, 198.96, 1.45],
    [24.0, 79.52, 243.0, 1.607],
    [30.0, 78.9, 234.65, 1.516],
    [36.0, 71.73, 233.78, 1.894],
    [42.0, 66.23, 237.67, 2.111],
    [48.0, 71.55, 240.43, 1.876],
    [6.0, 65.87, 189.57, 1.884],
    [12.0, 79.48, 230.5, 1.68],
    [18.0, 82.01, 255.38, 1.89],
    [24.0, 90.86, 348.34, 3.082],
    [30.0, 109.06, 421.39, 5.28],
    [36.0, 139.47, 461.1, 6.051],
    [42.0, 149.22, 479.33, 5.318],
    [6.0, 79.89, 226.8, 1.401],
    [12.0, 104.03, 405.64, 2.625],
    [18.0, 112.03, 421.44, 3.698],
    [24.0, 121.0, 502.86, 3.264],
    [30.0, 137.65, 544.94, 2.978],
    [42.0, 170.32, 629.02, 1.608],
    [6.0, 56.07, 209.26, 2.144],
    [12.0, 77.37, 253.46, 1.496],
    [18.0, 80.44, 337.23, 2.329],
    [24.0, 99.05, 387.03, 2.53],
    [30.0, 99.77, 403.97, 2.567],
    [36.0, 131.04, 485.88, 2.452],
    [42.0, 160.18, 581.34, 2.771],
    [48.0, 172.41, 637.78, 3.713],
]


@dataclass(frozen=True)
class NoveltyAssessment:
    """Interpretable representation, support, and abstention assessment."""

    representation_state: RepresentationState
    novelty_score: float  # Empirical percentile in [0.0, 1.0]
    support_score: int  # Interpretable index in [0, 100], 100 = maximum support
    distance: float  # Mean standardized Euclidean distance to k-NN reference
    nearest_reference_distance: float  # Distance to single nearest reference sample
    reference_population_size: int  # n=77
    feature_coverage: Dict[str, bool]
    coverage_ratio: float
    abstention_recommended: bool
    abstention_reason: Optional[str]
    status: str
    message: str
    provenance: Dict[str, Any] = field(default_factory=dict)


class NoveltyDetector:
    """Deterministic scientific novelty and support detector.

    Uses standardized Euclidean distance to the pre-fit historical reference
    population to determine empirical representation and abstention guidance.
    """

    def __init__(
        self,
        reference_matrix: Optional[List[List[float]]] = None,
        scaler_mean: Optional[List[float]] = None,
        scaler_std: Optional[List[float]] = None,
        q75_threshold: float = REFERENCE_DISTANCE_Q75,
        q95_threshold: float = REFERENCE_DISTANCE_Q95,
        k_neighbors: int = 3,
    ) -> None:
        raw_matrix = reference_matrix or HISTORICAL_REFERENCE_RECORDS
        self.scaler_mean = np.array(scaler_mean or REFERENCE_SCALER_MEAN, dtype=np.float64)
        self.scaler_std = np.array(scaler_std or REFERENCE_SCALER_STD, dtype=np.float64)
        self.q75 = float(q75_threshold)
        self.q95 = float(q95_threshold)
        self.k = int(k_neighbors)

        # Standardize reference population using reference-only parameters
        X_ref = np.array(raw_matrix, dtype=np.float64)
        self.reference_size = len(X_ref)
        self.Z_ref = (X_ref - self.scaler_mean) / self.scaler_std

        # Precompute reference internal k-NN distances for exact percentile ranking
        internal_knn_dists = []
        for i in range(self.reference_size):
            diff = self.Z_ref - self.Z_ref[i]
            dists = np.sort(np.linalg.norm(diff, axis=1))
            internal_knn_dists.append(float(np.mean(dists[1 : self.k + 1])))
        self.ref_internal_dists = np.sort(np.array(internal_knn_dists, dtype=np.float64))

    def evaluate(
        self,
        features: Optional[Dict[str, float]],
        ensemble_member_count: int,
    ) -> NoveltyAssessment:
        """Evaluate representation state and support distance for a forecast state.

        Strict fail-safe: if member count is below 5 or features are incomplete/corrupted,
        returns INSUFFICIENT_EVIDENCE with an explicit abstention recommendation.
        """
        # 1. Fail-Safe: Check member count
        if ensemble_member_count < 5:
            return NoveltyAssessment(
                representation_state=RepresentationState.INSUFFICIENT_EVIDENCE,
                novelty_score=1.0,
                support_score=0,
                distance=math.nan,
                nearest_reference_distance=math.nan,
                reference_population_size=self.reference_size,
                feature_coverage={f: (features is not None and f in features) for f in REFERENCE_FEATURES},
                coverage_ratio=0.0,
                abstention_recommended=True,
                abstention_reason=(
                    f"Insufficient ensemble member count ({ensemble_member_count}/11). "
                    "Cannot reliably evaluate forecast dispersion or reference representation."
                ),
                status="ABSTAIN_INSUFFICIENT_EVIDENCE",
                message="Representation assessment unavailable — insufficient forecast evidence.",
                provenance=self._build_provenance("DATA INSUFFICIENT"),
            )

        # 2. Check feature completeness and validity
        if features is None:
            return NoveltyAssessment(
                representation_state=RepresentationState.INSUFFICIENT_EVIDENCE,
                novelty_score=1.0,
                support_score=0,
                distance=math.nan,
                nearest_reference_distance=math.nan,
                reference_population_size=self.reference_size,
                feature_coverage={f: False for f in REFERENCE_FEATURES},
                coverage_ratio=0.0,
                abstention_recommended=True,
                abstention_reason="Missing feature dictionary payload.",
                status="ABSTAIN_INSUFFICIENT_EVIDENCE",
                message="Representation assessment unavailable — missing feature telemetry.",
                provenance=self._build_provenance("DATA INSUFFICIENT"),
            )

        coverage: Dict[str, bool] = {}
        values: List[float] = []
        is_corrupt = False

        for f in REFERENCE_FEATURES:
            if f in features and features[f] is not None:
                val = float(features[f])
                if math.isnan(val) or math.isinf(val):
                    is_corrupt = True
                    coverage[f] = False
                else:
                    coverage[f] = True
                    values.append(val)
            else:
                coverage[f] = False

        cov_ratio = float(sum(coverage.values())) / float(len(REFERENCE_FEATURES))

        if is_corrupt or cov_ratio < 1.0:
            missing_names = [f for f, present in coverage.items() if not present]
            return NoveltyAssessment(
                representation_state=RepresentationState.INSUFFICIENT_EVIDENCE,
                novelty_score=1.0,
                support_score=0,
                distance=math.nan,
                nearest_reference_distance=math.nan,
                reference_population_size=self.reference_size,
                feature_coverage=coverage,
                coverage_ratio=round(cov_ratio, 2),
                abstention_recommended=True,
                abstention_reason=f"Incomplete or corrupt features: {missing_names}.",
                status="ABSTAIN_INSUFFICIENT_EVIDENCE",
                message="Representation assessment unavailable — incomplete feature telemetry.",
                provenance=self._build_provenance("DATA INSUFFICIENT"),
            )

        # 3. Standardize input state strictly with reference parameters
        x = np.array(values, dtype=np.float64)
        z = (x - self.scaler_mean) / self.scaler_std

        # 4. Compute distances to reference population members
        diff = self.Z_ref - z
        distances = np.linalg.norm(diff, axis=1)
        sorted_dists = np.sort(distances)

        d_1nn = float(sorted_dists[0])
        d_knn = float(np.mean(sorted_dists[: self.k]))

        # Empirical percentile ranking against reference internal distances
        # rank / N gives the fraction of reference samples whose internal distance is <= d_knn
        rank = np.searchsorted(self.ref_internal_dists, d_knn, side="right")
        empirical_percentile = float(rank) / float(self.reference_size)
        novelty_score = round(min(1.0, max(0.0, empirical_percentile)), 3)

        # Support score is the inverse calibrated representation index
        # 100 indicates high support (well within the dense core), while 0 indicates high novelty
        support_score = int(round(max(0.0, min(100.0, (1.0 - novelty_score) * 100.0))))

        # 5. Deterministic Representation State Categorization
        if d_knn <= self.q75:
            state = RepresentationState.WELL_REPRESENTED
            abstention_rec = False
            abstention_reason = None
            status_code = "SUPPORT_CONFIRMED"
            message = (
                f"Well-represented forecast state (support index: {support_score}/100, "
                f"reference distance: {d_knn:.2f}). Forecast state falls within the dense "
                "historical reference population ForecastGuard was developed from."
            )
        elif d_knn <= self.q95:
            state = RepresentationState.LOW_SUPPORT
            abstention_rec = False
            abstention_reason = (
                "Forecast state lies in a sparse region of the reference distribution. "
                "ForecastGuard has limited historical support for this state."
            )
            status_code = "PROCEED_WITH_CAUTION"
            message = (
                f"Limited historical support for this state (support index: {support_score}/100, "
                f"reference distance: {d_knn:.2f}). Forecast dispersion lies in a sparse "
                "region of the reference population. Interpret model guidance with caution."
            )
        else:
            state = RepresentationState.NOVEL_STATE
            abstention_rec = True
            abstention_reason = (
                "Forecast state lies beyond the 95th percentile of the reference population "
                f"(reference distance: {d_knn:.2f} > Q95 {self.q95:.2f}). ForecastGuard has limited "
                "historical support for this state. Model extrapolation risk is elevated."
            )
            status_code = "CAUTION_NOVEL_STATE"
            message = (
                f"Novel state relative to reference population (support index: {support_score}/100, "
                f"reference distance: {d_knn:.2f}). ForecastGuard has limited historical "
                "support for this state. Recommendation: abstain from high-confidence reliance."
            )

        return NoveltyAssessment(
            representation_state=state,
            novelty_score=novelty_score,
            support_score=support_score,
            distance=round(d_knn, 3),
            nearest_reference_distance=round(d_1nn, 3),
            reference_population_size=self.reference_size,
            feature_coverage=coverage,
            coverage_ratio=round(cov_ratio, 2),
            abstention_recommended=abstention_rec,
            abstention_reason=abstention_reason,
            status=status_code,
            message=message,
            provenance=self._build_provenance("DATA COMPLETE"),
        )

    def _build_provenance(self, data_quality: str) -> Dict[str, Any]:
        return {
            "reference_id": REFERENCE_METADATA["reference_id"],
            "reference_sample_count": self.reference_size,
            "reference_cutoff_utc": REFERENCE_METADATA["cutoff_timestamp_utc"],
            "reference_storms": REFERENCE_METADATA["historical_storms"],
            "features_used": REFERENCE_FEATURES,
            "distance_metric": "Standardized Euclidean (k=3 Nearest Neighbors)",
            "q75_threshold": self.q75,
            "q95_threshold": self.q95,
            "data_quality": data_quality,
            "scientific_boundary_notice": (
                "Representation and novelty are computed strictly relative to ForecastGuard's "
                "historical reference population. This is not a claim that the atmosphere itself "
                "is unprecedented. Low support does not imply forecast bust."
            ),
        }


# Global pre-initialized detector instance
novelty_detector = NoveltyDetector()
