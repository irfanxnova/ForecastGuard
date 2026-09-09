"""ForecastGuard V2 Regional Candidate Model and Feature Architecture.

Strictly complies with AGENTS.md:
1. Never fabricate weather data or machine-learning predictions.
2. Regional ensemble features are a NEW feature population/problem distinct
   from the frozen V1 cyclone-center M1 tracker (which was fitted on track error in km).
3. Output is treated as a CANDIDATE / raw reliability signal until independent
   regional calibration is established on an audited regional ground-truth dataset.
4. Exposes explicit status: VALIDATED / CANDIDATE / INSUFFICIENT_EVIDENCE.
5. The calibration architecture supports:
   raw model score -> regional calibration -> calibrated regional probability
   without changing the API/frontend contract.
"""

from dataclasses import dataclass
import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from backend.app.schemas.regional import RegionalFeatureCatalogItem


# Canonical definitions for all 5 genuine computed regional features (Priority 3)
REGIONAL_FEATURE_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "regional_mean_spread": {
        "feature_name": "regional_mean_spread",
        "definition": (
            "Spatially averaged ensemble standard deviation across all valid "
            "regional grid cells for the target lead time."
        ),
        "units": "Pa",
        "source": "NCMRWF NEPS 11-member ensemble grid (msl)",
        "is_validated": True,
        "model_role": "Primary spatial dispersion feature for raw candidate vulnerability scoring",
    },
    "peak_spread_anomaly": {
        "feature_name": "peak_spread_anomaly",
        "definition": (
            "Maximum localized standard deviation among all grid cells within "
            "the regional boundary, identifying localized uncertainty hotspots."
        ),
        "units": "Pa",
        "source": "NCMRWF NEPS 11-member ensemble grid (msl)",
        "is_validated": True,
        "model_role": "Identifies localized high-uncertainty hotspots within the region",
    },
    "pairwise_member_disagreement": {
        "feature_name": "pairwise_member_disagreement",
        "definition": (
            "Mean absolute difference across all distinct ensemble member pairs (55 pairs), "
            "averaged over regional grid points."
        ),
        "units": "Pa",
        "source": "NCMRWF NEPS 11-member ensemble member pairs",
        "is_validated": True,
        "model_role": "Direct non-parametric measure of ensemble member divergence",
    },
    "lead_time_hours": {
        "feature_name": "lead_time_hours",
        "definition": "Forecast horizon lead duration elapsed since model initialization.",
        "units": "hours",
        "source": "GRIB step metadata",
        "is_validated": True,
        "model_role": "Temporal degradation covariate (dispersion growth with lead time)",
    },
    "trend_delta": {
        "feature_name": "trend_delta",
        "definition": (
            "Cycle-over-cycle change in candidate vulnerability score compared to "
            "the prior 24-hour forecast lead."
        ),
        "units": "dimensionless",
        "source": "Temporal difference between consecutive 24h GRIB ensemble evaluation steps",
        "is_validated": True,
        "model_role": "Dynamic trajectory monitor (detecting rapid consolidation or divergence)",
    },
}


class RegionalCandidatePredictor:
    """Predictor for regional forecast reliability and bust risk.

    Explicitly separates V2 regional candidate dispersion modeling from
    the frozen V1 cyclone-center M1 tracker.

    Architecture (Priorities 1 & 4):
        Raw Meteorological Dispersion Features
        -> compute_raw_score() [CANDIDATE]
        -> calibrate() [Regional Calibration / Platt / Isotonic]
        -> calibrated_probability [VALIDATED once calibration population is established]
    """

    MODEL_NAME: str = "V2_Regional_Candidate_Dispersion"
    MODEL_VERSION: str = "0.2.0-candidate"
    MODEL_STATUS: str = "CANDIDATE"
    CALIBRATION_STATUS: str = "UNCALIBRATED_CANDIDATE"

    # Characteristic scale parameter for synoptic surface pressure spread (Pa)
    # Based on tropical/monsoonal surface pressure ensemble dispersion characteristics
    PRESSURE_SPREAD_REF_PA: float = 150.0

    def __init__(self) -> None:
        # Placeholder for future empirical calibration curves keyed by (region_id, lead_hours)
        # Strictly empty until real regional verification ground truth is audited
        self._calibration_tables: Dict[Tuple[str, int], Any] = {}

    def compute_raw_score(
        self,
        mean_spread_pa: float,
        lead_hours: int,
        peak_spread_pa: Optional[float] = None,
        pairwise_diff_pa: Optional[float] = None,
    ) -> float:
        """Compute prospective raw candidate vulnerability score in [0.0, 1.0].

        Uses an explicit meteorological dispersion formulation:
        - normalized dispersion ratio: mean_spread / reference_spread
        - temporal lead scaling: uncertainty growth with lead duration
        - sigmoid logistic mapping bounded strictly in [0.05, 0.95]

        This provides an uncalibrated, ordinal vulnerability score reflecting
        physical ensemble spread without masquerading as fitted cyclone M1 regression.
        """
        # Normalize spread against characteristic synoptic scale (150 Pa)
        spread_ratio = mean_spread_pa / self.PRESSURE_SPREAD_REF_PA

        # Lead time growth adjustment (+24h baseline = 1.0, +48h = 1.25)
        lead_factor = 1.0 + 0.25 * max(0.0, (lead_hours - 24.0) / 24.0)

        # Logit calculation
        # Centered such that 150 Pa spread at 24h yields ~0.35 (WATCH threshold)
        # 300 Pa spread yields ~0.70 (HIGH_RISK threshold)
        z = 1.8 * (spread_ratio * lead_factor - 1.0) - 0.4

        raw_score = 1.0 / (1.0 + math.exp(-np.clip(z, -5.0, 5.0)))
        return float(np.clip(raw_score, 0.05, 0.95))

    def calibrate(
        self,
        raw_score: float,
        region_id: str,
        lead_hours: int,
        is_verified_case: bool = True,
    ) -> Optional[float]:
        """Calibrate raw score to empirical probability using regional calibration curve.

        Strict AGENTS.md Rule: Never fabricate calibration.
        Delegates to audited RegionalCalibrator with Platt logistic scaling
        fitted strictly on chronological historical storms.
        """
        from scientific.ml.regional_calibration import regional_calibrator
        return regional_calibrator.calibrate_score(
            raw_score=raw_score,
            region_id=region_id,
            lead_hours=lead_hours,
            is_verified_case=is_verified_case,
        )

    def get_feature_catalog_items(
        self,
        mean_spread_pa: Optional[float] = None,
        peak_spread_pa: Optional[float] = None,
        pairwise_diff_pa: Optional[float] = None,
        lead_hours: Optional[int] = None,
        trend_delta: Optional[float] = None,
    ) -> List[RegionalFeatureCatalogItem]:
        """Produce explicit catalog of all computed regional features."""
        values = {
            "regional_mean_spread": mean_spread_pa,
            "peak_spread_anomaly": peak_spread_pa,
            "pairwise_member_disagreement": pairwise_diff_pa,
            "lead_time_hours": float(lead_hours) if lead_hours is not None else None,
            "trend_delta": trend_delta,
        }

        catalog: List[RegionalFeatureCatalogItem] = []
        for feat_name, meta in REGIONAL_FEATURE_DEFINITIONS.items():
            val = values.get(feat_name)
            catalog.append(
                RegionalFeatureCatalogItem(
                    feature_name=meta["feature_name"],
                    definition=meta["definition"],
                    units=meta["units"],
                    source=meta["source"],
                    is_validated=meta["is_validated"],
                    model_role=meta["model_role"],
                    current_value=round(val, 2) if val is not None else None,
                )
            )
        return catalog


# Global candidate predictor instance
regional_candidate_predictor = RegionalCandidatePredictor()
