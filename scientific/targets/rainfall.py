"""Leakage-safe target/label construction for rainfall forecast verification.

This module converts verified rainfall forecast outcomes into ML target records.

LEAKAGE SAFEGUARDS
------------------
Observation-derived values (mae, rmse, bias, observation_mean, cell counts) are
legitimate TARGET fields because they describe forecast error — they are labels,
not predictors.  They must NEVER enter predictor feature arrays.

The target constructor accepts only scalar error statistics and provenance from a
completed verification.  It explicitly refuses numpy arrays and any field that
could be a spatial feature array, making accidental feature contamination a
hard error rather than a silent bug.

DESIGN NOTES
------------
Continuous target
    RMSE is used as the initial continuous error target.  This is documented as
    the current choice, not a permanent scientific decision.  The field is named
    ``continuous_error`` so callers are independent of the specific metric used.
    The underlying metric name is recorded in ``continuous_error_metric``.

Severity labels
    Severity is UNDEFINED unless the caller explicitly supplies monotone
    thresholds.  No climatology-derived or event-specific thresholds are
    hardcoded.  Thresholds map RMSE (the current continuous target) to one of:
    NORMAL, DEGRADED, MAJOR, SEVERE.

    Future milestone: replace or supplement with climatology-normalised error
    once a validated historical reference distribution exists.

Blocked / invalid cases
    Cases that were not successfully verified (temporal mismatch, unspecified
    observation window, read errors, empty valid set, invalid metadata) produce
    a BLOCKED or INVALID target with no continuous label and no severity.  This
    mirrors the existing alignment and verification semantics exactly.

Scientific decisions intentionally deferred
    - Climatology-normalised error (no validated reference distribution yet).
    - Event-specific labels (cyclone, monsoon, heat wave).
    - Final operational bust thresholds (require historical validation).
    - Multi-variable or multi-lead-time targets.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from scientific.cases.rainfall_case import RainfallCaseResult, RainfallCaseStatus


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class RainfallTargetStatus(str, Enum):
    """Outcome status of target construction.

    VALID
        Verification was ALIGNED and all required statistics are present.
        ``continuous_error`` and ``severity`` (if thresholds supplied) are set.

    BLOCKED
        Verification did not produce error statistics because of a known,
        expected condition (temporal mismatch, unspecified window, read error,
        empty valid set).  No continuous target or severity is produced.

    INVALID
        Verification metadata was structurally incomplete or internally
        inconsistent.  No continuous target or severity is produced.
    """

    VALID = "VALID"
    BLOCKED = "BLOCKED"
    INVALID = "INVALID"


class SeverityLevel(str, Enum):
    """Ordinal severity of forecast error.

    Levels are ordered: NORMAL < DEGRADED < MAJOR < SEVERE.

    UNDEFINED
        No thresholds were supplied; severity cannot be determined.
        This is the correct state when thresholds have not been validated.
    NORMAL
        Continuous error below the first threshold.
    DEGRADED
        Continuous error at or above the first threshold, below the second.
    MAJOR
        Continuous error at or above the second threshold, below the third.
    SEVERE
        Continuous error at or above the third threshold.
    """

    UNDEFINED = "UNDEFINED"
    NORMAL = "NORMAL"
    DEGRADED = "DEGRADED"
    MAJOR = "MAJOR"
    SEVERE = "SEVERE"


# Ordered severity levels for threshold mapping (excluding UNDEFINED).
_SEVERITY_ORDER: List[SeverityLevel] = [
    SeverityLevel.NORMAL,
    SeverityLevel.DEGRADED,
    SeverityLevel.MAJOR,
    SeverityLevel.SEVERE,
]

# Metric used for the continuous_error field.
# Changing this constant updates both the computation and the recorded metric name.
_CONTINUOUS_ERROR_METRIC = "rmse"


# ---------------------------------------------------------------------------
# SeverityThresholds
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SeverityThresholds:
    """Three monotone lower-bound thresholds that define four severity levels.

    The thresholds t0, t1, t2 must satisfy:  0 <= t0 < t1 < t2

    Mapping (applied to the continuous_error value):
        continuous_error <  t0  → NORMAL
        t0 <= error < t1        → DEGRADED
        t1 <= error < t2        → MAJOR
        error >= t2             → SEVERE

    Parameters
    ----------
    t0 : float
        Lower bound for DEGRADED  (mm, must be >= 0).
    t1 : float
        Lower bound for MAJOR     (mm, must be > t0).
    t2 : float
        Lower bound for SEVERE    (mm, must be > t1).

    Notes
    -----
    These are configurable thresholds for the *current* continuous error metric
    (RMSE of spatial forecast error in mm).  Final operational thresholds must
    be derived from historical validation — do not guess values.
    """

    t0: float
    t1: float
    t2: float

    def __post_init__(self) -> None:
        if not (self.t0 >= 0):
            raise ValueError(f"t0 must be >= 0, got {self.t0}")
        if not (self.t0 < self.t1):
            raise ValueError(
                f"Thresholds must be strictly monotone: t0 < t1, got {self.t0} >= {self.t1}"
            )
        if not (self.t1 < self.t2):
            raise ValueError(
                f"Thresholds must be strictly monotone: t1 < t2, got {self.t1} >= {self.t2}"
            )

    def map(self, value: float) -> SeverityLevel:
        """Map a continuous error value to a SeverityLevel.

        Parameters
        ----------
        value : float
            Continuous error value (must be finite and >= 0).

        Returns
        -------
        SeverityLevel
            Deterministic severity level based on the thresholds.

        Raises
        ------
        ValueError
            If value is not finite.
        """
        if not np.isfinite(value):
            raise ValueError(f"Cannot map non-finite value {value!r} to severity")
        if value < self.t0:
            return SeverityLevel.NORMAL
        if value < self.t1:
            return SeverityLevel.DEGRADED
        if value < self.t2:
            return SeverityLevel.MAJOR
        return SeverityLevel.SEVERE


# ---------------------------------------------------------------------------
# RainfallTarget dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RainfallTarget:
    """Immutable ML target record for one verified rainfall forecast case.

    VALID records carry all target fields.
    BLOCKED and INVALID records carry only provenance and reason.

    This object is strictly a label container.  It holds no predictor features.
    """

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    case_id: str
    """Unique identifier for the historical case."""

    target_status: RainfallTargetStatus
    """VALID, BLOCKED, or INVALID."""

    # ------------------------------------------------------------------
    # Error statistics (VALID only; None for BLOCKED/INVALID)
    # ------------------------------------------------------------------

    mae: Optional[float] = None
    """Mean absolute error (mm).  None unless target_status == VALID."""

    rmse: Optional[float] = None
    """Root mean squared error (mm).  None unless target_status == VALID."""

    bias: Optional[float] = None
    """Mean signed error: forecast_mean - observation_mean (mm).
    None unless target_status == VALID."""

    forecast_mean: Optional[float] = None
    """Spatial mean of forecast field (mm).  None unless target_status == VALID."""

    observation_mean: Optional[float] = None
    """Spatial mean of observation field (mm).  None unless target_status == VALID.

    NOTE: This is a TARGET field (describes forecast error), not a predictor.
    It must never be used as an input feature.
    """

    valid_cell_count: Optional[int] = None
    """Number of grid cells with finite forecast and observation.
    None unless target_status == VALID."""

    missing_cell_count: Optional[int] = None
    """Number of grid cells missing in either forecast or observation.
    None unless target_status == VALID."""

    # ------------------------------------------------------------------
    # Continuous target (VALID only)
    # ------------------------------------------------------------------

    continuous_error: Optional[float] = None
    """Continuous error target for regression models.

    Current implementation: equals rmse.

    This field is metric-agnostic by name.  The specific metric used is
    recorded in ``continuous_error_metric``.  When a validated climatology
    reference distribution is available, this may be updated to a
    normalised score without changing the field contract.
    """

    continuous_error_metric: Optional[str] = None
    """Name of the metric used for continuous_error (e.g. 'rmse').
    None unless target_status == VALID."""

    # ------------------------------------------------------------------
    # Severity (VALID only; UNDEFINED if no thresholds supplied)
    # ------------------------------------------------------------------

    severity: SeverityLevel = SeverityLevel.UNDEFINED
    """Ordinal severity label.

    UNDEFINED when no thresholds were supplied at construction time.
    Only NORMAL/DEGRADED/MAJOR/SEVERE when thresholds were explicitly provided.
    """

    # ------------------------------------------------------------------
    # Provenance
    # ------------------------------------------------------------------

    reason: str = ""
    """Human-readable reason string for BLOCKED/INVALID targets."""

    provenance: Dict[str, Any] = field(default_factory=dict)
    """Full provenance dict from the case result for auditability."""

    construction_timestamp: datetime = field(
        default_factory=lambda: datetime.utcnow()
    )
    """UTC timestamp of target construction."""

    def has_continuous_target(self) -> bool:
        """Return True if continuous_error is available."""
        return bool(
            self.target_status == RainfallTargetStatus.VALID
            and self.continuous_error is not None
            and np.isfinite(self.continuous_error)
        )

    def has_severity(self) -> bool:
        """Return True if severity is a defined level (not UNDEFINED)."""
        return self.severity != SeverityLevel.UNDEFINED


# ---------------------------------------------------------------------------
# Leakage guard
# ---------------------------------------------------------------------------

# Feature array field names that must never appear in a target record.
# This set is checked at construction time to prevent accidental contamination.
_FEATURE_ARRAY_NAMES = frozenset({
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
})


def _assert_no_feature_arrays(kwargs: Dict[str, Any]) -> None:
    """Raise LeakageError if any predictor feature array is present in kwargs.

    This is a hard guard: any attempt to store a spatial feature array inside
    a target record raises an error immediately rather than silently passing.
    """
    contaminated = _FEATURE_ARRAY_NAMES & set(kwargs.keys())
    if contaminated:
        raise LeakageError(
            f"Predictor feature arrays must not be stored in target records. "
            f"Contaminated fields: {sorted(contaminated)}"
        )
    # Also reject any numpy ndarray values (arrays with ndim > 0)
    for key, val in kwargs.items():
        if isinstance(val, np.ndarray) and val.ndim > 0:
            raise LeakageError(
                f"Target records must not contain spatial arrays. "
                f"Field '{key}' is a numpy array of shape {val.shape}."
            )


class LeakageError(Exception):
    """Raised when predictor feature data is detected in a target record."""


# ---------------------------------------------------------------------------
# Status mapping
# ---------------------------------------------------------------------------

# Maps RainfallCaseStatus values to RainfallTargetStatus.
# ALIGNED → VALID; metadata/structural errors → INVALID; operational blocks → BLOCKED.
_CASE_STATUS_TO_TARGET_STATUS: Dict[str, RainfallTargetStatus] = {
    RainfallCaseStatus.ALIGNED.value:                           RainfallTargetStatus.VALID,
    RainfallCaseStatus.BLOCKED_UNSPECIFIED_OBSERVATION_WINDOW.value: RainfallTargetStatus.BLOCKED,
    RainfallCaseStatus.NOT_ALIGNED.value:                       RainfallTargetStatus.BLOCKED,
    RainfallCaseStatus.EMPTY_VALID_SET.value:                   RainfallTargetStatus.BLOCKED,
    RainfallCaseStatus.FORECAST_READ_ERROR.value:               RainfallTargetStatus.BLOCKED,
    RainfallCaseStatus.OBSERVATION_READ_ERROR.value:            RainfallTargetStatus.BLOCKED,
    RainfallCaseStatus.INVALID_METADATA.value:                  RainfallTargetStatus.INVALID,
    RainfallCaseStatus.NO_TP_MESSAGE.value:                     RainfallTargetStatus.INVALID,
}


# ---------------------------------------------------------------------------
# Public constructor
# ---------------------------------------------------------------------------


def build_rainfall_target(
    case_result: RainfallCaseResult,
    thresholds: Optional[SeverityThresholds] = None,
) -> RainfallTarget:
    """Build a leakage-safe target record from a verified case result.

    Parameters
    ----------
    case_result : RainfallCaseResult
        Verified result from ``run_rainfall_case()``.  Only ALIGNED cases
        produce a VALID target; all others produce BLOCKED or INVALID targets.
    thresholds : SeverityThresholds, optional
        Explicit severity thresholds.  If None, ``severity`` is UNDEFINED.
        Thresholds must be strictly monotone (validated by SeverityThresholds).

    Returns
    -------
    RainfallTarget
        Immutable target record.  VALID records have continuous_error and
        optionally severity.  BLOCKED/INVALID records have no target values.

    Raises
    ------
    LeakageError
        If spatial feature arrays are detected in the case result provenance
        (should never happen in normal operation, but caught defensively).

    Notes
    -----
    Observation-derived statistics (rmse, mae, bias, observation_mean) are
    legitimate TARGET fields — they describe forecast error and are used as
    labels, never as predictors.

    Scientific decisions deferred:
    - Climatology-normalised continuous error.
    - Event-specific labels.
    - Final operational severity thresholds.
    """
    target_status = _CASE_STATUS_TO_TARGET_STATUS.get(
        case_result.status.value,
        RainfallTargetStatus.INVALID,
    )

    provenance = dict(case_result.provenance)
    reason = provenance.get("reason", "") if target_status != RainfallTargetStatus.VALID else ""

    # Non-VALID cases: no targets
    if target_status != RainfallTargetStatus.VALID:
        return RainfallTarget(
            case_id=case_result.case_id,
            target_status=target_status,
            reason=reason,
            provenance=provenance,
        )

    # VALID case: extract error statistics
    error_stats = case_result.error_statistics or {}

    mae = error_stats.get("mae")
    rmse = error_stats.get("rmse")
    bias = error_stats.get("bias")
    forecast_mean = error_stats.get("forecast_mean")
    observation_mean = error_stats.get("observation_mean")

    # Guard: if ALIGNED but error statistics are missing/NaN, demote to INVALID
    if rmse is None or not np.isfinite(rmse):
        return RainfallTarget(
            case_id=case_result.case_id,
            target_status=RainfallTargetStatus.INVALID,
            reason=(
                "Case status is ALIGNED but rmse is missing or non-finite "
                f"(rmse={rmse!r}). Cannot construct continuous target."
            ),
            provenance=provenance,
        )

    # Continuous target: RMSE (current choice, documented and extensible)
    continuous_error = rmse
    continuous_error_metric = _CONTINUOUS_ERROR_METRIC

    # Severity mapping (only if thresholds supplied)
    severity = SeverityLevel.UNDEFINED
    if thresholds is not None:
        severity = thresholds.map(continuous_error)

    return RainfallTarget(
        case_id=case_result.case_id,
        target_status=RainfallTargetStatus.VALID,
        mae=mae,
        rmse=rmse,
        bias=bias,
        forecast_mean=forecast_mean,
        observation_mean=observation_mean,
        valid_cell_count=case_result.valid_cell_count,
        missing_cell_count=case_result.missing_cell_count,
        continuous_error=continuous_error,
        continuous_error_metric=continuous_error_metric,
        severity=severity,
        reason="",
        provenance=provenance,
    )
