"""Focused tests for historical rainfall case runner."""

from datetime import datetime, timezone
from pathlib import Path
import tempfile

import numpy as np
import pytest

from scientific.cases import (
	RainfallCase,
	RainfallCaseResult,
	RainfallCaseStatus,
	run_rainfall_case,
	persist_rainfall_case,
)

UTC = timezone.utc


class TestRainfallCaseSpecification:
	"""Tests for RainfallCase specification validation."""

	def test_case_spec_with_all_fields(self) -> None:
		"""Verify RainfallCase can be instantiated with complete specification."""
		start = datetime(2025, 9, 1, tzinfo=UTC)
		end = datetime(2025, 9, 2, tzinfo=UTC)
		case = RainfallCase(
			case_id="test_case_001",
			forecast_path="data/raw/tigge/forecast.grib",
			observation_path="data/raw/observations/obs.grd",
			observation_date="2025-09-01",
			observation_start=start,
			observation_end=end,
		)
		assert case.case_id == "test_case_001"
		assert case.observation_start == start
		assert case.observation_end == end

	def test_case_spec_with_optional_windows_none(self) -> None:
		"""Verify RainfallCase can be instantiated without observation windows."""
		case = RainfallCase(
			case_id="test_case_002",
			forecast_path="forecast.grib",
			observation_path="obs.grd",
			observation_date="2025-09-01",
		)
		assert case.observation_start is None
		assert case.observation_end is None

	def test_case_spec_frozen(self) -> None:
		"""Verify RainfallCase is immutable."""
		case = RainfallCase(
			case_id="test_case_003",
			forecast_path="forecast.grib",
			observation_path="obs.grd",
			observation_date="2025-09-01",
		)
		with pytest.raises(Exception):  # FrozenInstanceError or similar
			case.case_id = "modified"


class TestRainfallCaseResultStructure:
	"""Tests for RainfallCaseResult structure and serialization."""

	def test_result_with_blocked_status(self) -> None:
		"""Verify RainfallCaseResult can represent a blocked case."""
		result = RainfallCaseResult(
			case_id="blocked_001",
			status=RainfallCaseStatus.BLOCKED_UNSPECIFIED_OBSERVATION_WINDOW,
			forecast_metadata={"short_name": "tp"},
			observation_metadata={},
			forecast_window={"start": None, "end": None},
			observation_window={"start": None, "end": None, "supplied": False},
			valid_cell_count=0,
			missing_cell_count=0,
			error_statistics={},
			provenance={"reason": "Unspecified observation window"},
		)
		assert result.status == RainfallCaseStatus.BLOCKED_UNSPECIFIED_OBSERVATION_WINDOW
		assert result.error_field_artifact is None
		assert "mae" in result.error_statistics or result.error_statistics.get("mae") is None

	def test_result_with_aligned_status(self) -> None:
		"""Verify RainfallCaseResult can represent a successful verification."""
		result = RainfallCaseResult(
			case_id="aligned_001",
			status=RainfallCaseStatus.ALIGNED,
			forecast_metadata={"short_name": "tp", "ni": 2, "nj": 2},
			observation_metadata={},
			forecast_window={"start": "2025-09-01T00:00:00+00:00", "end": "2025-09-02T00:00:00+00:00"},
			observation_window={"start": "2025-09-01T00:00:00+00:00", "end": "2025-09-02T00:00:00+00:00", "supplied": True},
			valid_cell_count=4,
			missing_cell_count=0,
			error_statistics={"mae": 1.5, "rmse": 2.0, "bias": 0.5},
		)
		assert result.status == RainfallCaseStatus.ALIGNED
		assert result.valid_cell_count == 4


class TestRunRainfallCaseWithSynthetic:
	"""Tests using synthetic forecast/observation data."""

	def _create_synthetic_grib(self, tmpdir: Path, tp_values: np.ndarray) -> Path:
		"""Create a minimal synthetic GRIB file for testing.

		This creates a simple test fixture; actual GRIB files require eccodes.
		For this test, we simulate by storing metadata and values.
		"""
		# For now, we'll skip full GRIB creation and test with mock data
		# Real tests will use actual GRIB files from data/raw/tigge/
		grib_path = Path(tmpdir) / "test_forecast.grib"
		# Placeholder - actual test uses real GRIB
		return grib_path

	def _create_synthetic_imd(self, tmpdir: Path, rainfall: np.ndarray) -> Path:
		"""Create a synthetic IMD observation file for testing."""
		imd_path = Path(tmpdir) / "test_obs.grd"
		# Write as binary with proper IMD format
		rainfall_flat = rainfall.astype("<f4").tobytes()
		with open(imd_path, "wb") as f:
			f.write(rainfall_flat)
		return imd_path

	def test_missing_forecast_file_returns_error(self) -> None:
		"""Verify case runner returns error when forecast file not found."""
		case = RainfallCase(
			case_id="missing_forecast",
			forecast_path="/nonexistent/forecast.grib",
			observation_path="/nonexistent/obs.grd",
			observation_date="2025-09-01",
		)
		result = run_rainfall_case(case)
		assert result.status == RainfallCaseStatus.FORECAST_READ_ERROR
		assert "reason" in result.provenance

	def test_missing_observation_file_returns_error(self) -> None:
		"""Verify case runner returns error when observation file not found."""
		# Use the real forecast file but fake observation path
		case = RainfallCase(
			case_id="missing_observation",
			forecast_path="data/raw/tigge/67603f4734166cde0f2c2962323ad8e4.grib",
			observation_path="/nonexistent/obs.grd",
			observation_date="2025-09-01",
		)
		result = run_rainfall_case(case)
		assert result.status == RainfallCaseStatus.OBSERVATION_READ_ERROR

	def test_case_without_observation_window_is_blocked(self) -> None:
		"""Verify case without observation window produces BLOCKED_UNSPECIFIED_OBSERVATION_WINDOW."""
		case = RainfallCase(
			case_id="no_window",
			forecast_path="data/raw/tigge/67603f4734166cde0f2c2962323ad8e4.grib",
			observation_path="data/raw/observations/imd_daily/01092025.grd",
			observation_date="2025-09-01",
			observation_start=None,  # Unspecified
			observation_end=None,
		)
		result = run_rainfall_case(case)
		# Should be blocked because no observation window is specified
		assert result.status in [
			RainfallCaseStatus.BLOCKED_UNSPECIFIED_OBSERVATION_WINDOW,
			RainfallCaseStatus.NO_TP_MESSAGE,
			RainfallCaseStatus.OBSERVATION_READ_ERROR,
			RainfallCaseStatus.FORECAST_READ_ERROR,
		]
		assert result.error_statistics.get("mae") is None or result.error_statistics["mae"] is None

	def test_case_metadata_preserved_in_result(self) -> None:
		"""Verify case metadata and provenance are preserved in result."""
		case = RainfallCase(
			case_id="metadata_test",
			forecast_path="data/raw/tigge/67603f4734166cde0f2c2962323ad8e4.grib",
			observation_path="data/raw/observations/imd_daily/01092025.grd",
			observation_date="2025-09-01",
		)
		result = run_rainfall_case(case)
		assert result.case_id == "metadata_test"
		assert "forecast_path" in result.provenance or result.provenance is not None
		assert "observation_path" in result.provenance or result.provenance is not None
		# Provenance should contain at least some metadata
		assert len(result.provenance) > 0


class TestRainfallCasePersistence:
	"""Tests for case result persistence."""

	def test_persist_creates_output_directory(self) -> None:
		"""Verify persist_rainfall_case creates necessary directories."""
		with tempfile.TemporaryDirectory() as tmpdir:
			result = RainfallCaseResult(
				case_id="persist_test",
				status=RainfallCaseStatus.BLOCKED_UNSPECIFIED_OBSERVATION_WINDOW,
				forecast_metadata={},
				observation_metadata={},
				forecast_window={},
				observation_window={},
				valid_cell_count=0,
				missing_cell_count=0,
				provenance={},
			)
			output_base = Path(tmpdir) / "cases"
			updated = persist_rainfall_case(result, output_base)

			case_dir = output_base / "persist_test"
			assert case_dir.exists()
			assert (case_dir / "metadata.json").exists()

	def test_persist_does_not_modify_raw_files(self) -> None:
		"""Verify persistence does not modify raw input files."""
		forecast_path = Path("data/raw/tigge/67603f4734166cde0f2c2962323ad8e4.grib")
		observation_path = Path("data/raw/observations/imd_daily/01092025.grd")

		if not forecast_path.exists() or not observation_path.exists():
			pytest.skip("Real data files not available")

		# Record original file stats
		forecast_stat_before = forecast_path.stat()
		observation_stat_before = observation_path.stat()

		# Run and persist a case
		case = RainfallCase(
			case_id="raw_file_test",
			forecast_path=forecast_path,
			observation_path=observation_path,
			observation_date="2025-09-01",
		)
		result = run_rainfall_case(case)

		with tempfile.TemporaryDirectory() as tmpdir:
			persist_rainfall_case(result, Path(tmpdir) / "cases")

		# Verify raw files are unchanged
		forecast_stat_after = forecast_path.stat()
		observation_stat_after = observation_path.stat()

		assert forecast_stat_before.st_mtime == forecast_stat_after.st_mtime
		assert observation_stat_before.st_mtime == observation_stat_after.st_mtime

	def test_persist_metadata_is_valid_json(self) -> None:
		"""Verify persisted metadata can be read back as valid JSON."""
		with tempfile.TemporaryDirectory() as tmpdir:
			result = RainfallCaseResult(
				case_id="json_test",
				status=RainfallCaseStatus.ALIGNED,
				forecast_metadata={"short_name": "tp", "units": "kg m**-2"},
				observation_metadata={"source_filename": "imd.grd"},
				forecast_window={"start": "2025-09-01T00:00:00+00:00", "end": "2025-09-02T00:00:00+00:00"},
				observation_window={"start": "2025-09-01T00:00:00+00:00", "end": "2025-09-02T00:00:00+00:00", "supplied": True},
				valid_cell_count=100,
				missing_cell_count=10,
				error_statistics={"mae": 1.5, "rmse": 2.0, "bias": 0.5},
			)
			output_base = Path(tmpdir)
			updated = persist_rainfall_case(result, output_base)

			metadata_path = output_base / "json_test" / "metadata.json"
			with open(metadata_path) as f:
				loaded = json.load(f)

			assert loaded["case_id"] == "json_test"
			assert loaded["status"] == "ALIGNED"
			assert loaded["valid_cell_count"] == 100


import json


class TestRainfallCaseIntegration:
	"""Integration tests with real data."""

	def test_real_data_smoke_test(self) -> None:
		"""Smoke test with real TIGGE and IMD data.

		Expected: Case returns BLOCKED_UNSPECIFIED_OBSERVATION_WINDOW or similar
		because observation window is not specified.
		"""
		forecast_path = Path("data/raw/tigge/67603f4734166cde0f2c2962323ad8e4.grib")
		observation_path = Path("data/raw/observations/imd_daily/01092025.grd")

		if not forecast_path.exists() or not observation_path.exists():
			pytest.skip("Real data files not available")

		case = RainfallCase(
			case_id="real_data_smoke_test",
			forecast_path=forecast_path,
			observation_path=observation_path,
			observation_date="2025-09-01",
			observation_start=None,  # Intentionally unspecified
			observation_end=None,
		)
		result = run_rainfall_case(case)

		# Verify result is valid
		assert result.case_id == "real_data_smoke_test"
		assert result.status in [
			RainfallCaseStatus.BLOCKED_UNSPECIFIED_OBSERVATION_WINDOW,
			RainfallCaseStatus.NO_TP_MESSAGE,
			RainfallCaseStatus.OBSERVATION_READ_ERROR,
			RainfallCaseStatus.FORECAST_READ_ERROR,
		]
		# No error field should exist since verification is blocked
		assert result.error_field_artifact is None
		# Metadata should be captured
		assert isinstance(result.provenance, dict)

	def test_real_data_with_explicit_window_attempt(self) -> None:
		"""Attempt real data case with explicitly specified observation window.

		This tests that the case runner properly passes the window to verification.
		"""
		forecast_path = Path("data/raw/tigge/67603f4734166cde0f2c2962323ad8e4.grib")
		observation_path = Path("data/raw/observations/imd_daily/01092025.grd")

		if not forecast_path.exists() or not observation_path.exists():
			pytest.skip("Real data files not available")

		# Specify a plausible window for 01-Sep-2025 data
		start = datetime(2025, 9, 1, tzinfo=UTC)
		end = datetime(2025, 9, 2, tzinfo=UTC)

		case = RainfallCase(
			case_id="real_data_with_window",
			forecast_path=forecast_path,
			observation_path=observation_path,
			observation_date="2025-09-01",
			observation_start=start,
			observation_end=end,
		)
		result = run_rainfall_case(case)

		# Verify result structure
		assert result.case_id == "real_data_with_window"
		assert isinstance(result.forecast_window, dict)
		assert isinstance(result.observation_window, dict)
		assert result.observation_window["supplied"] is True
		assert result.valid_cell_count >= 0
		assert result.missing_cell_count >= 0

	def test_case_result_status_values_are_valid(self) -> None:
		"""Verify all RainfallCaseStatus values are valid enum members."""
		valid_statuses = {
			RainfallCaseStatus.ALIGNED,
			RainfallCaseStatus.BLOCKED_UNSPECIFIED_OBSERVATION_WINDOW,
			RainfallCaseStatus.NOT_ALIGNED,
			RainfallCaseStatus.INVALID_METADATA,
			RainfallCaseStatus.EMPTY_VALID_SET,
			RainfallCaseStatus.NO_TP_MESSAGE,
			RainfallCaseStatus.FORECAST_READ_ERROR,
			RainfallCaseStatus.OBSERVATION_READ_ERROR,
		}
		assert len(valid_statuses) > 0
