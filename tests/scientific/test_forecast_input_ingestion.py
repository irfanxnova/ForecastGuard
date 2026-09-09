"""Tests for Core Operational Forecast Input Ingestion & Scientific Evidence Pipeline.

Verifies:
1. Input payload validation (cycle, valid_time, >= 5 ensemble members, coordinate bounds).
2. Data rejection and issue reporting for corrupted or insufficient ensemble members.
3. Feature extraction of prospective ensemble spread, divergence, and anisotropy.
4. Absence of data leakage (features derived strictly from forecast fixes).
5. Prospective operational semantics: PENDING_VERIFICATION when ground truth is withheld.
6. Post-event audit semantics: VERIFIED with track error computed against tolerance tau(lead).
7. M1 baseline calibrated prediction, OOD representation, multi-model consensus, and analogue retrieval.
8. Sample forecast fixtures catalog validity.
9. Live feed availability detection and operational fallback reporting.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict
import pytest

from backend.app.schemas.forecast_input import (
    EnsembleMemberFix,
    ForecastInputPayload,
    ObservedVerificationFix,
)
from backend.app.services.forecast_ingestion_service import (
    ForecastIngestionService,
    forecast_ingestion_service,
)
from scientific.validation.cyclone import haversine_distance


def _build_valid_raw_payload(
    with_observation: bool = False,
    num_members: int = 11,
    lead_hours: int = 24,
) -> Dict[str, Any]:
    """Helper to build a valid prospective or verified raw forecast dictionary."""
    members = []
    base_lat, base_lon = 13.5, 84.0
    for i in range(1, num_members + 1):
        angle = 2 * math.pi * (i / num_members)
        r = 0.5 * (i % 3 + 1) / 3.0
        members.append(
            {
                "member_id": i,
                "latitude": round(base_lat + r * math.sin(angle), 3),
                "longitude": round(base_lon + r * math.cos(angle), 3),
                "central_pressure_hpa": round(980.0 + (i % 5) * 2.5, 1),
            }
        )

    payload: Dict[str, Any] = {
        "cyclone_name": "MICHAUNG",
        "forecast_source": "NCMRWF_NEPS",
        "forecast_cycle": "2023-12-02T00:00:00Z",
        "lead_hours": lead_hours,
        "valid_time": "2023-12-03T00:00:00Z",
        "basin": "Bay of Bengal",
        "ensemble_members": members,
    }

    if with_observation:
        payload["observed_verification"] = {
            "observed_lat": 14.2,
            "observed_lon": 84.5,
            "observed_pressure_hpa": 982.0,
            "best_track_agency": "IMD_RSMC_NEW_DELHI",
        }

    return payload


# ---------------------------------------------------------------------------
# Ingestion & Validation Tests
# ---------------------------------------------------------------------------


def test_valid_forecast_payload_passes_validation() -> None:
    """A well-formed prospective payload passes validation cleanly."""
    raw = _build_valid_raw_payload(with_observation=False)
    parsed, val = forecast_ingestion_service.validate_payload(raw)

    assert val.is_valid is True
    assert val.validation_status == "PASS"
    assert len(val.errors) == 0
    assert val.ensemble_members_count == 11
    assert val.verification_mode == "PROSPECTIVE_PENDING"
    assert parsed is not None
    assert parsed.cyclone_name == "MICHAUNG"


def test_insufficient_members_rejected() -> None:
    """Payload with < 5 ensemble members must fail validation."""
    raw = _build_valid_raw_payload(num_members=3)
    parsed, val = forecast_ingestion_service.validate_payload(raw)

    assert val.is_valid is False
    assert val.validation_status == "REJECTED"
    assert parsed is None
    assert any("minimum 5 required" in err for err in val.errors)


def test_missing_metadata_rejected() -> None:
    """Missing cyclone name or lead time must produce validation errors."""
    raw = _build_valid_raw_payload()
    del raw["cyclone_name"]
    del raw["lead_hours"]
    parsed, val = forecast_ingestion_service.validate_payload(raw)

    assert val.is_valid is False
    assert parsed is None
    assert any("cyclone_name" in err for err in val.errors)
    assert any("lead_hours" in err for err in val.errors)


def test_out_of_bounds_coordinates_rejected() -> None:
    """Coordinates outside physical limits must produce validation errors."""
    raw = _build_valid_raw_payload()
    raw["ensemble_members"][0]["latitude"] = 95.0  # Invalid lat > 90
    parsed, val = forecast_ingestion_service.validate_payload(raw)

    assert val.is_valid is False
    assert parsed is None
    assert any("coordinate out of range" in err for err in val.errors)


# ---------------------------------------------------------------------------
# Feature Extraction & Leakage Protection
# ---------------------------------------------------------------------------


def test_leakage_protection_no_observation_in_features() -> None:
    """Analysis features must be identical whether observation is provided or withheld."""
    raw_prospective = _build_valid_raw_payload(with_observation=False)
    raw_verified = _build_valid_raw_payload(with_observation=True)

    parsed_prospective, _ = forecast_ingestion_service.validate_payload(raw_prospective)
    parsed_verified, _ = forecast_ingestion_service.validate_payload(raw_verified)

    assert parsed_prospective is not None
    assert parsed_verified is not None

    analysis_prospective = forecast_ingestion_service.analyze_forecast(parsed_prospective)
    analysis_verified = forecast_ingestion_service.analyze_forecast(parsed_verified)

    # Core predictive features and dimensions must be identical
    assert analysis_prospective.where.centroid_lat == analysis_verified.where.centroid_lat
    assert analysis_prospective.where.centroid_lon == analysis_verified.where.centroid_lon
    assert analysis_prospective.why.ensemble_spread_km == analysis_verified.why.ensemble_spread_km
    assert analysis_prospective.why.ensemble_divergence_km == analysis_verified.why.ensemble_divergence_km
    assert analysis_prospective.why.anisotropy_ratio == analysis_verified.why.anisotropy_ratio
    assert analysis_prospective.reliability_score == analysis_verified.reliability_score
    assert analysis_prospective.bust_risk_percent == analysis_verified.bust_risk_percent


# ---------------------------------------------------------------------------
# Operational Semantics: PENDING_VERIFICATION vs VERIFIED
# ---------------------------------------------------------------------------


def test_prospective_forecast_returns_pending_verification() -> None:
    """When observation is withheld, verification_status must be PENDING_VERIFICATION."""
    raw = _build_valid_raw_payload(with_observation=False)
    parsed, _ = forecast_ingestion_service.validate_payload(raw)
    assert parsed is not None

    analysis = forecast_ingestion_service.analyze_forecast(parsed)
    assert analysis.verification_status == "PENDING_VERIFICATION"
    assert analysis.verification_detail["status"] == "PENDING_VERIFICATION"
    assert analysis.verification_detail["verified_track_error_km"] is None
    assert "pending" in analysis.verification_detail["message"].lower()


def test_revealed_observation_returns_verified_status() -> None:
    """When observation is provided, verification_status must be VERIFIED with error."""
    raw = _build_valid_raw_payload(with_observation=True, lead_hours=24)
    parsed, _ = forecast_ingestion_service.validate_payload(raw)
    assert parsed is not None

    analysis = forecast_ingestion_service.analyze_forecast(parsed)
    assert analysis.verification_status == "VERIFIED"
    assert analysis.verification_detail["status"] == "VERIFIED"
    assert analysis.verification_detail["verified_track_error_km"] is not None
    assert analysis.verification_detail["verified_track_error_km"] > 0

    # Tolerance tau(24h) = 90 * (1 + 0.008 * 24) = 107.28 km
    expected_tau = round(90.0 * (1.0 + 0.008 * 24), 1)
    assert analysis.where.tolerance_radius_km == expected_tau

    outcome = analysis.verification_detail["outcome"]
    expected_outcome = "BUST" if analysis.verification_detail["verified_track_error_km"] >= expected_tau else "WITHIN_TOLERANCE"
    assert outcome == expected_outcome


# ---------------------------------------------------------------------------
# Full Scientific Pipeline Execution (WHERE, WHEN, RISK, WHY)
# ---------------------------------------------------------------------------


def test_operational_analysis_pipeline_contract() -> None:
    """Verify WHERE, WHEN, and WHY blocks conform to contract."""
    raw = _build_valid_raw_payload(lead_hours=36)
    parsed, _ = forecast_ingestion_service.validate_payload(raw)
    assert parsed is not None

    analysis = forecast_ingestion_service.analyze_forecast(parsed)

    # WHERE
    assert 5.0 <= analysis.where.centroid_lat <= 30.0
    assert 50.0 <= analysis.where.centroid_lon <= 100.0
    assert analysis.where.basin in ["Bay of Bengal", "Arabian Sea", "North Indian Ocean"]
    assert analysis.where.dispersion_radius_km > 0.0

    # WHEN
    assert analysis.when.lead_hours == 36
    assert analysis.when.forecast_cycle is not None
    assert analysis.when.valid_time is not None

    # RISK
    assert 0 <= analysis.reliability_score <= 100
    assert 0 <= analysis.bust_risk_percent <= 100
    assert analysis.reliability_state in ["NOMINAL", "VULNERABLE", "HIGH_RISK", "STABLE", "WATCH", "AWAITING_VERIFIED_CASE"]

    # WHY
    assert analysis.why.ensemble_spread_km > 0.0
    assert analysis.why.ensemble_divergence_km > 0.0
    assert analysis.why.anisotropy_ratio >= 1.0
    assert analysis.why.ood_representation_state in [
        "WELL_REPRESENTED",
        "LOW_SUPPORT",
        "NOVEL_STATE",
        "INSUFFICIENT_EVIDENCE",
    ]
    assert len(analysis.why.ranked_factors) >= 3


# ---------------------------------------------------------------------------
# Fixture Catalog & Live Status
# ---------------------------------------------------------------------------


def test_sample_fixtures_catalog_is_valid() -> None:
    """Sample fixtures catalog must contain at least 4 valid presets."""
    fixtures = forecast_ingestion_service.get_sample_forecasts()

    assert len(fixtures) >= 4
    fixture_ids = [f["sample_id"] for f in fixtures]
    assert "michaung_lead24_prospective" in fixture_ids
    assert "michaung_lead24_verified" in fixture_ids
    assert "midhili_lead30_bust_risk" in fixture_ids
    assert "biparjoy_lead18_false_confidence" in fixture_ids

    # Each fixture must pass validation
    for fixture in fixtures:
        parsed, val_res = forecast_ingestion_service.validate_payload(fixture["payload"])
        assert val_res.is_valid is True, f"Fixture {fixture['sample_id']} failed: {val_res.errors}"
        assert parsed is not None


def test_live_feed_status_reports_truthfully() -> None:
    """When live credentials are absent, live status reports offline with alternatives."""
    status = forecast_ingestion_service.get_live_feed_status()

    assert "live_feed_available" in status
    assert status["live_feed_available"] is False
    assert "status" in status
    assert "message" in status
    assert "alternatives" in status
    assert len(status["alternatives"]) >= 2
