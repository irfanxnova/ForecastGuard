"""Unit tests for ForecastGuard V2 Structured Evidence Engine.

Verifies:
- Deterministic construction of StructuredEvidence objects
- Factual attribution answering "WHY IS RELIABILITY DEGRADING?"
- Factual narrative answering "WHAT CHANGED?"
- Evidence status ('COMPLETE', 'PARTIAL', 'INSUFFICIENT') and evidence strength
- Non-LLM guarantee: strictly computed from physical signals
"""

import pytest

from scientific.features.ensemble_intelligence import (
    EnsembleMetrics,
    compute_ensemble_intelligence_from_members,
)
from scientific.features.trajectory_intelligence import (
    TrajectoryMetrics,
    compute_trajectory_intelligence,
)
from scientific.features.structured_evidence import (
    build_structured_evidence,
    generate_what_changed_summary,
    generate_why_now_attribution,
)


def test_structured_evidence_coherent_stable():
    """Verify structured evidence for stable, coherent forecast."""
    ens = EnsembleMetrics(
        member_count=11,
        mean_spread=45.0,
        spread_growth_rate=0.2,
        pairwise_disagreement=52.0,
        anisotropy_ratio=1.2,
        major_axis_spread=48.0,
        minor_axis_spread=42.0,
        bimodality_coefficient=0.32,
        dominant_cluster_fraction=1.0,
        cluster_separation=0.0,
        coherence_score=0.82,
        ensemble_state="COHERENT",
        state_description="Coherent ensemble state: tight member agreement.",
        units="km",
        is_validated=True,
    )
    traj = TrajectoryMetrics(
        case_id="TEST_00Z",
        region_id="MAR_BOB",
        forecast_cycle="2023-11-16T00:00:00Z",
        reference_cycle="2023-11-15T12:00:00Z",
        lead_hours=24,
        valid_time="2023-11-17T00:00:00Z",
        has_prior_cycle=True,
        cycle_revision_distance_km=18.5,
        cycle_spread_shift_km=-4.2,
        revision_rate_kmh=1.54,
        trajectory_speed_kmh=24.0,
        trajectory_curvature_deg=6.5,
        spread_growth_rate=0.2,
        trajectory_instability_km=3.0,
        instability_state="STABLE_PERSISTENT",
        state_description="Stable persistent trajectory: high cycle consistency.",
        trend="stable",
        is_validated=True,
    )

    ev = build_structured_evidence(
        region_id="MAR_BOB",
        region_name="Bay of Bengal Basin",
        lead_hours=24,
        ensemble=ens,
        trajectory=traj,
        reliability_state="STABLE",
        calibrated_prob=0.12,
        trend_delta=0.0,
    )

    assert ev.evidence_status == "COMPLETE"
    assert ev.evidence_strength == "HIGH"
    assert ev.ensemble.state == "COHERENT"
    assert ev.trajectory.state == "STABLE_PERSISTENT"
    assert "stable" in ev.why_now.lower()
    assert "shifted by 18.5 km" in ev.what_changed


def test_structured_evidence_rapid_revision_and_spreading():
    """Verify structured evidence when forecast experiences rapid revision and spreading dispersion."""
    ens = EnsembleMetrics(
        member_count=11,
        mean_spread=165.0,
        spread_growth_rate=8.5,
        pairwise_disagreement=195.0,
        anisotropy_ratio=2.45,
        major_axis_spread=190.0,
        minor_axis_spread=80.0,
        bimodality_coefficient=0.48,
        dominant_cluster_fraction=0.82,
        cluster_separation=45.0,
        coherence_score=0.32,
        ensemble_state="SPREADING",
        state_description="Spreading ensemble uncertainty.",
        units="km",
        is_validated=True,
    )
    traj = TrajectoryMetrics(
        case_id="TEST_00Z",
        region_id="MAR_BOB",
        forecast_cycle="2023-11-16T00:00:00Z",
        reference_cycle="2023-11-15T12:00:00Z",
        lead_hours=48,
        valid_time="2023-11-18T00:00:00Z",
        has_prior_cycle=True,
        cycle_revision_distance_km=112.4,
        cycle_spread_shift_km=42.0,
        revision_rate_kmh=9.37,
        trajectory_speed_kmh=31.0,
        trajectory_curvature_deg=35.0,
        spread_growth_rate=8.5,
        trajectory_instability_km=25.0,
        instability_state="RAPID_REVISION",
        state_description="Rapid cycle-to-cycle forecast revision.",
        trend="increasing",
        is_validated=True,
    )

    ev = build_structured_evidence(
        region_id="MAR_BOB",
        region_name="Bay of Bengal Basin",
        lead_hours=48,
        ensemble=ens,
        trajectory=traj,
        reliability_state="HIGH_RISK",
        calibrated_prob=0.34,
        trend_delta=0.12,
    )

    assert ev.ensemble.state == "SPREADING"
    assert ev.trajectory.state == "RAPID_REVISION"
    assert "112.4 km" in ev.why_now
    assert "shifted by 112.4 km" in ev.what_changed


def test_structured_evidence_insufficient():
    """Verify that insufficient data produces clean INSUFFICIENT evidence blocks."""
    ens_ins = EnsembleMetrics(
        member_count=0,
        mean_spread=0.0,
        spread_growth_rate=0.0,
        pairwise_disagreement=0.0,
        anisotropy_ratio=1.0,
        major_axis_spread=0.0,
        minor_axis_spread=0.0,
        bimodality_coefficient=0.333,
        dominant_cluster_fraction=1.0,
        cluster_separation=0.0,
        coherence_score=0.0,
        ensemble_state="INSUFFICIENT_EVIDENCE",
        state_description="No data.",
        units="km",
        is_validated=True,
    )

    ev = build_structured_evidence(
        region_id="MAR_AS",
        region_name="Arabian Sea Basin",
        lead_hours=24,
        ensemble=ens_ins,
        trajectory=None,
        reliability_state="INSUFFICIENT_EVIDENCE",
        calibrated_prob=None,
    )

    assert ev.evidence_status == "INSUFFICIENT"
    assert ev.evidence_strength == "INSUFFICIENT_EVIDENCE"
    assert ev.ensemble.state == "INSUFFICIENT_EVIDENCE"
    assert ev.trajectory.state == "INSUFFICIENT_EVIDENCE"
    assert "insufficient" in ev.why_now.lower()
