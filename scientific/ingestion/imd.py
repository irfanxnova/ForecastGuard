"""Reader for IMD daily binary rainfall observations."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Union

import numpy as np


IMD_LONGITUDE_COUNT = 241
IMD_LATITUDE_COUNT = 281
IMD_LONGITUDE_START = 50.0
IMD_LATITUDE_START = -30.0
IMD_GRID_SPACING = 0.25
IMD_UNDEFINED_VALUE = -999.0
IMD_EXPECTED_VALUE_COUNT = IMD_LONGITUDE_COUNT * IMD_LATITUDE_COUNT
IMD_EXPECTED_BYTE_LENGTH = IMD_EXPECTED_VALUE_COUNT * np.dtype("<f4").itemsize


IMD_DAILY_MERGED_SATELLITE_GAUGE_PRODUCT = "IMD_DAILY_MERGED_SATELLITE_GAUGE"
IMD_DAILY_MERGED_SATELLITE_GAUGE_END_HOUR_UTC = 3
IMD_DAILY_MERGED_SATELLITE_GAUGE_WINDOW_HOURS = 24
IMD_DAILY_MERGED_SATELLITE_GAUGE_WINDOW_BASIS = (
    "Documented IMD merged satellite-gauge daily rainfall convention: "
    "24-hour accumulation ending at 0830 IST (03:00 UTC)."
)


@dataclass(frozen=True)
class ImdDailyObservationWindow:
    """Explicit temporal convention for the IMD daily merged satellite-gauge product.

    This configuration applies only to the named IMD daily merged
    satellite-gauge rainfall product. It is not inferred from a ``.grd`` file
    and must not be generalized to other observation products.
    """

    product: str
    observation_date: date
    start: datetime
    end: datetime
    provenance: str

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-compatible temporal metadata for manifest provenance."""
        return {
            "product": self.product,
            "observation_date": self.observation_date.isoformat(),
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "window_hours": IMD_DAILY_MERGED_SATELLITE_GAUGE_WINDOW_HOURS,
            "basis": self.provenance,
        }


def imd_daily_merged_satellite_gauge_window(
    observation_date: Union[date, str],
) -> ImdDailyObservationWindow:
    """Return the explicit 03 UTC daily window for the configured IMD product.

    ``observation_date`` must be an ISO calendar date, not a timestamp. This
    prevents an arbitrary time component from being silently discarded.
    """
    if isinstance(observation_date, datetime):
        raise TypeError("observation_date must be a calendar date, not a datetime")
    if isinstance(observation_date, str):
        try:
            parsed_date = date.fromisoformat(observation_date)
        except ValueError as exc:
            raise ValueError(
                "observation_date must be an ISO date string (YYYY-MM-DD)"
            ) from exc
    elif isinstance(observation_date, date):
        parsed_date = observation_date
    else:
        raise TypeError("observation_date must be a date or an ISO date string")

    end = datetime.combine(
        parsed_date,
        time(hour=IMD_DAILY_MERGED_SATELLITE_GAUGE_END_HOUR_UTC),
        tzinfo=timezone.utc,
    )
    return ImdDailyObservationWindow(
        product=IMD_DAILY_MERGED_SATELLITE_GAUGE_PRODUCT,
        observation_date=parsed_date,
        start=end - timedelta(hours=IMD_DAILY_MERGED_SATELLITE_GAUGE_WINDOW_HOURS),
        end=end,
        provenance=IMD_DAILY_MERGED_SATELLITE_GAUGE_WINDOW_BASIS,
    )


@dataclass(frozen=True)
class ImdDailyObservation:
    """One IMD daily rainfall grid and its non-temporal provenance metadata."""

    rainfall: np.ndarray
    latitude: np.ndarray
    longitude: np.ndarray
    observation_date: date
    accumulation_window: Optional[str]
    source_file: str
    metadata: Dict[str, Any]


def _parse_observation_date(value: Union[date, datetime, str]) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(
                "observation_date must be a date or an ISO date string (YYYY-MM-DD)"
            ) from exc
    raise TypeError("observation_date must be a date, datetime, or ISO date string")


def _rainfall_statistics(rainfall: np.ndarray) -> Dict[str, Any]:
    valid_values = rainfall[~np.isnan(rainfall)]
    if valid_values.size == 0:
        minimum = maximum = mean = None
    else:
        minimum = float(np.min(valid_values))
        maximum = float(np.max(valid_values))
        mean = float(np.mean(valid_values))

    return {
        "shape": tuple(int(size) for size in rainfall.shape),
        "min": minimum,
        "max": maximum,
        "mean": mean,
        "missing_value_count": int(np.isnan(rainfall).sum()),
    }


def read_imd_daily_file(
    file_path: Union[str, Path],
    observation_date: Union[date, datetime, str],
) -> ImdDailyObservation:
    """Read one IMD daily ``.grd`` file using the official fixed grid definition.

    The accumulation window is intentionally left unspecified because it is not
    established by the binary file format or the supplied control-file metadata.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"IMD rainfall file not found: {path}")

    actual_byte_length = path.stat().st_size
    if actual_byte_length != IMD_EXPECTED_BYTE_LENGTH:
        raise ValueError(
            "Unsupported IMD rainfall file size: "
            f"expected {IMD_EXPECTED_BYTE_LENGTH} bytes for a "
            f"{IMD_LATITUDE_COUNT}x{IMD_LONGITUDE_COUNT} grid, "
            f"found {actual_byte_length} bytes"
        )

    raw_values = np.fromfile(path, dtype="<f4")
    if raw_values.size != IMD_EXPECTED_VALUE_COUNT:
        raise ValueError(
            "Unsupported IMD rainfall layout: "
            f"expected {IMD_EXPECTED_VALUE_COUNT} float32 values, found {raw_values.size}"
        )

    rainfall = raw_values.reshape(IMD_LATITUDE_COUNT, IMD_LONGITUDE_COUNT)
    rainfall[rainfall == IMD_UNDEFINED_VALUE] = np.nan
    latitude = IMD_LATITUDE_START + IMD_GRID_SPACING * np.arange(IMD_LATITUDE_COUNT)
    longitude = IMD_LONGITUDE_START + IMD_GRID_SPACING * np.arange(IMD_LONGITUDE_COUNT)
    parsed_date = _parse_observation_date(observation_date)
    statistics = _rainfall_statistics(rainfall)

    metadata = {
        **statistics,
        "source_filename": path.name,
        "observation_date": parsed_date,
        "grid_spacing": {"latitude": IMD_GRID_SPACING, "longitude": IMD_GRID_SPACING},
        "accumulation_window_status": "UNKNOWN/UNSPECIFIED",
        "undefined_value": IMD_UNDEFINED_VALUE,
    }
    return ImdDailyObservation(
        rainfall=rainfall,
        latitude=latitude,
        longitude=longitude,
        observation_date=parsed_date,
        accumulation_window=None,
        source_file=str(path),
        metadata=metadata,
    )
