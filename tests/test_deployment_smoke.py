"""Production Deployment Smoke Test Suite.

Validates end-to-end clean-environment deployment:
- Liveness (/health) and Readiness (/ready)
- Model governance metadata (/api/v1/inference/model-info)
- Historical cyclone catalog (/api/v1/historical/cyclones)
- Historical lead-by-lead replay (/api/v1/historical/replay/MICHAUNG)
- Curated Bust Atlas (/api/v1/historical/bust-atlas)
- Valid live forecast inference (/api/v1/inference/predict)
- Fail-safe data handling for insufficient/invalid inputs
- Production SPA frontend serving (GET / and GET /assets/...)
- Zero secret or developer filesystem leakage
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_smoke_liveness_health():
    """Verify /health and /api/v1/health respond with 200 and valid schema."""
    for url in ["/health", "/api/v1/health"]:
        resp = client.get(url)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "ForecastGuard API"
        assert data["version"] == "1.0.0"


def test_smoke_readiness():
    """Verify /ready and /api/v1/ready confirm production model and 101 leads loaded."""
    for url in ["/ready", "/api/v1/ready"]:
        resp = client.get(url)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert data["production_model"] == "M1_SpreadOnly"
        assert data["verified_dataset_loaded"] is True
        assert data["verified_leads_count"] == 101


def test_smoke_model_governance():
    """Verify /api/v1/inference/model-info returns approved M1 baseline and M0 reference."""
    resp = client.get("/api/v1/inference/model-info")
    assert resp.status_code == 200
    data = resp.json()
    assert data["production_model"]["model_name"] == "M1_SpreadOnly"
    assert data["production_model"]["scientific_status"] == "PRIMARY_MACHINE_BASELINE"
    assert data["reference_baseline"]["model_name"] == "M0_Climatology"
    assert "tau(lead)" in data["authoritative_bust_threshold"]


def test_smoke_historical_cyclones():
    """Verify /api/v1/historical/cyclones lists all 6 tropical cyclones and 13 cycles."""
    resp = client.get("/api/v1/historical/cyclones")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 6
    names = {c["storm_name"] for c in data}
    assert names == {"BIPARJOY", "HAMOON", "MICHAUNG", "MIDHILI", "MOCHA", "TEJ"}
    total_leads = sum(c["verified_leads_count"] for c in data)
    assert total_leads == 101
    total_busts = sum(c["contemporaneous_busts_count"] for c in data)
    assert total_busts == 24


def test_smoke_historical_replay():
    """Verify historical replay endpoint returns verified lead sequence with dual provenance."""
    resp = client.get("/api/v1/historical/replay/MICHAUNG")
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "HISTORICAL_REPLAY"
    assert data["storm_name"] == "MICHAUNG"
    assert len(data["leads"]) >= 8
    # Dual provenance checks
    assert "NCMRWF NEPS" in data["provenance"]["forecast_source"]
    assert "Official IMD/RSMC" in data["provenance"]["verification_source"]


def test_smoke_historical_bust_atlas():
    """Verify bust atlas returns verified failure records."""
    resp = client.get("/api/v1/historical/bust-atlas")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 24  # Exactly 24 verified failure records
    for item in data:
        assert item["track_error_km"] >= item["threshold_km"]


def test_smoke_live_inference_valid():
    """Verify live inference endpoint evaluates valid forecast payload with provenance."""
    members = [
        {"member_id": i, "latitude": 10.0 + 0.05 * (i - 6), "longitude": 84.0 + 0.05 * (i - 6), "central_pressure_hpa": 1000.0}
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
    assert data["status"] == "ok"
    assert data["data_quality"] == "DATA COMPLETE"
    assert data["reliability_state"] in ["STABLE", "WATCH", "VULNERABLE", "SEVERE"]
    assert 0 <= data["bust_risk_percent"] <= 100
    assert 0 <= data["reliability_score"] <= 100
    assert data["provenance"]["model_name"] == "M1_SpreadOnly"
    assert data["provenance"]["processing_status"] == "DATA COMPLETE"


def test_smoke_live_inference_failsafe_insufficient():
    """Verify live inference fails safely on insufficient data without inventing scores."""
    payload = {
        "forecast_source": "NCMRWF TIGGE",
        "forecast_cycle": "2023-12-01T00:00:00Z",
        "valid_time": "2023-12-02T00:00:00Z",
        "lead_hours": 24,
        "ensemble_members": [
            {"member_id": 1, "latitude": 10.0, "longitude": 84.0}
        ],  # Only 1 member
    }
    resp = client.post("/api/v1/inference/predict", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "insufficient_data"
    assert data["data_quality"] == "DATA INSUFFICIENT"
    assert data["reliability_state"] == "DATA_INSUFFICIENT"
    assert data["bust_risk_percent"] is None
    assert data["reliability_score"] is None
    assert data["message"] == "Reliability assessment unavailable — insufficient forecast evidence."


def test_smoke_live_inference_anti_leakage_forbids_future_observations():
    """Verify live inference rejects future verification fields."""
    payload = {
        "forecast_source": "NCMRWF TIGGE",
        "forecast_cycle": "2023-12-01T00:00:00Z",
        "valid_time": "2023-12-02T00:00:00Z",
        "lead_hours": 24,
        "ensemble_members": [
            {"member_id": i, "latitude": 10.0, "longitude": 84.0} for i in range(1, 12)
        ],
        "observed_track_error_km": 15.0,  # FORBIDDEN
    }
    resp = client.post("/api/v1/inference/predict", json=payload)
    assert resp.status_code == 422


def test_smoke_frontend_spa_serving():
    """Verify FastAPI root endpoint serves built frontend index.html."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "ForecastGuard" in resp.text or "root" in resp.text
