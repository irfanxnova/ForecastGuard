"""API endpoint integration tests for Multi-Model Forecast Agreement & NWP Evidence."""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_api_multimodel_audit_endpoint() -> None:
    """Verify GET /api/v1/inference/multimodel/audit returns accurate inventory and decision gate."""
    response = client.get("/api/v1/inference/multimodel/audit")
    assert response.status_code == 200

    data = response.json()
    assert data["total_models_cataloged"] >= 4
    assert data["available_operational_models"] == 1
    assert data["missing_archive_models"] >= 3
    assert data["decision_gate_status"] == "INSUFFICIENT_EVIDENCE"
    assert "NCMRWF_NEPS" in data["catalog"]
    assert data["catalog"]["NCMRWF_NEPS"]["status"] == "OPERATIONAL_ARCHIVED"
    assert "ECMWF_IFS" in data["catalog"]
    assert data["catalog"]["ECMWF_IFS"]["status"] == "MISSING_ARCHIVE"


def test_api_multimodel_agreement_single_model_failsafe() -> None:
    """Verify POST /api/v1/inference/multimodel/agreement returns INSUFFICIENT_EVIDENCE for 1 model."""
    payload = {
        "models": [
            {
                "model_id": "NCMRWF_NEPS",
                "center": "NCMRWF",
                "initialization_time": "2023-10-20T12:00:00Z",
                "forecast_lead_hours": 24,
                "valid_time": "2023-10-21T12:00:00Z",
                "latitude": 15.0,
                "longitude": 88.0,
                "mslp_hpa": 990.0,
            }
        ]
    }

    response = client.post("/api/v1/inference/multimodel/agreement", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["state"] == "INSUFFICIENT_EVIDENCE"
    assert data["available_model_count"] == 1
    assert data["validation_status"] == "INSUFFICIENT_EVIDENCE"
    assert "insufficient independent models" in data["agreement_notice"]


def test_api_multimodel_agreement_two_models_evaluation() -> None:
    """Verify POST /api/v1/inference/multimodel/agreement evaluates agreement when 2 models supplied."""
    payload = {
        "models": [
            {
                "model_id": "NCMRWF_NEPS",
                "center": "NCMRWF",
                "initialization_time": "2023-10-20T12:00:00Z",
                "forecast_lead_hours": 24,
                "valid_time": "2023-10-21T12:00:00Z",
                "latitude": 15.0,
                "longitude": 88.0,
                "mslp_hpa": 990.0,
            },
            {
                "model_id": "ECMWF_IFS",
                "center": "ECMWF",
                "initialization_time": "2023-10-20T12:00:00Z",
                "forecast_lead_hours": 24,
                "valid_time": "2023-10-21T12:00:00Z",
                "latitude": 15.2,
                "longitude": 88.1,
                "mslp_hpa": 992.0,
            },
        ]
    }

    response = client.post("/api/v1/inference/multimodel/agreement", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["state"] in ("AGREEMENT", "MODERATE_DISAGREEMENT", "HIGH_DISAGREEMENT")
    assert data["available_model_count"] == 2
    assert data["mean_track_separation_km"] is not None
    assert data["max_track_separation_km"] is not None
    assert data["validation_status"] == "EXPERIMENTAL"


def test_api_predict_includes_multimodel_evidence() -> None:
    """Verify POST /api/v1/inference/predict includes multimodel_evidence in canonical response."""
    payload = {
        "forecast_cycle": "2023-05-11T00:00:00Z",
        "lead_hours": 24,
        "valid_time": "2023-05-12T00:00:00Z",
        "ensemble_members": [
            {"member_id": i, "latitude": 15.0 + i * 0.1, "longitude": 88.0 + i * 0.1}
            for i in range(1, 12)
        ],
    }

    response = client.post("/api/v1/inference/predict", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "multimodel_evidence" in data
    assert data["multimodel_evidence"] is not None
    assert data["multimodel_evidence"]["state"] == "INSUFFICIENT_EVIDENCE"
    assert data["multimodel_evidence"]["available_model_count"] == 1


def test_api_multimodel_rejects_ground_truth_leakage() -> None:
    """Verify that multi-model agreement schema forbids future observation or verification targets."""
    payload = {
        "models": [
            {
                "model_id": "NCMRWF_NEPS",
                "center": "NCMRWF",
                "initialization_time": "2023-10-20T12:00:00Z",
                "forecast_lead_hours": 24,
                "valid_time": "2023-10-21T12:00:00Z",
                "latitude": 15.0,
                "longitude": 88.0,
                "track_error_km": 42.0,  # FORBIDDEN target leakage!
            }
        ]
    }

    response = client.post("/api/v1/inference/multimodel/agreement", json=payload)
    assert response.status_code in (400, 422)
