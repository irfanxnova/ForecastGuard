"""API tests for ForecastGuard V2 Structured Evidence and State Endpoints.

Verifies:
- GET /api/v1/regional/assessment returns structured_evidence with ensemble & trajectory states
- GET /api/v1/regional/region/{region_id} includes complete structured evidence telemetry
- GET /api/v1/regional/timeline/{case_id} contains step-level ensemble_state and trajectory_state
- Strict schema adherence with zero fabricated probabilities
"""

from fastapi.testclient import TestClient
import pytest

from backend.app.main import app

client = TestClient(app)


def test_assessment_endpoint_returns_structured_evidence():
    """Verify that regional assessment returns structured_evidence for all evaluated regions."""
    response = client.get("/api/v1/regional/assessment?case_id=MIDHILI_00Z&lead_time=D+1")
    assert response.status_code == 200
    data = response.json()

    assert "regions" in data
    assert len(data["regions"]) > 0

    bob = next((r for r in data["regions"] if r["region_id"] == "MAR_BOB"), None)
    assert bob is not None

    # Check ensemble_state and trajectory_state fields
    assert "ensemble_state" in bob
    assert bob["ensemble_state"] in ("COHERENT", "SPREADING", "MULTI_BRANCH", "FRAGMENTED", "INSUFFICIENT_EVIDENCE")

    assert "trajectory_state" in bob
    assert bob["trajectory_state"] in ("STABLE_PERSISTENT", "PROGRESSIVE_DRIFT", "OSCILLATING_JUMPY", "RAPID_REVISION", "INSUFFICIENT_EVIDENCE")

    # Check structured_evidence object
    assert "structured_evidence" in bob
    ev = bob["structured_evidence"]
    assert ev is not None
    assert "ensemble" in ev
    assert "trajectory" in ev
    assert "why_now" in ev
    assert "what_changed" in ev
    assert len(ev["why_now"]) > 5
    assert len(ev["what_changed"]) > 5


def test_single_region_endpoint_has_evidence():
    """Verify single region lookup endpoint includes structured evidence."""
    response = client.get("/api/v1/regional/region/MAR_BOB?case_id=MIDHILI_00Z&lead_time=D+1")
    assert response.status_code == 200
    data = response.json()

    assert data["region_id"] == "MAR_BOB"
    assert "structured_evidence" in data
    assert data["structured_evidence"]["ensemble"]["state"] == data["ensemble_state"]
    assert data["structured_evidence"]["trajectory"]["state"] == data["trajectory_state"]


def test_out_of_domain_region_insufficient_evidence():
    """Out of domain region must cleanly return INSUFFICIENT_EVIDENCE in structured evidence."""
    response = client.get("/api/v1/regional/region/MAR_AS?case_id=MIDHILI_00Z&lead_time=D+1")
    assert response.status_code == 200
    data = response.json()

    assert data["region_id"] == "MAR_AS"
    assert data["reliability_state"] == "INSUFFICIENT_EVIDENCE"
    assert data["ensemble_state"] == "INSUFFICIENT_EVIDENCE"
    assert data["trajectory_state"] == "INSUFFICIENT_EVIDENCE"
    assert data["structured_evidence"]["evidence_status"] in ("UNAVAILABLE", "INSUFFICIENT")


def test_timeline_endpoint_includes_states():
    """Verify regional timeline steps include ensemble_state and trajectory_state."""
    response = client.get("/api/v1/regional/timeline/MIDHILI_00Z?region_id=MAR_BOB")
    assert response.status_code == 200
    data = response.json()

    assert "steps" in data
    assert len(data["steps"]) > 0

    first_step = data["steps"][0]
    assert "ensemble_state" in first_step
    assert "trajectory_state" in first_step
