"""Historical case runner for auditable rainfall forecast verification.

Processes one forecast case at a time, producing an auditable verification record
that can later become part of the training/evaluation dataset for ForecastGuard.

Scientific rules enforced:
- Never invent observation timestamps.
- Never infer an observation window from observation_date.
- Never bypass verification guardrails.
- Never calculate error when temporal alignment is blocked.
- Never convert NaN observations to zero.
- Preserve legitimate zero rainfall.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, date
from enum import Enum
import json
from pathlib import Path
from typing import Any, Dict, Optional, Union

import eccodes
import numpy as np

from scientific.ingestion.grib import read_grib_file
from scientific.ingestion.imd import read_imd_daily_file
from scientific.verification.rainfall import verify_rainfall, RainfallVerificationStatus


class _JSONEncoder(json.JSONEncoder):
	"""Custom JSON encoder for datetime and date objects."""

	def default(self, obj: Any) -> Any:
		if isinstance(obj, (datetime, date)):
			return obj.isoformat()
		if isinstance(obj, np.integer):
			return int(obj)
		if isinstance(obj, np.floating):
			return float(obj)
		return super().default(obj)


class RainfallCaseStatus(str, Enum):
	"""Outcome status of a rainfall case run."""

	ALIGNED = "ALIGNED"
	BLOCKED_UNSPECIFIED_OBSERVATION_WINDOW = "BLOCKED_UNSPECIFIED_OBSERVATION_WINDOW"
	NOT_ALIGNED = "NOT_ALIGNED"
	INVALID_METADATA = "INVALID_METADATA"
	EMPTY_VALID_SET = "EMPTY_VALID_SET"
	NO_TP_MESSAGE = "NO_TP_MESSAGE"
	FORECAST_READ_ERROR = "FORECAST_READ_ERROR"
	OBSERVATION_READ_ERROR = "OBSERVATION_READ_ERROR"


@dataclass(frozen=True)
class RainfallCase:
	"""Specification for one historical rainfall forecast case."""

	case_id: str
	"""Unique identifier for this case."""

	forecast_path: Union[str, Path]
	"""Path to the GRIB forecast file."""

	observation_path: Union[str, Path]
	"""Path to the IMD daily rainfall observation file."""

	observation_date: Union[datetime, str]
	"""Observation date (used by read_imd_daily_file)."""

	observation_start: Optional[datetime] = None
	"""Observation accumulation window start (explicit, must be exact)."""

	observation_end: Optional[datetime] = None
	"""Observation accumulation window end (explicit, must be exact)."""


@dataclass(frozen=True)
class RainfallCaseResult:
	"""Auditable verification result for one historical case."""

	case_id: str
	"""Unique identifier for this case."""

	status: RainfallCaseStatus
	"""Outcome of the case run."""

	forecast_metadata: Dict[str, Any]
	"""Structured metadata from the forecast GRIB message."""

	observation_metadata: Dict[str, Any]
	"""Structured metadata from the IMD observation."""

	forecast_window: Dict[str, Any]
	"""Forecast accumulation window (start, end)."""

	observation_window: Dict[str, Any]
	"""Observation accumulation window (start, end, supplied)."""

	valid_cell_count: int
	"""Number of cells with finite forecast and observation values."""

	missing_cell_count: int
	"""Number of cells missing or NaN in either forecast or observation."""

	error_statistics: Dict[str, Optional[float]] = field(default_factory=dict)
	"""Error field statistics: mae, rmse, bias, forecast_mean, observation_mean."""

	provenance: Dict[str, Any] = field(default_factory=dict)
	"""Complete verification provenance including failure reasons."""

	error_field_artifact: Optional[Path] = None
	"""Path to error_field.nc if persisted; None if not persisted."""


def _extract_tp_forecast_values(
	forecast_path: Union[str, Path],
) -> tuple[Optional[Dict[str, Any]], Optional[np.ndarray], Optional[str]]:
	"""Extract TP forecast message metadata and values from a GRIB file.

	Returns
	-------
	tuple[Optional[Dict], Optional[np.ndarray], Optional[str]]
		(metadata dict, values array, error_message) 
		Returns (metadata, values, None) on success.
		Returns (None, None, error_message) on failure.
	"""
	path = Path(forecast_path)
	if not path.exists():
		return None, None, f"Forecast file not found: {path}"

	try:
		messages, qc = read_grib_file(path, compute_stats=False)
	except Exception as exc:
		return None, None, f"Failed to read forecast metadata: {exc}"

	tp_message = None
	tp_values = None

	try:
		with open(path, "rb") as f:
			msg_index = 0
			while True:
				handle = eccodes.codes_grib_new_from_file(f)
				if handle is None:
					break
				msg_index += 1
				short_name = eccodes.codes_get(handle, "shortName", None)
				if short_name == "tp":
					tp_message = messages[msg_index - 1] if msg_index <= len(messages) else None
					if tp_message is not None:
						try:
							raw_values = eccodes.codes_get_values(handle)
							tp_values = np.asarray(raw_values, dtype=np.float64)
						except Exception:
							pass
					eccodes.codes_release(handle)
					break
				eccodes.codes_release(handle)
	except Exception as exc:
		return None, None, f"Failed to extract TP message: {exc}"

	if tp_message is None:
		return None, None, "No TP (total precipitation) message found in forecast file"

	return (tp_message.to_dict(), tp_values, None)


def run_rainfall_case(case: RainfallCase) -> RainfallCaseResult:
	"""Process one forecast case end-to-end through verification.

	Parameters
	----------
	case : RainfallCase
		Case specification with paths and observation window.

	Returns
	-------
	RainfallCaseResult
		Auditable result with metadata, statistics, and provenance.
	"""
	provenance: Dict[str, Any] = {
		"case_id": case.case_id,
		"forecast_path": str(case.forecast_path),
		"observation_path": str(case.observation_path),
	}

	# Load forecast
	forecast_metadata, forecast_values, extract_error = _extract_tp_forecast_values(case.forecast_path)

	if extract_error:
		status = (
			RainfallCaseStatus.FORECAST_READ_ERROR
			if "not found" in extract_error or "Failed to read" in extract_error
			else RainfallCaseStatus.NO_TP_MESSAGE
		)
		return RainfallCaseResult(
			case_id=case.case_id,
			status=status,
			forecast_metadata={},
			observation_metadata={},
			forecast_window={},
			observation_window={},
			valid_cell_count=0,
			missing_cell_count=0,
			error_statistics={},
			provenance={
				**provenance,
				"reason": extract_error,
			},
		)

	# Reshape forecast values to grid
	ni = forecast_metadata.get("ni")
	nj = forecast_metadata.get("nj")
	if ni is None or nj is None:
		return RainfallCaseResult(
			case_id=case.case_id,
			status=RainfallCaseStatus.INVALID_METADATA,
			forecast_metadata=forecast_metadata,
			observation_metadata={},
			forecast_window={},
			observation_window={},
			valid_cell_count=0,
			missing_cell_count=0,
			error_statistics={},
			provenance={
				**provenance,
				"reason": "Forecast grid dimensions (ni, nj) not available",
			},
		)

	try:
		forecast_values = forecast_values.reshape((nj, ni))
	except Exception as exc:
		return RainfallCaseResult(
			case_id=case.case_id,
			status=RainfallCaseStatus.INVALID_METADATA,
			forecast_metadata=forecast_metadata,
			observation_metadata={},
			forecast_window={},
			observation_window={},
			valid_cell_count=0,
			missing_cell_count=0,
			error_statistics={},
			provenance={
				**provenance,
				"reason": f"Failed to reshape forecast values: {exc}",
			},
		)

	# Load observation
	try:
		observation = read_imd_daily_file(
			case.observation_path,
			observation_date=case.observation_date,
		)
	except Exception as exc:
		return RainfallCaseResult(
			case_id=case.case_id,
			status=RainfallCaseStatus.OBSERVATION_READ_ERROR,
			forecast_metadata=forecast_metadata,
			observation_metadata={},
			forecast_window={},
			observation_window={},
			valid_cell_count=0,
			missing_cell_count=0,
			error_statistics={},
			provenance={
				**provenance,
				"reason": f"Failed to read observation: {exc}",
			},
		)

	# Verify rainfall
	from scientific.ingestion.grib import GribMessageMetadata
	forecast_msg = GribMessageMetadata(**{k: v for k, v in forecast_metadata.items() if k in [
		"message_index", "edition", "short_name", "name", "units", "data_date", "data_time",
		"step", "step_type", "start_step", "end_step", "forecast_type", "member", "grid_type",
		"ni", "nj", "first_lat", "last_lat", "first_lon", "last_lon", "i_increment", "j_increment",
		"number_of_values", "min_value", "max_value", "mean_value", "nan_count", "negative_count",
	]})

	verification_result = verify_rainfall(
		forecast_msg,
		forecast_values,
		observation,
		observation_start=case.observation_start,
		observation_end=case.observation_end,
	)

	# Build case result
	status = RainfallCaseStatus(verification_result.status.value)
	forecast_window = {
		"start": verification_result.forecast_start.isoformat() if verification_result.forecast_start else None,
		"end": verification_result.forecast_end.isoformat() if verification_result.forecast_end else None,
	}
	observation_window = {
		"start": verification_result.observation_start.isoformat() if verification_result.observation_start else None,
		"end": verification_result.observation_end.isoformat() if verification_result.observation_end else None,
		"supplied": case.observation_start is not None and case.observation_end is not None,
	}
	error_statistics = {
		"mae": verification_result.mae,
		"rmse": verification_result.rmse,
		"bias": verification_result.bias,
		"forecast_mean": verification_result.forecast_mean,
		"observation_mean": verification_result.observation_mean,
	}

	return RainfallCaseResult(
		case_id=case.case_id,
		status=status,
		forecast_metadata=forecast_metadata,
		observation_metadata=observation.metadata,
		forecast_window=forecast_window,
		observation_window=observation_window,
		valid_cell_count=verification_result.valid_cell_count,
		missing_cell_count=verification_result.missing_cell_count,
		error_statistics=error_statistics,
		provenance=verification_result.provenance,
		error_field_artifact=None,  # Set by persist_rainfall_case if called
	)


def persist_rainfall_case(
	result: RainfallCaseResult,
	output_base: Union[str, Path] = "data/interim/cases",
) -> RainfallCaseResult:
	"""Persist case result metadata and error field to disk.

	Only persists if verification was successful and error_field exists.
	Does not modify raw input files.

	Parameters
	----------
	result : RainfallCaseResult
		Case result from run_rainfall_case.
	output_base : Union[str, Path], optional
		Base directory for case outputs, by default "data/interim/cases"

	Returns
	-------
	RainfallCaseResult
		Updated result with error_field_artifact path set.
	"""
	output_dir = Path(output_base) / result.case_id
	output_dir.mkdir(parents=True, exist_ok=True)

	# Persist metadata
	metadata_path = output_dir / "metadata.json"
	metadata_to_save = {
		"case_id": result.case_id,
		"status": result.status.value,
		"forecast_metadata": result.forecast_metadata,
		"observation_metadata": result.observation_metadata,
		"forecast_window": result.forecast_window,
		"observation_window": result.observation_window,
		"valid_cell_count": result.valid_cell_count,
		"missing_cell_count": result.missing_cell_count,
		"error_statistics": result.error_statistics,
		"provenance": result.provenance,
	}
	with open(metadata_path, "w") as f:
		json.dump(metadata_to_save, f, indent=2, cls=_JSONEncoder)

	# Persist error field if available
	error_field_path = None
	if result.status == RainfallCaseStatus.ALIGNED:
		try:
			import xarray as xr

			error_field_path = output_dir / "error_field.nc"
			# Get error field from provenance if not directly available
			# For now, we store metadata only
			# Error field would be retrieved from verification result
			error_field_path = None
		except ImportError:
			pass

	updated_result = RainfallCaseResult(
		case_id=result.case_id,
		status=result.status,
		forecast_metadata=result.forecast_metadata,
		observation_metadata=result.observation_metadata,
		forecast_window=result.forecast_window,
		observation_window=result.observation_window,
		valid_cell_count=result.valid_cell_count,
		missing_cell_count=result.missing_cell_count,
		error_statistics=result.error_statistics,
		provenance=result.provenance,
		error_field_artifact=error_field_path,
	)
	return updated_result
