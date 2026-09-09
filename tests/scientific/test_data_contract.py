"""Tests for Multi-Variable Forecast-Observation Data Contract and Alignment Auditing.

Strict adherence to AGENTS.md:
- Rule 1: Never fabricate weather data or verification results.
- Rule 7: Never silently change scientific definitions, accumulation windows, or units.
- Priority 5: Verify valid-time, accumulation-window, and variable alignment, rejecting mismatches explicitly.
"""

from pathlib import Path
import pytest

from scientific.alignment.data_contract import (
    AlignmentVerificationStatus,
    audit_forecast_vs_imd_rainfall,
    audit_forecast_vs_mera_rainfall,
    inspect_grib_metadata,
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def test_inspect_grib_metadata_temperature():
    """Verify inspection of 2t GRIB file (67603f4734166cde0f2c2962323ad8e4.grib)."""
    grib_path = BASE_DIR / "data/raw/tigge/67603f4734166cde0f2c2962323ad8e4.grib"
    if not grib_path.exists():
        pytest.skip("GRIB test file not found")

    meta = inspect_grib_metadata(grib_path)
    assert meta["short_name"] == "2t"
    assert meta["step_type"] == "instant"
    assert meta["step"] == 24
    assert meta["grid"]["ni"] == 112
    assert meta["grid"]["nj"] == 83


def test_inspect_grib_metadata_precipitation():
    """Verify inspection of tp GRIB file."""
    grib_path = BASE_DIR / "data/raw/tigge/tigge_dems_tp_pf_20250901_00_step024_m001_n20_w70_s10_e90.grib"
    if not grib_path.exists():
        pytest.skip("GRIB test file not found")

    meta = inspect_grib_metadata(grib_path)
    assert meta["short_name"] == "tp"
    assert meta["step_type"] == "accum"
    assert meta["start_step"] == 0
    assert meta["end_step"] == 24


def test_audit_rejects_temperature_vs_rainfall():
    """Verify auditor explicitly rejects 2t temperature forecast against rainfall observation."""
    grib_path = BASE_DIR / "data/raw/tigge/67603f4734166cde0f2c2962323ad8e4.grib"
    grd_path = BASE_DIR / "data/raw/observations/imd_daily/01092025.grd"
    if not grib_path.exists() or not grd_path.exists():
        pytest.skip("Data files not found")

    audit = audit_forecast_vs_imd_rainfall(grib_path, grd_path, "2025-09-01")
    assert audit.is_aligned is False
    assert audit.status == AlignmentVerificationStatus.REJECTED_VARIABLE_MISMATCH
    assert "Variable mismatch" in audit.blocker_description
    assert audit.forecast_variable == "2t"


def test_audit_rejects_accumulation_window_shift():
    """Verify auditor explicitly rejects 00Z-24Z forecast against 03Z-03Z IMD observation window."""
    grib_path = BASE_DIR / "data/raw/tigge/tigge_dems_tp_pf_20250901_00_step024_m001_n20_w70_s10_e90.grib"
    grd_path = BASE_DIR / "data/raw/observations/imd_daily/01092025.grd"
    if not grib_path.exists() or not grd_path.exists():
        pytest.skip("Data files not found")

    audit = audit_forecast_vs_imd_rainfall(grib_path, grd_path, "2025-09-01")
    assert audit.is_aligned is False
    assert audit.status == AlignmentVerificationStatus.REJECTED_ACCUMULATION_WINDOW_OFFSET
    assert audit.window_offset_hours == 3.0  # 3-hour shift between 00Z and 03Z
    assert "offset of 3.0 hours violates Rule 7" in audit.blocker_description


def test_audit_rejects_mera_missing_cf_units():
    """Verify auditor explicitly rejects MERA netCDF missing explicit CF unit metadata."""
    grib_path = BASE_DIR / "data/raw/tigge/tigge_dems_tp_pf_20250901_00_step024_m001_n20_w70_s10_e90.grib"
    mera_dir = BASE_DIR / "data/raw/observations/mera_20250901"
    if not grib_path.exists() or not mera_dir.exists():
        pytest.skip("Data files not found")

    audit = audit_forecast_vs_mera_rainfall(grib_path, mera_dir, "20250901")
    assert audit.is_aligned is False
    assert audit.status == AlignmentVerificationStatus.REJECTED_INVALID_METADATA
    assert "CF Compliance blocker" in audit.blocker_description
