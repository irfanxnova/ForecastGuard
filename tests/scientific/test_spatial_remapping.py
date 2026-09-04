"""Focused tests for experimental conservative spatial remapping."""

import numpy as np
import pytest

from scientific.remapping import conservative_remap_regular_latlon


def test_conservative_remap_preserves_constant_field() -> None:
    """A constant field remains constant on a coarser overlapping grid."""
    source_values = np.full((4, 4), 12.5)
    source_latitude = np.array([1.5, 0.5, -0.5, -1.5])
    source_longitude = np.array([0.5, 1.5, 2.5, 3.5])
    target_latitude = np.array([1.0, -1.0])
    target_longitude = np.array([1.0, 3.0])

    remapped = conservative_remap_regular_latlon(
        source_values,
        source_latitude,
        source_longitude,
        target_latitude,
        target_longitude,
    )

    assert remapped.shape == (2, 2)
    assert np.allclose(remapped, 12.5)


def test_conservative_remap_keeps_missing_source_cells_missing() -> None:
    """Missing source cells are excluded and all-missing targets remain NaN."""
    source_values = np.array([[1.0, np.nan], [np.nan, np.nan]])
    coordinates = np.array([0.5, -0.5])
    longitudes = np.array([0.5, 1.5])

    remapped = conservative_remap_regular_latlon(
        source_values,
        coordinates,
        longitudes,
        np.array([0.5, -0.5]),
        longitudes,
    )

    assert remapped[0, 0] == pytest.approx(1.0)
    assert np.isnan(remapped[0, 1])
    assert np.isnan(remapped[1]).all()


def test_conservative_remap_rejects_mismatched_source_shape() -> None:
    """Source values must match the supplied source coordinate dimensions."""
    with pytest.raises(ValueError, match="shape"):
        conservative_remap_regular_latlon(
            np.ones((2, 3)),
            np.array([0.5, -0.5]),
            np.array([0.5, 1.5]),
            np.array([0.5, -0.5]),
            np.array([0.5, 1.5]),
        )