"""Tests for ForecastGuard V2 Historical Replay Engine and Temporal Reliability Evolution.

Strictly verifies AGENTS.md rules:
- Rule 4: Never use future observations as predictor features.
- Rule 6: Every prediction must use only information available at forecast cutoff.
- Rule 14: Never invent historical cases or historical verification results.
- Rule 15: UI values must ultimately come from backend/data layer.
- Priority 1: Correct verification semantics (PENDING_VERIFICATION before valid time).
- Priority 2: Deterministic replay stepping and warning lead time calculation.
- Priority 3: Cycle-over-cycle comparison.
"""

from datetime import datetime
import pytest

from scientific.replay.replay_engine import replay_engine
from backend.app.services.regional_service import regional_service


def test_replay_engine_knowledge_boundary():
    """Verify that future observations are locked prior to cutoff time."""
    replay = replay_engine.build_case_replay("MIDHILI_00Z", focused_region_id="MAR_BOB")
    assert replay.case_id == "MIDHILI_00Z"
    assert replay.total_steps == 9  # T+0h, T+6h, T+12h, T+18h, T+24h, T+30h, T+36h, T+42h, T+48h

    # Step 0: T+0h (Cycle Initialization)
    step_0 = replay.steps[0]
    assert step_0.elapsed_hours == 0
    assert step_0.knowledge_boundary.elapsed_hours == 0
    # At T+0h, zero observations should be unlocked (all future valid times are > init_time)
    assert step_0.knowledge_boundary.available_observations_count == 0
    assert step_0.knowledge_boundary.future_observations_locked_count > 0
    assert step_0.knowledge_boundary.future_information_locked is True
    assert "FUTURE INFORMATION LOCKED" in step_0.knowledge_boundary.boundary_statement

    # Step 4: T+24h
    step_24 = replay.steps[4]
    assert step_24.elapsed_hours == 24
    # At T+24h, observations up to +24h should be unlocked, while +30h..+48h remain locked
    assert step_24.knowledge_boundary.available_observations_count > 0
    assert step_24.knowledge_boundary.future_observations_locked_count > 0

    # Step 8: T+48h (Final Step)
    step_48 = replay.steps[8]
    assert step_48.elapsed_hours == 48
    assert step_48.knowledge_boundary.future_observations_locked_count == 0
    assert step_48.knowledge_boundary.future_information_locked is False


def test_first_actionable_signal_calculation():
    """Verify exact calculation of warning lead time from real timestamps."""
    signal = replay_engine.compute_first_actionable_signal("MIDHILI_00Z", target_region_id="MAR_BOB")
    assert signal is not None
    assert signal.alert_triggered is True
    assert signal.signal_lead_hours is not None
    assert signal.downstream_failure_lead_hours is not None
    assert signal.warning_lead_hours is not None
    assert signal.warning_lead_hours > 0.0
    # Expected warning lead: 48h - 18h = 30h
    assert signal.warning_lead_hours == 30.0
    assert "Warning Lead" in signal.warning_lead_label


def test_first_actionable_signal_nominal_storm():
    """Verify that a storm with zero verified busts returns no false alarm alert."""
    signal = replay_engine.compute_first_actionable_signal("MICHAUNG_00Z", target_region_id="MAR_BOB")
    assert signal is not None
    assert signal.alert_triggered is False
    assert signal.warning_lead_hours is None
    assert "Zero verified forecast busts" in signal.narrative


def test_pending_verification_semantics():
    """Verify that verification status is PENDING_VERIFICATION before valid time."""
    # Forecast valid at 2023-11-17T00:00:00Z (D+1 / +24h)
    # 1. When cutoff is before valid time (e.g. at T+0h)
    resp_locked = regional_service.evaluate_regional_assessment(
        case_id="MIDHILI_00Z",
        lead_time="D+1",
        as_of_cutoff="2023-11-16T00:00:00Z",
        reveal_verification=True,
    )
    reg_locked = next(r for r in resp_locked.regions if r.region_id == "MAR_BOB")
    assert reg_locked.model_status == "VALIDATED"
    assert reg_locked.calibration_status == "CALIBRATED"
    assert reg_locked.verification_status == "PENDING_VERIFICATION"
    assert reg_locked.verification_detail is None

    # 2. When cutoff is at or after valid time (e.g. 2023-11-17T00:00:00Z)
    resp_unlocked = regional_service.evaluate_regional_assessment(
        case_id="MIDHILI_00Z",
        lead_time="D+1",
        as_of_cutoff="2023-11-17T00:00:00Z",
        reveal_verification=True,
    )
    reg_unlocked = next(r for r in resp_unlocked.regions if r.region_id == "MAR_BOB")
    assert reg_unlocked.model_status == "VALIDATED"
    assert reg_unlocked.calibration_status == "CALIBRATED"
    assert reg_unlocked.verification_status == "VERIFIED"
    assert reg_unlocked.verification_detail is not None
    assert reg_unlocked.verification_detail.track_error_km > 0.0

    # 3. When reveal_verification is explicitly False
    resp_hidden = regional_service.evaluate_regional_assessment(
        case_id="MIDHILI_00Z",
        lead_time="D+1",
        reveal_verification=False,
    )
    reg_hidden = next(r for r in resp_hidden.regions if r.region_id == "MAR_BOB")
    assert reg_hidden.verification_status == "PENDING_VERIFICATION"
    assert reg_hidden.verification_detail is None


def test_regional_timeline_generation():
    """Verify 6-hourly temporal timeline with state transitions."""
    timeline = regional_service.get_regional_timeline("MIDHILI_00Z", region_id="MAR_BOB")
    assert timeline.case_id == "MIDHILI_00Z"
    assert timeline.region_id == "MAR_BOB"
    assert len(timeline.steps) == 8  # 8 synoptic steps: 6, 12, 18, 24, 30, 36, 42, 48
    assert timeline.steps[0].lead_hours == 6
    assert timeline.steps[-1].lead_hours == 48

    # Verify state transitions recorded
    assert len(timeline.state_transitions) > 0
    first_trans = timeline.state_transitions[0]
    assert first_trans.from_state != first_trans.to_state
    assert first_trans.lead_hours in (6, 12, 18, 24, 30, 36, 42, 48)


def test_cycle_comparison():
    """Verify cycle comparison across consecutive cycles."""
    comp = regional_service.get_cycle_comparison("BIPARJOY_00Z", region_id="MAR_AS")
    assert comp is not None
    assert comp.current_cycle_iso == "2023-06-07T00:00:00Z"
    assert comp.region_id == "MAR_AS"
