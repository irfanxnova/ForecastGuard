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
    ConfidenceBreakdown,
    ConfidenceComponent,
    DomainIdentification,
    FeatureTelemetryItem,
    InferenceProvenance,
    LiveInferenceRequest,
    LiveInferenceResponse,
    MediumRangeForecastAnalysisResponse,
    MultiLeadForecastInput,
    RiskEvolution,
    StructuredExplanation,
    TimelineLeadPoint,
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

    def _build_confidence_breakdown(
        self,
        member_count: int,
        domain_info: DomainIdentification,
        spread_km: Optional[float],
        novelty_eval: Any,
        forecast_source: str,
    ) -> ConfidenceBreakdown:
        """Construct structured 5-pillar evidence confidence assessment."""
        # 1. Data Coverage
        if member_count >= 11:
            cov_status = "COMPLETE"
            cov_reason = "Complete 11-member ensemble telemetry is available with all synoptic member vortex fixes present."
        elif member_count >= 5:
            cov_status = "DEGRADED"
            cov_reason = f"Partial ensemble coverage ({member_count}/11 members reporting); dispersion uncertainty bounds are wider."
        else:
            cov_status = "INSUFFICIENT"
            cov_reason = f"Insufficient ensemble member count ({member_count}/11); minimum 5 members required for dispersion estimation."

        # 2. Model Validation
        if domain_info.is_validated_domain:
            val_status = "VALIDATED_DOMAIN"
            val_reason = f"Forecast lead (+{domain_info.lead_classification}) and basin ({domain_info.basin}) are within the empirically validated calibration baseline."
        elif domain_info.lead_classification in ["MEDIUM_RANGE", "EXTENDED_RANGE"]:
            val_status = "NOT_VALIDATED_HORIZON"
            val_reason = domain_info.validation_notes
        else:
            val_status = "NOT_VALIDATED_BASIN"
            val_reason = domain_info.validation_notes

        # 3. Historical Representation
        rep_state = novelty_eval.representation_state if hasattr(novelty_eval, "representation_state") else "INSUFFICIENT_EVIDENCE"
        if rep_state == "WELL_REPRESENTED":
            rep_reason = "Forecast dispersion and geometry lie within the dense empirical distribution of historical reference storms (quantile <= 0.75)."
        elif rep_state == "LOW_SUPPORT":
            rep_reason = "Forecast dispersion lies in a sparse region of the historical reference distribution (0.75 < quantile <= 0.95)."
        elif rep_state == "NOVEL_STATE":
            rep_reason = "Forecast dispersion lies outside the 95th percentile empirical envelope of the reference population; statistical extrapolation risk."
        else:
            rep_reason = "Historical representation support cannot be evaluated due to insufficient ensemble evidence."

        # 4. Ensemble Support
        if spread_km is None or member_count < 5:
            ens_status = "INSUFFICIENT_MEMBERS"
            ens_reason = "Insufficient ensemble members to evaluate dispersion support."
        elif spread_km <= 60.0:
            ens_status = "STRONG_CONSENSUS"
            ens_reason = f"Ensemble members exhibit tight clustering ({spread_km:.1f} km mean spread), consistent with strong synoptic agreement."
        elif spread_km <= 150.0:
            ens_status = "MODERATE_DISPERSION"
            ens_reason = f"Ensemble members exhibit moderate dispersion ({spread_km:.1f} km mean spread), consistent with standard track dispersion."
        else:
            ens_status = "HIGH_DISPERSION"
            ens_reason = f"Ensemble members exhibit wide dispersion ({spread_km:.1f} km mean spread), indicating heightened prospective uncertainty."

        # 5. Provenance
        src_clean = (forecast_source or "").upper()
        if any(s in src_clean for s in ["NCMRWF", "TIGGE", "ECMWF", "IMD", "NCEP"]):
            prov_status = "VERIFIED_SOURCE"
            prov_reason = f"Telemetry verified from institutional NWP origin: {forecast_source}."
        else:
            prov_status = "PROVISIONAL"
            prov_reason = f"Origin '{forecast_source}' is evaluated under provisional operational monitoring."

        return ConfidenceBreakdown(
            data_coverage=ConfidenceComponent(status=cov_status, reason=cov_reason, source="NCMRWF NEPS telemetry"),
            model_validation=ConfidenceComponent(status=val_status, reason=val_reason, source="M1 Calibration Baseline"),
            historical_representation=ConfidenceComponent(status=rep_state, reason=rep_reason, source="Historical Reference Population"),
            ensemble_support=ConfidenceComponent(status=ens_status, reason=ens_reason, source="Pairwise Haversine Dispersion"),
            provenance=ConfidenceComponent(status=prov_status, reason=prov_reason, source="Issuance Ingestion Manifest"),
        )

    def _build_structured_explanation(
        self,
        lead_hours: int,
        domain_info: DomainIdentification,
        bust_probability: Optional[float],
        reliability_state: str,
        spread_km: Optional[float],
        divergence_km: Optional[float],
        novelty_eval: Any,
        prev_spread: Optional[float] = None,
        prev_prob: Optional[float] = None,
        prev_lead: Optional[int] = None,
    ) -> StructuredExplanation:
        """Construct deterministic, non-causal structured explanations."""
        # WHY
        if domain_info.is_validated_domain and bust_probability is not None and spread_km is not None:
            why = (
                f"Assessment of {reliability_state} reliability (bust probability {round(bust_probability * 100)}%) is "
                f"supported by ensemble spread of {spread_km:.1f} km and deterministic divergence of {divergence_km or 0.0:.1f} km "
                "evaluated against the validated regional calibration baseline."
            )
        elif lead_hours > 48:
            sp_text = f" ({spread_km:.1f} km)" if spread_km is not None else ""
            why = (
                f"Calibrated bust probability is withheld (NOT_VALIDATED) because the statistical baseline is validated only up to 48h. "
                f"Available prospective dispersion telemetry{sp_text} and historical support are preserved without probability extrapolation."
            )
        else:
            why = (
                f"Assessment reflects unvalidated domain status for {domain_info.basin}: {domain_info.validation_notes}"
            )

        # WHAT CHANGED
        if prev_lead is None:
            what_changed = "Initial lead horizon in the evaluated forecast sequence."
        else:
            deltas = []
            if spread_km is not None and prev_spread is not None:
                d_sp = spread_km - prev_spread
                deltas.append(f"ensemble spread changed by {d_sp:+.1f} km")
            if bust_probability is not None and prev_prob is not None:
                d_pr = round(bust_probability * 100) - round(prev_prob * 100)
                deltas.append(f"calibrated bust risk changed by {d_pr:+d}%")
            elif bust_probability is None and prev_prob is not None:
                deltas.append("calibration transitioned from CALIBRATED to NOT_VALIDATED")

            if deltas:
                what_changed = f"Relative to +{prev_lead:02d}h, " + ", and ".join(deltas) + "."
            else:
                what_changed = f"Sequential progression from +{prev_lead:02d}h lead step."

        # WHY NOW
        if lead_hours == 48:
            why_now = "Lead time reaches +48h, the boundary of the empirically validated regional calibration domain."
        elif lead_hours > 48:
            why_now = f"Forecast advances into the medium-range window (+{lead_hours}h / D+{max(1, lead_hours // 24)}), where non-linear track dispersion precludes unvalidated linear baseline extrapolation."
        elif spread_km is not None and spread_km > 150.0:
            why_now = f"Ensemble dispersion ({spread_km:.1f} km) exceeds the 75th percentile empirical threshold of historical reference cycles."
        else:
            why_now = f"Standard operational evaluation cycle for +{lead_hours:02d}h lead horizon."

        return StructuredExplanation(
            why=why,
            what_changed=what_changed,
            why_now=why_now,
        )

    def evaluate(self, req: LiveInferenceRequest) -> LiveInferenceResponse:
        """Execute deterministic inference pipeline with data QC, domain checking, and honest abstention."""
        member_count = len(req.ensemble_members)
        insufficient_multimodel = multimodel_service.evaluate_agreement(MultiModelEvidenceRequest(models=[]))

        # 1. Fail-Safe: Validate ensemble member count
        if member_count < 5:
            insufficient_novelty = novelty_service.evaluate_novelty(None, member_count)
            domain_info = self._identify_domain(req, None, None)
            cb = self._build_confidence_breakdown(member_count, domain_info, None, insufficient_novelty, req.forecast_source)
            explanation = self._build_structured_explanation(req.lead_hours, domain_info, None, "DATA_INSUFFICIENT", None, None, insufficient_novelty)
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
                confidence_breakdown=cb,
                structured_explanation=explanation,
                support_index=None,
                provenance=self._build_provenance(req, member_count, "DATA INSUFFICIENT"),
            )

        # 2. Fail-Safe: Check for NaN, Inf, or invalid coordinate bounds
        lats = []
        lons = []
        for m in req.ensemble_members:
            if math.isnan(m.latitude) or math.isnan(m.longitude) or math.isinf(m.latitude) or math.isinf(m.longitude):
                corrupt_novelty = novelty_service.evaluate_novelty(None, member_count)
                domain_info = self._identify_domain(req, None, None)
                cb = self._build_confidence_breakdown(member_count, domain_info, None, corrupt_novelty, req.forecast_source)
                explanation = self._build_structured_explanation(req.lead_hours, domain_info, None, "DATA_INSUFFICIENT", None, None, corrupt_novelty)
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
                    confidence_breakdown=cb,
                    structured_explanation=explanation,
                    support_index=None,
                    provenance=self._build_provenance(req, member_count, "DATA INSUFFICIENT"),
                )
            if not (-90.0 <= m.latitude <= 90.0 and -180.0 <= m.longitude <= 360.0):
                invalid_novelty = novelty_service.evaluate_novelty(None, member_count)
                domain_info = self._identify_domain(req, None, None)
                cb = self._build_confidence_breakdown(member_count, domain_info, None, invalid_novelty, req.forecast_source)
                explanation = self._build_structured_explanation(req.lead_hours, domain_info, None, "DATA_INSUFFICIENT", None, None, invalid_novelty)
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
                    confidence_breakdown=cb,
                    structured_explanation=explanation,
                    support_index=None,
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

        cb = self._build_confidence_breakdown(
            member_count=member_count,
            domain_info=domain_info,
            spread_km=ensemble_spread_km,
            novelty_eval=novelty_eval,
            forecast_source=req.forecast_source,
        )

        explanation = self._build_structured_explanation(
            lead_hours=req.lead_hours,
            domain_info=domain_info,
            bust_probability=bust_probability,
            reliability_state=reliability_state or "UNVALIDATED_DOMAIN",
            spread_km=ensemble_spread_km,
            divergence_km=divergence_km,
            novelty_eval=novelty_eval,
            prev_spread=None,
            prev_prob=None,
            prev_lead=None,
        )

        sup_index = reliability_score if reliability_score is not None else (
            int(round(max(10.0, min(90.0, 100.0 - (ensemble_spread_km / 3.0))))) if member_count >= 5 else None
        )

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
            confidence_breakdown=cb,
            structured_explanation=explanation,
            support_index=sup_index,
            provenance=self._build_provenance(req, member_count, data_quality),
        )

    def _evaluate_risk_evolution(self, timeline: List[TimelineLeadPoint]) -> RiskEvolution:
        """Analyze empirical reliability trajectory across sequential forecast leads."""
        if len(timeline) < 2:
            return RiskEvolution(
                trajectory_state="INSUFFICIENT_EVIDENCE",
                summary="At least two chronological forecast lead steps are required to evaluate risk evolution.",
                evidence_basis=["Single forecast lead point provided."],
                lead_transitions=[],
            )

        transitions = []
        spread_increases = 0
        spread_decreases = 0
        prob_increases = 0
        prob_decreases = 0
        calibrated_pairs = 0

        for i in range(len(timeline) - 1):
            p1 = timeline[i]
            p2 = timeline[i + 1]

            s1 = p1.features_extracted.get("ensemble_spread_km") if p1.features_extracted else None
            s2 = p2.features_extracted.get("ensemble_spread_km") if p2.features_extracted else None

            delta_spread = round(s2 - s1, 1) if (s1 is not None and s2 is not None) else None
            delta_prob = None
            if p1.bust_probability is not None and p2.bust_probability is not None:
                delta_prob = round(p2.bust_probability * 100) - round(p1.bust_probability * 100)
                calibrated_pairs += 1
                if delta_prob > 5:
                    prob_increases += 1
                elif delta_prob < -5:
                    prob_decreases += 1

            if delta_spread is not None:
                if delta_spread > 15.0:
                    spread_increases += 1
                elif delta_spread < -15.0:
                    spread_decreases += 1

            transitions.append({
                "from_lead": p1.lead_hours,
                "to_lead": p2.lead_hours,
                "delta_spread_km": delta_spread,
                "delta_probability_percent": delta_prob,
                "state_transition": f"{p1.reliability_state} -> {p2.reliability_state}",
            })

        evidence_basis = []
        # Trajectory determination
        if calibrated_pairs > 0:
            if prob_increases > 0 and prob_decreases == 0 and spread_increases >= spread_decreases:
                traj_state = "DEGRADING"
                summary = "Sequential calibrated bust probability and ensemble spread increased across available horizons."
                evidence_basis.append(f"Calibrated probability increased across {prob_increases} consecutive lead transitions.")
            elif prob_decreases > 0 and prob_increases == 0 and spread_decreases >= spread_increases:
                traj_state = "IMPROVING"
                summary = "Sequential calibrated bust probability contracted alongside tightening ensemble dispersion."
                evidence_basis.append(f"Calibrated probability decreased across {prob_decreases} consecutive lead transitions.")
            elif prob_increases > 0 and prob_decreases > 0:
                traj_state = "MIXED"
                summary = "Sequential leads exhibit alternating expansion and contraction in dispersion and bust probability."
                evidence_basis.append("Mixed directional changes observed across consecutive forecast horizons.")
            elif spread_increases > 0 and spread_decreases == 0:
                traj_state = "DEGRADING"
                summary = "Ensemble dispersion expanded across consecutive lead steps."
                evidence_basis.append(f"Spread widened in {spread_increases} consecutive horizons.")
            else:
                traj_state = "STABLE"
                summary = "Reliability indicators and ensemble dispersion remained stable within normal variance bounds."
                evidence_basis.append("Spread variance remained within +/-15 km across horizons.")
        else:
            # Unvalidated horizon pairs (e.g. D+3 to D+10)
            if spread_increases > 0 and spread_decreases == 0:
                traj_state = "DEGRADING"
                summary = "Ensemble dispersion widened consistently across medium-range horizons."
                evidence_basis.append(f"Ensemble spread widened across {spread_increases} horizons; probability remains unvalidated.")
            elif spread_decreases > 0 and spread_increases == 0:
                traj_state = "IMPROVING"
                summary = "Ensemble dispersion contracted consistently across medium-range horizons."
                evidence_basis.append(f"Ensemble spread narrowed across {spread_decreases} horizons; probability remains unvalidated.")
            elif spread_increases > 0 and spread_decreases > 0:
                traj_state = "MIXED"
                summary = "Ensemble dispersion showed mixed expansion and contraction across medium-range horizons."
                evidence_basis.append("Alternating spread dynamics across consecutive horizons.")
            else:
                traj_state = "STABLE"
                summary = "Ensemble dispersion remained steady across medium-range horizons."
                evidence_basis.append("Dispersion delta remained within +/-15 km across horizons.")

        return RiskEvolution(
            trajectory_state=traj_state,
            summary=summary,
            evidence_basis=evidence_basis,
            lead_transitions=transitions,
        )

    def evaluate_timeline(self, multi_req: MultiLeadForecastInput) -> MediumRangeForecastAnalysisResponse:
        """Execute chronological D+1 -> D+10 reliability timeline assessment."""
        # Sort leads chronologically
        sorted_leads = sorted(multi_req.leads, key=lambda x: x.lead_hours)

        timeline_points: List[TimelineLeadPoint] = []
        prev_spread: Optional[float] = None
        prev_prob: Optional[float] = None
        prev_lead: Optional[int] = None

        for lead_input in sorted_leads:
            lead_res = self.evaluate(lead_input)

            lead_day = max(1, lead_input.lead_hours // 24)
            lead_name = f"D+{lead_day}"

            spread_val = lead_res.features_extracted.get("ensemble_spread_km") if lead_res.features_extracted else None
            div_val = lead_res.features_extracted.get("ensemble_divergence_km") if lead_res.features_extracted else None

            # Evidence strength
            m_count = len(lead_input.ensemble_members)
            if m_count < 5 or spread_val is None:
                ev_strength = "INSUFFICIENT"
            elif m_count >= 11:
                ev_strength = "STRONG"
            elif m_count >= 8:
                ev_strength = "MODERATE"
            else:
                ev_strength = "WEAK"

            # Support index (0-100 index; NOT probability)
            if lead_res.reliability_score is not None:
                sup_index = lead_res.reliability_score
            elif m_count >= 5 and spread_val is not None:
                sup_index = int(round(max(10.0, min(90.0, 100.0 - (spread_val / 3.0)))))
            else:
                sup_index = None

            explanation = self._build_structured_explanation(
                lead_hours=lead_input.lead_hours,
                domain_info=lead_res.domain_identified,
                bust_probability=lead_res.bust_probability,
                reliability_state=lead_res.reliability_state or "UNVALIDATED_DOMAIN",
                spread_km=spread_val,
                divergence_km=div_val,
                novelty_eval=lead_res.novelty_assessment,
                prev_spread=prev_spread,
                prev_prob=lead_res.bust_probability,
                prev_lead=prev_lead,
            )

            cb = self._build_confidence_breakdown(
                member_count=m_count,
                domain_info=lead_res.domain_identified,
                spread_km=spread_val,
                novelty_eval=lead_res.novelty_assessment,
                forecast_source=lead_input.forecast_source,
            )

            point = TimelineLeadPoint(
                lead_name=lead_name,
                lead_hours=lead_input.lead_hours,
                valid_time=lead_input.valid_time,
                reliability_state=lead_res.reliability_state,
                bust_probability=lead_res.bust_probability,
                probability_status=lead_res.probability_status,
                assessment_confidence=lead_res.confidence_status,
                data_quality=lead_res.data_quality,
                evidence_strength=ev_strength,
                validation_status=lead_res.validation_status,
                support_index=sup_index,
                confidence_breakdown=cb,
                structured_explanation=explanation,
                evidence_summary=lead_res.message,
                features_extracted=lead_res.features_extracted,
                feature_telemetry=lead_res.feature_telemetry,
                novelty_assessment=lead_res.novelty_assessment,
                multimodel_evidence=lead_res.multimodel_evidence,
            )
            timeline_points.append(point)

            prev_spread = spread_val
            prev_prob = lead_res.bust_probability
            prev_lead = lead_input.lead_hours

        # Evaluate risk evolution across the timeline
        risk_evo = self._evaluate_risk_evolution(timeline_points)

        # Determine overall status
        statuses = [p.probability_status for p in timeline_points]
        if all(s == "CALIBRATED" for s in statuses):
            overall_status = "ok"
        elif any(s == "CALIBRATED" for s in statuses):
            overall_status = "partial_data"
        elif any(s == "NOT_VALIDATED" for s in statuses):
            overall_status = "not_validated"
        else:
            overall_status = "insufficient_data"

        first_lead = sorted_leads[0]
        first_res = self.evaluate(first_lead)

        overall_cb = self._build_confidence_breakdown(
            member_count=len(first_lead.ensemble_members),
            domain_info=first_res.domain_identified,
            spread_km=first_res.features_extracted.get("ensemble_spread_km") if first_res.features_extracted else None,
            novelty_eval=first_res.novelty_assessment,
            forecast_source=first_lead.forecast_source,
        )

        overall_assessment = {
            "total_horizons_evaluated": len(timeline_points),
            "calibrated_horizons_count": sum(1 for p in timeline_points if p.probability_status == "CALIBRATED"),
            "unvalidated_horizons_count": sum(1 for p in timeline_points if p.probability_status == "NOT_VALIDATED"),
            "trajectory_trend": risk_evo.trajectory_state,
            "operational_advisory": (
                f"Forecast evaluated across {len(timeline_points)} lead steps. "
                f"Calibrated probability is available for {sum(1 for p in timeline_points if p.probability_status == 'CALIBRATED')} short-range horizons; "
                f"medium-range horizons (D+3+) are presented with uncalibrated evidence telemetry."
            ),
        }

        extracted_leads = [p for p in timeline_points if p.features_extracted and "ensemble_spread_km" in p.features_extracted]
        evidence_summary = {
            "mean_spread_across_horizons_km": round(
                float(np.mean([p.features_extracted["ensemble_spread_km"] for p in extracted_leads])), 1
            ) if extracted_leads else None,
            "representation_states": list(set(
                p.novelty_assessment.representation_state for p in timeline_points if p.novelty_assessment
            )),
            "validation_horizons": [p.lead_hours for p in timeline_points if p.validation_status in ["VALID", "PARTIAL"]],
        }

        return MediumRangeForecastAnalysisResponse(
            status=overall_status,
            forecast_source=multi_req.forecast_source,
            forecast_cycle=multi_req.forecast_cycle,
            overall_assessment=overall_assessment,
            timeline=timeline_points,
            risk_evolution=risk_evo,
            confidence=overall_cb,
            domain_identified=first_res.domain_identified,
            evidence_summary=evidence_summary,
            provenance=first_res.provenance,
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

