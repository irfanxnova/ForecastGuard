"""API Integration Tests for Forecast Upload, Validation, and Operational Analysis Endpoints."""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def _get_valid_sample_payload():
    return {
        "cyclone_name": "MICHAUNG",
        "forecast_source": "NCMRWF_NEPS",
        "forecast_cycle": "2023-12-02T00:00:00Z",
        "lead_hours": 24,
        "valid_time": "2023-12-03T00:00:00Z",
        "basin": "Bay of Bengal",
        "ensemble_members": [
            {
                "member_id": i,
                "latitude": 13.5 + 0.08 * (i - 6),
                "longitude": 84.0 + 0.08 * (i - 6),
                "central_pressure_hpa": 985.0 + i,
            }
            for i in range(1, 12)
        ],
    }


def test_api_upload_valid_payload():
    """Verify POST /api/v1/inference/upload returns 200 and is_valid=True."""
    payload = _get_valid_sample_payload()
    resp = client.post("/api/v1/inference/upload", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["is_valid"] is True
    assert data["validation_status"] == "PASS"
    assert data["ensemble_members_count"] == 11
    assert data["verification_mode"] == "PROSPECTIVE_PENDING"
    assert len(data["errors"]) == 0


def test_api_upload_invalid_payload():
    """Verify POST /api/v1/inference/upload reports issues for malformed input."""
    payload = _get_valid_sample_payload()
    payload["ensemble_members"] = payload["ensemble_members"][:3]  # Only 3 members (need >= 5)
    payload["forecast_cycle"] = ""

    resp = client.post("/api/v1/inference/upload", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["is_valid"] is False
    assert data["validation_status"] == "REJECTED"
    assert len(data["errors"]) >= 1


def test_api_analyze_prospective_forecast():
    """Verify POST /api/v1/inference/analyze returns full evidence breakdown in PENDING_VERIFICATION."""
    payload = _get_valid_sample_payload()
    resp = client.post("/api/v1/inference/analyze", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    # Operational contracts
    assert data["verification_status"] == "PENDING_VERIFICATION"
    assert data["verification_detail"]["verified_track_error_km"] is None
    assert "pending" in data["verification_detail"]["message"].lower()

    # WHERE block
    assert "where" in data
    assert 5.0 <= data["where"]["centroid_lat"] <= 30.0
    assert 50.0 <= data["where"]["centroid_lon"] <= 100.0
    assert data["where"]["dispersion_radius_km"] > 0
    assert data["where"]["basin"] == "Bay of Bengal"

    # WHEN block
    assert "when" in data
    assert data["when"]["lead_hours"] == 24
    assert data["when"]["forecast_cycle"] is not None
    assert data["when"]["expected_failure_window"] is not None

    # RISK & Reliability
    assert 0 <= data["reliability_score"] <= 100
    assert 0 <= data["bust_risk_percent"] <= 100
    assert data["reliability_state"] in ["NOMINAL", "VULNERABLE", "HIGH_RISK", "STABLE", "WATCH", "AWAITING_VERIFIED_CASE"]

    # WHY block
    assert "why" in data
    assert data["why"]["ensemble_spread_km"] > 0
    assert data["why"]["ensemble_divergence_km"] > 0
    assert data["why"]["anisotropy_ratio"] >= 1.0
    assert len(data["why"]["ranked_factors"]) >= 3

    # Operational message
    assert "MICHAUNG" in data["message"]


def test_api_analyze_verified_forecast():
    """Verify POST /api/v1/inference/analyze computes verified error when observation provided."""
    payload = _get_valid_sample_payload()
    payload["observed_verification"] = {
        "observed_lat": 14.5,
        "observed_lon": 85.0,
        "observed_pressure_hpa": 980.0,
        "best_track_agency": "IMD_RSMC_NEW_DELHI",
    }

    resp = client.post("/api/v1/inference/analyze", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["verification_status"] == "VERIFIED"
    assert data["verification_detail"]["verified_track_error_km"] is not None
    assert data["verification_detail"]["verified_track_error_km"] > 0
    assert "outcome" in data["verification_detail"]


def test_api_sample_forecasts_catalog():
    """Verify GET /api/v1/inference/sample-forecasts returns preset fixtures."""
    resp = client.get("/api/v1/inference/sample-forecasts")
    assert resp.status_code == 200
    fixtures = resp.json()

    assert isinstance(fixtures, list)
    assert len(fixtures) >= 4
    for f in fixtures:
        assert "sample_id" in f
        assert "label" in f
        assert "description" in f
        assert "payload" in f


def test_api_live_status_endpoint():
    """Verify GET /api/v1/inference/live-status returns truthful live feed status."""
    resp = client.get("/api/v1/inference/live-status")
    assert resp.status_code == 200
    data = resp.json()

    assert "live_feed_available" in data
    assert data["live_feed_available"] is False
    assert "status" in data
    assert "alternatives" in data
    assert len(data["alternatives"]) >= 2
