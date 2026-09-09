"""Unit tests for ForecastGuard V2 Environmental Intelligence Engine.

Verifies:
- Rigorous data audit of the 5 requested atmospheric variables (zero fabrication).
- Environmental pressure depth computation across synoptic annulus.
- Radial pressure gradient computation (hPa / 100 km).
- Outer directional pressure asymmetry computation.
- Deterministic classification of neutral MSLP environmental states.
- Clean INSUFFICIENT_EVIDENCE fallback for outside-domain coordinates.
- Explicit non-shear provenance note and non-causal attribution contracts.
"""

import numpy as np
import pytest

from scientific.features.environmental_intelligence import (
    ATMOSPHERIC_VARIABLE_AUDIT,
    classify_environmental_state,
    compute_environmental_pressure_depth,
    compute_pressure_gradient_asymmetry,
    compute_radial_pressure_gradient,
    extract_environmental_intelligence_from_grid,
    extract_fallback_environmental_insufficient,
    haversine_km,
)


def test_atmospheric_variable_audit_honesty():
    """Verify that all unprovided variables are rigorously marked UNAVAILABLE."""
    # 5 requested atmospheric parameters
    audit = ATMOSPHERIC_VARIABLE_AUDIT
    assert "wind_850hpa" in audit
    assert "wind_200hpa" in audit
    assert "vertical_wind_shear" in audit
    assert "mid_tropospheric_humidity" in audit
    assert "sea_surface_temperature" in audit

    for var_key in [
        "wind_850hpa",
        "wind_200hpa",
        "vertical_wind_shear",
        "mid_tropospheric_humidity",
        "sea_surface_temperature",
    ]:
        report = audit[var_key]
        assert report.status == "UNAVAILABLE"
        assert report.missingness_percent == 100.0
        assert report.cases_coverage_count == 0
        assert "not" in report.reason.lower() or "absent" in report.reason.lower() or "cannot" in report.reason.lower()

    # Verify MSLP field is AVAILABLE
    assert audit["surface_mslp_field"].status == "AVAILABLE"
    assert audit["surface_mslp_field"].missingness_percent == 0.0
    assert audit["surface_mslp_field"].cases_coverage_count == 6


def test_compute_pressure_depth_and_gradient():
    """Verify synthetic axisymmetric vortex yields exact depth and radial gradient."""
    # Create synthetic 0.5 deg grid around 15.0 N, 88.0 E
    lats = np.linspace(5.0, 25.0, 41)  # 0.5 deg steps
    lons = np.linspace(78.0, 98.0, 41)
    grid_lons, grid_lats = np.meshgrid(lons, lats)

    center_lat, center_lon = 15.0, 88.0
    center_pres = 970.0

    # Distance in km from center
    phi1, lam1 = np.radians(center_lat), np.radians(center_lon)
    phi2, lam2 = np.radians(grid_lats), np.radians(grid_lons)
    dphi = phi2 - phi1
    dlam = lam2 - lam1
    a = np.sin(dphi / 2.0) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2.0) ** 2
    dist_km = 6371.0 * 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))

    # Synthetic pressure: 970 at core, reaching 1010 at 500 km
    # P(r) = 970 + 40 * (r / 500), clamped at 1010
    synth_mslp = np.clip(970.0 + 40.0 * (dist_km / 500.0), 970.0, 1010.0)

    periph_pres, depth = compute_environmental_pressure_depth(
        center_lat=center_lat,
        center_lon=center_lon,
        center_pressure_hpa=center_pres,
        lats=lats,
        lons=lons,
        mslp_hpa_grid=synth_mslp,
        inner_radius_km=300.0,
        outer_radius_km=600.0,
    )

    assert depth > 25.0
    assert periph_pres > 995.0

    grad = compute_radial_pressure_gradient(depth, mean_annulus_radius_km=450.0)
    assert grad > 5.0  # hPa per 100km

    # Pure axisymmetric vortex should have minimal directional asymmetry
    asym = compute_pressure_gradient_asymmetry(
        center_lat=center_lat,
        center_lon=center_lon,
        lats=lats,
        lons=lons,
        mslp_hpa_grid=synth_mslp,
        inner_radius_km=300.0,
        outer_radius_km=600.0,
    )
    assert asym < 0.5  # Very low asymmetry


def test_pressure_gradient_asymmetry_dipole():
    """Verify that an environmental ridge-trough dipole creates strong directional asymmetry."""
    lats = np.linspace(5.0, 25.0, 41)
    lons = np.linspace(78.0, 98.0, 41)
    grid_lons, grid_lats = np.meshgrid(lons, lats)

    center_lat, center_lon = 15.0, 88.0

    # Add strong North-South environmental ridge (steep synoptic dipole)
    dipole_mslp = 1010.0 + (grid_lats - center_lat) * 4.0

    asym = compute_pressure_gradient_asymmetry(
        center_lat=center_lat,
        center_lon=center_lon,
        lats=lats,
        lons=lons,
        mslp_hpa_grid=dipole_mslp,
        inner_radius_km=300.0,
        outer_radius_km=600.0,
    )

    assert asym > 2.0  # Strong asymmetry


def test_classify_environmental_state():
    """Verify deterministic state classification boundaries."""
    # Deepening / Tightening -> Symmetric Deep Structure
    s1, _ = classify_environmental_state(pressure_gradient=4.2, asymmetry=1.0, pressure_depth=28.0)
    assert s1 == "SYMMETRIC_DEEP_PRESSURE_STRUCTURE"

    # Asymmetric Structure
    s2, _ = classify_environmental_state(pressure_gradient=2.5, asymmetry=2.8, pressure_depth=15.0)
    assert s2 == "ASYMMETRIC_WEAK_PRESSURE_STRUCTURE"

    # Weakening / Diffuse Structure
    s3, _ = classify_environmental_state(pressure_gradient=1.1, asymmetry=0.8, pressure_depth=8.0)
    assert s3 == "ASYMMETRIC_WEAK_PRESSURE_STRUCTURE"

    # Marginal Gradient Structure
    s4, _ = classify_environmental_state(pressure_gradient=2.2, asymmetry=0.9, pressure_depth=14.0)
    assert s4 == "MARGINAL_PRESSURE_STRUCTURE"

    # Insufficient Evidence
    s5, _ = classify_environmental_state(pressure_gradient=None, asymmetry=None, pressure_depth=None)
    assert s5 == "INSUFFICIENT_EVIDENCE"


def test_fallback_environmental_insufficient():
    """Verify clean insufficient evidence fallback."""
    fb = extract_fallback_environmental_insufficient("Test outside domain reason")
    assert fb.state == "INSUFFICIENT_EVIDENCE"
    assert fb.pressure_depth_hpa is None
    assert fb.pressure_gradient_hpa_per_100km is None
    assert fb.gradient_asymmetry_hpa_per_100km is None
    assert fb.upper_air_shear_status == "UNAVAILABLE"
    assert fb.mid_level_humidity_status == "UNAVAILABLE"
    assert fb.sst_status == "UNAVAILABLE"
    assert fb.validation_status == "INSUFFICIENT_EVIDENCE"
    assert "vertical wind shear" in fb.scientific_provenance_note.lower()
    assert "not a direct measurement" in fb.scientific_provenance_note.lower()
