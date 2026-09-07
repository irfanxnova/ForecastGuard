"""ForecastGuard P3 — Prospective Future-Bust Detection and Reliability Upgrade.

SIH26079: AI-Based Forecast Bust Detection for Medium-Range Weather Forecasts.

Extends Milestone P2 with:
1. Prospective Future-Bust Target formulation (t+6h, t+12h, t+24h, any within 24h).
2. Strict anti-leakage invariants (prediction at t uses strictly info up to t).
3. Ensemble Spatial Geometry Engine (anisotropy ratio, Sarle's bimodality, clustering).
4. Extended Trajectory Intelligence (spread acceleration, heading curvature, translation jitter).
5. Cycle-to-Cycle Forecast Revision Instability (comparing successive cycles at identical valid time).
6. False-Confidence & Reliability Contradiction Diagnostics (quadrants, RCI).
7. Controlled M0-M6 Ablation Ladder with empirical Keep/Kill decision engine.
8. Empirical Bust Atlas cataloging verified forecast failure dynamics and warning lead times.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from scipy import stats

from scientific.validation.cyclone import (
    EARTH_RADIUS_KM,
    BestTrackPoint,
    ClimatologyBaseline,
    ContinuousErrorMetrics,
    ForecastMemberTrackPoint,
    ModelMetrics,
    SpreadOnlyModel,
    VerifiedLeadEvaluation,
    compute_continuous_error_metrics,
    compute_earliest_warning,
    compute_ece,
    evaluate_forecast_lead,
    haversine_distance,
    parse_rsmc_best_tracks,
    parse_tigge_mslp_grib_ensemble,
    save_case_artifact,
)


@dataclass(frozen=True)
class EnsembleGeometry:
    """Spatial and track geometry metrics for an ensemble at a single forecast lead."""

    mean_pairwise_dist_km: float
    max_separation_km: float  # Divergence
    std_dist_to_centroid_km: float
    anisotropy_ratio: float  # sqrt(lambda_major / lambda_minor), >= 1.0
    major_axis_spread_km: float
    minor_axis_spread_km: float
    principal_axis_angle_deg: float
    bimodality_coefficient: float  # Sarle's BC along major axis
    dominant_cluster_fraction: float  # Fraction in majority cluster (0.5 to 1.0)
    cluster_separation_km: float  # Distance between 2 cluster centroids


def compute_ensemble_geometry(
    member_points: List[ForecastMemberTrackPoint],
    mean_lat: float,
    mean_lon: float,
) -> EnsembleGeometry:
    """Compute spatial track geometry across ensemble members in local tangent Cartesian coordinates."""
    n_members = len(member_points)
    if n_members < 2:
        return EnsembleGeometry(
            mean_pairwise_dist_km=0.0,
            max_separation_km=0.0,
            std_dist_to_centroid_km=0.0,
            anisotropy_ratio=1.0,
            major_axis_spread_km=0.0,
            minor_axis_spread_km=0.0,
            principal_axis_angle_deg=0.0,
            bimodality_coefficient=0.0,
            dominant_cluster_fraction=1.0,
            cluster_separation_km=0.0,
        )

    # 1. Pairwise distances
    pairwise_dists = [
        haversine_distance(m1.center_lat, m1.center_lon, m2.center_lat, m2.center_lon)
        for i, m1 in enumerate(member_points)
        for j, m2 in enumerate(member_points)
        if i < j
    ]
    mean_pairwise = float(np.mean(pairwise_dists)) if pairwise_dists else 0.0
    max_sep = float(np.max(pairwise_dists)) if pairwise_dists else 0.0

    # 2. Convert to local Cartesian coordinates (km) relative to ensemble centroid
    lat_rad = math.radians(mean_lat)
    km_per_deg_lat = 111.132
    km_per_deg_lon = 111.320 * math.cos(lat_rad)

    x_coords = np.array([(m.center_lon - mean_lon) * km_per_deg_lon for m in member_points])
    y_coords = np.array([(m.center_lat - mean_lat) * km_per_deg_lat for m in member_points])

    dists_to_centroid = np.sqrt(x_coords ** 2 + y_coords ** 2)
    std_dist_to_centroid = float(np.std(dists_to_centroid))

    # 3. Covariance matrix and principal components (anisotropy)
    coords_2d = np.column_stack([x_coords, y_coords])
    cov_matrix = np.cov(coords_2d, rowvar=False)

    if cov_matrix.ndim == 2 and not np.isnan(cov_matrix).any():
        eigenvals, eigenvecs = np.linalg.eigh(cov_matrix)
        # Sort descending
        idx = np.argsort(eigenvals)[::-1]
        eigenvals = np.maximum(eigenvals[idx], 1e-6)
        eigenvecs = eigenvecs[:, idx]

        major_spread = float(np.sqrt(eigenvals[0]))
        minor_spread = float(np.sqrt(eigenvals[1]))
        anisotropy = float(major_spread / max(1e-3, minor_spread))

        # Principal angle
        major_vec = eigenvecs[:, 0]
        angle_deg = float(math.degrees(math.atan2(major_vec[1], major_vec[0])) % 180.0)

        # 4. Multimodality / Bimodality along major principal axis
        projected = coords_2d @ major_vec
        n = len(projected)

        if n >= 4:
            skew_val = float(stats.skew(projected))
            kurt_val = float(stats.kurtosis(projected, fisher=False))  # Pearson kurtosis (normal=3)
            denom = kurt_val + (3.0 * (n - 1) ** 2) / ((n - 2) * (n - 3))
            bimodality_coef = float((skew_val ** 2 + 1.0) / max(1e-3, denom))
        else:
            bimodality_coef = 0.333  # Default unimodal

        # 5. 2-Cluster separation and dominant cluster fraction
        median_proj = float(np.median(projected))
        c1 = projected[projected <= median_proj]
        c2 = projected[projected > median_proj]

        if len(c1) > 0 and len(c2) > 0:
            cluster_sep = float(abs(np.mean(c2) - np.mean(c1)))
            dom_fraction = float(max(len(c1), len(c2)) / n)
        else:
            cluster_sep = 0.0
            dom_fraction = 1.0
    else:
        major_spread = float(np.std(x_coords))
        minor_spread = float(np.std(y_coords))
        anisotropy = 1.0
        angle_deg = 0.0
        bimodality_coef = 0.333
        dom_fraction = 1.0
        cluster_sep = 0.0

    return EnsembleGeometry(
        mean_pairwise_dist_km=mean_pairwise,
        max_separation_km=max_sep,
        std_dist_to_centroid_km=std_dist_to_centroid,
        anisotropy_ratio=anisotropy,
        major_axis_spread_km=major_spread,
        minor_axis_spread_km=minor_spread,
        principal_axis_angle_deg=angle_deg,
        bimodality_coefficient=bimodality_coef,
        dominant_cluster_fraction=dom_fraction,
        cluster_separation_km=cluster_sep,
    )


@dataclass(frozen=True)
class CycleRevisionPoint:
    """Comparison of forecast state between successive initialization cycles for the same storm."""

    has_prior_cycle: bool
    revision_distance_km: float = 0.0
    spread_shift_km: float = 0.0
    revision_rate_km_per_hour: float = 0.0


@dataclass(frozen=True)
class ProspectiveLeadFeatures:
    """Strictly anti-leakage feature and target vector for prospective future-bust prediction.

    Anti-Leakage Rule:
    At lead t, all predictor features are strictly derived from forecast data at leads t' <= t
    and cycles initialized <= current cycle.
    Future targets are derived from leads t' > t and used strictly for evaluation.
    """

    cyclone_name: str
    cycle_init_time: datetime
    lead_hours: int
    valid_time: datetime

    # --- Predictor Features Available at Lead t ---
    # 1. Snapshot Spread
    ensemble_spread_km: float
    ensemble_divergence_km: float
    mean_central_pressure_hpa: float

    # 2. Ensemble Spatial Geometry
    anisotropy_ratio: float
    major_axis_spread_km: float
    bimodality_coefficient: float
    dominant_cluster_fraction: float
    cluster_separation_km: float
    mean_pairwise_dist_km: float

    # 3. Trajectory Intelligence (t' <= t)
    spread_growth_km: float
    spread_acceleration_km: float
    trajectory_speed_kmh: float
    trajectory_curvature_deg: float
    anisotropy_growth_rate: float
    trajectory_instability_km: float

    # 4. Cycle-to-Cycle Instability
    has_prior_cycle: bool
    cycle_revision_distance_km: float
    cycle_spread_shift_km: float

    # 5. False-Confidence & Reliability Diagnostics
    reliability_contradiction_index: float
    confidence_quadrant: str  # FALSE_CONFIDENCE, CAUTIOUS_CORRECT, EXPECTED_RISK, RELIABLE_CONFIDENCE

    # --- Target Variables (NEVER USED AS INPUT FEATURES) ---
    contemp_is_bust: bool
    contemp_error_km: float
    contemp_bust_severity: str = "NORMAL"
    future_bust_plus6h: Optional[bool] = None
    future_error_plus6h: Optional[float] = None
    future_bust_plus12h: Optional[bool] = None
    future_error_plus12h: Optional[float] = None
    future_bust_plus24h: Optional[bool] = None
    future_error_plus24h: Optional[float] = None
    future_bust_within24h: Optional[bool] = None


def classify_confidence_quadrant(
    spread_km: float,
    future_error_km: Optional[float],
    median_spread_km: float = 100.0,
    bust_threshold_km: float = 90.0,
) -> str:
    """Classify forecast instance into one of 4 empirical reliability quadrants.
    
    NOTE: These are diagnostic categories for operational decision support,
    not deterministic physical laws. Thresholds (e.g. median spread, bust threshold)
    are empirical reference baselines grounded in the current pilot archive.
    """
    if future_error_km is None:
        return "UNKNOWN"
    is_low_spread = spread_km < median_spread_km
    is_future_bust = future_error_km >= bust_threshold_km

    if is_low_spread and is_future_bust:
        return "FALSE_CONFIDENCE"
    elif not is_low_spread and not is_future_bust:
        return "CAUTIOUS_CORRECT"
    elif not is_low_spread and is_future_bust:
        return "EXPECTED_RISK"
    else:
        return "RELIABLE_CONFIDENCE"


def extract_prospective_features(
    evaluations: List[VerifiedLeadEvaluation],
    prior_cycle_evals: Optional[List[VerifiedLeadEvaluation]] = None,
    median_spread_ref: float = 100.0,
) -> List[ProspectiveLeadFeatures]:
    """Extract strictly anti-leakage prospective features and multi-horizon future targets.

    For lead t:
    Features use ONLY evaluations at lead <= t.
    Targets look forward to t+6h, t+12h, t+24h.
    """
    sorted_evals = sorted(evaluations, key=lambda x: x.lead_hours)
    leads_dict = {ev.lead_hours: ev for ev in sorted_evals}
    feature_list: List[ProspectiveLeadFeatures] = []

    # Map prior cycle evaluations by valid_time for cycle revision comparison
    prior_by_valid: Dict[datetime, VerifiedLeadEvaluation] = {}
    if prior_cycle_evals:
        prior_by_valid = {ev.valid_time: ev for ev in prior_cycle_evals}

    for i, curr in enumerate(sorted_evals):
        lead = curr.lead_hours

        # 1. Ensemble Geometry at lead t
        geom = compute_ensemble_geometry(
            member_points=curr.member_points,
            mean_lat=curr.ensemble_mean_lat,
            mean_lon=curr.ensemble_mean_lon,
        )

        # 2. Trajectory Intelligence (leads <= t)
        if i >= 1:
            prev1 = sorted_evals[i - 1]
            dt1 = max(1, lead - prev1.lead_hours)
            spread_growth = (curr.ensemble_spread_km - prev1.ensemble_spread_km) / dt1
            step_dist = haversine_distance(
                prev1.ensemble_mean_lat, prev1.ensemble_mean_lon, curr.ensemble_mean_lat, curr.ensemble_mean_lon
            )
            speed = step_dist / dt1

            geom_prev = compute_ensemble_geometry(prev1.member_points, prev1.ensemble_mean_lat, prev1.ensemble_mean_lon)
            aniso_growth = (geom.anisotropy_ratio - geom_prev.anisotropy_ratio) / dt1
        else:
            spread_growth = 0.0
            speed = 0.0
            aniso_growth = 0.0

        if i >= 2:
            prev1 = sorted_evals[i - 1]
            prev2 = sorted_evals[i - 2]
            dt2 = max(1, prev1.lead_hours - prev2.lead_hours)
            prev_growth = (prev1.ensemble_spread_km - prev2.ensemble_spread_km) / dt2
            spread_accel = spread_growth - prev_growth

            # Heading change (curvature)
            bearing1 = math.degrees(math.atan2(prev1.ensemble_mean_lon - prev2.ensemble_mean_lon, prev1.ensemble_mean_lat - prev2.ensemble_mean_lat))
            bearing2 = math.degrees(math.atan2(curr.ensemble_mean_lon - prev1.ensemble_mean_lon, curr.ensemble_mean_lat - prev1.ensemble_mean_lat))
            curvature = abs(bearing2 - bearing1)
            if curvature > 180.0:
                curvature = 360.0 - curvature

            # Trajectory instability (jitter)
            dist1 = haversine_distance(prev2.ensemble_mean_lat, prev2.ensemble_mean_lon, prev1.ensemble_mean_lat, prev1.ensemble_mean_lon)
            dist2 = haversine_distance(prev1.ensemble_mean_lat, prev1.ensemble_mean_lon, curr.ensemble_mean_lat, curr.ensemble_mean_lon)
            jitter = abs(dist2 - dist1)
        else:
            spread_accel = 0.0
            curvature = 0.0
            jitter = 0.0

        # 3. Cycle-to-Cycle Instability
        has_prior = False
        rev_dist = 0.0
        spread_shift = 0.0
        if curr.valid_time in prior_by_valid:
            prior_ev = prior_by_valid[curr.valid_time]
            has_prior = True
            rev_dist = haversine_distance(
                curr.ensemble_mean_lat, curr.ensemble_mean_lon, prior_ev.ensemble_mean_lat, prior_ev.ensemble_mean_lon
            )
            spread_shift = curr.ensemble_spread_km - prior_ev.ensemble_spread_km

        # 4. Reliability Contradiction Index (RCI)
        # High anisotropy + rapid spread growth in relatively low/moderate baseline spread
        rci = (geom.anisotropy_ratio * max(0.0, spread_growth)) / max(10.0, curr.ensemble_spread_km)

        # 5. Prospective Targets (strictly leads > t)
        ev_plus6h = leads_dict.get(lead + 6)
        fut_bust_6h = ev_plus6h.is_bust if ev_plus6h else None
        fut_err_6h = ev_plus6h.mean_track_error_km if ev_plus6h else None

        ev_plus12h = leads_dict.get(lead + 12)
        fut_bust_12h = ev_plus12h.is_bust if ev_plus12h else None
        fut_err_12h = ev_plus12h.mean_track_error_km if ev_plus12h else None

        ev_plus24h = leads_dict.get(lead + 24)
        fut_bust_24h = ev_plus24h.is_bust if ev_plus24h else None
        fut_err_24h = ev_plus24h.mean_track_error_km if ev_plus24h else None

        # Any bust within next 24h: check all available leads in (lead, lead + 24]
        future_leads_in_24h = [ev for l, ev in leads_dict.items() if lead < l <= lead + 24]
        if future_leads_in_24h:
            fut_bust_w24h = any(ev.is_bust for ev in future_leads_in_24h)
            max_future_err = max(ev.mean_track_error_km for ev in future_leads_in_24h)
        else:
            fut_bust_w24h = None
            max_future_err = None

        quadrant = classify_confidence_quadrant(
            spread_km=curr.ensemble_spread_km,
            future_error_km=fut_err_12h if fut_err_12h is not None else fut_err_6h,
            median_spread_km=median_spread_ref,
            bust_threshold_km=curr.bust_threshold_km,
        )

        feature_list.append(
            ProspectiveLeadFeatures(
                cyclone_name=curr.cyclone_name,
                cycle_init_time=curr.initialization_time,
                lead_hours=lead,
                valid_time=curr.valid_time,
                ensemble_spread_km=curr.ensemble_spread_km,
                ensemble_divergence_km=curr.ensemble_divergence_km,
                mean_central_pressure_hpa=curr.ensemble_mean_pressure_hpa,
                anisotropy_ratio=geom.anisotropy_ratio,
                major_axis_spread_km=geom.major_axis_spread_km,
                bimodality_coefficient=geom.bimodality_coefficient,
                dominant_cluster_fraction=geom.dominant_cluster_fraction,
                cluster_separation_km=geom.cluster_separation_km,
                mean_pairwise_dist_km=geom.mean_pairwise_dist_km,
                spread_growth_km=spread_growth,
                spread_acceleration_km=spread_accel,
                trajectory_speed_kmh=speed,
                trajectory_curvature_deg=curvature,
                anisotropy_growth_rate=aniso_growth,
                trajectory_instability_km=jitter,
                has_prior_cycle=has_prior,
                cycle_revision_distance_km=rev_dist,
                cycle_spread_shift_km=spread_shift,
                reliability_contradiction_index=rci,
                confidence_quadrant=quadrant,
                contemp_is_bust=curr.is_bust,
                contemp_error_km=curr.mean_track_error_km,
                contemp_bust_severity=curr.bust_severity,
                future_bust_plus6h=fut_bust_6h,
                future_error_plus6h=fut_err_6h,
                future_bust_plus12h=fut_bust_12h,
                future_error_plus12h=fut_err_12h,
                future_bust_plus24h=fut_bust_24h,
                future_error_plus24h=fut_err_24h,
                future_bust_within24h=fut_bust_w24h,
            )
        )

    return feature_list


# ==============================================================================
# Model Ablation Suite (M0 through M6)
# ==============================================================================


class P3LogisticModel:
    """Regularized probabilistic logistic model for prospective bust prediction."""

    def __init__(self, c_param: float = 1.0) -> None:
        self.c_param = c_param
        self.clf = None
        self.base_rate = 0.5

    def fit(self, X: np.ndarray, y: np.ndarray) -> "P3LogisticModel":
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler

        self.base_rate = float(np.mean(y)) if len(y) > 0 else 0.5
        if len(set(y)) < 2:
            return self

        # Robust standardization to prevent scale dominance
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        clf = LogisticRegression(C=self.c_param, solver="lbfgs", max_iter=500, random_state=42)
        clf.fit(X_scaled, y)
        self.clf = clf
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if self.clf is not None and hasattr(self, "scaler"):
            X_scaled = self.scaler.transform(X)
            return self.clf.predict_proba(X_scaled)
        p = np.full(len(X), self.base_rate)
        return np.column_stack([1.0 - p, p])

    def predict(self, X: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        return (self.predict_proba(X)[:, 1] >= threshold).astype(int)


def extract_feature_matrix_for_ablation(
    features: List[ProspectiveLeadFeatures],
    model_id: str,
) -> np.ndarray:
    """Extract specific feature subsets strictly adhering to the ablation ladder."""
    rows = []
    for f in features:
        if model_id == "M0_Climatology":
            row = [f.lead_hours]
        elif model_id == "M1_SpreadOnly":
            row = [f.lead_hours, f.ensemble_spread_km]
        elif model_id == "M2_Spread_Trajectory":
            row = [
                f.lead_hours,
                f.ensemble_spread_km,
                f.spread_growth_km,
                f.spread_acceleration_km,
                f.trajectory_speed_kmh,
                f.trajectory_curvature_deg,
            ]
        elif model_id == "M3_Spread_Geometry":
            row = [
                f.lead_hours,
                f.ensemble_spread_km,
                f.anisotropy_ratio,
                f.bimodality_coefficient,
                f.cluster_separation_km,
                f.dominant_cluster_fraction,
            ]
        elif model_id == "M4_Spread_CycleInstability":
            row = [
                f.lead_hours,
                f.ensemble_spread_km,
                float(f.has_prior_cycle),
                f.cycle_revision_distance_km,
                f.cycle_spread_shift_km,
            ]
        elif model_id == "M5_Spread_FalseConfidence":
            row = [
                f.lead_hours,
                f.ensemble_spread_km,
                f.reliability_contradiction_index,
                f.ensemble_divergence_km,
            ]
        elif model_id == "M6_CombinedCandidate":
            row = [
                f.lead_hours,
                f.ensemble_spread_km,
                f.spread_growth_km,
                f.anisotropy_ratio,
                f.bimodality_coefficient,
                f.reliability_contradiction_index,
                f.trajectory_speed_kmh,
            ]
        else:
            raise ValueError(f"Unknown model_id: {model_id}")
        rows.append(row)

    return np.asarray(rows, dtype=np.float64)


@dataclass(frozen=True)
class KeepKillDecision:
    """Empirical decision on whether a feature family is retained or killed."""

    feature_family: str
    brier_score: float
    ece: float
    accuracy: float
    warning_lead_hours: Optional[int]
    delta_brier_vs_m1: float  # Negative is improvement
    delta_ece_vs_m1: float  # Negative is improvement
    status: str  # RETAINED, KILLED, INCONCLUSIVE
    scientific_justification: str


def evaluate_keep_kill(
    ablation_results: Dict[str, ModelMetrics],
    baseline_id: str = "M1_SpreadOnly",
) -> Dict[str, KeepKillDecision]:
    """Apply empirical Keep/Kill rule comparing each ablation model against baseline M1."""
    if baseline_id not in ablation_results:
        raise ValueError(f"Baseline {baseline_id} missing from ablation results")

    m1 = ablation_results[baseline_id]
    decisions: Dict[str, KeepKillDecision] = {}

    for model_id, m in ablation_results.items():
        if model_id == baseline_id:
            decisions[model_id] = KeepKillDecision(
                feature_family="M1_Baseline_Spread",
                brier_score=m.brier_score,
                ece=m.ece,
                accuracy=m.accuracy,
                warning_lead_hours=m.earliest_warning_lead_hours,
                delta_brier_vs_m1=0.0,
                delta_ece_vs_m1=0.0,
                status="RETAINED",
                scientific_justification="Established baseline: scalar ensemble spread.",
            )
            continue

        delta_brier = m.brier_score - m1.brier_score
        delta_ece = m.ece - m1.ece

        # Keep/Kill Logic:
        # Improves calibration (ECE lower) or Brier lower without degrading accuracy/warning lead
        if delta_brier < -0.005 or (delta_ece < -0.005 and delta_brier <= 0.005):
            status = "RETAINED"
            justification = f"Showed prospective calibration improvement in current pilot evaluation (delta ECE: {delta_ece:.4f}, delta Brier: {delta_brier:.4f}); provisional pending larger multi-season sample."
        elif abs(delta_brier) <= 0.005 and abs(delta_ece) <= 0.005:
            status = "INCONCLUSIVE"
            justification = "Marginal difference on pilot sample size; does not significantly separate from spread baseline."
        else:
            status = "KILLED"
            justification = f"Degrades out-of-event validation metrics (delta Brier: +{delta_brier:.4f}, delta ECE: +{delta_ece:.4f}). Complexity not earned."

        decisions[model_id] = KeepKillDecision(
            feature_family=model_id,
            brier_score=m.brier_score,
            ece=m.ece,
            accuracy=m.accuracy,
            warning_lead_hours=m.earliest_warning_lead_hours,
            delta_brier_vs_m1=delta_brier,
            delta_ece_vs_m1=delta_ece,
            status=status,
            scientific_justification=justification,
        )

    return decisions


# ==============================================================================
# Empirical Bust Atlas
# ==============================================================================


@dataclass(frozen=True)
class BustAtlasEntry:
    """Historical verified record of forecast degradation / bust event and antecedent conditions."""

    cyclone_name: str
    cycle_init_iso: str
    lead_hours: int
    valid_time_iso: str
    track_error_km: float
    bust_severity: str
    ensemble_spread_km: float
    anisotropy_ratio: float
    bimodality_coefficient: float
    trajectory_speed_kmh: float
    heading_curvature_deg: float
    confidence_quadrant: str
    prospective_alert_prob: float
    advance_warning_hours: Optional[int]
    verification_provenance: str = "Official IMD RSMC Best Track vs NCMRWF NEPS"


def build_bust_atlas(
    features: List[ProspectiveLeadFeatures],
    model: Any,
    feature_matrix: np.ndarray,
) -> List[BustAtlasEntry]:
    """Catalog all verified failure events with antecedent forecast conditions and warning leads."""
    probs = model.predict_proba(feature_matrix)[:, 1]
    atlas_entries: List[BustAtlasEntry] = []

    for f, prob in zip(features, probs):
        if f.contemp_is_bust:
            # Calculate warning advance: if an alert prob >= 0.5 was raised at an earlier lead
            # Prospective window invariant: An alert at t_past predicts a bust in (t_past, t_past + 24h].
            # Therefore, t_past is a valid advance warning for f.lead_hours iff t_past < f.lead_hours <= t_past + 24.
            valid_earlier_alert_leads = [
                f_past.lead_hours
                for f_past, p_past in zip(features, probs)
                if f_past.cyclone_name == f.cyclone_name
                and f_past.cycle_init_time == f.cycle_init_time
                and f_past.lead_hours < f.lead_hours <= f_past.lead_hours + 24
                and p_past >= 0.5
            ]
            adv_warn = (f.lead_hours - min(valid_earlier_alert_leads)) if valid_earlier_alert_leads else None

            severity = getattr(f, "contemp_bust_severity", "DEGRADED")

            atlas_entries.append(
                BustAtlasEntry(
                    cyclone_name=f.cyclone_name,
                    cycle_init_iso=f.cycle_init_time.isoformat(),
                    lead_hours=f.lead_hours,
                    valid_time_iso=f.valid_time.isoformat(),
                    track_error_km=f.contemp_error_km,
                    bust_severity=severity,
                    ensemble_spread_km=f.ensemble_spread_km,
                    anisotropy_ratio=f.anisotropy_ratio,
                    bimodality_coefficient=f.bimodality_coefficient,
                    trajectory_speed_kmh=f.trajectory_speed_kmh,
                    heading_curvature_deg=f.trajectory_curvature_deg,
                    confidence_quadrant=f.confidence_quadrant,
                    prospective_alert_prob=float(prob),
                    advance_warning_hours=adv_warn,
                )
            )

    return atlas_entries
