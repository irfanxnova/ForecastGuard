"""Tests for Historical Replay, Verified Cyclone Cases, and Bust Atlas."""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_list_historical_cyclones():
    """Verify all 6 tropical cyclones are listed with audited metadata."""
    response = client.get("/api/v1/historical/cyclones")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 6
    names = [c["storm_name"] for c in data]
    for expected in ["BIPARJOY", "HAMOON", "MICHAUNG", "MIDHILI", "MOCHA", "TEJ"]:
        assert expected in names

    total_leads = sum(c["verified_leads_count"] for c in data)
    assert total_leads == 101
    total_busts = sum(c["contemporaneous_busts_count"] for c in data)
    assert total_busts == 24


def test_historical_replay_michaung():
    """Verify historical replay for Cyclone MICHAUNG returns lead sequence and dual provenance."""
    response = client.get("/api/v1/historical/replay/MICHAUNG")
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "HISTORICAL_REPLAY"
    assert data["storm_name"] == "MICHAUNG"
    assert len(data["leads"]) >= 8

    # Verify lead points have both forecast and RSMC best-track centers
    lead_24 = [l for l in data["leads"] if l["lead_hours"] == 24][0]
    assert lead_24["lead_formatted"] == "+24h"
    assert "latitude" in lead_24["forecast_center"]
    assert "latitude" in lead_24["observed_center"]
    assert isinstance(lead_24["track_error_km"], float)
    assert lead_24["track_error_km"] < lead_24["threshold_km"]  # MICHAUNG was well-forecasted
    assert lead_24["is_bust"] is False

    # Check continuous error summary and provenance
    assert "mean_track_error_km" in data["continuous_error_summary"]
    assert "NCMRWF NEPS" in data["provenance"]["forecast_source"]
    assert "Official IMD/RSMC New Delhi" in data["provenance"]["verification_source"]


def test_historical_replay_unknown_storm_404():
    """Verify requesting non-existent storm returns 404."""
    response = client.get("/api/v1/historical/replay/NONEXISTENT_STORM")
    assert response.status_code == 404


def test_bust_atlas_endpoint():
    """Verify Bust Atlas returns verified forecast failure cases."""
    response = client.get("/api/v1/historical/bust-atlas")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    # Every bust atlas entry must have track error >= threshold
    for entry in data:
        assert entry["track_error_km"] >= entry["threshold_km"]
        assert entry["severity"] in ["DEGRADED", "SEVERE"]
