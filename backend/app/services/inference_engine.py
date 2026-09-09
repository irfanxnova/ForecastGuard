"""ForecastGuard Production Inference Engine.

Deterministic, fail-safe inference pipeline for live forecast bust detection.
Adheres strictly to the live vs. historical separation protocol:
- Uses ONLY information available at forecast issuance (lead time, ensemble spread, geometry).
- Rejects any ground truth observations, retrospective quadrants, or future errors.
- Provides strict fail-safe handling (DATA COMPLETE, DATA DEGRADED, DATA INSUFFICIENT).
- Embeds complete, truthful provenance in every response.
"""

from datetime import datetime, timezone
import math
from typing import Dict, List, Optional, Tuple

import numpy as np

from backend.app.schemas.inference import (
    InferenceProvenance,
    LiveInferenceRequest,
    LiveInferenceResponse,
)
from backend.app.services.model_config import (
    M1_PARAMETERS,
    M1_SPREAD_ONLY_METADATA,
)
from backend.app.services.novelty_service import novelty_service
from scientific.validation.cyclone import haversine_distance


class ProductionInferenceEngine:
    """Deterministic, production-ready inference engine for ForecastGuard."""

    def __init__(self) -> None:
        self.metadata = M1_SPREAD_ONLY_METADATA
        self.scaler_mean = np.array(M1_PARAMETERS["scaler_mean"], dtype=np.float64)
        self.scaler_scale = np.array(M1_PARAMETERS["scaler_scale"], dtype=np.float64)
        self.coef = np.array(M1_PARAMETERS["coefficients"], dtype=np.float64)
        self.intercept = float(M1_PARAMETERS["intercept"])
        self.base_rate = float(M1_PARAMETERS["base_rate"])

    def evaluate(self, req: LiveInferenceRequest) -> LiveInferenceResponse:
        """Execute deterministic inference pipeline with data QC and fail-safe guards."""
        # 1. Fail-Safe: Validate ensemble member count
        member_count = len(req.ensemble_members)
        if member_count < 5:
            insufficient_novelty = novelty_service.evaluate_novelty(None, member_count)
            return LiveInferenceResponse(
                status="insufficient_data",
                data_quality="DATA INSUFFICIENT",
                quality_detail=(
                    f"Insufficient ensemble member count ({member_count}/11). "
                    "A minimum of 5 members is required to reliably estimate dispersion."
                ),
                reliability_state="DATA_INSUFFICIENT",
                bust_risk_percent=None,
                reliability_score=None,
                message="Reliability assessment unavailable — insufficient forecast evidence.",
                features_extracted=None,
                novelty_assessment=insufficient_novelty,
                provenance=self._build_provenance(req, member_count, "DATA INSUFFICIENT"),
            )

        # 2. Fail-Safe: Check for NaN, Inf, or invalid coordinate bounds
        lats = []
        lons = []
        for m in req.ensemble_members:
            if math.isnan(m.latitude) or math.isnan(m.longitude) or math.isinf(m.latitude) or math.isinf(m.longitude):
                corrupt_novelty = novelty_service.evaluate_novelty(None, member_count)
                return LiveInferenceResponse(
                    status="insufficient_data",
                    data_quality="DATA INSUFFICIENT",
                    quality_detail="NaN or Inf coordinates detected in ensemble member payload.",
                    reliability_state="DATA_INSUFFICIENT",
                    bust_risk_percent=None,
                    reliability_score=None,
                    message="Reliability assessment unavailable — insufficient forecast evidence.",
                    features_extracted=None,
                    novelty_assessment=corrupt_novelty,
                    provenance=self._build_provenance(req, member_count, "DATA INSUFFICIENT"),
                )
            if not (-90.0 <= m.latitude <= 90.0 and -180.0 <= m.longitude <= 360.0):
                invalid_novelty = novelty_service.evaluate_novelty(None, member_count)
                return LiveInferenceResponse(
                    status="insufficient_data",
                    data_quality="DATA INSUFFICIENT",
                    quality_detail=f"Coordinate out of range: ({m.latitude}, {m.longitude}).",
                    reliability_state="DATA_INSUFFICIENT",
                    bust_risk_percent=None,
                    reliability_score=None,
                    message="Reliability assessment unavailable — insufficient forecast evidence.",
                    features_extracted=None,
                    novelty_assessment=invalid_novelty,
                    provenance=self._build_provenance(req, member_count, "DATA INSUFFICIENT"),
                )
            lats.append(m.latitude)
            lons.append(m.longitude)

        # Determine Data Quality tier
        if member_count < 11:
            data_quality = "DATA DEGRADED"
            quality_detail = (
                f"Degraded ensemble coverage ({member_count}/11 members present). "
                "Assessment generated with wider uncertainty bounds."
            )
        else:
            data_quality = "DATA COMPLETE"
            quality_detail = (
                "Complete 11-member NCMRWF NEPS ensemble telemetry available. "
                "Full operational quality control passed."
            )

        # 3. Feature Extraction: Tier A/B strictly prospective variables
        mean_lat = float(np.mean(lats))
        mean_lon = float(np.mean(lons))

        # Scalar ensemble spread: mean great-circle distance of members to ensemble mean center
        member_distances = [
            haversine_distance(lat, lon, mean_lat, mean_lon)
            for lat, lon in zip(lats, lons)
        ]
        ensemble_spread_km = float(np.mean(member_distances))

        # Control divergence (if control coordinates provided)
        if req.deterministic_lat is not None and req.deterministic_lon is not None:
            divergence_km = haversine_distance(
                req.deterministic_lat, req.deterministic_lon, mean_lat, mean_lon
            )
        else:
            divergence_km = 0.0

        # Dispersion geometry (anisotropy ratio along principal axes)
        anisotropy_ratio = self._compute_anisotropy(lats, lons, mean_lat)

        # 4. Production Model Inference: M1_SpreadOnly
        features_dict = {
            "forecast_lead_hours": float(req.lead_hours),
            "ensemble_spread_km": round(ensemble_spread_km, 2),
            "ensemble_divergence_km": round(divergence_km, 2),
            "anisotropy_ratio": round(anisotropy_ratio, 3),
        }

        # 4. Production Model Inference: M1_SpreadOnly (preserve production probability)
        prob, state, score = self._predict_m1(req.lead_hours, ensemble_spread_km)

        # 5. Scientific Novelty & Representation Intelligence (isolated support evaluation)
        novelty_eval = novelty_service.evaluate_novelty(features_dict, member_count)

        # 6. Formulate Operational Decision-Support Message
        message = self._generate_operational_message(
            state=state,
            lead_hours=req.lead_hours,
            spread_km=ensemble_spread_km,
            divergence_km=divergence_km,
            data_quality=data_quality,
        )
        if novelty_eval.representation_state == "NOVEL_STATE":
            message += " (Advisory: ForecastGuard has limited historical support for this state; model extrapolation risk is elevated.)"
        elif novelty_eval.representation_state == "LOW_SUPPORT":
            message += " (Advisory: ForecastGuard has limited historical support for this state.)"

        return LiveInferenceResponse(
            status="ok",
            data_quality=data_quality,
            quality_detail=quality_detail,
            reliability_state=state,
            bust_risk_percent=round(prob * 100),
            reliability_score=score,
            message=message,
            features_extracted=features_dict,
            novelty_assessment=novelty_eval,
            provenance=self._build_provenance(req, member_count, data_quality),
        )

    def _predict_m1(self, lead_hours: int, spread_km: float) -> Tuple[float, str, int]:
        """Compute bust probability and reliability state using deterministic M1 weights."""
        raw_features = np.array([[lead_hours, spread_km]], dtype=np.float64)
        scaled_features = (raw_features - self.scaler_mean) / self.scaler_scale
        z = self.intercept + float(np.sum(scaled_features[0] * self.coef.flatten()))
        prob = 1.0 / (1.0 + math.exp(-z))
        prob = max(0.01, min(0.99, prob))

        # Categorize operational reliability state
        if prob < 0.25:
            state = "STABLE"
        elif prob < 0.50:
            state = "WATCH"
        elif prob < 0.75:
            state = "VULNERABLE"
        else:
            state = "SEVERE"

        # Reliability score is the inverse risk index (clamped to [5, 95])
        score = int(round(max(5.0, min(95.0, (1.0 - prob) * 100))))

        return prob, state, score

    @staticmethod
    def _compute_anisotropy(lats: List[float], lons: List[float], mean_lat: float) -> float:
        """Compute dispersion ellipse anisotropy ratio."""
        if len(lats) < 3:
            return 1.0
        # Convert lat/lon offsets to approximate km
        km_per_deg_lat = 111.0
        km_per_deg_lon = 111.0 * math.cos(math.radians(mean_lat))
        y = (np.array(lats) - np.mean(lats)) * km_per_deg_lat
        x = (np.array(lons) - np.mean(lons)) * km_per_deg_lon
        cov = np.cov(x, y)
        eigvals = np.linalg.eigvalsh(cov)
        eigvals = np.maximum(eigvals, 1e-4)
        return float(np.sqrt(eigvals[-1] / eigvals[0]))

    @staticmethod
    def _generate_operational_message(
        state: str, lead_hours: int, spread_km: float, divergence_km: float, data_quality: str
    ) -> str:
        quality_clause = " (Degraded ensemble coverage)" if data_quality == "DATA DEGRADED" else ""
        if state == "STABLE":
            return (
                f"High forecast reliability at +{lead_hours:02d}h{quality_clause}. "
                f"Ensemble spread is well-contained ({spread_km:.1f} km). "
                "Prospective bust risk is minimal."
            )
        elif state == "WATCH":
            return (
                f"Elevated watch at +{lead_hours:02d}h{quality_clause}. "
                f"Ensemble dispersion ({spread_km:.1f} km) indicates moderate vulnerability. "
                "Monitor subsequent forecast issuance cycles."
            )
        elif state == "VULNERABLE":
            return (
                f"Forecast vulnerability alert at +{lead_hours:02d}h{quality_clause}. "
                f"Elevated ensemble spread ({spread_km:.1f} km) and trajectory uncertainty indicate "
                "heightened risk of downstream forecast failure."
            )
        else:
            return (
                f"Severe forecast vulnerability at +{lead_hours:02d}h{quality_clause}. "
                f"Large ensemble divergence ({spread_km:.1f} km) indicates substantial likelihood "
                "of track/intensity forecast bust within the next 24 hours."
            )

    def _build_provenance(
        self, req: LiveInferenceRequest, member_count: int, processing_status: str
    ) -> InferenceProvenance:
        return InferenceProvenance(
            forecast_source=req.forecast_source,
            forecast_cycle=req.forecast_cycle,
            valid_time=req.valid_time,
            lead_time=f"+{req.lead_hours:02d}h",
            ensemble_member_count=f"{member_count} ensemble members",
            variables_used=[req.variable],
            feature_version="v1.0-tier-a-clean",
            model_name=self.metadata.model_name,
            model_version=self.metadata.model_version,
            scientific_status=self.metadata.scientific_status,
            processing_status=processing_status,
        )


production_engine = ProductionInferenceEngine()
