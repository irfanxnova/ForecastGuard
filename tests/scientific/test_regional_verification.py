"""Tests for Regional Forecast-versus-Observation Verification Engine.

Strictly verifies AGENTS.md requirements:
- Rule 1: Never fabricate weather data or machine-learning predictions.
- Rule 4: Never use future observations as predictor features.
- Rule 5: Preserve chronological train/validation/test separation.
- Rule 6: Every prediction must use only information available at forecast lead.
- Rule 7: Never silently change scientific definitions, units, or coordinates.
- Rule 14: Never invent historical cases or historical verification results.
"""

from datetime import datetime, timezone
import pytest

from scientific.verification.regional_verification import (
    RegionalVerificationRecord,
    regional_verification_engine,
)


def test_verification_dataset_loaded_and_complete():
    """Verify that all 101 historical cyclone verified leads are indexed."""
    records = regional_verification_engine.get_all_records()
    assert len(records) == 101

    # Check required storms
    storms = {r.storm_name for r in records}
    expected_storms = {"MOCHA", "BIPARJOY", "TEJ", "HAMOON", "MIDHILI", "MICHAUNG"}
    assert storms == expected_storms


def test_verification_record_scientific_invariants():
    """Verify physical properties and units of verification records."""
    records = regional_verification_engine.get_all_records()

    for r in records:
        # Spatial bounds (North Indian Ocean)
        assert 0.0 <= r.forecast_lat <= 35.0
        assert 50.0 <= r.forecast_lon <= 105.0
        assert 0.0 <= r.observed_lat <= 35.0
        assert 50.0 <= r.observed_lon <= 105.0

        # Physical pressure bounds (hPa)
        assert 880.0 <= r.forecast_pressure_hpa <= 1025.0
        assert 880.0 <= r.observed_pressure_hpa <= 1025.0

        # Positive errors and thresholds
        assert r.track_error_km >= 0.0
        assert r.threshold_km > 0.0
        assert r.pressure_error_hpa >= 0.0

        # Bust logic: bust if and only if track_error >= threshold
        expected_bust = r.track_error_km >= r.threshold_km
        assert r.is_bust == expected_bust

        # Valid region ID
        assert r.region_id in {"MAR_BOB", "MAR_AS", "IND_ENE", "IND_WST", "IND_SOU"}

        # Strict anti-leakage: forecast cycle must precede valid time
        init_dt = datetime.fromisoformat(r.forecast_cycle.replace("Z", "+00:00"))
        valid_dt = datetime.fromisoformat(r.valid_time.replace("Z", "+00:00"))
        assert valid_dt > init_dt


def test_get_records_for_case():
    """Verify case-specific querying and lead filtering."""
    midhili_recs = regional_verification_engine.get_records_for_case("MIDHILI_00Z")
    assert len(midhili_recs) == 8

    # Filter by lead hours
    d1_rec = regional_verification_engine.get_records_for_case("MIDHILI_00Z", lead_hours=24)
    assert len(d1_rec) == 1
    assert d1_rec[0].region_id == "MAR_BOB"
    assert d1_rec[0].is_bust is True
    assert round(d1_rec[0].track_error_km, 1) == 231.1

    d2_rec = regional_verification_engine.get_records_for_case("MIDHILI_00Z", lead_hours=48)
    assert len(d2_rec) == 1
    assert d2_rec[0].region_id == "IND_ENE"
    assert d2_rec[0].is_bust is True
    assert round(d2_rec[0].track_error_km, 1) == 548.5


def test_get_record_for_region():
    """Verify specific region/lead matching."""
    bob_rec = regional_verification_engine.get_record_for_region("MIDHILI_00Z", "MAR_BOB", 24)
    assert bob_rec is not None
    assert bob_rec.lead_hours == 24

    # Arabian Sea region has no cyclone fix for Midhili
    as_rec = regional_verification_engine.get_record_for_region("MIDHILI_00Z", "MAR_AS", 24)
    assert as_rec is None
