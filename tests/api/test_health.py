"""Tests for the health check API endpoint."""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.schemas.health import HealthResponse


@pytest.fixture
def client() -> TestClient:
    """TestClient fixture for FastAPI application."""
    return TestClient(app)


def test_health_endpoint_status_code(client: TestClient) -> None:
    """Verify GET /api/v1/health returns HTTP 200 OK."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_health_endpoint_payload_structure(client: TestClient) -> None:
    """Verify health endpoint returns valid schema matching HealthResponse."""
    response = client.get("/api/v1/health")
    data = response.json()

    # Validate with Pydantic model
    health = HealthResponse(**data)
    assert health.status == "ok"
    assert health.service == "ForecastGuard API"
    assert health.version == "0.1.0"
    assert health.environment in ["development", "testing", "production"]


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
