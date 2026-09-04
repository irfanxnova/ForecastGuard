"""Focused tests for auditable rainfall verification."""

from datetime import datetime, timezone

import numpy as np
import pytest

from scientific.ingestion.grib import GribMessageMetadata
from scientific.ingestion.imd import ImdDailyObservation
from scientific.verification import (
    RainfallVerificationStatus,
    verify_rainfall,
)

UTC = timezone.utc


def _forecast(**overrides: object) -> GribMessageMetadata:
    values = {
        "message_index": 1,
        "edition": 2,
        "short_name": "tp",
        "units": "kg m**-2",
        "data_date": 20250901,
        "data_time": 0,
        "step_type": "accum",
        "start_step": 0,
        "end_step": 24,
        "grid_type": "regular_latitude_longitude",
        "ni": 2,
        "nj": 2,
        "first_lat": 20.0,
        "last_lat": 19.0,
        "first_lon": 70.0,
        "last_lon": 71.0,
        "i_increment": 1.0,
        "j_increment": -1.0,
    }
    values.update(overrides)
    return GribMessageMetadata(**values)


def _observation(values: np.ndarray, **overrides: object) -> ImdDailyObservation:
    defaults = {
        "rainfall": values,
        "latitude": np.array([20.0, 19.0]),
        "longitude": np.array([70.0, 71.0]),
        "observation_date": datetime(2025, 9, 1).date(),
        "accumulation_window": None,
        "source_file": "imd.grd",
        "metadata": {"source_filename": "imd.grd"},
    }
    defaults.update(overrides)
    return ImdDailyObservation(**defaults)


def _explicit_window() -> tuple[datetime, datetime]:
    return datetime(2025, 9, 1, tzinfo=UTC), datetime(2025, 9, 2, tzinfo=UTC)


def test_aligned_fields_produce_error_and_statistics() -> None:
    forecast = _forecast()
    observation = _observation(np.array([[1.0, 2.0], [3.0, 4.0]]))
    start, end = _explicit_window()

    result = verify_rainfall(forecast, np.array([[2.0, 4.0], [6.0, 8.0]]), observation, start, end)

    assert result.status is RainfallVerificationStatus.ALIGNED
    assert np.array_equal(result.error_field, np.array([[1.0, 2.0], [3.0, 4.0]]))
    assert result.valid_cell_count == 4
    assert result.forecast_start == start
    assert result.forecast_end == end
    assert result.observation_start == start
    assert result.observation_end == end
    assert result.mae == pytest.approx(2.5)
    assert result.rmse == pytest.approx(np.sqrt(7.5))
    assert result.bias == pytest.approx(2.5)


def test_nan_observations_are_excluded_from_error_statistics() -> None:
    start, end = _explicit_window()
    result = verify_rainfall(
        _forecast(),
        np.array([[2.0, 4.0], [6.0, 8.0]]),
        _observation(np.array([[1.0, np.nan], [3.0, 4.0]])),
        start,
        end,
    )

    assert result.valid_cell_count == 3
    assert result.missing_cell_count == 1
    assert np.isnan(result.error_field[0, 1])
    assert result.mae == pytest.approx(8.0 / 3.0)
    assert result.bias == pytest.approx(8.0 / 3.0)


def test_zero_observation_is_a_valid_value() -> None:
    start, end = _explicit_window()
    result = verify_rainfall(
        _forecast(),
        np.ones((2, 2)),
        _observation(np.zeros((2, 2))),
        start,
        end,
    )

    assert result.valid_cell_count == 4
    assert result.observation_mean == 0.0
    assert np.all(result.error_field == 1.0)


def test_unspecified_observation_window_blocks_without_calculation() -> None:
    result = verify_rainfall(
        _forecast(), np.ones((2, 2)), _observation(np.zeros((2, 2)))
    )

    assert result.status is RainfallVerificationStatus.BLOCKED_UNSPECIFIED_OBSERVATION_WINDOW
    assert result.error_field is None
    assert result.mae is None
    assert result.provenance["observation_accumulation_window"] is None
    assert result.forecast_start == datetime(2025, 9, 1, tzinfo=UTC)
    assert result.forecast_end == datetime(2025, 9, 2, tzinfo=UTC)
    assert result.observation_start is None
    assert result.observation_end is None


def test_mismatched_temporal_windows_are_blocked_without_calculation() -> None:
    start = datetime(2025, 9, 1, 3, tzinfo=UTC)
    end = datetime(2025, 9, 2, 3, tzinfo=UTC)
    result = verify_rainfall(
        _forecast(), np.ones((2, 2)), _observation(np.zeros((2, 2))), start, end
    )

    assert result.status is RainfallVerificationStatus.TEMPORAL_MISMATCH
    assert result.error_field is None
    assert result.mae is None
    assert result.forecast_start == datetime(2025, 9, 1, tzinfo=UTC)
    assert result.observation_start == start


def test_invalid_forecast_accumulation_metadata_is_blocked() -> None:
    start, end = _explicit_window()
    result = verify_rainfall(
        _forecast(end_step=12), np.ones((2, 2)), _observation(np.zeros((2, 2))), start, end
    )

    assert result.status is RainfallVerificationStatus.INVALID_METADATA
    assert result.error_field is None
    assert result.provenance["reason"] == "Forecast precipitation must have startStep=0 and endStep=24"


def test_different_grids_use_existing_conservative_remapping() -> None:
    start, end = _explicit_window()
    observation = _observation(
        np.full((2, 2), 2.0),
        latitude=np.array([20.5, 19.5]),
        longitude=np.array([70.5, 71.5]),
    )

    result = verify_rainfall(
        _forecast(), np.full((2, 2), 3.0), observation, start, end
    )

    assert result.status is RainfallVerificationStatus.ALIGNED
    assert np.allclose(result.error_field, 1.0)


def test_no_valid_cells_return_empty_status() -> None:
    start, end = _explicit_window()
    result = verify_rainfall(
        _forecast(), np.ones((2, 2)), _observation(np.full((2, 2), np.nan)), start, end
    )

    assert result.status is RainfallVerificationStatus.EMPTY_VALID_SET
    assert result.error_field is None
    assert result.valid_cell_count == 0
    assert result.missing_cell_count == 4
    assert result.rmse is None


def test_provenance_preserves_sources_and_alignment_metadata() -> None:
    start, end = _explicit_window()
    result = verify_rainfall(
        _forecast(), np.ones((2, 2)), _observation(np.zeros((2, 2))), start, end
    )

    assert result.provenance["observation_source"] == "imd.grd"
    assert result.provenance["observation_date"].isoformat() == "2025-09-01"
    assert result.provenance["forecast_units"] == "kg m**-2"
    assert result.provenance["alignment_status"] == "ALIGNED"
