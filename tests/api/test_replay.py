"""API tests for ForecastGuard V2 Replay, Timeline, and Cycle Comparison Endpoints."""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_api_get_regional_timeline():
    """Test GET /api/v1/regional/timeline/{case_id}."""
    resp = client.get("/api/v1/regional/timeline/MIDHILI_00Z?region_id=MAR_BOB")
    assert resp.status_code == 200
    data = resp.json()
    assert data["case_id"] == "MIDHILI_00Z"
    assert data["region_id"] == "MAR_BOB"
    assert len(data["steps"]) == 8
    assert "first_actionable_signal" in data
    if data["first_actionable_signal"]:
        assert data["first_actionable_signal"]["alert_triggered"] is True
        assert data["first_actionable_signal"]["warning_lead_hours"] == 30.0


def test_api_get_case_replay():
    """Test GET /api/v1/regional/replay/{case_id}."""
    resp = client.get("/api/v1/regional/replay/MIDHILI_00Z?region_id=MAR_BOB")
    assert resp.status_code == 200
    data = resp.json()
    assert data["case_id"] == "MIDHILI_00Z"
    assert data["total_steps"] == 9
    assert len(data["steps"]) == 9

    # Verify knowledge boundary fields in steps
    step_0 = data["steps"][0]
    assert step_0["elapsed_hours"] == 0
    assert step_0["knowledge_boundary"]["future_information_locked"] is True
    assert step_0["knowledge_boundary"]["available_observations_count"] == 0

    # Verify final step has 0 locked observations
    step_48 = data["steps"][8]
    assert step_48["elapsed_hours"] == 48
    assert step_48["knowledge_boundary"]["future_information_locked"] is False


def test_api_get_cycle_comparison():
    """Test GET /api/v1/regional/comparison/{case_id}."""
    resp = client.get("/api/v1/regional/comparison/BIPARJOY_00Z?region_id=MAR_AS")
    assert resp.status_code == 200
    data = resp.json()
    assert data["region_id"] == "MAR_AS"
    assert data["current_cycle_iso"] == "2023-06-07T00:00:00Z"


def test_api_assessment_cutoff_and_reveal_toggle():
    """Test GET /api/v1/regional/assessment with as_of_cutoff and reveal_verification."""
    # 1. With cutoff before valid time
    resp = client.get(
        "/api/v1/regional/assessment?case_id=MIDHILI_00Z&lead_time=D%2B1&as_of_cutoff=2023-11-16T00:00:00Z&reveal_verification=true"
    )
    assert resp.status_code == 200
    data = resp.json()
    reg = next(r for r in data["regions"] if r["region_id"] == "MAR_BOB")
    assert reg["verification_status"] == "PENDING_VERIFICATION"
    assert reg["verification_detail"] is None

    # 2. With cutoff after valid time
    resp2 = client.get(
        "/api/v1/regional/assessment?case_id=MIDHILI_00Z&lead_time=D%2B1&as_of_cutoff=2023-11-17T00:00:00Z&reveal_verification=true"
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    reg2 = next(r for r in data2["regions"] if r["region_id"] == "MAR_BOB")
    assert reg2["verification_status"] == "VERIFIED"
    assert reg2["verification_detail"] is not None
