"""Tests for real MERA NetCDF observation ingestion."""

from pathlib import Path

import numpy as np

from scientific.ingestion.mera import read_mera_file, read_mera_observations


SAMPLE_MERA_DIRECTORY = Path("data/raw/observations/mera_20250901")


def test_mera_file_preserves_rainfall_coordinates_and_time() -> None:
    """Verify one real MERA file is loaded without changing its metadata or values."""
    observation = read_mera_file(SAMPLE_MERA_DIRECTORY / "mera_2025090100.nc")

    assert observation.dimensions == {"time": 1, "longitude": 534, "latitude": 267}
    assert observation.rainfall.shape == (1, 267, 534)
    assert observation.rainfall.dtype == np.float32
    assert observation.rainfall_units is None
    assert np.array_equal(
        observation.time,
        np.array([np.datetime64("2025-09-01T00:00:00.000000000")]),
    )
    assert observation.latitude[0] == 19.988882427119496
    assert observation.latitude[-1] == 10.019213475187684
    assert observation.longitude[0] == 70.02258806262587
    assert observation.longitude[-1] == 89.99940592495538
    assert observation.statistics["number_of_values"] == 267 * 534
    assert observation.statistics["nan_count"] > 0
    assert observation.statistics["min"] == 0.0
    assert observation.statistics["max"] == 14.377263069152832


def test_mera_sample_reads_all_hourly_files_and_reports_qc() -> None:
    """Verify the real 24-hour MERA sample is complete and statistically reported."""
    result = read_mera_observations(SAMPLE_MERA_DIRECTORY)

    assert result.qc.status == "PASS"
    assert result.qc.file_count == 24
    assert result.qc.rainfall_file_count == 24
    assert len(result.observations) == 24
    assert result.qc.total_values == 24 * 267 * 534
    assert result.qc.nan_count > 0
    assert result.qc.negative_count == 0
    assert result.qc.minimum == 0.0
    assert result.qc.maximum == 35.64365005493164
    assert result.qc.mean is not None

    timestamps = [observation.time[0] for observation in result.observations]
    expected_timestamps = np.arange(
        np.datetime64("2025-09-01T00:00:00"),
        np.datetime64("2025-09-02T00:00:00"),
        np.timedelta64(1, "h"),
    )
    assert np.array_equal(timestamps, expected_timestamps)
    assert {observation.rainfall.shape for observation in result.observations} == {(1, 267, 534)}
    assert {observation.rainfall_units for observation in result.observations} == {None}