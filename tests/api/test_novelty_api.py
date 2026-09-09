"""API Tests for OOD Novelty, Support, and Abstention Endpoints."""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_api_reference_population_endpoint():
    """Verify GET /api/v1/inference/reference-population returns audited metadata."""
    resp = client.get("/api/v1/inference/reference-population")
    assert resp.status_code == 200
    data = resp.json()

    assert data["reference_id"] == "EXPANDED_CYCLONE_10CYCLES_77LEADS_MAY_NOV_2023"
    assert data["sample_count"] == 77
    assert data["historical_cycles_count"] == 10
    assert "MICHAUNG" not in data["historical_storms"]
    assert len(data["feature_names"]) == 4
    assert data["threshold_q75_well_represented"] == 0.8406
    assert data["threshold_q95_novel_state"] == 1.3601


def test_api_novelty_endpoint_valid_payload():
    """Verify POST /api/v1/inference/novelty returns structured representation assessment."""
    members = [
        {
            "member_id": i,
            "latitude": 15.0 + 0.08 * (i - 6),
            "longitude": 85.0 + 0.08 * (i - 6),
            "central_pressure_hpa": 995.0,
        }
        for i in range(1, 12)
    ]
    payload = {
        "forecast_source": "NCMRWF TIGGE",
        "forecast_cycle": "2023-12-01T00:00:00Z",
        "valid_time": "2023-12-02T00:00:00Z",
        "lead_hours": 24,
        "ensemble_members": members,
    }

    resp = client.post("/api/v1/inference/novelty", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["representation_state"] in [
        "WELL_REPRESENTED",
        "LOW_SUPPORT",
        "NOVEL_STATE",
        "INSUFFICIENT_EVIDENCE",
    ]
    assert 0.0 <= data["novelty_score"] <= 1.0
    assert 0 <= data["support_score"] <= 100
    assert data["distance"] is not None and data["distance"] > 0
    assert data["nearest_reference_distance"] is not None
    assert data["reference_population_size"] == 77
    assert data["coverage_ratio"] == 1.0
    assert isinstance(data["abstention_recommended"], bool)
    assert "historical reference population" in data["provenance"]["scientific_boundary_notice"]


def test_api_novelty_failsafe_insufficient_members():
    """Verify POST /api/v1/inference/novelty handles insufficient members with INSUFFICIENT_EVIDENCE."""
    payload = {
        "forecast_source": "NCMRWF TIGGE",
        "forecast_cycle": "2023-12-01T00:00:00Z",
        "valid_time": "2023-12-02T00:00:00Z",
        "lead_hours": 24,
        "ensemble_members": [
            {"member_id": 1, "latitude": 15.0, "longitude": 85.0}
        ],  # Only 1 member
    }

    resp = client.post("/api/v1/inference/novelty", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["representation_state"] == "INSUFFICIENT_EVIDENCE"
    assert data["abstention_recommended"] is True
    assert data["status"] == "ABSTAIN_INSUFFICIENT_EVIDENCE"
    assert data["distance"] is None


def test_api_predict_includes_novelty_assessment():
    """Verify POST /api/v1/inference/predict attaches novelty_assessment without altering risk index."""
    members = [
        {
            "member_id": i,
            "latitude": 15.0 + 0.05 * (i - 6),
            "longitude": 85.0 + 0.05 * (i - 6),
            "central_pressure_hpa": 995.0,
        }
        for i in range(1, 12)
    ]
    payload = {
        "forecast_source": "NCMRWF TIGGE",
        "forecast_cycle": "2023-12-01T00:00:00Z",
        "valid_time": "2023-12-02T00:00:00Z",
        "lead_hours": 24,
        "ensemble_members": members,
    }

    resp = client.post("/api/v1/inference/predict", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    # Core production baseline probability must be present and valid
    assert 0 <= data["bust_risk_percent"] <= 100
    assert 0 <= data["reliability_score"] <= 100

    # Novelty assessment must be attached
    assert "novelty_assessment" in data
    novelty = data["novelty_assessment"]
    assert novelty is not None
    assert novelty["representation_state"] in [
        "WELL_REPRESENTED",
        "LOW_SUPPORT",
        "NOVEL_STATE",
    ]
    assert novelty["reference_population_size"] == 77


def test_api_novelty_rejects_ground_truth_leakage():
    """Verify novelty endpoint strictly rejects ground truth observations with HTTP 422."""
    payload = {
        "forecast_source": "NCMRWF TIGGE",
        "forecast_cycle": "2023-12-01T00:00:00Z",
        "valid_time": "2023-12-02T00:00:00Z",
        "lead_hours": 24,
        "ensemble_members": [
            {"member_id": i, "latitude": 15.0, "longitude": 85.0} for i in range(1, 12)
        ],
        "observed_lat": 15.2,  # FORBIDDEN
    }

    resp = client.post("/api/v1/inference/novelty", json=payload)
    assert resp.status_code == 422
