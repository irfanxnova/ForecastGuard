"""Validation-only contract for forecast and observation rainfall alignment."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Optional

import numpy as np

from scientific.ingestion.grib import GribMessageMetadata
from scientific.ingestion.mera import MeraObservation


class AlignmentStatus(str, Enum):
    """Possible outcomes of rainfall alignment validation."""

    ALIGNED = "ALIGNED"
    BLOCKED_UNSPECIFIED_OBSERVATION_WINDOW = "BLOCKED_UNSPECIFIED_OBSERVATION_WINDOW"
    NOT_ALIGNED = "NOT_ALIGNED"
    INVALID_METADATA = "INVALID_METADATA"


@dataclass(frozen=True)
class GridCompatibility:
    """Metadata-only comparison of forecast and observation grids."""

    status: str
    forecast: Dict[str, Any]
    observation: Dict[str, Any]
    reason: str


@dataclass(frozen=True)
class RainfallAlignmentResult:
    """Traceable rainfall window and grid validation result."""

    status: AlignmentStatus
    forecast_initialization_time: Optional[datetime]
    forecast_accumulation_start: Optional[datetime]
    forecast_accumulation_end: Optional[datetime]
    observation_accumulation_start: Optional[datetime]
    observation_accumulation_end: Optional[datetime]
    spatial_grid: GridCompatibility
    reason: str


def _forecast_initialization_time(message: GribMessageMetadata) -> Optional[datetime]:
    """Convert complete GRIB date/time metadata to an aware UTC datetime."""
    if message.data_date <= 0 or not 0 <= message.data_time <= 2359:
        return None
    hour, minute = divmod(message.data_time, 100)
    if minute > 59:
        return None
    try:
        return datetime(
            message.data_date // 10000,
            (message.data_date // 100) % 100,
            message.data_date % 100,
            hour,
            minute,
            tzinfo=timezone.utc,
        )
    except ValueError:
        return None


def _grid_metadata(message: GribMessageMetadata) -> Dict[str, Any]:
    return {
        "grid_type": message.grid_type,
        "ni": message.ni,
        "nj": message.nj,
        "first_lat": message.first_lat,
        "last_lat": message.last_lat,
        "first_lon": message.first_lon,
        "last_lon": message.last_lon,
        "i_increment": message.i_increment,
        "j_increment": message.j_increment,
    }


def _observation_grid(observation: MeraObservation) -> Dict[str, Any]:
    latitude = observation.latitude
    longitude = observation.longitude
    return {
        "grid_type": "regular_latitude_longitude",
        "ni": int(longitude.size),
        "nj": int(latitude.size),
        "first_lat": float(latitude[0]) if latitude.size else None,
        "last_lat": float(latitude[-1]) if latitude.size else None,
        "first_lon": float(longitude[0]) if longitude.size else None,
        "last_lon": float(longitude[-1]) if longitude.size else None,
        "i_increment": float(longitude[1] - longitude[0]) if longitude.size > 1 else None,
        "j_increment": float(latitude[1] - latitude[0]) if latitude.size > 1 else None,
    }


def compare_rainfall_grids(
    forecast: GribMessageMetadata,
    observation: MeraObservation,
) -> GridCompatibility:
    """Compare grid metadata without regridding or changing either dataset."""
    forecast_grid = _grid_metadata(forecast)
    observation_grid = _observation_grid(observation)
    required_keys = tuple(forecast_grid)
    if any(forecast_grid[key] is None or observation_grid[key] is None for key in required_keys):
        return GridCompatibility(
            status="UNKNOWN",
            forecast=forecast_grid,
            observation=observation_grid,
            reason="Insufficient grid metadata for comparison",
        )

    matching = all(
        np.isclose(forecast_grid[key], observation_grid[key], rtol=0.0, atol=1e-9)
        if isinstance(forecast_grid[key], float)
        else forecast_grid[key] == observation_grid[key]
        for key in required_keys
    )
    return GridCompatibility(
        status="IDENTICAL" if matching else "DIFFERENT",
        forecast=forecast_grid,
        observation=observation_grid,
        reason="Grid metadata match" if matching else "Grid metadata differ",
    )


def validate_rainfall_alignment(
    forecast: GribMessageMetadata,
    observation: MeraObservation,
    observation_accumulation_start: Optional[datetime] = None,
    observation_accumulation_end: Optional[datetime] = None,
) -> RainfallAlignmentResult:
    """Validate explicit rainfall windows and grid metadata without verification."""
    initialization = _forecast_initialization_time(forecast)
    grid = compare_rainfall_grids(forecast, observation)
    common = {
        "forecast_initialization_time": initialization,
        "observation_accumulation_start": observation_accumulation_start,
        "observation_accumulation_end": observation_accumulation_end,
        "spatial_grid": grid,
    }

    if (
        forecast.short_name != "tp"
        or forecast.step_type != "accum"
        or initialization is None
        or forecast.start_step is None
        or forecast.end_step is None
        or forecast.start_step < 0
        or forecast.end_step < forecast.start_step
        or (observation_accumulation_start is None) != (observation_accumulation_end is None)
    ):
        return RainfallAlignmentResult(
            status=AlignmentStatus.INVALID_METADATA,
            forecast_accumulation_start=None,
            forecast_accumulation_end=None,
            reason="Required rainfall metadata is missing or invalid",
            **common,
        )

    forecast_start = initialization + timedelta(hours=forecast.start_step)
    forecast_end = initialization + timedelta(hours=forecast.end_step)
    common.update(
        forecast_accumulation_start=forecast_start,
        forecast_accumulation_end=forecast_end,
    )

    if observation_accumulation_start is None:
        return RainfallAlignmentResult(
            status=AlignmentStatus.BLOCKED_UNSPECIFIED_OBSERVATION_WINDOW,
            reason="Observation accumulation window is unspecified; timestamp was not interpreted",
            **common,
        )

    status = (
        AlignmentStatus.ALIGNED
        if (forecast_start, forecast_end)
        == (observation_accumulation_start, observation_accumulation_end)
        else AlignmentStatus.NOT_ALIGNED
    )
    return RainfallAlignmentResult(
        status=status,
        reason="Explicit physical accumulation windows match"
        if status is AlignmentStatus.ALIGNED
        else "Explicit physical accumulation windows differ",
        **common,
    )