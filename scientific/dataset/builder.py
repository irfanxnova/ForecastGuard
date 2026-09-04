"""Core dataset record builder."""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np

from scientific.cases.rainfall_case import RainfallCase, RainfallCaseResult
from scientific.features.ensemble_rainfall import extract_ensemble_rainfall_features
from scientific.ingestion.grib import read_grib_file
from scientific.verification.rainfall import RainfallVerificationStatus


class DatasetRecordStatus(str, Enum):
    """Outcome status of dataset record generation."""

    VALID = "VALID"
    """Case was ALIGNED and all data present. Contains targets."""

    BLOCKED_UNSPECIFIED_OBSERVATION_WINDOW = "BLOCKED_UNSPECIFIED_OBSERVATION_WINDOW"
    """Case blocked by alignment validator. No targets. Explicit window required."""

    BLOCKED_TEMPORAL_MISMATCH = "BLOCKED_TEMPORAL_MISMATCH"
    """Forecast and observation windows do not match. No targets."""

    BLOCKED_INVALID_METADATA = "BLOCKED_INVALID_METADATA"
    """Forecast or observation metadata incomplete. No targets."""

    BLOCKED_EMPTY_VALID_SET = "BLOCKED_EMPTY_VALID_SET"
    """No cells with finite forecast and observation values. No targets."""

    BLOCKED_FEATURE_EXTRACTION_ERROR = "BLOCKED_FEATURE_EXTRACTION_ERROR"
    """Ensemble feature extraction failed. No targets."""

    BLOCKED_FORECAST_READ_ERROR = "BLOCKED_FORECAST_READ_ERROR"
    """Could not read forecast file. No targets."""

    BLOCKED_OBSERVATION_READ_ERROR = "BLOCKED_OBSERVATION_READ_ERROR"
    """Could not read observation file. No targets."""


@dataclass(frozen=True)
class DatasetRecord:
    """One auditable dataset record from a verified historical case.

    Valid records (status == VALID) contain features and targets.
    Blocked records contain provenance and status reason but no targets.

    Designed for auditability: each record traces from raw case to features
    to verification to targets.
    """

    case_id: str
    """Unique identifier for the historical case."""

    status: DatasetRecordStatus
    """Outcome status. VALID → targets present. BLOCKED_* → no targets."""

    # -------------------------------------------------------------------------
    # Provenance
    # -------------------------------------------------------------------------

    forecast_initialization_time: Optional[datetime] = None
    """Datetime of forecast initialization (UTC)."""

    forecast_lead_hours: Optional[int] = None
    """Forecast lead time (hours). Typically 24."""

    forecast_source_model: Optional[str] = None
    """Forecast model identifier (e.g., 'NCMRWF', 'TIGGE')."""

    observation_source: Optional[str] = None
    """Observation dataset identifier (e.g., 'IMD_DAILY')."""

    observation_date: Optional[datetime] = None
    """Date of observation (typically date of accumulation end)."""

    forecast_accumulation_start: Optional[datetime] = None
    """Forecast window start (typically init_time + 0h)."""

    forecast_accumulation_end: Optional[datetime] = None
    """Forecast window end (typically init_time + 24h)."""

    observation_accumulation_start: Optional[datetime] = None
    """Observation window start (explicit, must match forecast)."""

    observation_accumulation_end: Optional[datetime] = None
    """Observation window end (explicit, must match forecast)."""

    ensemble_member_count: Optional[int] = None
    """Number of ensemble members."""

    grid_shape: Optional[tuple] = None
    """Grid dimensions (n_latitude, n_longitude)."""

    # -------------------------------------------------------------------------
    # Targets (only for VALID records)
    # -------------------------------------------------------------------------

    mae: Optional[float] = None
    """Mean absolute error (mm). None if status != VALID."""

    rmse: Optional[float] = None
    """Root mean squared error (mm). None if status != VALID."""

    bias: Optional[float] = None
    """Mean error: forecast_mean - observation_mean (mm). None if status != VALID."""

    forecast_mean: Optional[float] = None
    """Spatial mean of forecast field (mm). None if status != VALID."""

    observation_mean: Optional[float] = None
    """Spatial mean of observation field (mm). None if status != VALID."""

    valid_cell_count: Optional[int] = None
    """Number of cells with finite forecast and observation."""

    missing_cell_count: Optional[int] = None
    """Number of cells missing or NaN in either field."""

    # -------------------------------------------------------------------------
    # Features (only for VALID records)
    # -------------------------------------------------------------------------

    feature_names: List[str] = field(default_factory=list)
    """Names of the 24 ensemble rainfall features."""

    ensemble_mean: Optional[np.ndarray] = None
    ensemble_median: Optional[np.ndarray] = None
    ensemble_min: Optional[np.ndarray] = None
    ensemble_max: Optional[np.ndarray] = None
    ensemble_std: Optional[np.ndarray] = None
    ensemble_range: Optional[np.ndarray] = None
    ensemble_iqr: Optional[np.ndarray] = None
    ensemble_p10: Optional[np.ndarray] = None
    ensemble_p25: Optional[np.ndarray] = None
    ensemble_p75: Optional[np.ndarray] = None
    ensemble_p90: Optional[np.ndarray] = None
    coefficient_of_variation: Optional[np.ndarray] = None
    ensemble_skewness: Optional[np.ndarray] = None
    probability_rain_gt_1mm: Optional[np.ndarray] = None
    probability_rain_gt_10mm: Optional[np.ndarray] = None
    probability_rain_gt_25mm: Optional[np.ndarray] = None
    probability_rain_gt_50mm: Optional[np.ndarray] = None
    probability_rain_gt_100mm: Optional[np.ndarray] = None
    gradient_magnitude: Optional[np.ndarray] = None
    latitude_gradient: Optional[np.ndarray] = None
    longitude_gradient: Optional[np.ndarray] = None
    mean_pairwise_member_difference: Optional[np.ndarray] = None
    maximum_ensemble_gap: Optional[np.ndarray] = None
    member_agreement_fraction: Optional[np.ndarray] = None
    """24 ensemble rainfall feature arrays (only for VALID records). Shape: grid_shape."""

    # -------------------------------------------------------------------------
    # Status/Reason (for blocked cases)
    # -------------------------------------------------------------------------

    reason: str = ""
    """If status != VALID, the reason why targets are not produced."""

    provenance: Dict[str, Any] = field(default_factory=dict)
    """Complete provenance dict from case run and verification."""

    extraction_timestamp: datetime = field(default_factory=lambda: datetime.utcnow())
    """Timestamp of dataset record generation (UTC)."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a JSON-serializable dictionary.

        Feature arrays are converted to lists for JSON compatibility.
        NaN values are preserved as null in JSON.
        """
        result = asdict(self)

        # Convert numpy arrays to lists (preserves NaN as NaN in JSON)
        for key in self.feature_names:
            if key in result and isinstance(result[key], np.ndarray):
                arr = result[key]
                # Convert to list, preserving NaN
                result[key] = arr.tolist()

        # Convert datetime objects to ISO format strings
        for key in [
            "forecast_initialization_time",
            "observation_date",
            "forecast_accumulation_start",
            "forecast_accumulation_end",
            "observation_accumulation_start",
            "observation_accumulation_end",
            "extraction_timestamp",
        ]:
            if result[key] is not None and isinstance(result[key], datetime):
                result[key] = result[key].isoformat()

        # Convert enums to strings
        if isinstance(result["status"], DatasetRecordStatus):
            result["status"] = result["status"].value

        return result

    def has_targets(self) -> bool:
        """Return True if this record has computed targets (status == VALID)."""
        return self.status == DatasetRecordStatus.VALID


def build_dataset_record(
    case: RainfallCase,
    case_result: RainfallCaseResult,
) -> DatasetRecord:
    """Build a dataset record from a verified case result.

    This is the main entry point for converting case results to ML-ready records.

    Parameters
    ----------
    case : RainfallCase
        Original case specification.
    case_result : RainfallCaseResult
        Verified result from run_rainfall_case().

    Returns
    -------
    DatasetRecord
        Auditable dataset record. Valid records have targets; blocked records
        have status/reason but no targets.

    Notes
    -----
    - Only ALIGNED cases produce targets
    - Blocked cases are tracked with status/reason
    - No future observation information used
    - NaNs preserved (no imputation)
    - No bust labels or severity thresholds invented
    """
    # Map case status to dataset record status
    status_map = {
        "ALIGNED": DatasetRecordStatus.VALID,
        "BLOCKED_UNSPECIFIED_OBSERVATION_WINDOW": DatasetRecordStatus.BLOCKED_UNSPECIFIED_OBSERVATION_WINDOW,
        "NOT_ALIGNED": DatasetRecordStatus.BLOCKED_TEMPORAL_MISMATCH,
        "INVALID_METADATA": DatasetRecordStatus.BLOCKED_INVALID_METADATA,
        "EMPTY_VALID_SET": DatasetRecordStatus.BLOCKED_EMPTY_VALID_SET,
        "FORECAST_READ_ERROR": DatasetRecordStatus.BLOCKED_FORECAST_READ_ERROR,
        "OBSERVATION_READ_ERROR": DatasetRecordStatus.BLOCKED_OBSERVATION_READ_ERROR,
        "NO_TP_MESSAGE": DatasetRecordStatus.BLOCKED_FORECAST_READ_ERROR,
    }
    status = status_map.get(case_result.status.value, DatasetRecordStatus.BLOCKED_INVALID_METADATA)

    # Extract common provenance
    forecast_metadata = case_result.forecast_metadata or {}
    observation_metadata = case_result.observation_metadata or {}
    error_stats = case_result.error_statistics or {}

    # Determine forecast source model from metadata
    forecast_source = None
    if "centre_description" in forecast_metadata:
        centre_desc = forecast_metadata["centre_description"]
        if "NCMRWF" in centre_desc or centre_desc == "New Delhi":
            forecast_source = "NCMRWF"
        elif "ECMWF" in centre_desc or "European" in centre_desc:
            forecast_source = "TIGGE"

    # Parse initialization time if available
    init_time = None
    if "data_date" in forecast_metadata and "data_time" in forecast_metadata:
        from datetime import datetime, timezone
        try:
            data_date = forecast_metadata["data_date"]
            data_time = forecast_metadata["data_time"]
            year = data_date // 10000
            month = (data_date // 100) % 100
            day = data_date % 100
            hour = data_time // 100
            minute = data_time % 100
            init_time = datetime(year, month, day, hour, minute, tzinfo=timezone.utc)
        except (ValueError, TypeError):
            init_time = None

    # Parse forecast/observation windows
    forecast_window = case_result.forecast_window or {}
    observation_window = case_result.observation_window or {}

    from datetime import datetime, timezone

    def parse_iso(s: str) -> Optional[datetime]:
        if s is None:
            return None
        try:
            return datetime.fromisoformat(s)
        except (ValueError, TypeError):
            return None

    forecast_start = parse_iso(forecast_window.get("start"))
    forecast_end = parse_iso(forecast_window.get("end"))
    observation_start = parse_iso(observation_window.get("start"))
    observation_end = parse_iso(observation_window.get("end"))

    # For ALIGNED cases only: extract features and build targets
    features_dict = {}
    feature_names = []
    if status == DatasetRecordStatus.VALID:
        # Extract ensemble features
        try:
            # Load forecast GRIB to get ensemble members
            forecast_path = Path(case.forecast_path)
            messages, _ = read_grib_file(forecast_path, compute_stats=False)
            tp_messages = [m for m in messages if m.short_name == "tp"]

            if not tp_messages:
                return DatasetRecord(
                    case_id=case.case_id,
                    status=DatasetRecordStatus.BLOCKED_FEATURE_EXTRACTION_ERROR,
                    reason="No TP messages found during feature extraction",
                    provenance=case_result.provenance,
                )

            # Read ensemble members from GRIB
            import eccodes

            ensemble_members = {}
            with open(forecast_path, "rb") as f:
                all_handles = []
                while True:
                    handle = eccodes.codes_grib_new_from_file(f)
                    if handle is None:
                        break
                    all_handles.append(handle)

                for msg in tp_messages:
                    handle = all_handles[msg.message_index - 1]
                    raw_vals = eccodes.codes_get_values(handle)
                    values_1d = np.asarray(raw_vals, dtype=np.float64)
                    ensemble_members[msg.member] = (values_1d, msg.to_dict())

                for handle in all_handles:
                    eccodes.codes_release(handle)

            # Build grid metadata for feature extraction
            msg0 = tp_messages[0]
            grid_meta = {
                "ni": msg0.ni,
                "nj": msg0.nj,
                "first_lat": msg0.first_lat,
                "first_lon": msg0.first_lon,
                "last_lat": msg0.last_lat,
                "last_lon": msg0.last_lon,
                "lat_increment": msg0.j_increment,
                "lon_increment": msg0.i_increment,
            }

            # Extract ensemble features
            features = extract_ensemble_rainfall_features(ensemble_members, grid_meta)
            feature_names = features.feature_array_names()

            # Build features dict from dataclass
            for fname in feature_names:
                features_dict[fname] = getattr(features, fname)

        except Exception as e:
            return DatasetRecord(
                case_id=case.case_id,
                status=DatasetRecordStatus.BLOCKED_FEATURE_EXTRACTION_ERROR,
                reason=f"Feature extraction failed: {e}",
                provenance=case_result.provenance,
            )

    # Determine reason if blocked
    reason = ""
    if status != DatasetRecordStatus.VALID:
        reason = case_result.provenance.get("reason", "Unknown reason")

    # Build dataset record
    record = DatasetRecord(
        case_id=case.case_id,
        status=status,
        forecast_initialization_time=init_time,
        forecast_lead_hours=int(forecast_metadata.get("step", -1)) if forecast_metadata.get("step") is not None else None,
        forecast_source_model=forecast_source,
        observation_source=observation_metadata.get("source", "IMD_DAILY"),
        observation_date=parse_iso(str(observation_metadata.get("observation_date"))) if observation_metadata.get("observation_date") else None,
        forecast_accumulation_start=forecast_start,
        forecast_accumulation_end=forecast_end,
        observation_accumulation_start=observation_start,
        observation_accumulation_end=observation_end,
        ensemble_member_count=features.member_count if status == DatasetRecordStatus.VALID else None,
        grid_shape=tuple(error_stats.get("grid_shape", (0, 0))) if "grid_shape" in error_stats else tuple(features_dict.get(feature_names[0]).shape) if feature_names and status == DatasetRecordStatus.VALID else None,
        mae=error_stats.get("mae"),
        rmse=error_stats.get("rmse"),
        bias=error_stats.get("bias"),
        forecast_mean=error_stats.get("forecast_mean"),
        observation_mean=error_stats.get("observation_mean"),
        valid_cell_count=case_result.valid_cell_count if status == DatasetRecordStatus.VALID else None,
        missing_cell_count=case_result.missing_cell_count if status == DatasetRecordStatus.VALID else None,
        feature_names=feature_names,
        **features_dict,
        reason=reason,
        provenance=case_result.provenance,
    )

    return record
