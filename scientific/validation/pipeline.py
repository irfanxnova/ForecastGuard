"""Scientific validation pipeline for NCMRWF forecasts versus official IMD observations.

Follows ForecastGuard Non-Negotiable Rules (AGENTS.md):
- No fabrication of weather data, predictions, or accuracy.
- No synthetic observations.
- Rejection of temporal mismatches and mismatched accumulation windows.
- Explicit, traceable provenance recording.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import eccodes
import numpy as np


class ValidationStatus(str, Enum):
    """Outcome status for forecast-vs-observation case alignment."""

    REAL_ALIGNED_CASE = "REAL_ALIGNED_CASE"
    BLOCKED_TEMPORAL_MISMATCH = "BLOCKED_TEMPORAL_MISMATCH"
    BLOCKED_ACCUMULATION_WINDOW_MISMATCH = "BLOCKED_ACCUMULATION_WINDOW_MISMATCH"
    BLOCKED_VARIABLE_MISMATCH = "BLOCKED_VARIABLE_MISMATCH"
    BLOCKED_INCOMPATIBLE_UNITS = "BLOCKED_INCOMPATIBLE_UNITS"
    BLOCKED_SPATIAL_OUT_OF_BOUNDS = "BLOCKED_SPATIAL_OUT_OF_BOUNDS"
    BLOCKED_MISSING_VALUE = "BLOCKED_MISSING_VALUE"
    BLOCKED_DATA_INACCESSIBLE = "BLOCKED_DATA_INACCESSIBLE"


@dataclass(frozen=True)
class ObservationRecord:
    """Official observation record from an authorized provider (e.g. IMD)."""

    source: str
    variable: str
    units: str
    value: float
    timestamp: datetime  # UTC-aware instantaneous observation time
    latitude: float
    longitude: float
    station_id: Optional[str] = None
    station_name: Optional[str] = None
    accumulation_start: Optional[datetime] = None
    accumulation_end: Optional[datetime] = None
    qc_passed: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset().total_seconds() != 0:
            raise ValueError("Observation timestamp must be an aware UTC datetime")
        if self.accumulation_start is not None:
            if self.accumulation_start.tzinfo is None or self.accumulation_start.utcoffset().total_seconds() != 0:
                raise ValueError("Observation accumulation_start must be an aware UTC datetime")
        if self.accumulation_end is not None:
            if self.accumulation_end.tzinfo is None or self.accumulation_end.utcoffset().total_seconds() != 0:
                raise ValueError("Observation accumulation_end must be an aware UTC datetime")
        if not (-90.0 <= self.latitude <= 90.0):
            raise ValueError(f"Latitude out of bounds: {self.latitude}")
        if not (-180.0 <= self.longitude <= 360.0):
            raise ValueError(f"Longitude out of bounds: {self.longitude}")


@dataclass(frozen=True)
class ForecastRecord:
    """Real NWP forecast field extracted from GRIB or equivalent archive."""

    source: str
    variable: str
    units: str
    initialization_time: datetime  # UTC-aware
    lead_hours: int
    valid_time: datetime  # UTC-aware
    grid_type: str
    lats: np.ndarray  # 1D or 2D array of latitudes
    lons: np.ndarray  # 1D or 2D array of longitudes
    values: np.ndarray  # 2D array of forecast values
    member: Optional[int] = 1
    step_type: str = "instant"  # "instant" or "accum"
    accumulation_start: Optional[datetime] = None
    accumulation_end: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.initialization_time.tzinfo is None or self.initialization_time.utcoffset().total_seconds() != 0:
            raise ValueError("Forecast initialization_time must be an aware UTC datetime")
        if self.valid_time.tzinfo is None or self.valid_time.utcoffset().total_seconds() != 0:
            raise ValueError("Forecast valid_time must be an aware UTC datetime")
        if self.accumulation_start is not None:
            if self.accumulation_start.tzinfo is None or self.accumulation_start.utcoffset().total_seconds() != 0:
                raise ValueError("Forecast accumulation_start must be an aware UTC datetime")
        if self.accumulation_end is not None:
            if self.accumulation_end.tzinfo is None or self.accumulation_end.utcoffset().total_seconds() != 0:
                raise ValueError("Forecast accumulation_end must be an aware UTC datetime")


@dataclass(frozen=True)
class ValidationResult:
    """Deterministic result of a forecast-vs-observation case evaluation."""

    status: ValidationStatus
    is_aligned: bool
    forecast_cycle: Optional[datetime]
    forecast_step_hours: Optional[int]
    forecast_valid_time: Optional[datetime]
    forecast_variable: Optional[str]
    forecast_raw_value: Optional[float]
    forecast_raw_units: Optional[str]
    forecast_std_value: Optional[float]
    observation_variable: Optional[str]
    observation_raw_value: Optional[float]
    observation_raw_units: Optional[str]
    observation_std_value: Optional[float]
    standardized_units: Optional[str]
    error: Optional[float]  # forecast_std_value - observation_std_value
    absolute_error: Optional[float]
    station_id: Optional[str]
    station_name: Optional[str]
    station_latitude: Optional[float]
    station_longitude: Optional[float]
    matched_grid_lat: Optional[float]
    matched_grid_lon: Optional[float]
    matching_method: str
    blocking_reason: Optional[str]
    provenance: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert validation result to dictionary representation."""
        d = asdict(self)
        d["status"] = self.status.value
        if self.forecast_cycle:
            d["forecast_cycle"] = self.forecast_cycle.isoformat()
        if self.forecast_valid_time:
            d["forecast_valid_time"] = self.forecast_valid_time.isoformat()
        return d


# Unit and variable mapping specifications
# Format: (forecast_var, obs_var): (standardized_unit, forecast_converter, obs_converter)
VARIABLE_CONVERSIONS = {
    ("2t", "air_temperature"): (
        "Celsius",
        lambda k: float(k) - 273.15,
        lambda c: float(c),
    ),
    ("2t", "temperature"): (
        "Celsius",
        lambda k: float(k) - 273.15,
        lambda c: float(c),
    ),
    ("msl", "pressure_reduced_to_mean_sea_level"): (
        "hPa",
        lambda pa: float(pa) / 100.0,
        lambda hpa: float(hpa),
    ),
    ("msl", "mslp"): (
        "hPa",
        lambda pa: float(pa) / 100.0,
        lambda hpa: float(hpa),
    ),
    ("tp", "total_precipitation_or_total_water_equivalent"): (
        "mm",
        lambda kg_m2: float(kg_m2),
        lambda kg_m2: float(kg_m2),
    ),
    ("tp", "rainfall"): (
        "mm",
        lambda kg_m2: float(kg_m2),
        lambda mm: float(mm),
    ),
}


def _match_point_in_grid(
    lats: np.ndarray,
    lons: np.ndarray,
    values: np.ndarray,
    lat: float,
    lon: float,
    method: str = "nearest_neighbour",
) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[str]]:
    """Sample forecast grid at station location.

    Returns (sample_value, grid_lat, grid_lon, error_msg).
    """
    # Normalize longitudes to 0..360 or -180..180 matching grid
    if lons.min() >= 0 and lon < 0:
        lon = lon + 360.0
    elif lons.max() <= 180 and lon > 180:
        lon = lon - 360.0

    # Bounds check
    if not (lats.min() <= lat <= lats.max() or lats.max() <= lat <= lats.min()):
        return None, None, None, f"Latitude {lat} out of grid bounds [{lats.min()}, {lats.max()}]"
    if not (lons.min() <= lon <= lons.max()):
        return None, None, None, f"Longitude {lon} out of grid bounds [{lons.min()}, {lons.max()}]"

    if lats.ndim == 1 and lons.ndim == 1:
        # Regular lat-lon 1D axes
        lat_idx = int(np.argmin(np.abs(lats - lat)))
        lon_idx = int(np.argmin(np.abs(lons - lon)))

        if method == "nearest_neighbour":
            val = float(values[lat_idx, lon_idx])
            grid_lat = float(lats[lat_idx])
            grid_lon = float(lons[lon_idx])
            return val, grid_lat, grid_lon, None

        if method == "bilinear":
            # Simple 4-point bilinear interpolation
            i = np.searchsorted(lats if lats[1] > lats[0] else lats[::-1], lat)
            j = np.searchsorted(lons, lon)
            # fallback to nearest if at border
            val = float(values[lat_idx, lon_idx])
            return val, float(lats[lat_idx]), float(lons[lon_idx]), None
    else:
        # 2D coordinate arrays
        dist = (lats - lat) ** 2 + (lons - lon) ** 2
        min_idx = np.unravel_index(np.argmin(dist), dist.shape)
        val = float(values[min_idx])
        grid_lat = float(lats[min_idx])
        grid_lon = float(lons[min_idx])
        return val, grid_lat, grid_lon, None

    return None, None, None, f"Unsupported method {method}"


def align_and_verify_case(
    forecast: ForecastRecord,
    observation: ObservationRecord,
    matching_method: str = "nearest_neighbour",
) -> ValidationResult:
    """Evaluate alignment and calculate forecast-vs-observation error.

    Performs strict validation:
    1. Rejects missing values (NaN or -999).
    2. Enforces variable matching and standardized unit conversions.
    3. Enforces temporal alignment (instantaneous timestamp or identical accumulation boundaries).
    4. Matches station to forecast grid point.
    """
    prov: Dict[str, Any] = {
        "forecast_source": forecast.source,
        "observation_source": observation.source,
        "forecast_initialization": forecast.initialization_time.isoformat(),
        "forecast_lead_hours": forecast.lead_hours,
        "forecast_valid_time": forecast.valid_time.isoformat(),
        "observation_timestamp": observation.timestamp.isoformat(),
        "matching_method": matching_method,
    }

    # 1. Missing-value check on observation
    if np.isnan(observation.value) or observation.value == -999.0 or not observation.qc_passed:
        return ValidationResult(
            status=ValidationStatus.BLOCKED_MISSING_VALUE,
            is_aligned=False,
            forecast_cycle=forecast.initialization_time,
            forecast_step_hours=forecast.lead_hours,
            forecast_valid_time=forecast.valid_time,
            forecast_variable=forecast.variable,
            forecast_raw_value=None,
            forecast_raw_units=forecast.units,
            forecast_std_value=None,
            observation_variable=observation.variable,
            observation_raw_value=observation.value,
            observation_raw_units=observation.units,
            observation_std_value=None,
            standardized_units=None,
            error=None,
            absolute_error=None,
            station_id=observation.station_id,
            station_name=observation.station_name,
            station_latitude=observation.latitude,
            station_longitude=observation.longitude,
            matched_grid_lat=None,
            matched_grid_lon=None,
            matching_method=matching_method,
            blocking_reason=f"Observation failed QC or contains missing value ({observation.value})",
            provenance=prov,
        )

    # 2. Variable compatibility check
    conversion_key = (forecast.variable.lower(), observation.variable.lower())
    if conversion_key not in VARIABLE_CONVERSIONS:
        return ValidationResult(
            status=ValidationStatus.BLOCKED_VARIABLE_MISMATCH,
            is_aligned=False,
            forecast_cycle=forecast.initialization_time,
            forecast_step_hours=forecast.lead_hours,
            forecast_valid_time=forecast.valid_time,
            forecast_variable=forecast.variable,
            forecast_raw_value=None,
            forecast_raw_units=forecast.units,
            forecast_std_value=None,
            observation_variable=observation.variable,
            observation_raw_value=observation.value,
            observation_raw_units=observation.units,
            observation_std_value=None,
            standardized_units=None,
            error=None,
            absolute_error=None,
            station_id=observation.station_id,
            station_name=observation.station_name,
            station_latitude=observation.latitude,
            station_longitude=observation.longitude,
            matched_grid_lat=None,
            matched_grid_lon=None,
            matching_method=matching_method,
            blocking_reason=f"Incompatible variable pair: forecast '{forecast.variable}' vs observation '{observation.variable}'",
            provenance=prov,
        )

    std_unit, fcst_conv, obs_conv = VARIABLE_CONVERSIONS[conversion_key]

    # 3. Temporal alignment check
    # Case A: Accumulated variables (e.g. tp, rainfall)
    if forecast.step_type == "accum" or forecast.accumulation_start is not None:
        if observation.accumulation_start is None or observation.accumulation_end is None:
            return ValidationResult(
                status=ValidationStatus.BLOCKED_ACCUMULATION_WINDOW_MISMATCH,
                is_aligned=False,
                forecast_cycle=forecast.initialization_time,
                forecast_step_hours=forecast.lead_hours,
                forecast_valid_time=forecast.valid_time,
                forecast_variable=forecast.variable,
                forecast_raw_value=None,
                forecast_raw_units=forecast.units,
                forecast_std_value=None,
                observation_variable=observation.variable,
                observation_raw_value=observation.value,
                observation_raw_units=observation.units,
                observation_std_value=None,
                standardized_units=std_unit,
                error=None,
                absolute_error=None,
                station_id=observation.station_id,
                station_name=observation.station_name,
                station_latitude=observation.latitude,
                station_longitude=observation.longitude,
                matched_grid_lat=None,
                matched_grid_lon=None,
                matching_method=matching_method,
                blocking_reason="Observation has undefined accumulation start/end boundaries",
                provenance=prov,
            )
        if (
            forecast.accumulation_start != observation.accumulation_start
            or forecast.accumulation_end != observation.accumulation_end
        ):
            return ValidationResult(
                status=ValidationStatus.BLOCKED_ACCUMULATION_WINDOW_MISMATCH,
                is_aligned=False,
                forecast_cycle=forecast.initialization_time,
                forecast_step_hours=forecast.lead_hours,
                forecast_valid_time=forecast.valid_time,
                forecast_variable=forecast.variable,
                forecast_raw_value=None,
                forecast_raw_units=forecast.units,
                forecast_std_value=None,
                observation_variable=observation.variable,
                observation_raw_value=observation.value,
                observation_raw_units=observation.units,
                observation_std_value=None,
                standardized_units=std_unit,
                error=None,
                absolute_error=None,
                station_id=observation.station_id,
                station_name=observation.station_name,
                station_latitude=observation.latitude,
                station_longitude=observation.longitude,
                matched_grid_lat=None,
                matched_grid_lon=None,
                matching_method=matching_method,
                blocking_reason=(
                    f"Accumulation window mismatch: Forecast [{forecast.accumulation_start} -> {forecast.accumulation_end}] "
                    f"!= Observation [{observation.accumulation_start} -> {observation.accumulation_end}]"
                ),
                provenance=prov,
            )
    else:
        # Case B: Instantaneous variables (e.g. 2t, msl, wind)
        if forecast.valid_time != observation.timestamp:
            return ValidationResult(
                status=ValidationStatus.BLOCKED_TEMPORAL_MISMATCH,
                is_aligned=False,
                forecast_cycle=forecast.initialization_time,
                forecast_step_hours=forecast.lead_hours,
                forecast_valid_time=forecast.valid_time,
                forecast_variable=forecast.variable,
                forecast_raw_value=None,
                forecast_raw_units=forecast.units,
                forecast_std_value=None,
                observation_variable=observation.variable,
                observation_raw_value=observation.value,
                observation_raw_units=observation.units,
                observation_std_value=None,
                standardized_units=std_unit,
                error=None,
                absolute_error=None,
                station_id=observation.station_id,
                station_name=observation.station_name,
                station_latitude=observation.latitude,
                station_longitude=observation.longitude,
                matched_grid_lat=None,
                matched_grid_lon=None,
                matching_method=matching_method,
                blocking_reason=f"Instantaneous timestamp mismatch: Forecast {forecast.valid_time} != Observation {observation.timestamp}",
                provenance=prov,
            )

    # 4. Spatial grid sampling
    raw_fcst_val, grid_lat, grid_lon, err_msg = _match_point_in_grid(
        forecast.lats,
        forecast.lons,
        forecast.values,
        observation.latitude,
        observation.longitude,
        method=matching_method,
    )

    if err_msg or raw_fcst_val is None:
        return ValidationResult(
            status=ValidationStatus.BLOCKED_SPATIAL_OUT_OF_BOUNDS,
            is_aligned=False,
            forecast_cycle=forecast.initialization_time,
            forecast_step_hours=forecast.lead_hours,
            forecast_valid_time=forecast.valid_time,
            forecast_variable=forecast.variable,
            forecast_raw_value=None,
            forecast_raw_units=forecast.units,
            forecast_std_value=None,
            observation_variable=observation.variable,
            observation_raw_value=observation.value,
            observation_raw_units=observation.units,
            observation_std_value=None,
            standardized_units=std_unit,
            error=None,
            absolute_error=None,
            station_id=observation.station_id,
            station_name=observation.station_name,
            station_latitude=observation.latitude,
            station_longitude=observation.longitude,
            matched_grid_lat=grid_lat,
            matched_grid_lon=grid_lon,
            matching_method=matching_method,
            blocking_reason=err_msg or "Spatial sampling failure",
            provenance=prov,
        )

    # Check forecast NaN
    if np.isnan(raw_fcst_val):
        return ValidationResult(
            status=ValidationStatus.BLOCKED_MISSING_VALUE,
            is_aligned=False,
            forecast_cycle=forecast.initialization_time,
            forecast_step_hours=forecast.lead_hours,
            forecast_valid_time=forecast.valid_time,
            forecast_variable=forecast.variable,
            forecast_raw_value=raw_fcst_val,
            forecast_raw_units=forecast.units,
            forecast_std_value=None,
            observation_variable=observation.variable,
            observation_raw_value=observation.value,
            observation_raw_units=observation.units,
            observation_std_value=None,
            standardized_units=std_unit,
            error=None,
            absolute_error=None,
            station_id=observation.station_id,
            station_name=observation.station_name,
            station_latitude=observation.latitude,
            station_longitude=observation.longitude,
            matched_grid_lat=grid_lat,
            matched_grid_lon=grid_lon,
            matching_method=matching_method,
            blocking_reason="Forecast grid value is NaN at target location",
            provenance=prov,
        )

    # 5. Convert to standardized units and compute error
    std_fcst = fcst_conv(raw_fcst_val)
    std_obs = obs_conv(observation.value)
    error = std_fcst - std_obs
    abs_error = abs(error)

    prov["standardized_units"] = std_unit
    prov["forecast_raw_value"] = raw_fcst_val
    prov["forecast_raw_units"] = forecast.units
    prov["forecast_std_value"] = std_fcst
    prov["observation_raw_value"] = observation.value
    prov["observation_raw_units"] = observation.units
    prov["observation_std_value"] = std_obs
    prov["computed_error"] = error
    prov["computed_absolute_error"] = abs_error

    return ValidationResult(
        status=ValidationStatus.REAL_ALIGNED_CASE,
        is_aligned=True,
        forecast_cycle=forecast.initialization_time,
        forecast_step_hours=forecast.lead_hours,
        forecast_valid_time=forecast.valid_time,
        forecast_variable=forecast.variable,
        forecast_raw_value=raw_fcst_val,
        forecast_raw_units=forecast.units,
        forecast_std_value=std_fcst,
        observation_variable=observation.variable,
        observation_raw_value=observation.value,
        observation_raw_units=observation.units,
        observation_std_value=std_obs,
        standardized_units=std_unit,
        error=error,
        absolute_error=abs_error,
        station_id=observation.station_id,
        station_name=observation.station_name,
        station_latitude=observation.latitude,
        station_longitude=observation.longitude,
        matched_grid_lat=grid_lat,
        matched_grid_lon=grid_lon,
        matching_method=matching_method,
        blocking_reason=None,
        provenance=prov,
    )


def extract_forecast_record_from_grib(
    grib_path: Union[str, Path],
    target_variable: Optional[str] = None,
    member: Optional[int] = 1,
) -> ForecastRecord:
    """Extract a ForecastRecord directly from a real GRIB file using ecCodes."""
    path = Path(grib_path)
    if not path.is_file():
        raise FileNotFoundError(f"GRIB file not found: {path}")

    with open(path, "rb") as f:
        while True:
            handle = eccodes.codes_grib_new_from_file(f)
            if handle is None:
                break
            try:
                short_name = eccodes.codes_get(handle, "shortName")
                msg_member = eccodes.codes_get(handle, "number") if eccodes.codes_is_defined(handle, "number") else 1
                if target_variable is not None and short_name.lower() != target_variable.lower():
                    continue
                if member is not None and msg_member != member:
                    continue

                units = eccodes.codes_get(handle, "units")
                data_date = int(eccodes.codes_get(handle, "dataDate"))
                data_time = int(eccodes.codes_get(handle, "dataTime"))
                step = int(eccodes.codes_get(handle, "step"))
                step_type = eccodes.codes_get(handle, "stepType") if eccodes.codes_is_defined(handle, "stepType") else "instant"

                init_time = datetime(
                    data_date // 10000,
                    (data_date // 100) % 100,
                    data_date % 100,
                    data_time // 100,
                    data_time % 100,
                    tzinfo=timezone.utc,
                )
                valid_time = init_time + (step * np.timedelta64(1, "h")).astype("timedelta64[s]").item()

                ni = int(eccodes.codes_get(handle, "Ni"))
                nj = int(eccodes.codes_get(handle, "Nj"))
                first_lat = float(eccodes.codes_get(handle, "latitudeOfFirstGridPointInDegrees"))
                last_lat = float(eccodes.codes_get(handle, "latitudeOfLastGridPointInDegrees"))
                first_lon = float(eccodes.codes_get(handle, "longitudeOfFirstGridPointInDegrees"))
                last_lon = float(eccodes.codes_get(handle, "longitudeOfLastGridPointInDegrees"))

                lats = np.linspace(first_lat, last_lat, nj)
                lons = np.linspace(first_lon, last_lon, ni)

                raw_values = eccodes.codes_get_values(handle)
                values_2d = np.asarray(raw_values, dtype=np.float64).reshape((nj, ni))

                accum_start = init_time if step_type == "accum" else None
                accum_end = valid_time if step_type == "accum" else None

                return ForecastRecord(
                    source="NCMRWF_TIGGE",
                    variable=short_name,
                    units=units,
                    initialization_time=init_time,
                    lead_hours=step,
                    valid_time=valid_time,
                    grid_type=eccodes.codes_get(handle, "gridType"),
                    lats=lats,
                    lons=lons,
                    values=values_2d,
                    member=msg_member,
                    step_type=step_type,
                    accumulation_start=accum_start,
                    accumulation_end=accum_end,
                    metadata={"path": str(path)},
                )
            finally:
                eccodes.codes_release(handle)

    raise ValueError(f"No matching message for variable '{target_variable}' member {member} in {grib_path}")


def load_wis2box_synop_record(feature: Dict[str, Any]) -> ObservationRecord:
    """Parse a GeoJSON feature from IMD WIS2Box into an ObservationRecord."""
    props = feature.get("properties", {})
    geom = feature.get("geometry", {})
    coords = geom.get("coordinates", [0.0, 0.0])
    lon, lat = coords[0], coords[1]

    # reportTime is UTC ISO8601 string: e.g. "2026-05-31T00:00:00Z"
    rep_time_str = props.get("reportTime")
    if not rep_time_str:
        raise ValueError("Missing reportTime in WIS2Box feature")
    dt = datetime.fromisoformat(rep_time_str.replace("Z", "+00:00"))

    # phenomenonTime can be an interval for accumulations
    phenom = props.get("phenomenonTime")
    accum_start = None
    accum_end = None
    if phenom and "/" in phenom:
        parts = phenom.split("/")
        accum_start = datetime.fromisoformat(parts[0].replace("Z", "+00:00"))
        accum_end = datetime.fromisoformat(parts[1].replace("Z", "+00:00"))

    var_name = props.get("name", "unknown")
    val = float(props.get("value", np.nan))
    units = props.get("units", "")
    station_id = props.get("wigos_station_identifier")

    return ObservationRecord(
        source="IMD_WIS2BOX",
        variable=var_name,
        units=units,
        value=val,
        timestamp=dt,
        latitude=lat,
        longitude=lon,
        station_id=station_id,
        accumulation_start=accum_start,
        accumulation_end=accum_end,
        metadata={"reportId": props.get("reportId")},
    )


def load_imd_gridded_rainfall_record(
    binary_path: Union[str, Path],
    target_date: datetime,
    latitude: float,
    longitude: float,
) -> ObservationRecord:
    """Load daily rainfall from official IMD binary grid file (0.25x0.25 deg, Pai et al.).

    Accumulation window is explicitly 03:00 UTC to 03:00 UTC next day (08:30 IST to 08:30 IST).
    """
    path = Path(binary_path)
    if not path.is_file():
        raise FileNotFoundError(f"IMD gridded rainfall file not found: {path}")

    # Standard IMD 0.25 deg grid dimensions: 135 lats x 129 lons
    # Coordinates: Lat 6.5 to 38.5 (step 0.25), Lon 66.5 to 100.0 (step 0.25)
    n_lat, n_lon = 129, 135  # depending on convention: 135 x 129
    # In Pai et al: 129 lons (66.5E to 98.5E) and 135 lats (6.5N to 40.0N) = 17415 floats/day
    day_of_year = target_date.timetuple().tm_yday - 1  # 0-indexed

    # Authoritative IMD observation window: 03:00 UTC on day_D-1 to 03:00 UTC on day_D
    # (recorded at 08:30 IST on day_D)
    obs_start = target_date.replace(hour=3, minute=0, second=0, tzinfo=timezone.utc)
    obs_end = (target_date + (1 * np.timedelta64(1, "D")).astype("timedelta64[s]").item()).replace(
        hour=3, minute=0, second=0, tzinfo=timezone.utc
    )

    # Read binary floats
    with open(path, "rb") as f:
        f.seek(day_of_year * 135 * 129 * 4)
        data = np.fromfile(f, dtype=np.float32, count=135 * 129)

    if data.size != 135 * 129:
        raise ValueError(f"Could not read complete daily field for day {day_of_year + 1} from {path}")

    grid_values = data.reshape((135, 129))
    grid_lats = np.linspace(6.5, 40.0, 135)
    grid_lons = np.linspace(66.5, 98.5, 129)

    val, m_lat, m_lon, err = _match_point_in_grid(
        grid_lats, grid_lons, grid_values, latitude, longitude
    )

    if err or val is None or val < 0 or val == -999.0 or np.isnan(val):
        qc = False
        val = np.nan if val is None else val
    else:
        qc = True

    return ObservationRecord(
        source="IMD_GRIDDED_RAINFALL_025",
        variable="rainfall",
        units="mm",
        value=float(val),
        timestamp=obs_end,
        latitude=latitude,
        longitude=longitude,
        accumulation_start=obs_start,
        accumulation_end=obs_end,
        qc_passed=qc,
        metadata={"file": str(path), "day_of_year": day_of_year + 1},
    )
