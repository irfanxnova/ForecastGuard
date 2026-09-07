"""Tests for the health and readiness API endpoints."""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.schemas.health import HealthResponse, ReadinessResponse


@pytest.fixture
def client() -> TestClient:
    """TestClient fixture for FastAPI application."""
    return TestClient(app)


def test_health_endpoint_status_code(client: TestClient) -> None:
    """Verify GET /api/v1/health and GET /health return HTTP 200 OK."""
    for path in ["/api/v1/health", "/health"]:
        response = client.get(path)
        assert response.status_code == 200
        health = HealthResponse(**response.json())
        assert health.status == "ok"
        assert health.service == "ForecastGuard API"
        assert health.version == "1.0.0"


def test_readiness_endpoint(client: TestClient) -> None:
    """Verify GET /ready and GET /api/v1/ready return HTTP 200 OK with model and dataset status."""
    for path in ["/api/v1/ready", "/ready"]:
        response = client.get(path)
        assert response.status_code == 200
        ready = ReadinessResponse(**response.json())
        assert ready.status == "ready"
        assert ready.production_model == "M1_SpreadOnly"
        assert ready.verified_dataset_loaded is True
        assert ready.verified_leads_count == 101


def test_health_endpoint_contains_no_fabricated_data(client: TestClient) -> None:
    """Ensure no fake weather, ML predictions, or risk scores are present."""
    response = client.get("/api/v1/health")
    data = response.json()

    forbidden_keys = {
        "risk_score",
        "bust_probability",
        "weather",
        "forecast",
        "temperature",
        "precipitation",
        "model_accuracy",
    }
    present_keys = set(data.keys())
    intersection = forbidden_keys.intersection(present_keys)
    assert not intersection, f"Found unexpected keys in health check response: {intersection}"
