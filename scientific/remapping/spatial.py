"""Small experimental conservative remapping utility for regular lat/lon fields."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import eccodes
import numpy as np
import xarray as xr

from scientific.ingestion.grib import GribMessageMetadata, read_grib_file
from scientific.ingestion.mera import MeraObservation, read_mera_file


@dataclass(frozen=True)
class RemappingDiagnostics:
    """Reproducible diagnostics for one spatial-only remapping experiment."""

    source_grid_dimensions: Tuple[int, int]
    source_latitude_bounds: Tuple[float, float]
    source_longitude_bounds: Tuple[float, float]
    target_grid_dimensions: Tuple[int, int]
    target_latitude_bounds: Tuple[float, float]
    target_longitude_bounds: Tuple[float, float]
    remapping_method: str
    valid_source_cells: int
    source_cells: int
    valid_source_fraction: float
    valid_target_cells: int
    target_cells: int
    valid_target_fraction: float
    remapped_min: Optional[float]
    remapped_max: Optional[float]
    remapped_mean: Optional[float]
    nan_remains_after_remapping: bool
    negative_values_after_remapping: bool
    observation_units: Optional[str]
    observation_timestamp: str
    temporal_comparison_performed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _cell_edges(coordinates: np.ndarray) -> np.ndarray:
    """Derive bounds from adjacent centers without changing the field."""
    if coordinates.ndim != 1 or coordinates.size < 2:
        raise ValueError("A remapping grid requires at least two coordinate centers")
    differences = np.diff(coordinates)
    if not np.all(differences > 0) and not np.all(differences < 0):
        raise ValueError("Grid coordinates must be strictly monotonic")
    edges = np.empty(coordinates.size + 1, dtype=np.float64)
    edges[1:-1] = (coordinates[:-1] + coordinates[1:]) / 2.0
    edges[0] = coordinates[0] - (coordinates[1] - coordinates[0]) / 2.0
    edges[-1] = coordinates[-1] + (coordinates[-1] - coordinates[-2]) / 2.0
    return edges


def _overlap_measure(lower_a: float, upper_a: float, lower_b: float, upper_b: float) -> float:
    return max(0.0, min(upper_a, upper_b) - max(lower_a, lower_b))


def _overlap_weights(source_edges: np.ndarray, target_edges: np.ndarray) -> list[list[tuple[int, float]]]:
    """Precompute positive one-dimensional source/target cell overlaps."""
    weights: list[list[tuple[int, float]]] = []
    for target_index in range(target_edges.size - 1):
        target_low = min(target_edges[target_index], target_edges[target_index + 1])
        target_high = max(target_edges[target_index], target_edges[target_index + 1])
        target_weights: list[tuple[int, float]] = []
        for source_index in range(source_edges.size - 1):
            source_low = min(source_edges[source_index], source_edges[source_index + 1])
            source_high = max(source_edges[source_index], source_edges[source_index + 1])
            overlap = _overlap_measure(target_low, target_high, source_low, source_high)
            if overlap > 0.0:
                target_weights.append((source_index, overlap))
        weights.append(target_weights)
    return weights


def conservative_remap_regular_latlon(
    source_values: np.ndarray,
    source_latitude: np.ndarray,
    source_longitude: np.ndarray,
    target_latitude: np.ndarray,
    target_longitude: np.ndarray,
) -> np.ndarray:
    """Area-weight a regular lat/lon field onto another regular lat/lon grid.

    Cell overlaps use longitude width multiplied by the absolute difference in
    sine(latitude), which is proportional to spherical cell area. NaN source
    cells are excluded from both the numerator and denominator.
    """
    source_values = np.asarray(source_values)
    source_latitude = np.asarray(source_latitude, dtype=np.float64)
    source_longitude = np.asarray(source_longitude, dtype=np.float64)
    target_latitude = np.asarray(target_latitude, dtype=np.float64)
    target_longitude = np.asarray(target_longitude, dtype=np.float64)
    if source_values.shape != (source_latitude.size, source_longitude.size):
        raise ValueError("Source values shape does not match source coordinates")

    source_lat_edges = _cell_edges(source_latitude)
    source_lon_edges = _cell_edges(source_longitude)
    target_lat_edges = _cell_edges(target_latitude)
    target_lon_edges = _cell_edges(target_longitude)
    source_lat_edges_area = np.sin(np.deg2rad(source_lat_edges))
    target_lat_edges_area = np.sin(np.deg2rad(target_lat_edges))
    latitude_weights = _overlap_weights(source_lat_edges_area, target_lat_edges_area)
    longitude_weights = _overlap_weights(source_lon_edges, target_lon_edges)
    remapped = np.full((target_latitude.size, target_longitude.size), np.nan, dtype=np.float64)

    for target_lat_index, latitude_overlaps in enumerate(latitude_weights):
        for target_lon_index, longitude_overlaps in enumerate(longitude_weights):
            weighted_sum = 0.0
            valid_weight = 0.0
            for source_lat_index, lat_weight in latitude_overlaps:
                for source_lon_index, lon_weight in longitude_overlaps:
                    value = source_values[source_lat_index, source_lon_index]
                    weight = lat_weight * lon_weight
                    if np.isfinite(value):
                        weighted_sum += float(value) * weight
                        valid_weight += weight
            if valid_weight > 0.0:
                remapped[target_lat_index, target_lon_index] = weighted_sum / valid_weight
    return remapped


def _selected_tp_field(
    forecast_path: Union[str, Path],
) -> Tuple[GribMessageMetadata, np.ndarray]:
    """Read TP member 1 metadata through the existing reader and its raw values."""
    messages, qc = read_grib_file(forecast_path, compute_stats=True)
    if qc.status == "FAIL":
        raise ValueError(f"Forecast GRIB QC failed: {qc.issues}")
    selected = next(
        (
            message for message in messages
            if message.short_name == "tp" and message.member == 1
        ),
        None,
    )
    if selected is None:
        raise ValueError("Forecast GRIB does not contain total precipitation member 1")

    with open(forecast_path, "rb") as file_handle:
        for message_index in range(1, selected.message_index + 1):
            handle = eccodes.codes_grib_new_from_file(file_handle)
            if handle is None:
                raise ValueError("Selected forecast message could not be read")
            try:
                if message_index == selected.message_index:
                    values = np.asarray(eccodes.codes_get_values(handle), dtype=np.float64)
                    return selected, values.reshape((selected.nj, selected.ni))
            finally:
                eccodes.codes_release(handle)
    raise ValueError("Selected forecast message could not be read")


def run_spatial_remapping_experiment(
    forecast_path: Union[str, Path],
    observation_path: Union[str, Path],
    output_dir: Union[str, Path] = "data/interim",
) -> Tuple[Path, Path, RemappingDiagnostics]:
    """Remap the 00:00 MERA field to the native forecast grid only."""
    forecast_metadata, _forecast_values = _selected_tp_field(forecast_path)
    observation = read_mera_file(observation_path)
    if observation.rainfall.shape[0] != 1:
        raise ValueError("The selected MERA file must contain exactly one time slice")

    remapped = conservative_remap_regular_latlon(
        observation.rainfall[0],
        observation.latitude,
        observation.longitude,
        np.linspace(
            forecast_metadata.first_lat,
            forecast_metadata.last_lat,
            forecast_metadata.nj,
        ),
        np.linspace(
            forecast_metadata.first_lon,
            forecast_metadata.last_lon,
            forecast_metadata.ni,
        ),
    )
    target_latitude = np.linspace(forecast_metadata.first_lat, forecast_metadata.last_lat, forecast_metadata.nj)
    target_longitude = np.linspace(forecast_metadata.first_lon, forecast_metadata.last_lon, forecast_metadata.ni)
    valid_source = int(np.isfinite(observation.rainfall[0]).sum())
    valid_target = int(np.isfinite(remapped).sum())
    finite_remapped = remapped[np.isfinite(remapped)]
    diagnostics = RemappingDiagnostics(
        source_grid_dimensions=(observation.latitude.size, observation.longitude.size),
        source_latitude_bounds=(float(observation.latitude[0]), float(observation.latitude[-1])),
        source_longitude_bounds=(float(observation.longitude[0]), float(observation.longitude[-1])),
        target_grid_dimensions=(target_latitude.size, target_longitude.size),
        target_latitude_bounds=(float(target_latitude[0]), float(target_latitude[-1])),
        target_longitude_bounds=(float(target_longitude[0]), float(target_longitude[-1])),
        remapping_method="conservative area-weighted cell-overlap on regular latitude/longitude grids",
        valid_source_cells=valid_source,
        source_cells=int(observation.rainfall[0].size),
        valid_source_fraction=valid_source / observation.rainfall[0].size,
        valid_target_cells=valid_target,
        target_cells=int(remapped.size),
        valid_target_fraction=valid_target / remapped.size,
        remapped_min=float(np.min(finite_remapped)) if finite_remapped.size else None,
        remapped_max=float(np.max(finite_remapped)) if finite_remapped.size else None,
        remapped_mean=float(np.mean(finite_remapped)) if finite_remapped.size else None,
        nan_remains_after_remapping=bool(np.isnan(remapped).any()),
        negative_values_after_remapping=bool(np.any(remapped[np.isfinite(remapped)] < 0)),
        observation_units=observation.rainfall_units,
        observation_timestamp=str(observation.time[0]),
    )

    target_directory = Path(output_dir)
    target_directory.mkdir(parents=True, exist_ok=True)
    artifact_path = target_directory / "m1_4_experimental_mera_00_remapped_to_ncmrwf.nc"
    report_path = target_directory / "m1_4_experimental_mera_00_remapping_report.json"
    dataset = xr.Dataset(
        {
            "Rainfall_remapped_experimental": (("latitude", "longitude"), remapped),
        },
        coords={"latitude": target_latitude, "longitude": target_longitude},
        attrs={
            "artifact_status": "EXPERIMENTAL_ONLY",
            "remapping_method": diagnostics.remapping_method,
            "source_observation": str(observation_path),
            "target_grid": "native NCMRWF/TIGGE TP member 1 grid",
            "observation_timestamp": diagnostics.observation_timestamp,
            "observation_accumulation_window": "UNSPECIFIED",
            "temporal_comparison_performed": "false",
        },
    )
    dataset.to_netcdf(artifact_path)
    report_path.write_text(
        json.dumps(diagnostics.to_dict(), indent=2),
        encoding="utf-8",
    )
    return artifact_path, report_path, diagnostics