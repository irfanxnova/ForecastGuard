"""Tests for Live Operational Inference, Fail-Safe Data QC, and Anti-Leakage."""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def build_valid_payload(member_count: int = 11, lead: int = 24):
    """Generate syntactically valid issuance-time ensemble forecast payload."""
    members = []
    for i in range(1, member_count + 1):
        members.append({
            "member_id": i,
            "latitude": 10.5 + 0.05 * (i - 6),
            "longitude": 84.2 + 0.05 * (i - 6),
            "central_pressure_hpa": 995.0 + i,
        })
    return {
        "forecast_source": "NCMRWF TIGGE",
        "forecast_cycle": "2023-12-01T00:00:00Z",
        "valid_time": "2023-12-02T00:00:00Z",
        "lead_hours": lead,
        "variable": "Mean Sea Level Pressure (msl)",
        "deterministic_lat": 10.5,
        "deterministic_lon": 84.2,
        "ensemble_members": members,
    }


def test_live_inference_data_complete():
    """Verify live inference with complete 11-member ensemble."""
    payload = build_valid_payload(11, 24)
    response = client.post("/api/v1/inference/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["data_quality"] == "DATA COMPLETE"
    assert data["reliability_state"] in ["STABLE", "WATCH", "VULNERABLE", "SEVERE"]
    assert isinstance(data["bust_risk_percent"], int)
    assert isinstance(data["reliability_score"], int)
    assert "spread" in data["message"].lower()
    # Check complete provenance
    prov = data["provenance"]
    assert prov["forecast_source"] == "NCMRWF TIGGE"
    assert prov["model_name"] == "M1_SpreadOnly"
    assert prov["scientific_status"] == "PRIMARY_MACHINE_BASELINE"
    assert prov["processing_status"] == "DATA COMPLETE"


def test_live_inference_data_degraded_partial_ensemble():
    """Verify fail-safe handles partial ensemble (7 members) as DATA DEGRADED."""
    payload = build_valid_payload(7, 24)
    response = client.post("/api/v1/inference/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["data_quality"] == "DATA DEGRADED"
    assert "Degraded ensemble coverage" in data["quality_detail"]
    assert data["reliability_state"] is not None
    assert data["provenance"]["processing_status"] == "DATA DEGRADED"


def test_live_inference_data_insufficient_few_members():
    """Verify fail-safe: < 5 members returns DATA INSUFFICIENT with null score."""
    payload = build_valid_payload(3, 24)
    response = client.post("/api/v1/inference/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "insufficient_data"
    assert data["data_quality"] == "DATA INSUFFICIENT"
    assert data["reliability_state"] == "DATA_INSUFFICIENT"
    assert data["bust_risk_percent"] is None
    assert data["reliability_score"] is None
    assert data["message"] == "Reliability assessment unavailable — insufficient forecast evidence."


def test_live_inference_data_insufficient_nan_coords():
    """Verify fail-safe: NaN coordinate returns DATA INSUFFICIENT in production engine."""
    from backend.app.schemas.inference import LiveInferenceRequest, EnsembleMemberInput
    from backend.app.services.inference_engine import production_engine

    members = [
        EnsembleMemberInput(member_id=i, latitude=10.5, longitude=84.2, central_pressure_hpa=1000.0)
        for i in range(1, 12)
    ]
    # Inject NaN directly into an object
    members[0].latitude = float("nan")

    req = LiveInferenceRequest(
        forecast_source="NCMRWF TIGGE",
        forecast_cycle="2023-12-01T00:00:00Z",
        valid_time="2023-12-02T00:00:00Z",
        lead_hours=24,
        ensemble_members=members,
    )
    res = production_engine.evaluate(req)
    assert res.data_quality == "DATA INSUFFICIENT"
    assert res.bust_risk_percent is None
    assert res.message == "Reliability assessment unavailable — insufficient forecast evidence."


def test_live_inference_strict_anti_leakage_forbids_ground_truth():
    """Strict anti-leakage test: Live inference rejects any ground-truth or verification field."""
    payload = build_valid_payload(11, 24)
    # Attempt to inject verification data into live inference
    payload["observed_lat"] = 10.5
    payload["track_error_km"] = 15.2
    payload["confidence_quadrant"] = "QUADRANT_B_FALSE_CONFIDENCE"
    payload["is_bust"] = False

    response = client.post("/api/v1/inference/predict", json=payload)
    # Pydantic ConfigDict(extra='forbid') MUST reject with 422 Unprocessable Entity
    assert response.status_code == 422
    err_body = response.json()
    assert "error" in err_body or "detail" in err_body


def test_live_inference_rejects_invalid_timestamp():
    """Verify invalid timestamp formatting is rejected."""
    payload = build_valid_payload(11, 24)
    payload["forecast_cycle"] = "not-a-timestamp"
    response = client.post("/api/v1/inference/predict", json=payload)
    assert response.status_code == 422


def test_model_info_governance_endpoint():
    """Verify model-info returns approved M1 baseline and M0 reference metadata."""
    response = client.get("/api/v1/inference/model-info")
    assert response.status_code == 200
    data = response.json()
    assert data["production_model"]["model_name"] == "M1_SpreadOnly"
    assert data["production_model"]["scientific_status"] == "PRIMARY_MACHINE_BASELINE"
    assert data["reference_baseline"]["model_name"] == "M0_Climatology"
    assert len(data["research_catalog"]) == 7
