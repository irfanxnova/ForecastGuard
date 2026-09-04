"""Reader for MERA hourly NetCDF rainfall observations."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np
import xarray as xr


@dataclass(frozen=True)
class MeraObservation:
    """One MERA NetCDF file with raw coordinates, time, data, and statistics."""

    source_file: str
    dimensions: Dict[str, int]
    latitude: np.ndarray
    longitude: np.ndarray
    time: np.ndarray
    rainfall: np.ndarray
    rainfall_units: Optional[str]
    statistics: Dict[str, Union[float, int]]
    global_attributes: Dict[str, Any]


@dataclass(frozen=True)
class MeraQCReport:
    """Basic integrity and numerical QC for a MERA observation collection."""

    status: str
    file_count: int
    rainfall_file_count: int
    total_values: int
    nan_count: int
    negative_count: int
    minimum: Optional[float]
    maximum: Optional[float]
    mean: Optional[float]
    issues: List[str]


@dataclass(frozen=True)
class MeraObservationCollection:
    """All hourly MERA files read from one directory."""

    observations: List[MeraObservation]
    qc: MeraQCReport


def _rainfall_statistics(values: np.ndarray) -> Dict[str, Union[float, int]]:
    """Report NaN-aware statistics without changing the source values."""
    finite_values = values[~np.isnan(values)]
    if finite_values.size == 0:
        minimum = maximum = mean = None
    else:
        minimum = float(np.min(finite_values))
        maximum = float(np.max(finite_values))
        mean = float(np.mean(finite_values))

    return {
        "number_of_values": int(values.size),
        "nan_count": int(np.isnan(values).sum()),
        "negative_count": int(np.sum(values < 0)),
        "min": minimum,
        "max": maximum,
        "mean": mean,
    }


def read_mera_file(file_path: Union[str, Path]) -> MeraObservation:
    """Read one MERA NetCDF file while preserving its raw data and metadata."""
    path = Path(file_path)
    with xr.open_dataset(path) as dataset:
        if "Rainfall" not in dataset.data_vars:
            raise ValueError(f"MERA file does not contain Rainfall: {path}")

        rainfall_variable = dataset["Rainfall"]
        missing_dimensions = {
            dimension for dimension in ("time", "latitude", "longitude")
            if dimension not in dataset
        }
        if missing_dimensions:
            missing = ", ".join(sorted(missing_dimensions))
            raise ValueError(f"MERA file is missing required coordinates: {missing}")

        rainfall = np.asarray(rainfall_variable.values)
        latitude = np.asarray(dataset["latitude"].values)
        longitude = np.asarray(dataset["longitude"].values)
        time = np.asarray(dataset["time"].values)
        statistics = _rainfall_statistics(rainfall)
        rainfall_units = rainfall_variable.attrs.get("units")
        global_attributes = dict(dataset.attrs)
        dimensions = {name: int(size) for name, size in dataset.sizes.items()}

    return MeraObservation(
        source_file=str(path),
        dimensions=dimensions,
        latitude=latitude,
        longitude=longitude,
        time=time,
        rainfall=rainfall,
        rainfall_units=rainfall_units,
        statistics=statistics,
        global_attributes=global_attributes,
    )


def read_mera_observations(
    directory: Union[str, Path],
) -> MeraObservationCollection:
    """Read all hourly MERA NetCDF files in a directory in filename order."""
    directory_path = Path(directory)
    paths = sorted(directory_path.glob("*.nc"))
    observations: List[MeraObservation] = []
    issues: List[str] = []

    for path in paths:
        try:
            observations.append(read_mera_file(path))
        except Exception as exc:
            issues.append(f"{path.name}: {exc}")

    rainfall_values = [observation.rainfall for observation in observations]
    if rainfall_values:
        all_values = np.concatenate([values.reshape(-1) for values in rainfall_values])
        aggregate = _rainfall_statistics(all_values)
    else:
        aggregate = {
            "number_of_values": 0,
            "nan_count": 0,
            "negative_count": 0,
            "min": None,
            "max": None,
            "mean": None,
        }

    if not paths:
        issues.append(f"No NetCDF files found in {directory_path}")
    if len(observations) != len(paths):
        issues.append("One or more MERA files could not be read")

    qc = MeraQCReport(
        status="PASS" if not issues else "FAIL",
        file_count=len(paths),
        rainfall_file_count=len(observations),
        total_values=aggregate["number_of_values"],
        nan_count=aggregate["nan_count"],
        negative_count=aggregate["negative_count"],
        minimum=aggregate["min"],
        maximum=aggregate["max"],
        mean=aggregate["mean"],
        issues=issues,
    )
    return MeraObservationCollection(observations=observations, qc=qc)