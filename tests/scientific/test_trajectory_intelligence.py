"""Unit tests for ForecastGuard V2 Forecast Trajectory Intelligence Engine.

Verifies:
- Haversine distance and forward bearing geometry
- Cycle-to-cycle revision comparison at identical verification valid time (T_valid)
- Strict anti-leakage invariants: cutoff T boundary strictly enforced
- Deterministic trajectory instability states:
  * STABLE_PERSISTENT
  * PROGRESSIVE_DRIFT
  * OSCILLATING_JUMPY
  * RAPID_REVISION
  * INSUFFICIENT_EVIDENCE
- Trajectory curvature, translation speed, and step distance jitter
"""

import math
import pytest

from scientific.features.trajectory_intelligence import (
    classify_trajectory_state,
    compute_bearing_deg,
    compute_trajectory_intelligence,
    haversine_distance,
)


def test_haversine_and_bearing_accuracy():
    """Verify standard geodetic calculation between known coordinates."""
    # 1 degree of latitude is approx 111.13 km
    dist = haversine_distance(10.0, 80.0, 11.0, 80.0)
    assert 110.5 <= dist <= 111.5

    # True North bearing from (10.0, 80.0) to (11.0, 80.0) is 0° / 360°
    bearing_north = compute_bearing_deg(10.0, 80.0, 11.0, 80.0)
    assert bearing_north == pytest.approx(0.0, abs=0.5)

    # Due East bearing from (10.0, 80.0) to (10.0, 81.0) is 90°
    bearing_east = compute_bearing_deg(10.0, 80.0, 10.0, 81.0)
    assert bearing_east == pytest.approx(90.0, abs=0.5)


def test_trajectory_insufficient_evidence_when_single_cycle():
    """When no prior cycle and no multi-lead history exists, state must be INSUFFICIENT_EVIDENCE."""
    traj = compute_trajectory_intelligence(
        case_id="TEST_00Z",
        region_id="MAR_BOB",
        forecast_cycle_iso="2023-11-16T00:00:00Z",
        lead_hours=6,
        valid_time_iso="2023-11-16T06:00:00Z",
        current_center=(15.0, 85.0),
        prior_cycle_center=None,
        prior_cycle_iso=None,
    )
    assert traj.instability_state == "INSUFFICIENT_EVIDENCE"
    assert traj.has_prior_cycle is False
    assert traj.cycle_revision_distance_km is None


def test_rapid_revision_state_classification():
    """Large cycle revision distance (>= 70 km) must classify as RAPID_REVISION."""
    state, desc = classify_trajectory_state(
        has_prior_cycle=True,
        cycle_revision_km=98.5,
        curvature_deg=10.0,
        instability_jitter_km=5.0,
        speed_kmh=20.0,
        spread_growth_rate=1.0,
    )
    assert state == "RAPID_REVISION"
    assert "Rapid cycle-to-cycle forecast revision" in desc
    assert "98.5 km" in desc


def test_oscillating_jumpy_state_classification():
    """Sharp heading curvature (>= 45°) or large translation jitter must classify as OSCILLATING_JUMPY."""
    state, desc = classify_trajectory_state(
        has_prior_cycle=True,
        cycle_revision_km=35.0,
        curvature_deg=65.2,
        instability_jitter_km=42.0,
        speed_kmh=22.0,
        spread_growth_rate=2.0,
    )
    assert state == "OSCILLATING_JUMPY"
    assert "Oscillating forecast trajectory" in desc


def test_progressive_drift_state_classification():
    """Moderate cycle revision (25-70 km) with smooth curvature must classify as PROGRESSIVE_DRIFT."""
    state, desc = classify_trajectory_state(
        has_prior_cycle=True,
        cycle_revision_km=44.2,
        curvature_deg=15.0,
        instability_jitter_km=10.0,
        speed_kmh=24.0,
        spread_growth_rate=0.5,
    )
    assert state == "PROGRESSIVE_DRIFT"
    assert "Progressive trajectory drift" in desc


def test_stable_persistent_state_classification():
    """Minimal cycle revision (< 25 km) and low curvature must classify as STABLE_PERSISTENT."""
    state, desc = classify_trajectory_state(
        has_prior_cycle=True,
        cycle_revision_km=14.8,
        curvature_deg=8.0,
        instability_jitter_km=4.0,
        speed_kmh=25.0,
        spread_growth_rate=0.1,
    )
    assert state == "STABLE_PERSISTENT"
    assert "Stable persistent trajectory" in desc


def test_trajectory_anti_leakage_boundary():
    """Verify that lead history only uses leads <= current lead hours (no future steps)."""
    # History with leads 6, 12, 18, 24
    history = [
        (6, 12.0, 85.0, 60.0),
        (12, 13.0, 85.2, 70.0),
        (18, 14.2, 85.5, 80.0),
        (24, 15.5, 86.0, 95.0),
    ]

    # Evaluated at lead 12h: only leads 6 and 12 should be accessible
    traj_12h = compute_trajectory_intelligence(
        case_id="TEST_00Z",
        region_id="MAR_BOB",
        forecast_cycle_iso="2023-11-16T00:00:00Z",
        lead_hours=12,
        valid_time_iso="2023-11-16T12:00:00Z",
        current_center=(13.0, 85.2),
        current_spread_km=70.0,
        lead_history=history,
    )
    # Speed computed over (12.0, 85.0) -> (13.0, 85.2) over 6 hours: ~113 km / 6h = ~18.8 km/h
    assert traj_12h.trajectory_speed_kmh == pytest.approx(18.8, abs=2.0)
    # Curvature needs at least 3 points, so at lead 12h curvature is None (anti-leakage)
    assert traj_12h.trajectory_curvature_deg is None

    # Evaluated at lead 18h: leads 6, 12, 18 accessible (3 points -> curvature exists)
    traj_18h = compute_trajectory_intelligence(
        case_id="TEST_00Z",
        region_id="MAR_BOB",
        forecast_cycle_iso="2023-11-16T00:00:00Z",
        lead_hours=18,
        valid_time_iso="2023-11-16T18:00:00Z",
        current_center=(14.2, 85.5),
        current_spread_km=80.0,
        lead_history=history,
    )
    assert traj_18h.trajectory_curvature_deg is not None
