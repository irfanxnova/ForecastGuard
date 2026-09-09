"""Tests for Predefined Analytical Regionalization and Domain Intersection."""

import pytest
import numpy as np

from scientific.remapping.regions import (
    PREDEFINED_REGIONS,
    PredefinedRegion,
    check_domain_overlap,
    create_region_grid_mask,
    get_all_regions,
    get_region_by_id,
)


def test_standard_regions_integrity():
    """Verify all predefined analytical regions are properly registered and non-empty."""
    regions = get_all_regions()
    assert len(regions) == 7
    expected_ids = {"MAR_BOB", "MAR_AS", "IND_ENE", "IND_SOU", "IND_CEN", "IND_WST", "IND_NW"}
    assert {r.region_id for r in regions} == expected_ids

    for r in regions:
        assert r.min_lat < r.max_lat
        assert r.min_lon < r.max_lon
        assert r.min_lat <= r.center_lat <= r.max_lat
        assert r.min_lon <= r.center_lon <= r.max_lon
        assert len(r.boundary_polygon) >= 4
        # Center should be inside the region
        assert r.contains_point(r.center_lat, r.center_lon)


def test_point_in_region_strict_bounds():
    """Verify points outside bounding box evaluate to False immediately."""
    bob = get_region_by_id("MAR_BOB")
    assert bob is not None

    # Equator point (outside south boundary 8.0 N)
    assert not bob.contains_point(0.0, 88.0)
    # London point
    assert not bob.contains_point(51.5, 0.0)
    # Inside Bay of Bengal center
    assert bob.contains_point(15.0, 88.0)


def test_domain_overlap_calculation():
    """Verify domain overlap calculation between GRIB bounds and regions."""
    bob = get_region_by_id("MAR_BOB")
    as_region = get_region_by_id("MAR_AS")
    assert bob is not None and as_region is not None

    # Bay of Bengal GRIB bounds (Midhili: lat 10.08-25.92, lon 80.1-97.92)
    is_supported, coverage = check_domain_overlap(25.92, 10.08, 80.1, 97.92, bob)
    assert is_supported
    assert coverage > 50.0

    # Arabian Sea region against Bay of Bengal GRIB bounds
    is_as_supported, as_coverage = check_domain_overlap(25.92, 10.08, 80.1, 97.92, as_region)
    assert not is_as_supported
    assert as_coverage == 0.0


def test_create_region_grid_mask():
    """Verify 2D grid mask creation preserves coordinate structure and bounds."""
    bob = get_region_by_id("MAR_BOB")
    assert bob is not None

    lats = np.linspace(25.0, 10.0, 16)
    lons = np.linspace(70.0, 95.0, 26)

    mask = create_region_grid_mask(lats, lons, bob)
    assert mask.shape == (16, 26)
    assert mask.dtype == bool
    # Should have positive count in Bay of Bengal
    assert np.sum(mask) > 0
    # Arabian Sea points (lon < 75) must all be False
    lon_2d, _ = np.meshgrid(lons, lats)
    assert np.sum(mask[lon_2d < 75.0]) == 0
