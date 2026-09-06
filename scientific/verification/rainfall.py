"""Auditable rainfall forecast-versus-observation verification."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

import numpy as np

from scientific.alignment import AlignmentStatus, validate_rainfall_alignment
from scientific.ingestion.grib import GribMessageMetadata
from scientific.ingestion.imd import ImdDailyObservation
from scientific.remapping import conservative_remap_regular_latlon


class RainfallVerificationStatus(str, Enum):
    """Outcomes of rainfall verification eligibility and calculation."""

    ALIGNED = AlignmentStatus.ALIGNED.value
    BLOCKED_UNSPECIFIED_OBSERVATION_WINDOW = (
        AlignmentStatus.BLOCKED_UNSPECIFIED_OBSERVATION_WINDOW.value
    )
    NOT_ALIGNED = AlignmentStatus.NOT_ALIGNED.value
    TEMPORAL_MISMATCH = AlignmentStatus.NOT_ALIGNED.value
    INVALID_METADATA = AlignmentStatus.INVALID_METADATA.value
    EMPTY_VALID_SET = "EMPTY_VALID_SET"


@dataclass(frozen=True)
class RainfallVerificationResult:
    """Rainfall error field, statistics, and provenance for one comparison."""

    status: RainfallVerificationStatus
    forecast_start: Optional[datetime]
    forecast_end: Optional[datetime]
    observation_start: Optional[datetime]
    observation_end: Optional[datetime]
    error_field: Optional[np.ndarray]
    valid_cell_count: int
    missing_cell_count: int
    mae: Optional[float]
    rmse: Optional[float]
    bias: Optional[float]
    forecast_mean: Optional[float]
    observation_mean: Optional[float]
    provenance: Dict[str, Any]


def _target_coordinates(forecast: GribMessageMetadata) -> tuple[np.ndarray, np.ndarray]:
    if (
        forecast.ni is None
        or forecast.nj is None
        or forecast.first_lat is None
        or forecast.last_lat is None
        or forecast.first_lon is None
        or forecast.last_lon is None
        or forecast.ni <= 0
        or forecast.nj <= 0
    ):
        raise ValueError("Forecast grid metadata is incomplete")
    latitude = np.linspace(forecast.first_lat, forecast.last_lat, forecast.nj)
    longitude = np.linspace(forecast.first_lon, forecast.last_lon, forecast.ni)
    return latitude, longitude


def _blocked_result(
    status: RainfallVerificationStatus,
    reason: str,
    forecast: GribMessageMetadata,
    observation: ImdDailyObservation,
    forecast_start: Optional[datetime] = None,
    forecast_end: Optional[datetime] = None,
    observation_start: Optional[datetime] = None,
    observation_end: Optional[datetime] = None,
    observation_window_metadata: Optional[Dict[str, Any]] = None,
) -> RainfallVerificationResult:
    return RainfallVerificationResult(
        status=status,
        forecast_start=forecast_start,
        forecast_end=forecast_end,
        observation_start=observation_start,
        observation_end=observation_end,
        error_field=None,
        valid_cell_count=0,
        missing_cell_count=0,
        mae=None,
        rmse=None,
        bias=None,
        forecast_mean=None,
        observation_mean=None,
        provenance={
            "reason": reason,
            "forecast_metadata": forecast.to_dict(),
            "observation_source": observation.source_file,
            "observation_date": observation.observation_date,
            "observation_accumulation_window": observation.accumulation_window,
            "observation_window_metadata": observation_window_metadata,
        },
    )


def verify_rainfall(
    forecast: GribMessageMetadata,
    forecast_values: np.ndarray,
    observation: ImdDailyObservation,
    observation_start: Optional[datetime] = None,
    observation_end: Optional[datetime] = None,
    observation_window_metadata: Optional[Dict[str, Any]] = None,
) -> RainfallVerificationResult:
    """Verify an explicit 0-24 hour forecast against an IMD rainfall field.

    No verification is performed unless the existing alignment validator accepts
    the forecast metadata and an explicit observation accumulation window.
    """
    forecast_array = np.asarray(forecast_values, dtype=np.float64)
    try:
        target_latitude, target_longitude = _target_coordinates(forecast)
    except ValueError as exc:
        return _blocked_result(
            RainfallVerificationStatus.INVALID_METADATA,
            str(exc),
            forecast,
            observation,
            observation_window_metadata=observation_window_metadata,
        )

    if forecast.units != "kg m**-2":
        return _blocked_result(
            RainfallVerificationStatus.INVALID_METADATA,
            "Forecast precipitation units must be kg m**-2",
            forecast,
            observation,
            observation_window_metadata=observation_window_metadata,
        )
    if forecast.start_step != 0 or forecast.end_step != 24:
        return _blocked_result(
            RainfallVerificationStatus.INVALID_METADATA,
            "Forecast precipitation must have startStep=0 and endStep=24",
            forecast,
            observation,
            observation_window_metadata=observation_window_metadata,
        )
    if forecast_array.shape != (forecast.nj, forecast.ni):
        return _blocked_result(
            RainfallVerificationStatus.INVALID_METADATA,
            "Forecast values shape does not match forecast grid metadata",
            forecast,
            observation,
            observation_window_metadata=observation_window_metadata,
        )

    alignment = validate_rainfall_alignment(
        forecast,
        observation,  # ImdDailyObservation has the coordinates required by this validator.
        observation_start,
        observation_end,
    )
    status = RainfallVerificationStatus(alignment.status.value)
    provenance = {
        "alignment_status": alignment.status.value,
        "alignment_reason": alignment.reason,
        "forecast_start": alignment.forecast_accumulation_start,
        "forecast_end": alignment.forecast_accumulation_end,
        "observation_start": observation_start,
        "observation_end": observation_end,
        "forecast_metadata": forecast.to_dict(),
        "forecast_grid": alignment.spatial_grid.forecast,
        "observation_grid": alignment.spatial_grid.observation,
        "forecast_units": forecast.units,
        "observation_source": observation.source_file,
        "observation_date": observation.observation_date,
        "observation_accumulation_window": observation.accumulation_window,
        "observation_window_supplied": (
            observation_start is not None
            and observation_end is not None
        ),
        "observation_window_metadata": observation_window_metadata,
    }
    if alignment.status is not AlignmentStatus.ALIGNED:
        return RainfallVerificationResult(
            status=status,
            forecast_start=alignment.forecast_accumulation_start,
            forecast_end=alignment.forecast_accumulation_end,
            observation_start=observation_start,
            observation_end=observation_end,
            error_field=None,
            valid_cell_count=0,
            missing_cell_count=0,
            mae=None,
            rmse=None,
            bias=None,
            forecast_mean=None,
            observation_mean=None,
            provenance=provenance,
        )

    observation_values = np.asarray(observation.rainfall)
    if observation_values.ndim == 3 and observation_values.shape[0] == 1:
        observation_values = observation_values[0]
    if observation_values.shape != (observation.latitude.size, observation.longitude.size):
        raise ValueError("Observation values shape does not match observation coordinates")

    if alignment.spatial_grid.status == "IDENTICAL":
        comparable_observation = observation_values.astype(np.float64, copy=False)
    else:
        comparable_observation = conservative_remap_regular_latlon(
            observation_values,
            observation.latitude,
            observation.longitude,
            target_latitude,
            target_longitude,
        )

    valid = np.isfinite(forecast_array) & np.isfinite(comparable_observation)
    valid_cell_count = int(valid.sum())
    missing_cell_count = int(valid.size - valid_cell_count)
    if valid_cell_count == 0:
        provenance["reason"] = "No cells contain finite forecast and observation values"
        return RainfallVerificationResult(
            status=RainfallVerificationStatus.EMPTY_VALID_SET,
            forecast_start=alignment.forecast_accumulation_start,
            forecast_end=alignment.forecast_accumulation_end,
            observation_start=observation_start,
            observation_end=observation_end,
            error_field=None,
            valid_cell_count=0,
            missing_cell_count=missing_cell_count,
            mae=None,
            rmse=None,
            bias=None,
            forecast_mean=None,
            observation_mean=None,
            provenance=provenance,
        )

    error_field = np.full(forecast_array.shape, np.nan, dtype=np.float64)
    error_field[valid] = forecast_array[valid] - comparable_observation[valid]
    errors = error_field[valid]
    return RainfallVerificationResult(
        status=RainfallVerificationStatus.ALIGNED,
        forecast_start=alignment.forecast_accumulation_start,
        forecast_end=alignment.forecast_accumulation_end,
        observation_start=observation_start,
        observation_end=observation_end,
        error_field=error_field,
        valid_cell_count=valid_cell_count,
        missing_cell_count=missing_cell_count,
        mae=float(np.mean(np.abs(errors))),
        rmse=float(np.sqrt(np.mean(errors**2))),
        bias=float(np.mean(errors)),
        forecast_mean=float(np.mean(forecast_array[valid])),
        observation_mean=float(np.mean(comparable_observation[valid])),
        provenance=provenance,
    )


verify_rainfall_field = verify_rainfall
