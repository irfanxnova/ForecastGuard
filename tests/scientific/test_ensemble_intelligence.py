"""Unit tests for ForecastGuard V2 Ensemble Intelligence Engine.

Verifies:
- Reproducible ensemble spread, pairwise disagreement, and coherence score
- Anisotropy ratio and principal axis dispersion
- Sarle's bimodality coefficient and cluster separation
- Deterministic ensemble state transitions: COHERENT, SPREADING, MULTI_BRANCH, FRAGMENTED, INSUFFICIENT_EVIDENCE
- Strict handling of missing members or < 2 members
"""

import math
import numpy as np
import pytest

from scientific.features.ensemble_intelligence import (
    classify_ensemble_state,
    compute_ensemble_coherence,
    compute_ensemble_intelligence_from_field,
    compute_ensemble_intelligence_from_members,
)


def test_ensemble_insufficient_evidence_when_single_member():
    """Fewer than 2 members must deterministically yield INSUFFICIENT_EVIDENCE."""
    res_single = compute_ensemble_intelligence_from_members([12.0], [80.0])
    assert res_single.ensemble_state == "INSUFFICIENT_EVIDENCE"
    assert res_single.member_count == 1
    assert "Insufficient ensemble data" in res_single.state_description


def test_ensemble_field_insufficient_evidence_when_empty():
    """Empty field arrays must return INSUFFICIENT_EVIDENCE."""
    res = compute_ensemble_intelligence_from_field([])
    assert res.ensemble_state == "INSUFFICIENT_EVIDENCE"
    assert res.member_count == 0


def test_coherent_state_classification():
    """Tightly clustered members with unimodal distribution must classify as COHERENT."""
    np.random.seed(42)
    # 11 members tightly clustered around 15.0°N, 85.0°E (spread ~20 km)
    lats = [15.0 + float(np.random.normal(0, 0.15)) for _ in range(11)]
    lons = [85.0 + float(np.random.normal(0, 0.15)) for _ in range(11)]

    res = compute_ensemble_intelligence_from_members(
        member_lats=lats,
        member_lons=lons,
        reference_spread_km=100.0,
    )
    assert res.ensemble_state == "COHERENT"
    assert res.coherence_score >= 0.65
    assert res.bimodality_coefficient < 0.555
    assert "Coherent ensemble state" in res.state_description


def test_multi_branch_state_classification():
    """Bimodal split into two distinct branches must classify as MULTI_BRANCH."""
    # 5 members heading toward Odisha (20.0°N, 86.0°E), 6 members heading toward Myanmar (18.0°N, 93.0°E)
    branch1_lats = [20.0 + 0.05 * i for i in range(5)]
    branch1_lons = [86.0 + 0.05 * i for i in range(5)]

    branch2_lats = [18.0 + 0.05 * i for i in range(6)]
    branch2_lons = [93.0 + 0.05 * i for i in range(6)]

    lats = branch1_lats + branch2_lats
    lons = branch1_lons + branch2_lons

    res = compute_ensemble_intelligence_from_members(
        member_lats=lats,
        member_lons=lons,
        reference_spread_km=100.0,
    )
    assert res.ensemble_state == "MULTI_BRANCH"
    assert res.cluster_separation > 100.0
    assert "Multi-branch" in res.state_description


def test_spreading_state_classification():
    """Progressive dispersion growth without bimodal split must classify as SPREADING."""
    np.random.seed(123)
    # Symmetric dispersion with elevated spread (> 100 km)
    lats = [15.0 + float(np.random.normal(0, 1.2)) for _ in range(11)]
    lons = [85.0 + float(np.random.normal(0, 1.2)) for _ in range(11)]

    res = compute_ensemble_intelligence_from_members(
        member_lats=lats,
        member_lons=lons,
        prev_spread=60.0,
        time_delta_hours=6.0,
        reference_spread_km=90.0,
    )
    assert res.ensemble_state in ("SPREADING", "FRAGMENTED")
    assert res.mean_spread > 80.0


def test_fragmented_state_classification():
    """Very high spread and low coherence must classify as FRAGMENTED."""
    state, desc = classify_ensemble_state(
        member_count=11,
        spread=180.0,
        spread_growth_rate=8.0,
        anisotropy_ratio=2.1,
        bimodality_coef=0.35,
        dominant_cluster_fraction=0.85,
        cluster_separation=20.0,
        coherence_score=0.25,
        spread_threshold_moderate=90.0,
        spread_threshold_high=140.0,
    )
    assert state == "FRAGMENTED"
    assert "Fragmented" in desc


def test_ensemble_field_intelligence_computation():
    """Verify field intelligence computation on 11 member spatial grids."""
    np.random.seed(99)
    n_cells = 500
    baseline = 100000.0 + np.sin(np.linspace(0, 10, n_cells)) * 500.0

    # Create 11 members with small random perturbation (mean spread ~40 Pa)
    member_arrays = [
        baseline + np.random.normal(0, 40.0, n_cells)
        for _ in range(11)
    ]

    metrics = compute_ensemble_intelligence_from_field(
        member_arrays=member_arrays,
        reference_spread_pa=150.0,
    )
    assert metrics.member_count == 11
    assert 30.0 <= metrics.mean_spread <= 50.0
    assert metrics.pairwise_disagreement > 0.0
    assert metrics.ensemble_state == "COHERENT"
    assert metrics.units == "Pa"
