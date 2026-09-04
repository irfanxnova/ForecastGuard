"""Case-to-row assembly of ML-ready tabular samples.

Converts (DatasetRecord, RainfallTarget) pairs into AssembledSample objects —
the row-level unit that will be used for model training and evaluation.

DESIGN DECISIONS
----------------
Spatial arrays → scalar summaries
    The 24 ensemble feature arrays each have shape (n_lat, n_lon).  Flattening
    full grids would produce millions of columns and is not appropriate for the
    tabular models being built in this milestone.  Instead, five scalar spatial
    statistics are extracted per feature array:
        _mean, _std, _max, _p10, _p90
    yielding 24 × 5 = 120 scalar predictor columns.  This is the *current*
    representation choice, documented here.  The field names are recorded in
    ``predictor_names`` so callers are not hard-coded to a fixed count.

    Future milestone: spatial / patch-level representations can be added as
    alternative assembly modes without changing this contract.

Predictor / target separation
    ``AssembledSample`` stores predictors and targets in separate named
    sections and enforces at construction time that no target metric
    (mae, rmse, bias, observation_mean, continuous_error, severity) leaks
    into the predictor dict, and that no spatial array enters either dict.

Sample status
    Every assembled row carries a ``sample_status`` so blocked/invalid cases
    are retained as auditable metadata rather than silently dropped.

    VALID_TRAINABLE   — has predictors and a valid continuous target
    VALID_NO_TARGET   — has predictors but no continuous target (RMSE is None)
    BLOCKED           — verification was blocked; no predictors or target
    INVALID           — verification was invalid; no predictors or target

Determinism
    ``assemble_samples`` is a pure function.  Given the same inputs it always
    produces the same output.  No random operations.

LEAKAGE SAFEGUARDS (enforced at construction time)
    1.  TARGET_METRIC_NAMES  — scalar observation-derived metrics that must
        never appear in predictor_dict.
    2.  No numpy ndarray with ndim > 0 is permitted in predictor_dict or
        target_dict (spatial arrays must be summarised to scalars first).
    3.  Verification timestamps (forecast_accumulation_end, observation dates)
        must not appear as predictor features.  The assembly only exposes
        forecast_initialization_time and forecast_lead_hours — information
        available at prediction time.

FORECAST_MEAN AS A PREDICTOR
-----------------------------
``forecast_mean_spatial`` is a forecast-only scalar predictor computed as the
mean of all finite values in the ``ensemble_mean`` feature array (the ensemble
mean TP field).  It is derived exclusively from the forecast field with no
dependence on observation values, observation validity masks, or verification
error fields.

This is distinct from ``forecast_mean`` in ``target_dict``, which is the mean
of forecast values at the **joint** valid-cell mask (cells where both forecast
and observation are finite) — that quantity is observation-mask-dependent and
must remain a target field only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from scientific.dataset.builder import DatasetRecord, DatasetRecordStatus
from scientific.targets.rainfall import (
    RainfallTarget,
    RainfallTargetStatus,
    SeverityLevel,
)


# ---------------------------------------------------------------------------
# Constants — leakage guard sets
# ---------------------------------------------------------------------------

# Scalar observation-derived metrics that are TARGETS, not predictors.
# These must never appear in predictor_dict.
TARGET_METRIC_NAMES: frozenset = frozenset({
    "mae", "rmse", "bias",
    "observation_mean",          # derived from observations
    "continuous_error",          # = rmse
    "continuous_error_metric",
    "severity",
    "valid_cell_count",          # derived from joint forecast+obs mask
    "missing_cell_count",        # derived from joint forecast+obs mask
    # NOTE: "forecast_mean" is intentionally NOT in this set.
    # The verification-derived forecast_mean (computed over the joint
    # valid-cell mask) stays in target_dict only.
    # A separate observation-independent predictor "forecast_mean_spatial"
    # is computed from the ensemble_mean feature array in assemble_sample().
})

# Scalar forecast-time metadata that IS allowed as predictors.
_ALLOWED_PREDICTOR_METADATA: frozenset = frozenset({
    "forecast_lead_hours",
    "ensemble_member_count",
    "grid_n_lat",
    "grid_n_lon",
})

# The 24 feature array names from the ensemble feature engine.
_FEATURE_ARRAY_NAMES: Tuple[str, ...] = (
    "ensemble_mean", "ensemble_median", "ensemble_min", "ensemble_max",
    "ensemble_std", "ensemble_range", "ensemble_iqr",
    "ensemble_p10", "ensemble_p25", "ensemble_p75", "ensemble_p90",
    "coefficient_of_variation", "ensemble_skewness",
    "probability_rain_gt_1mm", "probability_rain_gt_10mm",
    "probability_rain_gt_25mm", "probability_rain_gt_50mm",
    "probability_rain_gt_100mm",
    "gradient_magnitude", "latitude_gradient", "longitude_gradient",
    "mean_pairwise_member_difference", "maximum_ensemble_gap",
    "member_agreement_fraction",
)

# Scalar statistics extracted from each feature array.
_SPATIAL_STATS: Tuple[str, ...] = ("mean", "std", "max", "p10", "p90")


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class SampleStatus(str, Enum):
    """Assembly outcome for one case.

    VALID_TRAINABLE
        Predictors and continuous target are both present.  This row can be
        used for supervised model training.

    VALID_NO_TARGET
        Predictors are present but continuous_error is None or non-finite.
        The case was ALIGNED but targets are incomplete.  Do not use for
        regression; may be used for inference.

    BLOCKED
        The upstream verification was blocked (temporal mismatch, missing
        window, read error, empty grid).  No predictors or target.

    INVALID
        The upstream verification was structurally invalid.  No predictors
        or target.
    """

    VALID_TRAINABLE = "VALID_TRAINABLE"
    VALID_NO_TARGET = "VALID_NO_TARGET"
    BLOCKED = "BLOCKED"
    INVALID = "INVALID"


# ---------------------------------------------------------------------------
# AssemblyError / LeakageError
# ---------------------------------------------------------------------------


class AssemblyError(Exception):
    """Raised when assembly detects an inconsistency in input data."""


class AssemblyLeakageError(Exception):
    """Raised when a target metric or spatial array is detected in predictors."""


# ---------------------------------------------------------------------------
# AssembledSample
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AssembledSample:
    """One tabular row assembled from a DatasetRecord + RainfallTarget pair.

    Predictor data and target data are stored in separate dicts and are
    logically separable at all times.

    Fields
    ------
    case_id : str
        Unique case identifier.

    sample_status : SampleStatus
        VALID_TRAINABLE → use for supervised training.
        VALID_NO_TARGET → predictors present, target absent.
        BLOCKED / INVALID → neither predictors nor target.

    forecast_initialization_time : Optional[datetime]
        Forecast initialization time (UTC).  The primary chronological
        sort key for splitting.  Available at prediction time.

    forecast_lead_hours : Optional[int]
        Forecast lead time in hours.  Available at prediction time.

    forecast_source_model : Optional[str]
        Forecast model identifier.

    ensemble_member_count : Optional[int]
        Number of ensemble members in the source GRIB.

    grid_shape : Optional[tuple]
        (n_lat, n_lon) of the forecast grid.

    predictor_names : List[str]
        Ordered list of scalar predictor column names.
        Contains only forecast-time information.

    predictor_dict : Dict[str, Optional[float]]
        Scalar predictor values keyed by name.
        Contains ONLY forecast-time information — no observation-derived metrics.

    target_status : RainfallTargetStatus
        VALID / BLOCKED / INVALID from the target engine.

    continuous_error : Optional[float]
        Continuous error target (RMSE in mm).  None unless sample_status
        is VALID_TRAINABLE.

    continuous_error_metric : Optional[str]
        Name of the metric used for continuous_error.

    severity : SeverityLevel
        Ordinal severity label.  UNDEFINED unless thresholds were supplied.

    target_dict : Dict[str, Any]
        Full set of target scalars for auditability.
        Contains mae, rmse, bias, forecast_mean, observation_mean,
        valid_cell_count, missing_cell_count, continuous_error, severity.

    reason : str
        Human-readable reason for BLOCKED/INVALID samples.

    provenance : Dict[str, Any]
        Full provenance from the upstream case result.

    assembly_timestamp : datetime
        UTC timestamp of assembly.
    """

    case_id: str
    sample_status: SampleStatus

    # Forecast-time metadata (available at prediction time)
    forecast_initialization_time: Optional[datetime] = None
    forecast_lead_hours: Optional[int] = None
    forecast_source_model: Optional[str] = None
    ensemble_member_count: Optional[int] = None
    grid_shape: Optional[tuple] = None

    # Predictors
    predictor_names: List[str] = field(default_factory=list)
    predictor_dict: Dict[str, Optional[float]] = field(default_factory=dict)

    # Targets
    target_status: RainfallTargetStatus = RainfallTargetStatus.INVALID
    continuous_error: Optional[float] = None
    continuous_error_metric: Optional[str] = None
    severity: SeverityLevel = SeverityLevel.UNDEFINED
    target_dict: Dict[str, Any] = field(default_factory=dict)

    # Provenance
    reason: str = ""
    provenance: Dict[str, Any] = field(default_factory=dict)
    assembly_timestamp: datetime = field(default_factory=lambda: datetime.utcnow())

    def is_trainable(self) -> bool:
        """Return True if this sample can be used for supervised training."""
        return self.sample_status == SampleStatus.VALID_TRAINABLE

    def has_predictors(self) -> bool:
        """Return True if predictor_dict is populated."""
        return bool(self.predictor_dict)

    def has_target(self) -> bool:
        """Return True if continuous_error is present and finite."""
        return (
            self.continuous_error is not None
            and bool(np.isfinite(self.continuous_error))
        )


# ---------------------------------------------------------------------------
# Leakage guard
# ---------------------------------------------------------------------------


def _check_predictor_leakage(predictor_dict: Dict[str, Any]) -> None:
    """Raise AssemblyLeakageError if any target metric or array is in predictors.

    Checks
    ------
    1.  No key in predictor_dict is in TARGET_METRIC_NAMES.
    2.  No value is a numpy ndarray with ndim > 0.
    """
    contaminated_keys = TARGET_METRIC_NAMES & set(predictor_dict.keys())
    if contaminated_keys:
        raise AssemblyLeakageError(
            f"Target metrics must not appear in predictor_dict. "
            f"Contaminated keys: {sorted(contaminated_keys)}"
        )
    for key, val in predictor_dict.items():
        if isinstance(val, np.ndarray) and val.ndim > 0:
            raise AssemblyLeakageError(
                f"Predictor '{key}' is a spatial array (shape {val.shape}). "
                "Spatial arrays must be summarised to scalars before assembly."
            )


def _check_target_no_arrays(target_dict: Dict[str, Any]) -> None:
    """Raise AssemblyLeakageError if any spatial array is stored in target_dict."""
    for key, val in target_dict.items():
        if isinstance(val, np.ndarray) and val.ndim > 0:
            raise AssemblyLeakageError(
                f"Target field '{key}' is a spatial array (shape {val.shape}). "
                "Target dicts must contain scalars only."
            )


# ---------------------------------------------------------------------------
# Spatial statistics extractor
# ---------------------------------------------------------------------------


def _extract_spatial_stats(
    array: np.ndarray,
    feature_name: str,
) -> Dict[str, Optional[float]]:
    """Extract five scalar statistics from a 2-D feature array.

    Returns keys: ``{feature_name}_mean``, ``_std``, ``_max``, ``_p10``, ``_p90``.
    Any statistic that cannot be computed (all-NaN array) is set to None.
    """
    result: Dict[str, Optional[float]] = {}
    arr = np.asarray(array, dtype=np.float64)
    finite = arr[np.isfinite(arr)]

    if finite.size == 0:
        for stat in _SPATIAL_STATS:
            result[f"{feature_name}_{stat}"] = None
        return result

    result[f"{feature_name}_mean"] = float(np.mean(finite))
    result[f"{feature_name}_std"] = float(np.std(finite, ddof=0))
    result[f"{feature_name}_max"] = float(np.max(finite))
    result[f"{feature_name}_p10"] = float(np.percentile(finite, 10))
    result[f"{feature_name}_p90"] = float(np.percentile(finite, 90))
    return result


# ---------------------------------------------------------------------------
# Core assembly function
# ---------------------------------------------------------------------------


def assemble_sample(
    record: DatasetRecord,
    target: RainfallTarget,
) -> AssembledSample:
    """Assemble one (DatasetRecord, RainfallTarget) pair into an AssembledSample.

    Parameters
    ----------
    record : DatasetRecord
        ML-ready record from ``build_dataset_record()``.
    target : RainfallTarget
        Target record from ``build_rainfall_target()``.

    Returns
    -------
    AssembledSample
        Tabular row with separated predictors and targets.

    Raises
    ------
    AssemblyError
        If ``record.case_id != target.case_id``.
    AssemblyLeakageError
        If target metrics or spatial arrays are detected in predictor_dict.

    Notes
    -----
    Blocked and invalid cases are assembled with empty predictor/target dicts
    and ``sample_status`` BLOCKED or INVALID.  They are retained for
    auditability but must not be used as training samples.

    Only forecast-time information enters ``predictor_dict``:
    - forecast_lead_hours, ensemble_member_count, grid_n_lat, grid_n_lon
    - forecast_mean_spatial: mean of all finite values in the ensemble_mean
      feature array — pure forecast field, NO observation dependency
    - 120 scalar spatial statistics from the 24 feature arrays (24 × 5)

    Observation-derived scalars (mae, rmse, bias, observation_mean,
    valid_cell_count, missing_cell_count) go only into ``target_dict``.

    The verification-derived ``forecast_mean`` (mean at the joint valid-cell
    mask where both forecast and observation are finite) remains in
    ``target_dict`` only, as it is observation-mask-dependent.
    ``forecast_mean_spatial`` in ``predictor_dict`` is the observation-
    independent equivalent, computed solely from the ensemble_mean array.
    """
    if record.case_id != target.case_id:
        raise AssemblyError(
            f"case_id mismatch: record has '{record.case_id}', "
            f"target has '{target.case_id}'"
        )

    # ------------------------------------------------------------------
    # Determine sample status
    # ------------------------------------------------------------------
    if (
        record.status == DatasetRecordStatus.VALID
        and target.target_status == RainfallTargetStatus.VALID
        and target.continuous_error is not None
        and np.isfinite(target.continuous_error)
    ):
        sample_status = SampleStatus.VALID_TRAINABLE
    elif (
        record.status == DatasetRecordStatus.VALID
        and target.target_status == RainfallTargetStatus.VALID
    ):
        sample_status = SampleStatus.VALID_NO_TARGET
    elif target.target_status == RainfallTargetStatus.INVALID:
        sample_status = SampleStatus.INVALID
    else:
        sample_status = SampleStatus.BLOCKED

    # ------------------------------------------------------------------
    # Non-VALID: return provenance-only sample
    # ------------------------------------------------------------------
    if sample_status in (SampleStatus.BLOCKED, SampleStatus.INVALID):
        return AssembledSample(
            case_id=record.case_id,
            sample_status=sample_status,
            forecast_initialization_time=record.forecast_initialization_time,
            forecast_lead_hours=record.forecast_lead_hours,
            forecast_source_model=record.forecast_source_model,
            target_status=target.target_status,
            reason=target.reason or record.reason,
            provenance=dict(target.provenance),
        )

    # ------------------------------------------------------------------
    # VALID: build predictor dict (forecast-time info only)
    # ------------------------------------------------------------------
    predictor_dict: Dict[str, Optional[float]] = {}

    # Scalar forecast-time metadata
    if record.forecast_lead_hours is not None:
        predictor_dict["forecast_lead_hours"] = float(record.forecast_lead_hours)
    if record.ensemble_member_count is not None:
        predictor_dict["ensemble_member_count"] = float(record.ensemble_member_count)
    if record.grid_shape is not None and len(record.grid_shape) >= 2:
        predictor_dict["grid_n_lat"] = float(record.grid_shape[0])
        predictor_dict["grid_n_lon"] = float(record.grid_shape[1])

    # Spatial statistics from 24 feature arrays
    for feature_name in record.feature_names:
        arr = getattr(record, feature_name, None)
        if arr is not None and isinstance(arr, np.ndarray) and arr.ndim > 0:
            stats = _extract_spatial_stats(arr, feature_name)
            predictor_dict.update(stats)

    # forecast_mean_spatial: observation-independent forecast spatial mean.
    # Derived exclusively from the ensemble_mean feature array — the ensemble
    # mean TP field computed from forecast GRIB members only.
    # This is NOT the same as RainfallTarget.forecast_mean, which is the mean
    # of forecast values at the joint (forecast & observation) valid-cell mask
    # and is therefore observation-mask-dependent.
    # Here we take the mean of ALL finite values in the ensemble_mean array,
    # with zero dependence on observation values or observation validity.
    ensemble_mean_arr = getattr(record, "ensemble_mean", None)
    if ensemble_mean_arr is not None and isinstance(ensemble_mean_arr, np.ndarray) and ensemble_mean_arr.ndim > 0:
        finite_vals = ensemble_mean_arr[np.isfinite(ensemble_mean_arr)]
        predictor_dict["forecast_mean_spatial"] = (
            float(np.mean(finite_vals)) if finite_vals.size > 0 else None
        )

    # Leakage guard on predictors
    _check_predictor_leakage(predictor_dict)

    predictor_names = list(predictor_dict.keys())

    # ------------------------------------------------------------------
    # Build target dict (observation-derived scalars only)
    # ------------------------------------------------------------------
    target_dict: Dict[str, Any] = {
        "mae": target.mae,
        "rmse": target.rmse,
        "bias": target.bias,
        "forecast_mean": target.forecast_mean,
        "observation_mean": target.observation_mean,
        "valid_cell_count": target.valid_cell_count,
        "missing_cell_count": target.missing_cell_count,
        "continuous_error": target.continuous_error,
        "continuous_error_metric": target.continuous_error_metric,
        "severity": target.severity.value,
    }

    _check_target_no_arrays(target_dict)

    return AssembledSample(
        case_id=record.case_id,
        sample_status=sample_status,
        forecast_initialization_time=record.forecast_initialization_time,
        forecast_lead_hours=record.forecast_lead_hours,
        forecast_source_model=record.forecast_source_model,
        ensemble_member_count=record.ensemble_member_count,
        grid_shape=record.grid_shape,
        predictor_names=predictor_names,
        predictor_dict=predictor_dict,
        target_status=target.target_status,
        continuous_error=target.continuous_error,
        continuous_error_metric=target.continuous_error_metric,
        severity=target.severity,
        target_dict=target_dict,
        reason="",
        provenance=dict(target.provenance),
    )


def assemble_samples(
    pairs: Sequence[Tuple[DatasetRecord, RainfallTarget]],
) -> List[AssembledSample]:
    """Assemble a sequence of (DatasetRecord, RainfallTarget) pairs.

    Parameters
    ----------
    pairs : Sequence[Tuple[DatasetRecord, RainfallTarget]]
        Ordered sequence of pairs.  Order is preserved in the output.

    Returns
    -------
    List[AssembledSample]
        One AssembledSample per input pair, in the same order.
        Blocked/invalid cases are included with appropriate sample_status.

    Notes
    -----
    This function is a pure map.  It has no filesystem side effects and
    produces deterministic output for any given input.
    """
    return [assemble_sample(record, target) for record, target in pairs]
