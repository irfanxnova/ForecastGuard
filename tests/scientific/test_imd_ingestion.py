"""Tests for IMD daily binary rainfall ingestion."""

from datetime import date

import numpy as np
import pytest

from scientific.ingestion.imd import (
    IMD_EXPECTED_BYTE_LENGTH,
    IMD_EXPECTED_VALUE_COUNT,
    read_imd_daily_file,
)


EXPECTED_SHAPE = (281, 241)


def write_grid(path, values: np.ndarray) -> None:
    values.astype("<f4").tofile(path)


def test_reads_exact_imd_grid_and_preserves_dtype(tmp_path) -> None:
    values = np.arange(IMD_EXPECTED_VALUE_COUNT, dtype=np.float32)
    path = tmp_path / "01092025.grd"
    write_grid(path, values)

    observation = read_imd_daily_file(path, date(2025, 9, 1))

    assert observation.rainfall.shape == EXPECTED_SHAPE
    assert observation.rainfall.dtype == np.dtype("float32")
    assert observation.rainfall[0, 0] == 0.0
    assert observation.rainfall[-1, -1] == IMD_EXPECTED_VALUE_COUNT - 1
    assert path.stat().st_size == IMD_EXPECTED_BYTE_LENGTH


def test_generates_coordinates_from_imd_grid_definition(tmp_path) -> None:
    path = tmp_path / "rain.grd"
    write_grid(path, np.zeros(IMD_EXPECTED_VALUE_COUNT, dtype=np.float32))

    observation = read_imd_daily_file(path, "2025-09-01")

    assert observation.latitude.shape == (281,)
    assert observation.longitude.shape == (241,)
    assert np.allclose(observation.latitude, -30.0 + 0.25 * np.arange(281))
    assert np.allclose(observation.longitude, 50.0 + 0.25 * np.arange(241))


def test_converts_undefined_values_to_nan_without_changing_zero(tmp_path) -> None:
    values = np.zeros(IMD_EXPECTED_VALUE_COUNT, dtype=np.float32)
    values[1] = -999.0
    path = tmp_path / "rain.grd"
    write_grid(path, values)

    observation = read_imd_daily_file(path, date(2025, 9, 1))

    assert observation.rainfall[0, 0] == 0.0
    assert np.isnan(observation.rainfall[0, 1])
    assert observation.metadata["missing_value_count"] == 1
    assert observation.metadata["min"] == 0.0
    assert observation.metadata["max"] == 0.0
    assert observation.metadata["mean"] == 0.0


def test_invalid_file_size_raises_clear_error(tmp_path) -> None:
    path = tmp_path / "invalid.grd"
    path.write_bytes(b"too short")

    with pytest.raises(ValueError, match="expected 270884 bytes"):
        read_imd_daily_file(path, date(2025, 9, 1))


def test_observation_date_is_explicit_and_separate_from_file_name(tmp_path) -> None:
    path = tmp_path / "01092025.grd"
    write_grid(path, np.zeros(IMD_EXPECTED_VALUE_COUNT, dtype=np.float32))

    observation = read_imd_daily_file(path, date(2025, 9, 2))

    assert observation.observation_date == date(2025, 9, 2)
    assert observation.metadata["observation_date"] == date(2025, 9, 2)


def test_accumulation_window_remains_unspecified(tmp_path) -> None:
    path = tmp_path / "rain.grd"
    write_grid(path, np.zeros(IMD_EXPECTED_VALUE_COUNT, dtype=np.float32))

    observation = read_imd_daily_file(path, date(2025, 9, 1))

    assert observation.accumulation_window is None
    assert observation.metadata["accumulation_window_status"] == "UNKNOWN/UNSPECIFIED"


def test_missing_file_raises_clear_error(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="IMD rainfall file not found"):
        read_imd_daily_file(tmp_path / "missing.grd", date(2025, 9, 1))
