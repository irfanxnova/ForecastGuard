"""GRIB2 reader and ingestion processor for ForecastGuard.

Reads real NWP forecast files (e.g. NCMRWF/TIGGE) using ecCodes, extracts structured
metadata and numerical statistics without modifying units, grids, or values, performs
non-destructive quality control, and produces deterministic machine-readable manifests.

Strictly follows AGENTS.md, ARCHITECTURE.md, and SCIENCE_SPEC.md:
- No fabrication of data.
- No silent unit conversions, clipping, or regridding.
- No scientific assumptions not backed by GRIB metadata.
"""

from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import eccodes
import numpy as np


@dataclass(frozen=True)
class GribMessageMetadata:
    """Structured metadata and statistics extracted from a single GRIB message."""

    message_index: int
    edition: int
    short_name: str
    name: Optional[str] = None
    units: Optional[str] = None
    data_date: int = 0
    data_time: int = 0
    step: int = 0
    step_type: Optional[str] = None
    start_step: Optional[int] = None
    end_step: Optional[int] = None
    forecast_type: Optional[str] = None
    member: Optional[int] = None
    grid_type: str = "unknown"
    ni: Optional[int] = None
    nj: Optional[int] = None
    first_lat: Optional[float] = None
    first_lon: Optional[float] = None
    last_lat: Optional[float] = None
    last_lon: Optional[float] = None
    i_increment: Optional[float] = None
    j_increment: Optional[float] = None
    number_of_values: int = 0
    min_value: float = 0.0
    max_value: float = 0.0
    mean_value: float = 0.0
    nan_count: int = 0
    negative_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary representation."""
        return asdict(self)


@dataclass
class GribQCReport:
    """Quality control integrity report for an ingested GRIB file."""

    can_open: bool
    total_messages_parsed: int
    supported_edition: bool
    data_values_readable: bool
    metadata_complete: bool
    unexpected_nan_count: int
    total_negative_values: int
    negative_counts_by_variable: Dict[str, int] = field(default_factory=dict)
    tp_negative_count: int = 0
    status: str = "PASS"  # "PASS", "WARN", "FAIL"
    issues: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert QC report to dictionary representation."""
        return asdict(self)


def _safe_codes_get(handle: Any, key: str, default: Any = None) -> Any:
    """Safely get a key from an ecCodes handle without raising exceptions."""
    try:
        if eccodes.codes_is_defined(handle, key):
            return eccodes.codes_get(handle, key)
    except Exception:
        pass
    return default


def parse_grib_message(handle: Any, index: int, compute_stats: bool = True) -> GribMessageMetadata:
    """Extract structured metadata and numerical statistics from a single ecCodes GRIB handle.

    Parameters
    ----------
    handle : Any
        An open ecCodes GRIB message handle.
    index : int
        1-based index of the message within the file.
    compute_stats : bool, optional
        Whether to retrieve values and compute min/max/mean/NaN/negative counts.

    Returns
    -------
    GribMessageMetadata
        Extracted metadata and summary statistics.
    """
    edition = int(_safe_codes_get(handle, "editionNumber", 0))
    short_name = str(_safe_codes_get(handle, "shortName", "unknown"))
    name = _safe_codes_get(handle, "name")
    units = _safe_codes_get(handle, "units")
    data_date = int(_safe_codes_get(handle, "dataDate", 0))
    data_time = int(_safe_codes_get(handle, "dataTime", 0))
    step = int(_safe_codes_get(handle, "step", 0))
    step_type = _safe_codes_get(handle, "stepType")
    start_step = _safe_codes_get(handle, "startStep")
    if start_step is not None:
        start_step = int(start_step)
    end_step = _safe_codes_get(handle, "endStep")
    if end_step is not None:
        end_step = int(end_step)

    forecast_type = _safe_codes_get(handle, "type")
    member = _safe_codes_get(handle, "number")
    if member is None:
        member = _safe_codes_get(handle, "perturbationNumber")
    if member is not None:
        member = int(member)

    grid_type = str(_safe_codes_get(handle, "gridType", "unknown"))
    ni = _safe_codes_get(handle, "Ni")
    if ni is not None:
        ni = int(ni)
    nj = _safe_codes_get(handle, "Nj")
    if nj is not None:
        nj = int(nj)

    first_lat = _safe_codes_get(handle, "latitudeOfFirstGridPointInDegrees")
    if first_lat is not None:
        first_lat = float(first_lat)
    first_lon = _safe_codes_get(handle, "longitudeOfFirstGridPointInDegrees")
    if first_lon is not None:
        first_lon = float(first_lon)
    last_lat = _safe_codes_get(handle, "latitudeOfLastGridPointInDegrees")
    if last_lat is not None:
        last_lat = float(last_lat)
    last_lon = _safe_codes_get(handle, "longitudeOfLastGridPointInDegrees")
    if last_lon is not None:
        last_lon = float(last_lon)

    i_increment = _safe_codes_get(handle, "iDirectionIncrementInDegrees")
    if i_increment is not None:
        i_increment = float(i_increment)
    j_increment = _safe_codes_get(handle, "jDirectionIncrementInDegrees")
    if j_increment is not None:
        j_increment = float(j_increment)

    number_of_values = 0
    min_value = 0.0
    max_value = 0.0
    mean_value = 0.0
    nan_count = 0
    negative_count = 0

    if compute_stats:
        raw_values = eccodes.codes_get_values(handle)
        values = np.asarray(raw_values, dtype=np.float64)
        number_of_values = int(values.size)
        nan_count = int(np.isnan(values).sum())
        negative_count = int(np.sum(values < 0))

        if number_of_values > 0 and nan_count < number_of_values:
            min_value = float(np.nanmin(values))
            max_value = float(np.nanmax(values))
            mean_value = float(np.nanmean(values))

    return GribMessageMetadata(
        message_index=index,
        edition=edition,
        short_name=short_name,
        name=name,
        units=units,
        data_date=data_date,
        data_time=data_time,
        step=step,
        step_type=step_type,
        start_step=start_step,
        end_step=end_step,
        forecast_type=forecast_type,
        member=member,
        grid_type=grid_type,
        ni=ni,
        nj=nj,
        first_lat=first_lat,
        first_lon=first_lon,
        last_lat=last_lat,
        last_lon=last_lon,
        i_increment=i_increment,
        j_increment=j_increment,
        number_of_values=number_of_values,
        min_value=min_value,
        max_value=max_value,
        mean_value=mean_value,
        nan_count=nan_count,
        negative_count=negative_count,
    )


def perform_qc(
    messages: List[GribMessageMetadata],
    can_open: bool,
    open_error: Optional[str] = None,
) -> GribQCReport:
    """Evaluate non-destructive quality control integrity on parsed messages."""
    issues: List[str] = []
    if open_error:
        issues.append(f"File open error: {open_error}")

    if not can_open or not messages:
        return GribQCReport(
            can_open=can_open,
            total_messages_parsed=0,
            supported_edition=False,
            data_values_readable=False,
            metadata_complete=False,
            unexpected_nan_count=0,
            total_negative_values=0,
            negative_counts_by_variable={},
            tp_negative_count=0,
            status="FAIL",
            issues=issues or ["No messages could be parsed from GRIB file"],
        )

    supported_edition = all(msg.edition in (1, 2) for msg in messages)
    if not supported_edition:
        issues.append("Found unsupported GRIB edition(s)")

    data_values_readable = all(msg.number_of_values > 0 for msg in messages)
    if not data_values_readable:
        issues.append("Some messages had zero data values readable")

    metadata_complete = all(
        msg.short_name != "unknown" and msg.grid_type != "unknown" and msg.data_date > 0
        for msg in messages
    )
    if not metadata_complete:
        issues.append("Some messages have missing or incomplete core identification metadata")

    total_nan_count = sum(msg.nan_count for msg in messages)
    if total_nan_count > 0:
        issues.append(f"Encountered {total_nan_count} unexpected NaN values")

    total_negative_values = sum(msg.negative_count for msg in messages)
    neg_by_var: Dict[str, int] = {}
    for msg in messages:
        neg_by_var[msg.short_name] = neg_by_var.get(msg.short_name, 0) + msg.negative_count

    tp_negative_count = neg_by_var.get("tp", 0)
    if tp_negative_count > 0:
        issues.append(f"Encountered {tp_negative_count} negative values in total precipitation (tp)")

    status = "PASS"
    if open_error or not can_open or not supported_edition or not data_values_readable:
        status = "FAIL"
    elif total_nan_count > 0 or tp_negative_count > 0 or not metadata_complete:
        status = "WARN"

    return GribQCReport(
        can_open=can_open,
        total_messages_parsed=len(messages),
        supported_edition=supported_edition,
        data_values_readable=data_values_readable,
        metadata_complete=metadata_complete,
        unexpected_nan_count=total_nan_count,
        total_negative_values=total_negative_values,
        negative_counts_by_variable=neg_by_var,
        tp_negative_count=tp_negative_count,
        status=status,
        issues=issues,
    )


def read_grib_file(
    file_path: Union[str, Path],
    compute_stats: bool = True,
) -> Tuple[List[GribMessageMetadata], GribQCReport]:
    """Read a GRIB2 file using ecCodes and parse all messages with QC.

    Parameters
    ----------
    file_path : Union[str, Path]
        Path to the GRIB file.
    compute_stats : bool, optional
        Whether to compute per-message statistics on values.

    Returns
    -------
    Tuple[List[GribMessageMetadata], GribQCReport]
        List of parsed message metadata and the overall QC report.
    """
    path = Path(file_path)
    if not path.exists():
        qc = perform_qc([], can_open=False, open_error=f"File not found: {path}")
        return [], qc

    messages: List[GribMessageMetadata] = []
    can_open = False
    open_error: Optional[str] = None

    try:
        with open(path, "rb") as f:
            can_open = True
            msg_index = 0
            while True:
                handle = eccodes.codes_grib_new_from_file(f)
                if handle is None:
                    break
                msg_index += 1
                try:
                    meta = parse_grib_message(handle, index=msg_index, compute_stats=compute_stats)
                    messages.append(meta)
                finally:
                    eccodes.codes_release(handle)
    except Exception as exc:
        open_error = str(exc)

    qc = perform_qc(messages, can_open=can_open, open_error=open_error)
    return messages, qc


parse_grib_file = read_grib_file


def group_messages(messages: List[GribMessageMetadata]) -> Dict[str, Any]:
    """Group GRIB messages by initialization time, variable, type, step, and member."""
    grouped: Dict[str, Any] = {}

    for msg in messages:
        init_time = f"{msg.data_date} {msg.data_time:04d} UTC"
        var = msg.short_name
        ftype = msg.forecast_type or "unknown"
        step = msg.step
        member = msg.member if msg.member is not None else -1

        if init_time not in grouped:
            grouped[init_time] = {"variables": {}}

        variables = grouped[init_time]["variables"]
        if var not in variables:
            variables[var] = {
                "name": msg.name,
                "units": msg.units,
                "step_type": msg.step_type,
                "forecast_types": {},
            }

        if ftype not in variables[var]["forecast_types"]:
            variables[var]["forecast_types"][ftype] = {}

        step_key = f"step_{step}"
        if step_key not in variables[var]["forecast_types"][ftype]:
            variables[var]["forecast_types"][ftype][step_key] = {
                "start_step": msg.start_step,
                "end_step": msg.end_step,
                "members": {},
            }

        variables[var]["forecast_types"][ftype][step_key]["members"][member] = {
            "message_index": msg.message_index,
            "min": msg.min_value,
            "max": msg.max_value,
            "mean": msg.mean_value,
            "nan_count": msg.nan_count,
            "negative_count": msg.negative_count,
        }

    return grouped


def generate_manifest(
    file_path: Union[str, Path],
    output_dir: Optional[Union[str, Path]] = None,
) -> Path:
    """Ingest a GRIB file, parse all messages, run QC, and generate a deterministic JSON manifest.

    Parameters
    ----------
    file_path : Union[str, Path]
        Path to the GRIB input file.
    output_dir : Optional[Union[str, Path]], optional
        Directory where manifest should be written. Defaults to 'data/manifests'.

    Returns
    -------
    Path
        Path to the generated JSON manifest file.
    """
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Cannot generate manifest: file not found at {path}")

    # Compute deterministic SHA256 of input file
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    file_hash = sha256.hexdigest()
    file_size = path.stat().st_size

    # Ingest and QC
    messages, qc = read_grib_file(path, compute_stats=True)

    # Unique dimensions
    unique_vars = sorted(list({m.short_name for m in messages}))
    unique_types = sorted(list({m.forecast_type for m in messages if m.forecast_type}))
    unique_members = sorted(list({m.member for m in messages if m.member is not None}))
    unique_init_times = sorted(list({f"{m.data_date} {m.data_time:04d} UTC" for m in messages}))
    unique_steps = sorted(list({m.step for m in messages}))

    # Extract distinct grid descriptions
    grids: List[Dict[str, Any]] = []
    seen_grids = set()
    for m in messages:
        grid_sig = (
            m.grid_type,
            m.ni,
            m.nj,
            m.first_lat,
            m.first_lon,
            m.last_lat,
            m.last_lon,
            m.i_increment,
            m.j_increment,
        )
        if grid_sig not in seen_grids:
            seen_grids.add(grid_sig)
            grids.append({
                "grid_type": m.grid_type,
                "ni": m.ni,
                "nj": m.nj,
                "latitude_first": m.first_lat,
                "longitude_first": m.first_lon,
                "latitude_last": m.last_lat,
                "longitude_last": m.last_lon,
                "i_direction_increment": m.i_increment,
                "j_direction_increment": m.j_increment,
                "number_of_points": m.number_of_values,
            })

    grouped = group_messages(messages)

    # Output directory
    if output_dir is None:
        target_dir = path.parent.parent.parent / "manifests"
        if not target_dir.exists():
            target_dir = Path("data/manifests").resolve()
    else:
        target_dir = Path(output_dir).resolve()

    target_dir.mkdir(parents=True, exist_ok=True)
    manifest_filename = f"{path.stem}_manifest.json"
    manifest_path = target_dir / manifest_filename

    manifest_data: Dict[str, Any] = {
        "source_file_name": path.name,
        "source_file_size_bytes": file_size,
        "source_file_sha256": file_hash,
        "total_message_count": len(messages),
        "unique_variables": unique_vars,
        "forecast_types": unique_types,
        "ensemble_members": unique_members,
        "initialization_times": unique_init_times,
        "forecast_steps": unique_steps,
        "grid_descriptions": grids,
        "grouped_structure": grouped,
        "qc_summary": qc.to_dict(),
        "messages": [m.to_dict() for m in messages],
        "runtime_metadata": {
            "parser_version": "0.1.0",
            "eccodes_version": getattr(eccodes, "__version__", "unknown"),
        },
    }

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    return manifest_path
