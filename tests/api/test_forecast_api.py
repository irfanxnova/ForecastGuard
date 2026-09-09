"""Tests for live forecast exploration and operational capability discipline."""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import create_app

app = create_app()


@pytest.fixture
def client() -> TestClient:
    """TestClient fixture for FastAPI application."""
    return TestClient(app)


def test_forecast_locations_endpoint(client: TestClient) -> None:
    """Verify GET /api/v1/forecast/locations returns vetted presets."""
    response = client.get("/api/v1/forecast/locations")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 5

    names = [loc["name"] for loc in data]
    assert "Bay of Bengal (Cyclone Midhili Sector)" in names
    assert "Arabian Sea (Cyclone Biparjoy Sector)" in names

    # Validate schema fields
    for loc in data:
        assert "name" in loc
        assert "latitude" in loc
        assert "longitude" in loc


def test_live_forecast_validated_cyclone_case(client: TestClient) -> None:
    """Verify live forecast returns real calibrated bust probability for supported cyclone cases."""
    response = client.get(
        "/api/v1/forecast/live",
        params={
            "latitude": 20.8,
            "longitude": 90.5,
            "case_id": "MIDHILI_00Z",
            "location_name": "Midhili Verification Sector",
        },
    )
    assert response.status_code == 200
    data = response.json()

    assert data["capability_status"] == "VALIDATED_CYCLONE_DOMAIN"
    assert data["calibrated_bust_probability"] is not None
    assert 0.0 <= data["calibrated_bust_probability"] <= 1.0
    assert "%" in data["bust_probability_display"]
    assert len(data["forecast_steps"]) == 10
    assert data["forecast_steps"][0]["lead_day"] == "D+1"
    assert data["forecast_steps"][9]["lead_day"] == "D+10"
    assert data["evidence_summary"] is not None
    assert "evidence_rows" in data["evidence_summary"]
    assert len(data["evidence_summary"]["evidence_rows"]) >= 4


def test_live_forecast_unvalidated_coordinates_discipline(client: TestClient) -> None:
    """Verify unvalidated coordinates strictly output capability notice with null bust probability."""
    response = client.get(
        "/api/v1/forecast/live",
        params={
            "latitude": 28.6139,
            "longitude": 77.2090,
            "location_name": "New Delhi Urban Sector",
        },
    )
    assert response.status_code == 200
    data = response.json()

    # CRITICAL SCIENTIFIC INTEGRITY CHECK:
    # Must never fabricate a bust probability or scientific risk score outside validated population
    assert data["capability_status"] == "NOT_VALIDATED_FOR_THIS_INPUT_DOMAIN"
    assert data["calibrated_bust_probability"] is None
    assert data["bust_probability_display"] == "NOT VALIDATED FOR THIS INPUT DOMAIN"
    assert "NOT VALIDATED FOR THIS INPUT DOMAIN" in data["scientific_boundary_notice"]
    assert len(data["forecast_steps"]) == 10
    assert data["location"]["latitude"] == 28.6139
    assert data["location"]["longitude"] == 77.2090


def test_live_forecast_coordinate_bounds_validation(client: TestClient) -> None:
    """Verify invalid coordinate bounds return 422 validation error."""
    # Latitude > 90
    response = client.get(
        "/api/v1/forecast/live",
        params={"latitude": 95.0, "longitude": 80.0},
    )
    assert response.status_code == 422

    # Latitude < -90
    response = client.get(
        "/api/v1/forecast/live",
        params={"latitude": -95.0, "longitude": 80.0},
    )
    assert response.status_code == 422
