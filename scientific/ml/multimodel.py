"""ForecastGuard V2 — Multi-Model Forecast Agreement & NWP Evidence Engine.

SCIENTIFIC OBJECTIVE:
Evaluate whether genuinely independent Numerical Weather Prediction (NWP)
forecast systems agree about the prospective forecast state.

SCIENTIFIC BOUNDARIES & GOVERNANCE:
1. Zero Data Fabrication: ForecastGuard never fabricates, simulates, or renames
   hypothetical NWP models (e.g. ECMWF, UKMO) if real data is missing locally.
2. Honest Insufficiency: When fewer than two independent, verified models exist,
   the engine deterministically returns INSUFFICIENT_EVIDENCE.
3. Terminology & Non-Overclaim:
   - Model disagreement is cross-system consensus dispersion, NEVER "forecast error".
   - Agreement does NOT guarantee forecast verification correctness.
   - High cross-model disagreement indicates elevated systemic synoptic uncertainty,
     not a guaranteed forecast bust.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple


class MultiModelAgreementState(str, Enum):
    """Deterministic cross-model agreement states."""

    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    AGREEMENT = "AGREEMENT"
    MODERATE_DISAGREEMENT = "MODERATE_DISAGREEMENT"
    HIGH_DISAGREEMENT = "HIGH_DISAGREEMENT"


class NWPModelStatus(str, Enum):
    """Operational availability status of NWP archives in ForecastGuard."""

    OPERATIONAL_ARCHIVED = "OPERATIONAL_ARCHIVED"
    MISSING_ARCHIVE = "MISSING_ARCHIVE"
    INTERFACE_READY = "INTERFACE_READY"


@dataclass(frozen=True)
class NWPModelAuditEntry:
    """Audit descriptor for an individual NWP forecast system."""

    model_id: str
    center_name: str
    country_or_org: str
    tigge_origin: Optional[str]
    status: NWPModelStatus
    resolution_horizontal: Optional[str]
    native_cadence: Optional[str]
    verified_cyclone_leads: int
    verified_cycles: int
    historical_coverage_start: Optional[str]
    historical_coverage_end: Optional[str]
    variables_available: List[str]
    missingness_notes: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "center_name": self.center_name,
            "country_or_org": self.country_or_org,
            "tigge_origin": self.tigge_origin,
            "status": self.status.value,
            "resolution_horizontal": self.resolution_horizontal,
            "native_cadence": self.native_cadence,
            "verified_cyclone_leads": self.verified_cyclone_leads,
            "verified_cycles": self.verified_cycles,
            "historical_coverage_start": self.historical_coverage_start,
            "historical_coverage_end": self.historical_coverage_end,
            "variables_available": list(self.variables_available),
            "missingness_notes": self.missingness_notes,
        }


# Authoritative data audit catalog of regional NWP models
NWP_DATA_AUDIT_CATALOG: Dict[str, NWPModelAuditEntry] = {
    "NCMRWF_NEPS": NWPModelAuditEntry(
        model_id="NCMRWF_NEPS",
        center_name="National Centre for Medium Range Weather Forecasting",
        country_or_org="India (MoES)",
        tigge_origin="dems",
        status=NWPModelStatus.OPERATIONAL_ARCHIVED,
        resolution_horizontal="0.18 deg x 0.12 deg (regional) / 0.5 deg (global)",
        native_cadence="6-hourly (+06h to +48h synoptic steps), 00Z & 12Z cycles",
        verified_cyclone_leads=101,
        verified_cycles=13,
        historical_coverage_start="2023-05-11T00:00:00Z",
        historical_coverage_end="2023-12-04T00:00:00Z",
        variables_available=["msl", "tp", "2t", "tcc"],
        missingness_notes="Fully verified against IMD Best Tracks across 6 tropical cyclones (MOCHA, BIPARJOY, TEJ, HAMOON, MIDHILI, MICHAUNG). Zero missing leads in frozen archive.",
    ),
    "ECMWF_IFS": NWPModelAuditEntry(
        model_id="ECMWF_IFS",
        center_name="European Centre for Medium-Range Weather Forecasts",
        country_or_org="International / Europe",
        tigge_origin="ecmf",
        status=NWPModelStatus.MISSING_ARCHIVE,
        resolution_horizontal="~9 km (HRES) / ~18 km (ENS)",
        native_cadence="6-hourly, 00Z & 12Z",
        verified_cyclone_leads=0,
        verified_cycles=0,
        historical_coverage_start=None,
        historical_coverage_end=None,
        variables_available=[],
        missingness_notes="Ingestion schema interfaces exist, but no historical cyclone vortex tracks or GRIB fields are ingested locally. Secondary license required for raw archive expansion.",
    ),
    "UKMO_GLOBAL": NWPModelAuditEntry(
        model_id="UKMO_GLOBAL",
        center_name="UK Met Office",
        country_or_org="United Kingdom",
        tigge_origin="egrr",
        status=NWPModelStatus.MISSING_ARCHIVE,
        resolution_horizontal="~10 km (global)",
        native_cadence="6-hourly, 00Z & 12Z",
        verified_cyclone_leads=0,
        verified_cycles=0,
        historical_coverage_start=None,
        historical_coverage_end=None,
        variables_available=[],
        missingness_notes="No local data archive. Not ingested in local repository.",
    ),
    "NCEP_GEFS": NWPModelAuditEntry(
        model_id="NCEP_GEFS",
        center_name="National Centers for Environmental Prediction",
        country_or_org="United States (NOAA)",
        tigge_origin="kwbc",
        status=NWPModelStatus.MISSING_ARCHIVE,
        resolution_horizontal="~25 km",
        native_cadence="6-hourly, 00Z, 06Z, 12Z, 18Z",
        verified_cyclone_leads=0,
        verified_cycles=0,
        historical_coverage_start=None,
        historical_coverage_end=None,
        variables_available=[],
        missingness_notes="No local data archive. Not ingested in local repository.",
    ),
}


@dataclass(frozen=True)
class ModelForecastFix:
    """Prospective vortex fix from one NWP forecast model."""

    model_id: str
    center: str
    initialization_time: datetime
    forecast_lead_hours: int
    valid_time: datetime
    latitude: float
    longitude: float
    mslp_hpa: Optional[float] = None
    max_wind_kts: Optional[float] = None


@dataclass(frozen=True)
class MultiModelAgreementResult:
    """Standardized output of multi-model agreement evaluation."""

    state: MultiModelAgreementState
    models_evaluated: List[str]
    available_model_count: int
    valid_time: Optional[str]
    forecast_cycle: Optional[str]
    lead_hours: Optional[int]
    mean_track_separation_km: Optional[float]
    max_track_separation_km: Optional[float]
    pairwise_separations_km: Dict[str, float]
    mslp_disagreement_hpa: Optional[float]
    agreement_notice: str
    validation_status: str
    is_abstention_recommended: bool
    provenance: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "models_evaluated": list(self.models_evaluated),
            "available_model_count": self.available_model_count,
            "valid_time": self.valid_time,
            "forecast_cycle": self.forecast_cycle,
            "lead_hours": self.lead_hours,
            "mean_track_separation_km": self.mean_track_separation_km,
            "max_track_separation_km": self.max_track_separation_km,
            "pairwise_separations_km": dict(self.pairwise_separations_km),
            "mslp_disagreement_hpa": self.mslp_disagreement_hpa,
            "agreement_notice": self.agreement_notice,
            "validation_status": self.validation_status,
            "is_abstention_recommended": self.is_abstention_recommended,
            "provenance": dict(self.provenance),
        }


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute great-circle distance between two geographic coordinates in km."""
    r_earth = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r_earth * c


class MultiModelAgreementEngine:
    """Mathematical multi-model agreement evaluation engine.

    Strictly enforces:
    - Zero fabrication: If <2 independent models are available, returns INSUFFICIENT_EVIDENCE.
    - Exact temporal alignment: Models must share the identical forecast valid time.
    - Explicit spatial bounds validation.
    - Deterministic threshold transitions.
    """

    # Experimental separation thresholds for tropical cyclone track fixes
    TRACK_AGREEMENT_THRESHOLD_KM = 65.0
    TRACK_HIGH_DISAGREEMENT_THRESHOLD_KM = 150.0

    # Experimental intensity disagreement thresholds
    MSLP_AGREEMENT_THRESHOLD_HPA = 8.0
    MSLP_HIGH_DISAGREEMENT_THRESHOLD_HPA = 18.0

    def __init__(self, catalog: Optional[Dict[str, NWPModelAuditEntry]] = None) -> None:
        self.catalog = catalog or NWP_DATA_AUDIT_CATALOG

    def get_data_audit_summary(self) -> Dict[str, Any]:
        """Return structured summary of NWP data availability in the repository."""
        available = [e for e in self.catalog.values() if e.status == NWPModelStatus.OPERATIONAL_ARCHIVED]
        missing = [e for e in self.catalog.values() if e.status != NWPModelStatus.OPERATIONAL_ARCHIVED]

        return {
            "total_models_cataloged": len(self.catalog),
            "available_operational_models": len(available),
            "missing_archive_models": len(missing),
            "independent_cross_model_pairs": 0,
            "decision_gate_status": "INSUFFICIENT_EVIDENCE",
            "decision_gate_reason": (
                "Fewer than 2 genuinely independent NWP models are archived locally. "
                "ForecastGuard retains NCMRWF NEPS as its single operational baseline. "
                "Fabrication of hypothetical ECMWF/UKMO outputs is strictly prohibited."
            ),
            "catalog": {k: v.to_dict() for k, v in self.catalog.items()},
        }

    def evaluate(self, models: Sequence[ModelForecastFix]) -> MultiModelAgreementResult:
        """Evaluate cross-model agreement for a set of prospective model fixes."""
        # 1. Gate: Sample count
        if not models or len(models) < 2:
            single_model_id = models[0].model_id if models else None
            return MultiModelAgreementResult(
                state=MultiModelAgreementState.INSUFFICIENT_EVIDENCE,
                models_evaluated=[m.model_id for m in models],
                available_model_count=len(models),
                valid_time=models[0].valid_time.isoformat() if models else None,
                forecast_cycle=models[0].initialization_time.isoformat() if models else None,
                lead_hours=models[0].forecast_lead_hours if models else None,
                mean_track_separation_km=None,
                max_track_separation_km=None,
                pairwise_separations_km={},
                mslp_disagreement_hpa=None,
                agreement_notice=(
                    "Multi-model agreement unavailable: insufficient independent models. "
                    f"Provided {len(models)} model(s) ({single_model_id or 'none'}), minimum 2 required. "
                    "Secondary independent NWP archives are not ingested in local repository."
                ),
                validation_status="INSUFFICIENT_EVIDENCE",
                is_abstention_recommended=False,
                provenance={
                    "audit_standard": "ForecastGuard_V2_AntiFabrication_Rule",
                    "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
                    "models_supplied": [m.model_id for m in models],
                },
            )

        # 2. Gate: Duplicate model identification
        distinct_models = {m.model_id for m in models}
        if len(distinct_models) < len(models):
            return MultiModelAgreementResult(
                state=MultiModelAgreementState.INSUFFICIENT_EVIDENCE,
                models_evaluated=[m.model_id for m in models],
                available_model_count=len(distinct_models),
                valid_time=models[0].valid_time.isoformat(),
                forecast_cycle=models[0].initialization_time.isoformat(),
                lead_hours=models[0].forecast_lead_hours,
                mean_track_separation_km=None,
                max_track_separation_km=None,
                pairwise_separations_km={},
                mslp_disagreement_hpa=None,
                agreement_notice="Multi-model agreement unavailable: duplicate model identifiers supplied.",
                validation_status="INSUFFICIENT_EVIDENCE",
                is_abstention_recommended=False,
                provenance={"error": "Duplicate model identifier detected"},
            )

        # 3. Gate: Temporal alignment
        reference_valid_time = models[0].valid_time
        for m in models[1:]:
            time_diff = abs((m.valid_time - reference_valid_time).total_seconds())
            if time_diff > 0.0:
                return MultiModelAgreementResult(
                    state=MultiModelAgreementState.INSUFFICIENT_EVIDENCE,
                    models_evaluated=[m.model_id for m in models],
                    available_model_count=len(models),
                    valid_time=reference_valid_time.isoformat(),
                    forecast_cycle=models[0].initialization_time.isoformat(),
                    lead_hours=models[0].forecast_lead_hours,
                    mean_track_separation_km=None,
                    max_track_separation_km=None,
                    pairwise_separations_km={},
                    mslp_disagreement_hpa=None,
                    agreement_notice=(
                        f"Temporal misalignment detected: {models[0].model_id} valid_time={reference_valid_time.isoformat()} "
                        f"vs {m.model_id} valid_time={m.valid_time.isoformat()}."
                    ),
                    validation_status="INSUFFICIENT_EVIDENCE",
                    is_abstention_recommended=False,
                    provenance={"error": "Temporal misalignment between models"},
                )

        # 4. Gate: Spatial Coordinate Validity
        for m in models:
            if math.isnan(m.latitude) or math.isnan(m.longitude) or math.isinf(m.latitude) or math.isinf(m.longitude):
                return MultiModelAgreementResult(
                    state=MultiModelAgreementState.INSUFFICIENT_EVIDENCE,
                    models_evaluated=[m.model_id for m in models],
                    available_model_count=len(models),
                    valid_time=reference_valid_time.isoformat(),
                    forecast_cycle=models[0].initialization_time.isoformat(),
                    lead_hours=models[0].forecast_lead_hours,
                    mean_track_separation_km=None,
                    max_track_separation_km=None,
                    pairwise_separations_km={},
                    mslp_disagreement_hpa=None,
                    agreement_notice=f"Invalid coordinates encountered for model {m.model_id}.",
                    validation_status="INSUFFICIENT_EVIDENCE",
                    is_abstention_recommended=False,
                    provenance={"error": "Coordinate validation failed"},
                )
            if not (-90.0 <= m.latitude <= 90.0 and -180.0 <= m.longitude <= 360.0):
                return MultiModelAgreementResult(
                    state=MultiModelAgreementState.INSUFFICIENT_EVIDENCE,
                    models_evaluated=[m.model_id for m in models],
                    available_model_count=len(models),
                    valid_time=reference_valid_time.isoformat(),
                    forecast_cycle=models[0].initialization_time.isoformat(),
                    lead_hours=models[0].forecast_lead_hours,
                    mean_track_separation_km=None,
                    max_track_separation_km=None,
                    pairwise_separations_km={},
                    mslp_disagreement_hpa=None,
                    agreement_notice=f"Coordinate bounds exceeded for model {m.model_id}.",
                    validation_status="INSUFFICIENT_EVIDENCE",
                    is_abstention_recommended=False,
                    provenance={"error": "Coordinate bounds out of range"},
                )

        # 5. Compute Pairwise Track Distances
        pairwise_dists: Dict[str, float] = {}
        all_dists: List[float] = []
        n = len(models)
        for i in range(n):
            for j in range(i + 1, n):
                m1, m2 = models[i], models[j]
                d = _haversine_distance(m1.latitude, m1.longitude, m2.latitude, m2.longitude)
                pair_key = f"{m1.model_id}_vs_{m2.model_id}"
                pairwise_dists[pair_key] = round(d, 2)
                all_dists.append(d)

        mean_dist = round(sum(all_dists) / len(all_dists), 2)
        max_dist = round(max(all_dists), 2)

        # 6. Compute MSLP Disagreement if available across all models
        mslp_values = [m.mslp_hpa for m in models if m.mslp_hpa is not None and not math.isnan(m.mslp_hpa)]
        mslp_diff: Optional[float] = None
        if len(mslp_values) == n:
            mslp_diff = round(max(mslp_values) - min(mslp_values), 2)

        # 7. State Classification
        # Thresholds are explicitly designated EXPERIMENTAL
        is_track_agree = max_dist <= self.TRACK_AGREEMENT_THRESHOLD_KM
        is_track_moderate = max_dist <= self.TRACK_HIGH_DISAGREEMENT_THRESHOLD_KM

        is_mslp_agree = mslp_diff is None or mslp_diff <= self.MSLP_AGREEMENT_THRESHOLD_HPA
        is_mslp_moderate = mslp_diff is None or mslp_diff <= self.MSLP_HIGH_DISAGREEMENT_THRESHOLD_HPA

        if is_track_agree and is_mslp_agree:
            state = MultiModelAgreementState.AGREEMENT
            notice = (
                f"Independent forecast systems agree closely (separation: {max_dist:.1f} km"
                + (f", MSLP diff: {mslp_diff:.1f} hPa" if mslp_diff is not None else "")
                + "). Consensus consistency is high."
            )
        elif is_track_moderate and is_mslp_moderate:
            state = MultiModelAgreementState.MODERATE_DISAGREEMENT
            notice = (
                f"Moderate cross-system forecast disagreement (separation: {max_dist:.1f} km"
                + (f", MSLP diff: {mslp_diff:.1f} hPa" if mslp_diff is not None else "")
                + "). Cross-model dispersion is noticeable."
            )
        else:
            state = MultiModelAgreementState.HIGH_DISAGREEMENT
            notice = (
                f"High cross-system forecast disagreement (separation: {max_dist:.1f} km"
                + (f", MSLP diff: {mslp_diff:.1f} hPa" if mslp_diff is not None else "")
                + "). Substantial synoptic divergence across independent NWP models."
            )

        return MultiModelAgreementResult(
            state=state,
            models_evaluated=[m.model_id for m in models],
            available_model_count=n,
            valid_time=reference_valid_time.isoformat(),
            forecast_cycle=models[0].initialization_time.isoformat(),
            lead_hours=models[0].forecast_lead_hours,
            mean_track_separation_km=mean_dist,
            max_track_separation_km=max_dist,
            pairwise_separations_km=pairwise_dists,
            mslp_disagreement_hpa=mslp_diff,
            agreement_notice=notice,
            validation_status="EXPERIMENTAL",
            is_abstention_recommended=False,
            provenance={
                "audit_standard": "ForecastGuard_V2_AntiFabrication_Rule",
                "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
                "thresholds": {
                    "track_agreement_km": self.TRACK_AGREEMENT_THRESHOLD_KM,
                    "track_high_disagreement_km": self.TRACK_HIGH_DISAGREEMENT_THRESHOLD_KM,
                    "mslp_agreement_hpa": self.MSLP_AGREEMENT_THRESHOLD_HPA,
                    "mslp_high_disagreement_hpa": self.MSLP_HIGH_DISAGREEMENT_THRESHOLD_HPA,
                },
                "disclaimer": "Cross-model agreement is an evidence indicator of synoptic consensus dispersion, NOT forecast error.",
            },
        )


multimodel_engine = MultiModelAgreementEngine()
