"""Tests for IMD daily binary rainfall ingestion."""

from datetime import date, datetime, timedelta, timezone

import numpy as np
import pytest

from scientific.ingestion.imd import (
    IMD_DAILY_MERGED_SATELLITE_GAUGE_PRODUCT,
    IMD_EXPECTED_BYTE_LENGTH,
    IMD_EXPECTED_VALUE_COUNT,
    imd_daily_merged_satellite_gauge_window,
    read_imd_daily_file,
)


EXPECTED_SHAPE = (281, 241)
UTC = timezone.utc


class TestImdDailyMergedSatelliteGaugeWindow:
    """Product-scoped temporal metadata, independent of the IMD file reader."""

    def test_observation_date_maps_to_03_utc_end_and_24_hour_start(self) -> None:
        window = imd_daily_merged_satellite_gauge_window("2025-09-02")

        assert window.product == IMD_DAILY_MERGED_SATELLITE_GAUGE_PRODUCT
        assert window.end == datetime(2025, 9, 2, 3, tzinfo=UTC)
        assert window.start == datetime(2025, 9, 1, 3, tzinfo=UTC)
        assert window.end - window.start == timedelta(hours=24)

    def test_window_is_utc_aware(self) -> None:
        window = imd_daily_merged_satellite_gauge_window(date(2025, 9, 2))

        assert window.start.tzinfo is UTC
        assert window.end.tzinfo is UTC

    @pytest.mark.parametrize("value", ["2025-02-30", "2025-09-02T03:00:00"])
    def test_invalid_observation_date_or_time_is_rejected(self, value: str) -> None:
        with pytest.raises(ValueError, match="ISO date"):
            imd_daily_merged_satellite_gauge_window(value)

    def test_datetime_input_is_rejected_without_discarding_its_time(self) -> None:
        with pytest.raises(TypeError, match="calendar date"):
            imd_daily_merged_satellite_gauge_window(
                datetime(2025, 9, 2, 3, tzinfo=UTC)
            )

    def test_metadata_preserves_product_scoped_documented_basis(self) -> None:
        metadata = imd_daily_merged_satellite_gauge_window("2025-09-02").to_dict()

        assert metadata["window_hours"] == 24
        assert "0830 IST" in metadata["basis"]
        assert "03:00 UTC" in metadata["basis"]


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
