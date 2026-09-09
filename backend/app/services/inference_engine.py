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
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from backend.app.schemas.inference import (
    CanonicalForecastInput,
    DomainIdentification,
    FeatureTelemetryItem,
    InferenceProvenance,
    LiveInferenceRequest,
    LiveInferenceResponse,
)
from backend.app.services.model_config import (
    M1_PARAMETERS,
    M1_SPREAD_ONLY_METADATA,
)
from backend.app.services.novelty_service import novelty_service
from backend.app.services.multimodel_service import multimodel_service
from backend.app.schemas.multimodel import MultiModelEvidenceRequest
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

    def _identify_domain(
        self, req: CanonicalForecastInput, mean_lat: Optional[float], mean_lon: Optional[float]
    ) -> DomainIdentification:
        """Classify spatial basin, lead horizon, and model calibration domain support."""
        # 1. Spatial Basin Classification
        target_lat = mean_lat if mean_lat is not None else (req.latitude or (req.deterministic_lat if req.deterministic_lat is not None else 15.0))
        target_lon = mean_lon if mean_lon is not None else (req.longitude or (req.deterministic_lon if req.deterministic_lon is not None else 85.0))

        # Check explicit region string if provided
        region_str = req.region.upper() if req.region else ""
        if "BOB" in region_str or "BAY OF BENGAL" in region_str:
            basin = "Bay of Bengal"
            region_name = req.region or "MAR_BOB"
            basin_valid = True
        elif "AS" in region_str or "ARABIAN" in region_str:
            basin = "Arabian Sea"
            region_name = req.region or "MAR_AS"
            basin_valid = True
        elif "NATL" in region_str or "ATLANTIC" in region_str:
            basin = "North Atlantic"
            region_name = req.region or "NATL"
            basin_valid = False
        elif 5.0 <= target_lat <= 30.0 and 48.0 <= target_lon <= 100.0:
            basin_valid = True
            if target_lon < 77.5:
                basin = "Arabian Sea"
                region_name = req.region or "MAR_AS"
            else:
                basin = "Bay of Bengal"
                region_name = req.region or "MAR_BOB"
        else:
            basin = "North Atlantic / Extra-Basin" if (-85.0 <= target_lon <= 0.0 and 10.0 <= target_lat <= 60.0) else "Global / Extra-Basin"
            region_name = req.region or "EXTRA_BASIN"
            basin_valid = False

        # 2. Lead Time Horizon Classification
        lead = req.lead_hours
        if lead < 6:
            lead_classification = "NOWCAST"
            lead_valid = False
        elif 6 <= lead <= 48:
            lead_classification = "SHORT_RANGE"
            lead_valid = True
        elif 48 < lead <= 120:
            lead_classification = "MEDIUM_RANGE"
            lead_valid = False
        else:
            lead_classification = "EXTENDED_RANGE"
            lead_valid = False

        # 3. Variable Validation
        var_lower = (req.variable or "").lower()
        supported_var_keywords = ["msl", "pressure", "vortex", "cyclone", "track", "mean sea level"]
        var_valid = any(k in var_lower for k in supported_var_keywords)

        # 4. Synthesize Domain Support
        is_validated = basin_valid and lead_valid and var_valid

        if is_validated:
            validation_notes = (
                f"Validated for {basin} tropical cyclone track dispersion at +{lead:02d}h lead."
            )
        elif not lead_valid and lead > 48:
            validation_notes = (
                f"Calibrated bust probability is not validated for lead times > 48h (D+3 to D+10; current={lead}h). "
                "Track error growth and dispersion become non-linear; extrapolation of M1 baseline is scientifically invalid."
            )
        elif not lead_valid and lead < 6:
            validation_notes = (
                f"Lead time +{lead}h is classified as nowcast and is not covered by the 6h-48h calibrated baseline."
            )
        elif not basin_valid:
            validation_notes = (
                f"Spatial basin '{basin}' (lat {target_lat:.1f}, lon {target_lon:.1f}) falls outside "
                "the validated North Indian Ocean basin (5°N-30°N, 48°E-100°E). Model weights are not regionalized for this domain."
            )
        elif not var_valid:
            validation_notes = (
                f"Variable '{req.variable}' does not have a calibrated bust baseline in ForecastGuard."
            )
        else:
            validation_notes = "Domain is outside the validated operational baseline."

        return DomainIdentification(
            basin=basin,
            region=region_name,
            lead_classification=lead_classification,
            is_validated_domain=is_validated,
            validation_notes=validation_notes,
        )

    def evaluate(self, req: LiveInferenceRequest) -> LiveInferenceResponse:
        """Execute deterministic inference pipeline with data QC, domain checking, and honest abstention."""
        member_count = len(req.ensemble_members)
        insufficient_multimodel = multimodel_service.evaluate_agreement(MultiModelEvidenceRequest(models=[]))

        # 1. Fail-Safe: Validate ensemble member count
        if member_count < 5:
            insufficient_novelty = novelty_service.evaluate_novelty(None, member_count)
            domain_info = self._identify_domain(req, None, None)
            return LiveInferenceResponse(
                status="insufficient_data",
                validation_status="INSUFFICIENT",
                data_quality="DATA INSUFFICIENT",
                quality_detail=(
                    f"Insufficient ensemble member count ({member_count}/11). "
                    "A minimum of 5 members is required to reliably estimate dispersion."
                ),
                domain_identified=domain_info,
                reliability_state="DATA_INSUFFICIENT",
                bust_probability=None,
                probability_status="INSUFFICIENT_EVIDENCE",
                confidence_status="INSUFFICIENT",
                bust_risk_percent=None,
                reliability_score=None,
                message="Reliability assessment unavailable — insufficient forecast evidence.",
                features_extracted=None,
                feature_telemetry=None,
                novelty_assessment=insufficient_novelty,
                multimodel_evidence=insufficient_multimodel,
                model_status=self.metadata.model_name,
                calibration_status="NOT_VALIDATED",
                verification_status="PENDING_VERIFICATION",
                provenance=self._build_provenance(req, member_count, "DATA INSUFFICIENT"),
            )

        # 2. Fail-Safe: Check for NaN, Inf, or invalid coordinate bounds
        lats = []
        lons = []
        for m in req.ensemble_members:
            if math.isnan(m.latitude) or math.isnan(m.longitude) or math.isinf(m.latitude) or math.isinf(m.longitude):
                corrupt_novelty = novelty_service.evaluate_novelty(None, member_count)
                domain_info = self._identify_domain(req, None, None)
                return LiveInferenceResponse(
                    status="insufficient_data",
                    validation_status="INSUFFICIENT",
                    data_quality="DATA INSUFFICIENT",
                    quality_detail="NaN or Inf coordinates detected in ensemble member payload.",
                    domain_identified=domain_info,
                    reliability_state="DATA_INSUFFICIENT",
                    bust_probability=None,
                    probability_status="INSUFFICIENT_EVIDENCE",
                    confidence_status="INSUFFICIENT",
                    bust_risk_percent=None,
                    reliability_score=None,
                    message="Reliability assessment unavailable — insufficient forecast evidence.",
                    features_extracted=None,
                    feature_telemetry=None,
                    novelty_assessment=corrupt_novelty,
                    multimodel_evidence=insufficient_multimodel,
                    model_status=self.metadata.model_name,
                    calibration_status="NOT_VALIDATED",
                    verification_status="PENDING_VERIFICATION",
                    provenance=self._build_provenance(req, member_count, "DATA INSUFFICIENT"),
                )
            if not (-90.0 <= m.latitude <= 90.0 and -180.0 <= m.longitude <= 360.0):
                invalid_novelty = novelty_service.evaluate_novelty(None, member_count)
                domain_info = self._identify_domain(req, None, None)
                return LiveInferenceResponse(
                    status="insufficient_data",
                    validation_status="INSUFFICIENT",
                    data_quality="DATA INSUFFICIENT",
                    quality_detail=f"Coordinate out of range: ({m.latitude}, {m.longitude}).",
                    domain_identified=domain_info,
                    reliability_state="DATA_INSUFFICIENT",
                    bust_probability=None,
                    probability_status="INSUFFICIENT_EVIDENCE",
                    confidence_status="INSUFFICIENT",
                    bust_risk_percent=None,
                    reliability_score=None,
                    message="Reliability assessment unavailable — insufficient forecast evidence.",
                    features_extracted=None,
                    feature_telemetry=None,
                    novelty_assessment=invalid_novelty,
                    multimodel_evidence=insufficient_multimodel,
                    model_status=self.metadata.model_name,
                    calibration_status="NOT_VALIDATED",
                    verification_status="PENDING_VERIFICATION",
                    provenance=self._build_provenance(req, member_count, "DATA INSUFFICIENT"),
                )
            lats.append(m.latitude)
            lons.append(m.longitude)

        # 3. Determine Data Quality tier
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

        # 4. Feature Extraction: Tier A/B strictly prospective variables
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

        features_dict = {
            "forecast_lead_hours": float(req.lead_hours),
            "ensemble_spread_km": round(ensemble_spread_km, 2),
            "ensemble_divergence_km": round(divergence_km, 2),
            "anisotropy_ratio": round(anisotropy_ratio, 3),
        }

        # 5. Domain Identification
        domain_info = self._identify_domain(req, mean_lat, mean_lon)

        # 6. Build Audited Feature Telemetry Records
        feature_telemetry = [
            FeatureTelemetryItem(
                name="ensemble_spread",
                value=round(ensemble_spread_km, 2),
                unit="km",
                source="NCMRWF NEPS pairwise haversine dispersion",
                availability="AVAILABLE",
                validation_status="VALIDATED" if domain_info.is_validated_domain else "UNVALIDATED",
            ),
            FeatureTelemetryItem(
                name="ensemble_divergence",
                value=round(divergence_km, 2),
                unit="km",
                source="Deterministic vs Ensemble Mean distance",
                availability="AVAILABLE" if req.deterministic_lat is not None else "UNAVAILABLE",
                validation_status="VALIDATED",
            ),
            FeatureTelemetryItem(
                name="dispersion_anisotropy",
                value=round(anisotropy_ratio, 3),
                unit="dimensionless",
                source="Principal axis eigenvalue covariance ratio",
                availability="AVAILABLE",
                validation_status="VALIDATED",
            ),
            FeatureTelemetryItem(
                name="active_ensemble_members",
                value=float(member_count),
                unit="members",
                source="Operational synoptic fixes",
                availability="AVAILABLE" if member_count == 11 else "DEGRADED",
                validation_status="VALIDATED",
            ),
        ]

        # 7. Scientific Novelty & Representation Intelligence
        novelty_eval = novelty_service.evaluate_novelty(features_dict, member_count)

        # 8. Confidence Status Assessment (disentangles evidence completeness from probability calibration)
        if not domain_info.is_validated_domain:
            # For unvalidated domains, bust probability is withheld, but evidence confidence reflects data completeness:
            confidence_status = "HIGH" if member_count == 11 else ("MODERATE" if member_count >= 5 else "INSUFFICIENT")
        elif novelty_eval.representation_state == "WELL_REPRESENTED":
            confidence_status = "HIGH" if member_count == 11 else "MODERATE"
        elif novelty_eval.representation_state == "LOW_SUPPORT":
            confidence_status = "MODERATE"
        elif novelty_eval.representation_state == "NOVEL_STATE":
            confidence_status = "LOW"
        else:
            confidence_status = "INSUFFICIENT"

        # 9. Multi-Model Consensus Evidence
        multimodel_eval = multimodel_service.evaluate_live_cyclone_fix(
            model_id=req.model or "NCMRWF_NEPS",
            center=req.forecast_source,
            initialization_time=req.forecast_cycle,
            forecast_lead_hours=req.lead_hours,
            valid_time=req.valid_time,
            latitude=mean_lat,
            longitude=mean_lon,
        )

        # 10. Probability Estimation vs Honest Abstention
        if domain_info.is_validated_domain:
            prob, state, score = self._predict_m1(req.lead_hours, ensemble_spread_km)
            bust_probability = round(prob, 4)
            bust_risk_percent = round(prob * 100)
            reliability_score = score
            probability_status = "CALIBRATED"
            calibration_status = "CALIBRATED"
            reliability_state = state
            validation_status = "VALID" if member_count == 11 else "PARTIAL"
            op_status = "ok"

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
        else:
            # Unvalidated domain: NEVER invent a probability
            bust_probability = None
            bust_risk_percent = None
            reliability_score = None
            probability_status = "NOT_VALIDATED"
            calibration_status = "NOT_VALIDATED"
            reliability_state = "UNVALIDATED_DOMAIN"
            validation_status = "NOT_VALIDATED"
            op_status = "not_validated"

            if req.lead_hours > 48:
                message = (
                    f"Forecast analysis completed for +{req.lead_hours:02d}h lead. "
                    "Calibrated bust probability is withheld (NOT_VALIDATED): "
                    f"{domain_info.validation_notes} Feature telemetry and novelty support are preserved."
                )
            else:
                message = (
                    f"Forecast analysis completed for domain '{domain_info.basin}'. "
                    "Calibrated bust probability is withheld (NOT_VALIDATED): "
                    f"{domain_info.validation_notes} Feature telemetry and novelty support are preserved."
                )

        ensemble_evidence = {
            "mean_latitude": round(mean_lat, 4),
            "mean_longitude": round(mean_lon, 4),
            "spread_km": round(ensemble_spread_km, 2),
            "divergence_km": round(divergence_km, 2),
            "anisotropy_ratio": round(anisotropy_ratio, 3),
            "member_count": member_count,
            "sample_bounding_box": {
                "min_lat": min(lats),
                "max_lat": max(lats),
                "min_lon": min(lons),
                "max_lon": max(lons),
            },
        }

        return LiveInferenceResponse(
            status=op_status,
            validation_status=validation_status,
            data_quality=data_quality,
            quality_detail=quality_detail,
            domain_identified=domain_info,
            reliability_state=reliability_state,
            bust_probability=bust_probability,
            probability_status=probability_status,
            confidence_status=confidence_status,
            bust_risk_percent=bust_risk_percent,
            reliability_score=reliability_score,
            message=message,
            features_extracted=features_dict,
            feature_telemetry=feature_telemetry,
            ensemble_evidence=ensemble_evidence,
            trajectory_evidence=None,
            environmental_evidence=None,
            historical_memory_evidence=None,
            novelty_assessment=novelty_eval,
            multimodel_evidence=multimodel_eval,
            model_status=self.metadata.model_name,
            calibration_status=calibration_status,
            verification_status="PENDING_VERIFICATION",
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

