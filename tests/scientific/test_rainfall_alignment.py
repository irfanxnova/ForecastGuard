"""Focused tests for the validation-only rainfall alignment contract."""

from datetime import datetime, timezone
from dataclasses import replace
from pathlib import Path

import numpy as np

from scientific.alignment import AlignmentStatus, validate_rainfall_alignment
from scientific.ingestion.grib import GribMessageMetadata
from scientific.ingestion.mera import MeraObservation, read_mera_file


SAMPLE_MERA_FILE = Path("data/raw/observations/mera_20250901/mera_2025090100.nc")
UTC = timezone.utc


def _forecast(**overrides: object) -> GribMessageMetadata:
    values = {
        "message_index": 1,
        "edition": 2,
        "short_name": "tp",
        "data_date": 20250901,
        "data_time": 0,
        "step_type": "accum",
        "start_step": 0,
        "end_step": 24,
        "grid_type": "regular_ll",
        "ni": 2,
        "nj": 2,
        "first_lat": 20.0,
        "last_lat": 10.0,
        "first_lon": 70.0,
        "last_lon": 71.0,
        "i_increment": 1.0,
        "j_increment": -10.0,
    }
    values.update(overrides)
    return GribMessageMetadata(**values)


def _observation() -> MeraObservation:
    latitude = np.array([20.0, 10.0])
    longitude = np.array([70.0, 71.0])
    return MeraObservation(
        source_file="test.nc",
        dimensions={"time": 1, "latitude": 2, "longitude": 2},
        latitude=latitude,
        longitude=longitude,
        time=np.array([np.datetime64("2025-09-01T00:00:00")]),
        rainfall=np.zeros((1, 2, 2), dtype=np.float32),
        rainfall_units=None,
        statistics={"number_of_values": 4, "nan_count": 0, "negative_count": 0},
        global_attributes={},
    )


def test_unspecified_mera_window_is_blocked() -> None:
    """Verify an observation timestamp is not treated as an accumulation boundary."""
    result = validate_rainfall_alignment(_forecast(), read_mera_file(SAMPLE_MERA_FILE))

    assert result.status is AlignmentStatus.BLOCKED_UNSPECIFIED_OBSERVATION_WINDOW
    assert result.observation_accumulation_start is None
    assert result.observation_accumulation_end is None
    assert result.forecast_accumulation_start == datetime(2025, 9, 1, tzinfo=UTC)
    assert result.forecast_accumulation_end == datetime(2025, 9, 2, tzinfo=UTC)


def test_matching_explicit_windows_are_aligned() -> None:
    """Verify exact explicit physical windows are accepted."""
    result = validate_rainfall_alignment(
        _forecast(),
        _observation(),
        datetime(2025, 9, 1, tzinfo=UTC),
        datetime(2025, 9, 2, tzinfo=UTC),
    )

    assert result.status is AlignmentStatus.ALIGNED


def test_mismatched_explicit_windows_are_not_aligned() -> None:
    """Verify different explicit physical windows are rejected."""
    result = validate_rainfall_alignment(
        _forecast(),
        _observation(),
        datetime(2025, 9, 1, 1, tzinfo=UTC),
        datetime(2025, 9, 2, 1, tzinfo=UTC),
    )

    assert result.status is AlignmentStatus.NOT_ALIGNED


def test_invalid_forecast_metadata_is_invalid() -> None:
    """Verify missing forecast accumulation metadata cannot be aligned."""
    result = validate_rainfall_alignment(
        _forecast(start_step=None),
        _observation(),
        datetime(2025, 9, 1, tzinfo=UTC),
        datetime(2025, 9, 2, tzinfo=UTC),
    )

    assert result.status is AlignmentStatus.INVALID_METADATA


def test_different_grids_are_reported_without_regridding() -> None:
    """Verify grid differences are reported and source coordinates remain unchanged."""
    observation = replace(_observation(), longitude=np.array([70.0, 72.0]))

    result = validate_rainfall_alignment(
        _forecast(),
        observation,
        datetime(2025, 9, 1, tzinfo=UTC),
        datetime(2025, 9, 2, tzinfo=UTC),
    )

    assert result.status is AlignmentStatus.ALIGNED
    assert result.spatial_grid.status == "DIFFERENT"
    assert result.spatial_grid.observation["last_lon"] == 72.0