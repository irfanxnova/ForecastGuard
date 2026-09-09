"""FastAPI integration tests for Historical Forecast Memory, Bust Atlas, and Fingerprints.

SIH26079: AI-Based Forecast Bust Detection for Medium-Range Weather Forecasts.
Validates:
1. POST /api/v1/historical/memory/search with valid state vector.
2. POST /api/v1/historical/memory/search rejects forbidden ground-truth fields (422).
3. POST /api/v1/historical/memory/search with query_case_id.
4. GET /api/v1/historical/memory/analogue/{case_id} detail lookup.
5. GET /api/v1/historical/bust-atlas/detail with query filters.
6. GET /api/v1/historical/fingerprint/{storm_name} failure fingerprint.
7. Proper 404 responses for nonexistent cases/storms.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_api_search_historical_memory_with_vector():
    """Verify POST /historical/memory/search returns ranked analogues and verified outcomes."""
    payload = {
        "query_state": {
            "lead_hours": 24,
            "ensemble_spread_km": 105.0,
            "anisotropy_ratio": 1.9,
            "bimodality_coefficient": 0.18,
            "trajectory_curvature_deg": 15.0,
        },
        "top_k": 4,
    }
    response = client.post("/api/v1/historical/memory/search", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["mode"] == "HISTORICAL_MEMORY_SEARCH"
    assert data["query_lead_hours"] == 24
    assert data["total_reference_cases"] == 101
    assert len(data["matches"]) == 4

    for match in data["matches"]:
        assert match["rank"] >= 1
        assert "case_id" in match
        assert "storm_name" in match
        assert 0.0 <= match["similarity_score"] <= 1.0
        assert 0 <= match["similarity_percent"] <= 100
        assert match["standardized_distance"] >= 0.0

        # Anti-leakage: verify verified outcome is present and clearly segregated
        outcome = match["verified_outcome"]
        assert outcome["verification_status"] == "VERIFIED"
        assert outcome["track_error_km"] is not None
        assert outcome["threshold_km"] is not None
        assert outcome["is_bust"] is not None

        # Verify dimension breakdown exists and is populated
        assert len(match["dimension_breakdown"]) >= 4

        # Verify failure fingerprint
        assert match["failure_fingerprint"] is not None
        assert "observed_pattern_summary" in match["failure_fingerprint"]


def test_api_search_historical_memory_anti_leakage_forbids_ground_truth():
    """Verify API strictly rejects ground-truth or error fields in query payload."""
    payload = {
        "query_state": {
            "lead_hours": 24,
            "ensemble_spread_km": 100.0,
            "track_error_km": 25.0,  # FORBIDDEN
        }
    }
    response = client.post("/api/v1/historical/memory/search", json=payload)
    assert response.status_code == 422


def test_api_search_historical_memory_by_case_id():
    """Verify search using an existing archive case ID."""
    payload = {
        "query_case_id": "2023_MIDHILI_MIDHILI_00Z_plus24h",
        "top_k": 3,
        "exclude_same_storm": True,
    }
    response = client.post("/api/v1/historical/memory/search", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["matches"]) == 3
    for match in data["matches"]:
        assert match["storm_name"] != "MIDHILI"


def test_api_get_analogue_detail():
    """Verify GET /historical/memory/analogue/{case_id} returns complete case details."""
    case_id = "2023_MOCHA_MOCHA_00Z_plus24h"
    response = client.get(f"/api/v1/historical/memory/analogue/{case_id}")
    assert response.status_code == 200
    data = response.json()

    assert data["case_id"] == case_id
    assert data["storm_name"] == "MOCHA"
    assert data["forecast_lead_hours"] == 24
    assert data["verified_outcome"]["verification_status"] == "VERIFIED"
    assert data["verified_outcome"]["track_error_km"] == 96.71
    assert data["verified_outcome"]["threshold_km"] == 107.28
    assert data["verified_outcome"]["is_bust"] is False


def test_api_get_analogue_detail_not_found():
    """Verify 404 for invalid case ID."""
    response = client.get("/api/v1/historical/memory/analogue/NON_EXISTENT_CASE")
    assert response.status_code == 404


def test_api_bust_atlas_detail_endpoint():
    """Verify GET /historical/bust-atlas/detail returns comprehensive records."""
    response = client.get("/api/v1/historical/bust-atlas/detail")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 20

    for record in data:
        assert record["verification_status"] == "VERIFIED"
        assert record["track_error_km"] >= record["threshold_km"]
        assert record["failure_fingerprint"] is not None
        assert "forecast_center" in record
        assert "observed_center" in record


def test_api_bust_atlas_detail_filtered():
    """Verify filtering bust atlas by storm name."""
    response = client.get("/api/v1/historical/bust-atlas/detail?storm_name=BIPARJOY")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    for record in data:
        assert record["storm_name"] == "BIPARJOY"


def test_api_storm_fingerprint():
    """Verify GET /historical/fingerprint/{storm_name} returns diagnostic summary."""
    response = client.get("/api/v1/historical/fingerprint/MIDHILI")
    assert response.status_code == 200
    data = response.json()

    assert data["storm_name"] == "MIDHILI"
    assert data["status"] == "VERIFIED"
    assert data["total_verified_leads"] == 8
    assert data["verified_busts_count"] == 6
    assert data["peak_track_error_km"] > 500.0  # Midhili peak error is 548.5 km
    assert data["failure_onset_lead_hours"] is not None
    assert "representative_fingerprint" in data
    assert "failure_cases" in data


def test_api_storm_fingerprint_not_found():
    """Verify 404 for unknown storm name in fingerprint endpoint."""
    response = client.get("/api/v1/historical/fingerprint/UNKNOWN_HURRICANE")
    assert response.status_code == 404
