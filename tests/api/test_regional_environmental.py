"""API Tests for Regional Environmental Conditioning Intelligence."""

from fastapi.testclient import TestClient
import pytest

from backend.app.main import app

client = TestClient(app)


def test_regional_assessment_includes_environmental_intelligence():
    """Verify that canonical regional assessment includes real Environmental Intelligence."""
    resp = client.get("/api/v1/regional/assessment?case_id=MIDHILI_00Z&lead_time=D+1")
    assert resp.status_code == 200
    data = resp.json()

    # Find focused active region (Bay of Bengal)
    bob = next((r for r in data["regions"] if r["region_id"] == "MAR_BOB"), None)
    assert bob is not None
    assert "environmental_state" in bob
    assert bob["environmental_state"] in [
        "SYMMETRIC_DEEP_PRESSURE_STRUCTURE",
        "MARGINAL_PRESSURE_STRUCTURE",
        "ASYMMETRIC_WEAK_PRESSURE_STRUCTURE",
    ]
    assert "shear" not in bob["environmental_state"].lower()
    assert "proxy" not in bob["environmental_state"].lower()

    # Check StructuredEvidence environmental block
    se = bob.get("structured_evidence")
    assert se is not None
    assert "environmental" in se
    env = se["environmental"]
    assert env is not None
    assert env["state"] == bob["environmental_state"]
    assert env["pressure_depth_hpa"] is not None
    assert env["pressure_gradient_hpa_per_100km"] is not None
    assert env["gradient_asymmetry_hpa_per_100km"] is not None

    # Verify locked / unavailable variable transparency
    assert env["upper_air_shear_status"] == "UNAVAILABLE"
    assert env["mid_level_humidity_status"] == "UNAVAILABLE"
    assert env["sst_status"] == "UNAVAILABLE"
    assert env["validation_status"] == "EXPERIMENTAL"

    # Verify explicit provenance note separating MSLP from direct shear measurement
    assert "scientific_provenance_note" in env
    prov_note = env["scientific_provenance_note"].lower()
    assert "vertical wind shear" in prov_note
    assert "not a direct measurement" in prov_note

    # Verify non-causal language in why_now
    why_now = se["why_now"].lower()
    assert "caused" not in why_now
    assert "because of" not in why_now
    assert "shear proxy" not in why_now
    assert "steering dipole proxy" not in why_now


def test_regional_timeline_includes_environmental_state():
    """Verify that regional timeline steps include environmental state."""
    resp = client.get("/api/v1/regional/timeline/MIDHILI_00Z?region_id=MAR_BOB")
    assert resp.status_code == 200
    data = resp.json()

    steps = data["steps"]
    assert len(steps) >= 2
    for step in steps:
        assert "environmental_state" in step
        assert step["environmental_state"] is not None


def test_unsupported_region_environmental_insufficient():
    """Verify that regions outside domain have clean INSUFFICIENT_EVIDENCE environmental blocks."""
    resp = client.get("/api/v1/regional/assessment?case_id=MIDHILI_00Z&lead_time=D+1")
    assert resp.status_code == 200
    data = resp.json()

    arabian_sea = next((r for r in data["regions"] if r["region_id"] == "MAR_AS"), None)
    assert arabian_sea is not None
    assert arabian_sea["environmental_state"] == "INSUFFICIENT_EVIDENCE"
    se = arabian_sea.get("structured_evidence")
    assert se is not None
    env = se.get("environmental")
    assert env is not None
    assert env["state"] == "INSUFFICIENT_EVIDENCE"
    assert env["pressure_depth_hpa"] is None
    assert env["pressure_gradient_hpa_per_100km"] is None
