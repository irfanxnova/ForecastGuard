"""ForecastGuard V2 — Structured Evidence Engine.

Synthesizes Ensemble Intelligence and Forecast Trajectory Intelligence into a deterministic
Structured Evidence Object answering:
- WHY IS RELIABILITY DEGRADING?
- WHAT CHANGED?
- HOW COHERENT IS THE ENSEMBLE?
- IS THE FORECAST BECOMING UNSTABLE?

Strict adherence to AGENTS.md:
- Rule 1: Never fabricate weather data or machine-learning predictions.
- Rule 6: Predictions use strictly information available up to the forecast cutoff.
- Rule 15: UI values must come from the backend/data layer, never hardcoded in the frontend.
- Non-negotiable: Structured evidence must be generated from actual computed signals,
  NOT by an LLM inventing scientific explanations.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Literal, Optional

from scientific.features.ensemble_intelligence import EnsembleMetrics, EnsembleStateLiteral
from scientific.features.trajectory_intelligence import TrajectoryMetrics, TrajectoryStateLiteral
from scientific.features.environmental_intelligence import (
    AvailabilityStatus,
    EnvironmentalIntelligenceResult,
    EnvironmentalState,
)


EvidenceStatusLiteral = Literal["COMPLETE", "PARTIAL", "UNAVAILABLE", "INSUFFICIENT"]
EvidenceStrengthLiteral = Literal["HIGH", "MODERATE", "LOW", "INSUFFICIENT_EVIDENCE"]


@dataclass(frozen=True)
class EnsembleEvidenceBlock:
    """Ensemble intelligence summary for structured evidence."""

    state: EnsembleStateLiteral
    state_description: str
    member_count: int
    mean_spread: Optional[float]
    spread_unit: str
    coherence_score: Optional[float]
    anisotropy_ratio: Optional[float]
    bimodality_coefficient: Optional[float]
    dominant_cluster_fraction: Optional[float]
    cluster_separation: Optional[float]
    pairwise_disagreement: Optional[float]
    status: EvidenceStatusLiteral


@dataclass(frozen=True)
class TrajectoryEvidenceBlock:
    """Forecast trajectory intelligence summary for structured evidence."""

    state: TrajectoryStateLiteral
    state_description: str
    has_prior_cycle: bool
    reference_cycle: Optional[str]
    cycle_revision_distance_km: Optional[float]
    cycle_spread_shift_km: Optional[float]
    revision_rate_kmh: Optional[float]
    trajectory_speed_kmh: Optional[float]
    trajectory_curvature_deg: Optional[float]
    spread_growth_rate: Optional[float]
    trajectory_instability_km: Optional[float]
    status: EvidenceStatusLiteral


@dataclass(frozen=True)
class EnvironmentalEvidenceBlock:
    """Environmental conditioning intelligence summary for structured evidence."""

    state: EnvironmentalState
    state_description: str
    pressure_depth_hpa: Optional[float]
    pressure_gradient_hpa_per_100km: Optional[float]
    gradient_asymmetry_hpa_per_100km: Optional[float]
    gradient_trend_hpa_per_100km: Optional[float]
    core_pressure_hpa: Optional[float]
    peripheral_pressure_hpa: Optional[float]
    upper_air_shear_status: AvailabilityStatus
    mid_level_humidity_status: AvailabilityStatus
    sst_status: AvailabilityStatus
    validation_status: Literal["VALIDATED", "EXPERIMENTAL", "INSUFFICIENT_EVIDENCE"]
    provenance: str
    status: EvidenceStatusLiteral
    scientific_provenance_note: str = (
        "Derived from NCMRWF NEPS ensemble MSLP pressure-gradient geometry. "
        "NOT a direct measurement of vertical wind shear, upper-air wind, or humidity."
    )


@dataclass(frozen=True)
class StructuredEvidence:
    """Canonical deterministic evidence object backing regional reliability assessments."""

    region_id: str
    region_name: str
    lead_hours: int
    ensemble: EnsembleEvidenceBlock
    trajectory: TrajectoryEvidenceBlock
    environmental: Optional[EnvironmentalEvidenceBlock]
    trend: Literal["increasing", "decreasing", "stable", "unavailable"]
    why_now: str
    what_changed: str
    evidence_status: EvidenceStatusLiteral
    evidence_strength: EvidenceStrengthLiteral
    source_provenance: str


def generate_why_now_attribution(
    ensemble: EnsembleMetrics,
    trajectory: Optional[TrajectoryMetrics],
    reliability_state: str,
    calibrated_prob: Optional[float],
    environmental: Optional[EnvironmentalIntelligenceResult] = None,
) -> str:
    """Generate deterministic factual attribution answering 'WHY IS RELIABILITY DEGRADING?'."""
    if ensemble.ensemble_state == "INSUFFICIENT_EVIDENCE":
        return "Insufficient observation or forecast data within region boundaries to determine physical drivers."

    reasons: List[str] = []

    # 1. Ensemble structural drivers
    if ensemble.ensemble_state == "MULTI_BRANCH":
        reasons.append(
            f"ensemble tracks bifurcated into dual scenarios along principal axis "
            f"(BC={ensemble.bimodality_coefficient:.3f}, separation={ensemble.cluster_separation:.1f} {ensemble.units})"
        )
    elif ensemble.ensemble_state == "FRAGMENTED":
        reasons.append(
            f"ensemble consensus broke down across {ensemble.member_count} members "
            f"(coherence={ensemble.coherence_score:.2f}, spread={ensemble.mean_spread:.1f} {ensemble.units})"
        )
    elif ensemble.ensemble_state == "SPREADING":
        reasons.append(
            f"member dispersion expanded to {ensemble.mean_spread:.1f} {ensemble.units} "
            f"with anisotropy ratio {ensemble.anisotropy_ratio:.2f}"
        )

    # 2. Trajectory stability drivers
    if trajectory is not None:
        if trajectory.instability_state == "RAPID_REVISION" and trajectory.cycle_revision_distance_km is not None:
            reasons.append(
                f"forecast underwent a {trajectory.cycle_revision_distance_km:.1f} km shift "
                f"from prior initialization run for identical valid time"
            )
        elif trajectory.instability_state == "OSCILLATING_JUMPY":
            reasons.append(
                f"trajectory shows heading curvature of {trajectory.trajectory_curvature_deg:.1f}° "
                f"and speed jitter of {trajectory.trajectory_instability_km:.1f} km"
            )
        elif trajectory.instability_state == "PROGRESSIVE_DRIFT" and trajectory.cycle_revision_distance_km is not None:
            reasons.append(
                f"forecast tracks exhibit progressive drift of {trajectory.cycle_revision_distance_km:.1f} km across consecutive runs"
            )

    # 3. Environmental conditioning signals (associative only, non-causal per Rule 17)
    if environmental is not None and environmental.state != "INSUFFICIENT_EVIDENCE":
        if environmental.state == "ASYMMETRIC_WEAK_PRESSURE_STRUCTURE":
            if environmental.gradient_asymmetry_hpa_per_100km is not None and environmental.gradient_asymmetry_hpa_per_100km >= 2.2:
                reasons.append(
                    f"associated with asymmetric synoptic pressure pattern "
                    f"({environmental.gradient_asymmetry_hpa_per_100km:.2f} hPa/100km cross-domain asymmetry)"
                )
            elif environmental.pressure_gradient_hpa_per_100km is not None:
                reasons.append(
                    f"conditioned by diffuse synoptic pressure structure "
                    f"({environmental.pressure_gradient_hpa_per_100km:.2f} hPa/100km radial gradient)"
                )
        elif environmental.state == "SYMMETRIC_DEEP_PRESSURE_STRUCTURE" and environmental.pressure_gradient_hpa_per_100km is not None:
            reasons.append(
                f"conditioned by deep, symmetric radial pressure gradient "
                f"({environmental.pressure_gradient_hpa_per_100km:.2f} hPa/100km, depth {environmental.pressure_depth_hpa:.1f} hPa)"
            )
        elif environmental.state == "MARGINAL_PRESSURE_STRUCTURE" and environmental.pressure_gradient_hpa_per_100km is not None:
            reasons.append(
                f"conditioned by marginal environmental pressure gradient "
                f"({environmental.pressure_gradient_hpa_per_100km:.2f} hPa/100km)"
            )

    if not reasons:
        if reliability_state == "STABLE":
            return (
                f"Reliability is stable: ensemble exhibits high coherence ({ensemble.coherence_score:.2f}) "
                f"and consistent trajectory dynamics with minimal revision."
            )
        return (
            f"Reliability is governed by baseline lead-time dispersion "
            f"({ensemble.mean_spread:.1f} {ensemble.units}) across {ensemble.member_count} ensemble members."
        )

    explanation = "; ".join(reasons)
    prob_prefix = "Vulnerability driven by: "
    return f"{prob_prefix}{explanation}."


def generate_what_changed_summary(
    ensemble: EnsembleMetrics,
    trajectory: Optional[TrajectoryMetrics],
    trend_delta: Optional[float] = None,
    environmental: Optional[EnvironmentalIntelligenceResult] = None,
) -> str:
    """Generate deterministic narrative answering 'WHAT CHANGED?'."""
    parts: List[str] = []

    # Cycle-to-cycle comparison
    if trajectory is not None and trajectory.has_prior_cycle:
        rev_km = trajectory.cycle_revision_distance_km
        shift_km = trajectory.cycle_spread_shift_km
        if rev_km is not None:
            shift_text = ""
            if shift_km is not None:
                dir_str = "widened" if shift_km > 0 else "narrowed"
                shift_text = f", while ensemble spread {dir_str} by {abs(shift_km):.1f} km"
            parts.append(
                f"Cycle-over-cycle: forecast center shifted by {rev_km:.1f} km at identical valid time{shift_text}"
            )

    # Lead-over-lead temporal progression
    if trend_delta is not None and abs(trend_delta) >= 0.02:
        dir_word = "increased" if trend_delta > 0 else "decreased"
        pct = abs(round(trend_delta * 100))
        parts.append(f"Lead trend: vulnerability score {dir_word} by {pct}% over the preceding 24h lead")
    elif ensemble.spread_growth_rate != 0.0:
        grow_dir = "expanding" if ensemble.spread_growth_rate > 0 else "consolidating"
        parts.append(f"Ensemble dispersion is {grow_dir} at {abs(ensemble.spread_growth_rate):.1f} {ensemble.units}/h")

    # Environmental pressure conditioning changes
    if environmental is not None and environmental.gradient_trend_hpa_per_100km is not None:
        grad_trend = environmental.gradient_trend_hpa_per_100km
        if abs(grad_trend) >= 0.2:
            dir_word = "strengthened" if grad_trend > 0 else "relaxed"
            parts.append(
                f"Environmental conditioning: radial pressure gradient {dir_word} by "
                f"{abs(grad_trend):.2f} hPa/100km"
            )

    if not parts:
        if trajectory is not None and not trajectory.has_prior_cycle:
            return "Baseline cycle initialization. No consecutive prior cycle available on disk for cycle-over-cycle delta."
        return "Reliability profile and ensemble spread remained consistent with the prior evaluation step."

    return ". ".join(parts) + "."


def build_structured_evidence(
    region_id: str,
    region_name: str,
    lead_hours: int,
    ensemble: EnsembleMetrics,
    trajectory: Optional[TrajectoryMetrics],
    reliability_state: str,
    calibrated_prob: Optional[float],
    trend_delta: Optional[float] = None,
    source_provenance: str = "NCMRWF NEPS (origin=dems, 11 members)",
    environmental: Optional[EnvironmentalIntelligenceResult] = None,
) -> StructuredEvidence:
    """Construct complete canonical Structured Evidence Object."""
    is_insufficient = ensemble.ensemble_state == "INSUFFICIENT_EVIDENCE"
    
    # Evidence status
    if is_insufficient:
        ev_status: EvidenceStatusLiteral = "INSUFFICIENT"
        ev_strength: EvidenceStrengthLiteral = "INSUFFICIENT_EVIDENCE"
    elif trajectory is not None and trajectory.has_prior_cycle:
        ev_status = "COMPLETE"
        ev_strength = "HIGH" if ensemble.member_count >= 11 else "MODERATE"
    else:
        ev_status = "PARTIAL"
        ev_strength = "MODERATE"

    # Ensemble evidence block
    ens_block = EnsembleEvidenceBlock(
        state=ensemble.ensemble_state,
        state_description=ensemble.state_description,
        member_count=ensemble.member_count,
        mean_spread=ensemble.mean_spread if not is_insufficient else None,
        spread_unit=ensemble.units,
        coherence_score=ensemble.coherence_score if not is_insufficient else None,
        anisotropy_ratio=ensemble.anisotropy_ratio if not is_insufficient else None,
        bimodality_coefficient=ensemble.bimodality_coefficient if not is_insufficient else None,
        dominant_cluster_fraction=ensemble.dominant_cluster_fraction if not is_insufficient else None,
        cluster_separation=ensemble.cluster_separation if not is_insufficient else None,
        pairwise_disagreement=ensemble.pairwise_disagreement if not is_insufficient else None,
        status="COMPLETE" if not is_insufficient else "INSUFFICIENT",
    )

    # Trajectory evidence block
    if trajectory is not None:
        traj_block = TrajectoryEvidenceBlock(
            state=trajectory.instability_state,
            state_description=trajectory.state_description,
            has_prior_cycle=trajectory.has_prior_cycle,
            reference_cycle=trajectory.reference_cycle,
            cycle_revision_distance_km=trajectory.cycle_revision_distance_km,
            cycle_spread_shift_km=trajectory.cycle_spread_shift_km,
            revision_rate_kmh=trajectory.revision_rate_kmh,
            trajectory_speed_kmh=trajectory.trajectory_speed_kmh,
            trajectory_curvature_deg=trajectory.trajectory_curvature_deg,
            spread_growth_rate=trajectory.spread_growth_rate,
            trajectory_instability_km=trajectory.trajectory_instability_km,
            status="COMPLETE" if trajectory.has_prior_cycle else "PARTIAL",
        )
        traj_trend = trajectory.trend
    else:
        traj_block = TrajectoryEvidenceBlock(
            state="INSUFFICIENT_EVIDENCE",
            state_description="Trajectory metrics unavailable.",
            has_prior_cycle=False,
            reference_cycle=None,
            cycle_revision_distance_km=None,
            cycle_spread_shift_km=None,
            revision_rate_kmh=None,
            trajectory_speed_kmh=None,
            trajectory_curvature_deg=None,
            spread_growth_rate=None,
            trajectory_instability_km=None,
            status="UNAVAILABLE",
        )
        traj_trend = "unavailable"

    # Environmental evidence block
    if environmental is not None:
        env_block = EnvironmentalEvidenceBlock(
            state=environmental.state,
            state_description=environmental.state_description,
            pressure_depth_hpa=environmental.pressure_depth_hpa,
            pressure_gradient_hpa_per_100km=environmental.pressure_gradient_hpa_per_100km,
            gradient_asymmetry_hpa_per_100km=environmental.gradient_asymmetry_hpa_per_100km,
            gradient_trend_hpa_per_100km=environmental.gradient_trend_hpa_per_100km,
            core_pressure_hpa=environmental.core_pressure_hpa,
            peripheral_pressure_hpa=environmental.peripheral_pressure_hpa,
            upper_air_shear_status=environmental.upper_air_shear_status,
            mid_level_humidity_status=environmental.mid_level_humidity_status,
            sst_status=environmental.sst_status,
            validation_status=environmental.validation_status,
            provenance=environmental.provenance,
            scientific_provenance_note=environmental.scientific_provenance_note,
            status="COMPLETE" if environmental.state != "INSUFFICIENT_EVIDENCE" else "INSUFFICIENT",
        )
    else:
        env_block = None

    why_now = generate_why_now_attribution(
        ensemble=ensemble,
        trajectory=trajectory,
        reliability_state=reliability_state,
        calibrated_prob=calibrated_prob,
        environmental=environmental,
    )

    what_changed = generate_what_changed_summary(
        ensemble=ensemble,
        trajectory=trajectory,
        trend_delta=trend_delta,
        environmental=environmental,
    )

    return StructuredEvidence(
        region_id=region_id,
        region_name=region_name,
        lead_hours=lead_hours,
        ensemble=ens_block,
        trajectory=traj_block,
        environmental=env_block,
        trend=traj_trend,
        why_now=why_now,
        what_changed=what_changed,
        evidence_status=ev_status,
        evidence_strength=ev_strength,
        source_provenance=source_provenance,
    )
