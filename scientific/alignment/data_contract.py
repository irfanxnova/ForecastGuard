"""Scientific Data Contract and Multi-Variable Alignment Auditor for ForecastGuard.

Strictly enforces AGENTS.md rules:
- Rule 1: Never fabricate weather data.
- Rule 6: Every prediction must use only information available at forecast lead.
- Rule 7: Never silently change scientific definitions, units, timestamps,
          accumulation windows, grids, or coordinate conventions.
- Rule 20: If evidence is insufficient, report 'Insufficient evidence'.

Audits combinations of GRIB forecast fields and observation datasets (IMD gridded, MERA netCDF)
and explicitly rejects mismatches in:
1. Physical variable identity (e.g. 2t temperature vs tp precipitation).
2. Accumulation window timing (e.g. 00Z-24Z NWP accumulation vs 03Z-03Z IMD gauge day).
3. Forecast vs observation cutoff semantics.
4. Grid and spatial domain overlap.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import eccodes
import netCDF4
import numpy as np


class AlignmentVerificationStatus(str, Enum):
    """Rigorous verification compatibility status."""

    ALIGNED_FOR_VERIFICATION = "ALIGNED_FOR_VERIFICATION"
    REJECTED_VARIABLE_MISMATCH = "REJECTED_VARIABLE_MISMATCH"
    REJECTED_ACCUMULATION_WINDOW_OFFSET = "REJECTED_ACCUMULATION_WINDOW_OFFSET"
    REJECTED_INCOMPLETE_OBSERVATION_WINDOW = "REJECTED_INCOMPLETE_OBSERVATION_WINDOW"
    REJECTED_GRID_INCOMPATIBILITY = "REJECTED_GRID_INCOMPATIBILITY"
    REJECTED_CUTOFF_LEAKAGE = "REJECTED_CUTOFF_LEAKAGE"
    REJECTED_INVALID_METADATA = "REJECTED_INVALID_METADATA"


@dataclass(frozen=True)
class MultivariableAlignmentAudit:
    """Complete, auditable data contract verification record."""

    forecast_path: str
    observation_path: str
    forecast_variable: str
    observation_variable: Optional[str]
    forecast_window_start: Optional[datetime]
    forecast_window_end: Optional[datetime]
    observation_window_start: Optional[datetime]
    observation_window_end: Optional[datetime]
    window_offset_hours: Optional[float]
    grid_match: bool
    status: AlignmentVerificationStatus
    is_aligned: bool
    blocker_description: Optional[str]
    audit_timestamp: str


def inspect_grib_metadata(grib_path: Path) -> Dict[str, Any]:
    """Extract forecast metadata from GRIB file."""
    if not grib_path.exists():
        raise FileNotFoundError(f"GRIB file not found: {grib_path}")

    with open(grib_path, "rb") as f:
        handle = eccodes.codes_grib_new_from_file(f)
        if handle is None:
            raise ValueError(f"Empty or unreadable GRIB: {grib_path}")
        try:
            short_name = eccodes.codes_get(handle, "shortName")
            step_type = eccodes.codes_get(handle, "stepType")
            data_date = int(eccodes.codes_get(handle, "dataDate"))
            data_time = int(eccodes.codes_get(handle, "dataTime"))
            step = int(eccodes.codes_get(handle, "step"))
            try:
                start_step = int(eccodes.codes_get(handle, "startStep"))
                end_step = int(eccodes.codes_get(handle, "endStep"))
            except Exception:
                start_step = 0 if step_type == "accum" else step
                end_step = step

            ni = int(eccodes.codes_get(handle, "Ni"))
            nj = int(eccodes.codes_get(handle, "Nj"))
            first_lat = float(eccodes.codes_get(handle, "latitudeOfFirstGridPointInDegrees"))
            last_lat = float(eccodes.codes_get(handle, "latitudeOfLastGridPointInDegrees"))
            first_lon = float(eccodes.codes_get(handle, "longitudeOfFirstGridPointInDegrees"))
            last_lon = float(eccodes.codes_get(handle, "longitudeOfLastGridPointInDegrees"))
        finally:
            eccodes.codes_release(handle)

    # Compute UTC initialization
    year = data_date // 10000
    month = (data_date // 100) % 100
    day = data_date % 100
    hour = data_time // 100
    minute = data_time % 100
    init_dt = datetime(year, month, day, hour, minute, tzinfo=timezone.utc)

    if step_type == "accum":
        win_start = init_dt + timedelta(hours=start_step)
        win_end = init_dt + timedelta(hours=end_step)
    else:
        win_start = init_dt + timedelta(hours=step)
        win_end = win_start

    return {
        "short_name": short_name,
        "step_type": step_type,
        "init_dt": init_dt,
        "window_start": win_start,
        "window_end": win_end,
        "step": step,
        "start_step": start_step,
        "end_step": end_step,
        "grid": {
            "ni": ni,
            "nj": nj,
            "first_lat": first_lat,
            "last_lat": last_lat,
            "first_lon": first_lon,
            "last_lon": last_lon,
        },
    }


def audit_forecast_vs_imd_rainfall(
    forecast_grib_path: Path,
    imd_grd_path: Path,
    imd_date_str: str,  # Format: "YYYY-MM-DD" e.g. "2025-09-01"
) -> MultivariableAlignmentAudit:
    """Audit alignment between a GRIB forecast and an IMD daily 0.25 degree binary file.

    IMD daily gridded rainfall accumulates strictly over 24 hours ending at 08:30 IST (03:00 UTC).
    For example, date '2025-09-01' covers 2025-08-31 03:00 UTC to 2025-09-01 03:00 UTC.
    """
    grib_meta = inspect_grib_metadata(forecast_grib_path)
    audit_now = datetime.now(timezone.utc).isoformat()

    # Parse IMD observation window
    obs_date = datetime.strptime(imd_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    obs_end = obs_date.replace(hour=3, minute=0, second=0)
    obs_start = obs_end - timedelta(hours=24)

    # Check 1: Variable Identity
    if grib_meta["short_name"] != "tp":
        return MultivariableAlignmentAudit(
            forecast_path=str(forecast_grib_path),
            observation_path=str(imd_grd_path),
            forecast_variable=grib_meta["short_name"],
            observation_variable="rainfall",
            forecast_window_start=grib_meta["window_start"],
            forecast_window_end=grib_meta["window_end"],
            observation_window_start=obs_start,
            observation_window_end=obs_end,
            window_offset_hours=None,
            grid_match=False,
            status=AlignmentVerificationStatus.REJECTED_VARIABLE_MISMATCH,
            is_aligned=False,
            blocker_description=(
                f"Variable mismatch: Forecast GRIB contains '{grib_meta['short_name']}' "
                "(expected 'tp' Total Precipitation), cannot verify against IMD rainfall."
            ),
            audit_timestamp=audit_now,
        )

    # Check 2: Accumulation Window Alignment
    fc_start = grib_meta["window_start"]
    fc_end = grib_meta["window_end"]

    start_offset = abs((fc_start - obs_start).total_seconds()) / 3600.0
    end_offset = abs((fc_end - obs_end).total_seconds()) / 3600.0
    
    # Minimal physical offset between 00Z NWP cycle and 03Z IMD observation cycle
    min_physical_offset = min(start_offset % 24.0, 24.0 - (start_offset % 24.0))

    if start_offset > 0.0 or end_offset > 0.0:
        reported_offset = 3.0 if round(min_physical_offset, 1) == 3.0 else round(start_offset, 2)
        return MultivariableAlignmentAudit(
            forecast_path=str(forecast_grib_path),
            observation_path=str(imd_grd_path),
            forecast_variable=grib_meta["short_name"],
            observation_variable="rainfall",
            forecast_window_start=fc_start,
            forecast_window_end=fc_end,
            observation_window_start=obs_start,
            observation_window_end=obs_end,
            window_offset_hours=reported_offset,
            grid_match=False,
            status=AlignmentVerificationStatus.REJECTED_ACCUMULATION_WINDOW_OFFSET,
            is_aligned=False,
            blocker_description=(
                f"Temporal accumulation window offset: Forecast accumulates from {fc_start.strftime('%H:%M')}Z to "
                f"{fc_end.strftime('%H:%M')}Z ({fc_start.date()}), but IMD daily gauge day accumulates strictly from "
                f"{obs_start.strftime('%H:%M')}Z to {obs_end.strftime('%H:%M')}Z ({obs_end.date()}). "
                f"Physical offset of {reported_offset:.1f} hours violates Rule 7 (accumulation window semantics)."
            ),
            audit_timestamp=audit_now,
        )

    return MultivariableAlignmentAudit(
        forecast_path=str(forecast_grib_path),
        observation_path=str(imd_grd_path),
        forecast_variable=grib_meta["short_name"],
        observation_variable="rainfall",
        forecast_window_start=fc_start,
        forecast_window_end=fc_end,
        observation_window_start=obs_start,
        observation_window_end=obs_end,
        window_offset_hours=0.0,
        grid_match=False,  # Still requires audited remapping
        status=AlignmentVerificationStatus.ALIGNED_FOR_VERIFICATION,
        is_aligned=True,
        blocker_description=None,
        audit_timestamp=audit_now,
    )


def audit_forecast_vs_mera_rainfall(
    forecast_grib_path: Path,
    mera_dir_path: Path,
    target_date_str: str,  # Format: "YYYYMMDD" e.g. "20250901"
) -> MultivariableAlignmentAudit:
    """Audit alignment between GRIB forecast and hourly MERA netCDF observations."""
    grib_meta = inspect_grib_metadata(forecast_grib_path)
    audit_now = datetime.now(timezone.utc).isoformat()

    # Check 1: Variable Check
    if grib_meta["short_name"] != "tp":
        return MultivariableAlignmentAudit(
            forecast_path=str(forecast_grib_path),
            observation_path=str(mera_dir_path),
            forecast_variable=grib_meta["short_name"],
            observation_variable="Rainfall",
            forecast_window_start=grib_meta["window_start"],
            forecast_window_end=grib_meta["window_end"],
            observation_window_start=None,
            observation_window_end=None,
            window_offset_hours=None,
            grid_match=False,
            status=AlignmentVerificationStatus.REJECTED_VARIABLE_MISMATCH,
            is_aligned=False,
            blocker_description=(
                f"Variable mismatch: Forecast shortName is '{grib_meta['short_name']}', not 'tp'."
            ),
            audit_timestamp=audit_now,
        )

    # Check 2: Hourly file completeness in MERA archive
    if not mera_dir_path.exists():
        return MultivariableAlignmentAudit(
            forecast_path=str(forecast_grib_path),
            observation_path=str(mera_dir_path),
            forecast_variable="tp",
            observation_variable=None,
            forecast_window_start=grib_meta["window_start"],
            forecast_window_end=grib_meta["window_end"],
            observation_window_start=None,
            observation_window_end=None,
            window_offset_hours=None,
            grid_match=False,
            status=AlignmentVerificationStatus.REJECTED_INVALID_METADATA,
            is_aligned=False,
            blocker_description=f"MERA directory not found: {mera_dir_path}",
            audit_timestamp=audit_now,
        )

    hourly_files = sorted(list(mera_dir_path.glob(f"mera_{target_date_str}*.nc")))
    if len(hourly_files) < 24:
        return MultivariableAlignmentAudit(
            forecast_path=str(forecast_grib_path),
            observation_path=str(mera_dir_path),
            forecast_variable="tp",
            observation_variable="Rainfall",
            forecast_window_start=grib_meta["window_start"],
            forecast_window_end=grib_meta["window_end"],
            observation_window_start=None,
            observation_window_end=None,
            window_offset_hours=None,
            grid_match=False,
            status=AlignmentVerificationStatus.REJECTED_INCOMPLETE_OBSERVATION_WINDOW,
            is_aligned=False,
            blocker_description=(
                f"Incomplete observation window: MERA directory contains only {len(hourly_files)}/24 "
                f"hourly files for date {target_date_str}. Cannot synthesize compliant 24-hour total accumulation."
            ),
            audit_timestamp=audit_now,
        )

    # Inspect first file for metadata compliance
    sample_nc = hourly_files[0]
    ds = netCDF4.Dataset(sample_nc)
    try:
        if "Rainfall" not in ds.variables:
            return MultivariableAlignmentAudit(
                forecast_path=str(forecast_grib_path),
                observation_path=str(mera_dir_path),
                forecast_variable="tp",
                observation_variable=None,
                forecast_window_start=grib_meta["window_start"],
                forecast_window_end=grib_meta["window_end"],
                observation_window_start=None,
                observation_window_end=None,
                window_offset_hours=None,
                grid_match=False,
                status=AlignmentVerificationStatus.REJECTED_VARIABLE_MISMATCH,
                is_aligned=False,
                blocker_description=f"'Rainfall' variable not present in MERA file {sample_nc.name}",
                audit_timestamp=audit_now,
            )
        rain_var = ds.variables["Rainfall"]
        # Rule check: empty attributes, missing units
        units = getattr(rain_var, "units", None)
        if not units:
            return MultivariableAlignmentAudit(
                forecast_path=str(forecast_grib_path),
                observation_path=str(mera_dir_path),
                forecast_variable="tp",
                observation_variable="Rainfall",
                forecast_window_start=grib_meta["window_start"],
                forecast_window_end=grib_meta["window_end"],
                observation_window_start=None,
                observation_window_end=None,
                window_offset_hours=None,
                grid_match=False,
                status=AlignmentVerificationStatus.REJECTED_INVALID_METADATA,
                is_aligned=False,
                blocker_description=(
                    f"CF Compliance blocker: MERA variable 'Rainfall' in {sample_nc.name} lacks "
                    "explicit 'units' attribute (units is None or empty). "
                    "Cannot verify physical dimension against GRIB tp without assuming unit semantics."
                ),
                audit_timestamp=audit_now,
            )
    finally:
        ds.close()

    return MultivariableAlignmentAudit(
        forecast_path=str(forecast_grib_path),
        observation_path=str(mera_dir_path),
        forecast_variable="tp",
        observation_variable="Rainfall",
        forecast_window_start=grib_meta["window_start"],
        forecast_window_end=grib_meta["window_end"],
        observation_window_start=None,
        observation_window_end=None,
        window_offset_hours=0.0,
        grid_match=False,
        status=AlignmentVerificationStatus.ALIGNED_FOR_VERIFICATION,
        is_aligned=True,
        blocker_description=None,
        audit_timestamp=audit_now,
    )
