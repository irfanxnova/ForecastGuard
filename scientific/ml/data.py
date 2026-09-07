"""Data preparation and leakage guardrails for ForecastGuard ML models.

Converts AssembledSample sequences and SplitResult objects into feature
matrices (X) and target vectors (y) with strict leakage enforcement.

Scientific rules enforced:
1. TARGET_METRIC_NAMES must never appear in feature matrices.
2. Chronological separation is preserved: preprocessors (imputer, scaler)
   are fit strictly on training partitions and applied to validation/test.
3. Incomplete or non-trainable samples are filtered or quarantined.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

from scientific.dataset.assembly import (
    TARGET_METRIC_NAMES,
    AssembledSample,
    SampleStatus,
)
from scientific.dataset.splits import SplitResult
from scientific.targets.rainfall import SeverityLevel


class MLDataError(Exception):
    """Raised when dataset extraction or transformation fails."""


class MLDataLeakageError(MLDataError):
    """Raised when an observation-derived target metric is detected in features."""


@dataclass(frozen=True)
class MLDataset:
    """Extracted tabular dataset ready for machine learning.

    Predictors and targets are strictly segregated.
    """

    X: np.ndarray
    """Feature matrix of shape (n_samples, n_features)."""

    feature_names: List[str]
    """Ordered names of the predictor columns."""

    case_ids: List[str]
    """Unique case identifiers for auditability."""

    initialization_times: List[Optional[datetime]]
    """Forecast initialization datetimes (UTC)."""

    lead_hours: List[Optional[int]]
    """Forecast lead time in hours for each sample."""

    continuous_targets: np.ndarray
    """Continuous error target (RMSE in mm) of shape (n_samples,)."""

    binary_targets: Optional[np.ndarray] = None
    """Binary bust indicator (1 = bust, 0 = normal) of shape (n_samples,)."""

    severity_targets: Optional[List[SeverityLevel]] = None
    """Ordinal severity level for each sample."""

    severity_codes: Optional[np.ndarray] = None
    """Integer-encoded severity (NORMAL=0, DEGRADED=1, MAJOR=2, SEVERE=3)."""

    @property
    def sample_count(self) -> int:
        """Return number of samples."""
        return len(self.case_ids)

    @property
    def feature_count(self) -> int:
        """Return number of features."""
        return len(self.feature_names)


def _check_leakage(feature_names: Sequence[str]) -> None:
    """Raise MLDataLeakageError if any target metric is in feature names."""
    contaminated = set(feature_names) & TARGET_METRIC_NAMES
    if contaminated:
        raise MLDataLeakageError(
            f"Observation-derived target metrics detected in ML feature names: "
            f"{sorted(contaminated)}. Target metrics must never enter predictors."
        )


def _severity_to_code(severity: SeverityLevel) -> int:
    """Map SeverityLevel to integer code."""
    mapping = {
        SeverityLevel.NORMAL: 0,
        SeverityLevel.DEGRADED: 1,
        SeverityLevel.MAJOR: 2,
        SeverityLevel.SEVERE: 3,
        SeverityLevel.UNDEFINED: -1,
    }
    return mapping.get(severity, -1)


def extract_ml_dataset(
    samples: Sequence[AssembledSample],
    *,
    feature_names: Optional[Sequence[str]] = None,
    bust_threshold: Optional[float] = None,
    bust_severities: Optional[Set[SeverityLevel]] = None,
    require_trainable: bool = True,
) -> MLDataset:
    """Extract an MLDataset from a collection of AssembledSample objects.

    Parameters
    ----------
    samples : Sequence[AssembledSample]
        Input assembled tabular samples.
    feature_names : Optional[Sequence[str]]
        Explicit ordered list of predictor names. If None, inferred from the
        first sample with predictors.
    bust_threshold : Optional[float]
        Continuous error threshold defining a bust (error >= threshold -> 1).
    bust_severities : Optional[Set[SeverityLevel]]
        Set of severity levels defining a bust (e.g. {MAJOR, SEVERE}).
        Used if bust_threshold is None.
    require_trainable : bool
        If True, only samples with sample_status == VALID_TRAINABLE are included.
        If False, any sample with predictors is included.
    """
    if not samples:
        return MLDataset(
            X=np.empty((0, 0), dtype=np.float64),
            feature_names=[] if feature_names is None else list(feature_names),
            case_ids=[],
            initialization_times=[],
            lead_hours=[],
            continuous_targets=np.empty((0,), dtype=np.float64),
            binary_targets=np.empty((0,), dtype=np.int32),
            severity_targets=[],
            severity_codes=np.empty((0,), dtype=np.int32),
        )

    # Filter samples
    if require_trainable:
        selected_samples = [s for s in samples if s.is_trainable()]
    else:
        selected_samples = [s for s in samples if s.has_predictors()]

    if not selected_samples:
        names = [] if feature_names is None else list(feature_names)
        return MLDataset(
            X=np.empty((0, len(names)), dtype=np.float64),
            feature_names=names,
            case_ids=[],
            initialization_times=[],
            lead_hours=[],
            continuous_targets=np.empty((0,), dtype=np.float64),
            binary_targets=np.empty((0,), dtype=np.int32),
            severity_targets=[],
            severity_codes=np.empty((0,), dtype=np.int32),
        )

    # Determine canonical feature names
    if feature_names is None:
        first_with_preds = next((s for s in selected_samples if s.predictor_names), None)
        if first_with_preds:
            canonical_names = list(first_with_preds.predictor_names)
        else:
            all_keys = set()
            for s in selected_samples:
                all_keys.update(s.predictor_dict.keys())
            canonical_names = sorted(all_keys)
    else:
        canonical_names = list(feature_names)

    # Enforce leakage guardrail
    _check_leakage(canonical_names)

    # Build feature matrix and targets
    n_samples = len(selected_samples)
    n_features = len(canonical_names)
    X = np.full((n_samples, n_features), np.nan, dtype=np.float64)

    case_ids: List[str] = []
    init_times: List[Optional[datetime]] = []
    lead_hours: List[Optional[int]] = []
    continuous_targets: List[float] = []
    severity_targets: List[SeverityLevel] = []
    severity_codes: List[int] = []

    for i, sample in enumerate(selected_samples):
        case_ids.append(sample.case_id)
        init_times.append(sample.forecast_initialization_time)
        lead_hours.append(sample.forecast_lead_hours)
        continuous_targets.append(
            sample.continuous_error if sample.continuous_error is not None else np.nan
        )
        severity_targets.append(sample.severity)
        severity_codes.append(_severity_to_code(sample.severity))

        for j, fname in enumerate(canonical_names):
            val = sample.predictor_dict.get(fname)
            if val is not None:
                X[i, j] = float(val)

    y_continuous = np.asarray(continuous_targets, dtype=np.float64)
    y_severity_codes = np.asarray(severity_codes, dtype=np.int32)

    # Binary bust target construction
    binary_targets: Optional[np.ndarray] = None
    if bust_threshold is not None:
        valid_mask = np.isfinite(y_continuous)
        binary = np.zeros(n_samples, dtype=np.int32)
        binary[valid_mask & (y_continuous >= bust_threshold)] = 1
        binary_targets = binary
    elif bust_severities is not None:
        binary_targets = np.array(
            [1 if s in bust_severities else 0 for s in severity_targets],
            dtype=np.int32,
        )
    else:
        # Default operational bust: MAJOR or SEVERE
        default_bust_set = {SeverityLevel.MAJOR, SeverityLevel.SEVERE}
        binary_targets = np.array(
            [1 if s in default_bust_set else 0 for s in severity_targets],
            dtype=np.int32,
        )

    return MLDataset(
        X=X,
        feature_names=canonical_names,
        case_ids=case_ids,
        initialization_times=init_times,
        lead_hours=lead_hours,
        continuous_targets=y_continuous,
        binary_targets=binary_targets,
        severity_targets=severity_targets,
        severity_codes=y_severity_codes,
    )


class FeaturePreprocessor:
    """Leakage-safe feature preprocessor with imputation and standardization.

    Must be fitted exclusively on the training partition.
    """

    def __init__(self, with_scaling: bool = True) -> None:
        self.with_scaling = with_scaling
        self.imputer = SimpleImputer(strategy="median")
        self.scaler = StandardScaler() if with_scaling else None
        self.is_fitted = False
        self.feature_names: List[str] = []

    def fit(self, X: np.ndarray, feature_names: Optional[List[str]] = None) -> "FeaturePreprocessor":
        """Fit imputer and scaler on training features."""
        if X.shape[0] == 0:
            raise MLDataError("Cannot fit preprocessor on an empty array.")
        self.imputer.fit(X)
        X_imp = self.imputer.transform(X)
        if self.scaler is not None:
            self.scaler.fit(X_imp)
        self.is_fitted = True
        self.feature_names = list(feature_names) if feature_names else []
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        """Transform features using parameters learned on training data."""
        if not self.is_fitted:
            raise MLDataError("Preprocessor must be fitted before transforming data.")
        if X.shape[0] == 0:
            return np.empty((0, len(self.feature_names)), dtype=np.float64)
        X_imp = self.imputer.transform(X)
        if self.scaler is not None:
            return self.scaler.transform(X_imp)
        return X_imp

    def fit_transform(
        self, X: np.ndarray, feature_names: Optional[List[str]] = None
    ) -> np.ndarray:
        """Fit and transform training features."""
        return self.fit(X, feature_names).transform(X)
