"""ForecastGuard probabilistic forecast-bust models.

Follows the controlled model ladder in ARCHITECTURE.md (Sections 124, 235–237):
- Model 0: ClimatologyBaseline (empirical training base rate)
- Model 1: SpreadOnlyBaseline (single-feature spread predictor)
- Model 1: CalibratedLogisticModel (regularized logistic regression with Platt scaling)
- Model 2: TreeBustModel (Random Forest probability classifier)
- Regressor: ContinuousErrorRegressor (continuous RMSE estimation)
- Multiclass: BustSeverityClassifier (ordinal severity probability distribution)

Non-negotiable scientific rules:
1. Probabilities are bounded in [0.0, 1.0].
2. Features must never contain observation-derived targets.
3. Feature importances reflect statistical association, NEVER causal claims.
4. Deterministic: random_state is explicitly controlled.
"""

from __future__ import annotations

import json
import pickle
import warnings
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, Ridge

from scientific.targets.rainfall import SeverityLevel, SeverityThresholds


class ModelError(Exception):
    """Raised when model configuration, training, or prediction fails."""


class BaseBustModel(ABC):
    """Abstract base class for all ForecastGuard bust prediction models."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self.is_fitted = False
        self.feature_names: List[str] = []

    @abstractmethod
    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: Optional[Sequence[str]] = None,
    ) -> "BaseBustModel":
        """Fit the model on training features X and binary labels y."""

    @abstractmethod
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Return calibrated probability of bust P(Bust=1) for each sample in X.

        Returns array of shape (n_samples,) with values in [0.0, 1.0].
        """

    def predict(self, X: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        """Return binary class predictions (0 or 1) at the given threshold."""
        prob = self.predict_proba(X)
        return (prob >= threshold).astype(np.int32)

    @abstractmethod
    def get_feature_importances(self) -> Dict[str, float]:
        """Return feature importance / coefficient weights dictionary."""

    def save(self, path: Union[str, Path], metadata: Optional[Dict[str, Any]] = None) -> None:
        """Serialize model artifact to disk."""
        target_path = Path(path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "model_name": self.model_name,
            "class_name": self.__class__.__name__,
            "is_fitted": self.is_fitted,
            "feature_names": self.feature_names,
            "model_instance": self,
            "metadata": metadata or {},
        }
        with open(target_path, "wb") as f:
            pickle.dump(payload, f, protocol=5)

    @classmethod
    def load(cls, path: Union[str, Path]) -> "BaseBustModel":
        """Load serialized model artifact from disk."""
        source_path = Path(path)
        if not source_path.exists():
            raise FileNotFoundError(f"Model file not found: {source_path}")
        with open(source_path, "rb") as f:
            payload = pickle.load(f)
        instance = payload["model_instance"]
        if not isinstance(instance, BaseBustModel):
            raise ModelError(f"Loaded object is not a BaseBustModel: {type(instance)}")
        return instance


# ---------------------------------------------------------------------------
# Model 0: Climatology Baseline
# ---------------------------------------------------------------------------


class ClimatologyBaseline(BaseBustModel):
    """Model 0: Predicts the empirical base rate from the training split.

    Serves as the reference baseline for Brier Skill Score calculation.
    """

    def __init__(self) -> None:
        super().__init__(model_name="Model 0 — Climatology Baseline")
        self.climatology_prob = 0.0

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: Optional[Sequence[str]] = None,
    ) -> "ClimatologyBaseline":
        if len(y) == 0:
            raise ModelError("Cannot fit ClimatologyBaseline on an empty target vector.")
        self.climatology_prob = float(np.mean(y == 1))
        self.feature_names = list(feature_names) if feature_names else []
        self.is_fitted = True
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise ModelError("Model must be fitted before predict_proba().")
        n_samples = X.shape[0]
        return np.full(n_samples, self.climatology_prob, dtype=np.float64)

    def get_feature_importances(self) -> Dict[str, float]:
        return {}


# ---------------------------------------------------------------------------
# Model 1a: Spread-Only Baseline
# ---------------------------------------------------------------------------


class SpreadOnlyBaseline(BaseBustModel):
    """Model 1a: Single-predictor logistic model using ensemble spread.

    Evaluates whether raw ensemble spread alone reliably predicts bust risk.
    """

    def __init__(
        self,
        spread_feature_name: str = "ensemble_std_mean",
        random_state: int = 42,
    ) -> None:
        super().__init__(model_name="Model 1a — Spread-Only Baseline")
        self.spread_feature_name = spread_feature_name
        self.random_state = random_state
        self.classifier = LogisticRegression(random_state=random_state)
        self.spread_feature_index: Optional[int] = None

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: Optional[Sequence[str]] = None,
    ) -> "SpreadOnlyBaseline":
        if len(y) == 0:
            raise ModelError("Cannot fit SpreadOnlyBaseline on empty target vector.")
        self.feature_names = list(feature_names) if feature_names else []

        # Find spread feature column
        if self.feature_names and self.spread_feature_name in self.feature_names:
            self.spread_feature_index = self.feature_names.index(self.spread_feature_name)
        elif self.feature_names:
            # Fallback to any feature containing 'std' or column 0
            matching = [
                i for i, name in enumerate(self.feature_names) if "std" in name.lower()
            ]
            self.spread_feature_index = matching[0] if matching else 0
        else:
            self.spread_feature_index = 0

        X_spread = X[:, self.spread_feature_index : self.spread_feature_index + 1]

        # Fit single-variable logistic regression if both classes present
        unique_classes = np.unique(y)
        if len(unique_classes) > 1:
            self.classifier.fit(X_spread, y)
        else:
            # Single class fallback
            self.classifier = None
            self._single_class_prob = float(unique_classes[0])

        self.is_fitted = True
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise ModelError("Model must be fitted before predict_proba().")
        if X.shape[0] == 0:
            return np.empty((0,), dtype=np.float64)

        if self.classifier is None:
            return np.full(X.shape[0], self._single_class_prob, dtype=np.float64)

        X_spread = X[:, self.spread_feature_index : self.spread_feature_index + 1]
        probs = self.classifier.predict_proba(X_spread)[:, 1]
        return np.clip(probs, 0.0, 1.0)

    def get_feature_importances(self) -> Dict[str, float]:
        fname = (
            self.feature_names[self.spread_feature_index]
            if self.feature_names and self.spread_feature_index is not None
            else self.spread_feature_name
        )
        if self.classifier is not None and hasattr(self.classifier, "coef_"):
            weight = float(self.classifier.coef_[0][0])
            return {fname: weight}
        return {fname: 0.0}


# ---------------------------------------------------------------------------
# Model 1b: Calibrated Logistic Regression
# ---------------------------------------------------------------------------


class CalibratedLogisticModel(BaseBustModel):
    """Model 1b: Regularized Logistic Regression with Platt Scaling calibration.

    Features are expected to be preprocessed (imputed and scaled).
    Outputs well-calibrated probabilities P(Bust=1) in [0.0, 1.0].
    """

    def __init__(
        self,
        C: float = 1.0,
        calibration_method: str = "sigmoid",
        cv: int = 3,
        random_state: int = 42,
    ) -> None:
        super().__init__(model_name="Model 1b — Calibrated Logistic Regression")
        self.C = C
        self.calibration_method = calibration_method
        self.cv = cv
        self.random_state = random_state
        self.base_classifier = LogisticRegression(
            C=C,
            penalty="l2",
            solver="lbfgs",
            max_iter=1000,
            random_state=random_state,
        )
        self.calibrated_classifier: Optional[Any] = None
        self._single_class_prob: Optional[float] = None

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: Optional[Sequence[str]] = None,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
    ) -> "CalibratedLogisticModel":
        if len(y) == 0:
            raise ModelError("Cannot fit CalibratedLogisticModel on empty data.")
        self.feature_names = list(feature_names) if feature_names else []

        unique_classes = np.unique(y)
        if len(unique_classes) < 2:
            self.calibrated_classifier = None
            self._single_class_prob = float(unique_classes[0])
            self.is_fitted = True
            return self

        # Fit base model
        self.base_classifier.fit(X, y)

        if X_val is not None and y_val is not None and len(np.unique(y_val)) > 1:
            # Prefit calibration on hold-out validation partition
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message=".*prefit.*")
                self.calibrated_classifier = CalibratedClassifierCV(
                    estimator=self.base_classifier,
                    method=self.calibration_method,
                    cv="prefit",
                )
                self.calibrated_classifier.fit(X_val, y_val)
        else:
            # K-fold cross-validated calibration on training set
            min_class_count = int(np.min(np.bincount(y)))
            folds = min(self.cv, min_class_count)
            if folds >= 2:
                self.calibrated_classifier = CalibratedClassifierCV(
                    estimator=self.base_classifier,
                    method=self.calibration_method,
                    cv=folds,
                )
                self.calibrated_classifier.fit(X, y)
            else:
                self.calibrated_classifier = self.base_classifier

        self.is_fitted = True
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise ModelError("Model must be fitted before predict_proba().")
        if X.shape[0] == 0:
            return np.empty((0,), dtype=np.float64)

        if self._single_class_prob is not None:
            return np.full(X.shape[0], self._single_class_prob, dtype=np.float64)

        probs = self.calibrated_classifier.predict_proba(X)[:, 1]
        return np.clip(probs, 0.0, 1.0)

    def get_feature_importances(self) -> Dict[str, float]:
        """Return standardized logistic regression weights.

        WARNING: Regression weights indicate statistical association within the
        fitted model. They do NOT imply causal influence.
        """
        if not hasattr(self.base_classifier, "coef_"):
            return {}

        coefs = self.base_classifier.coef_[0]
        names = (
            self.feature_names
            if len(self.feature_names) == len(coefs)
            else [f"feature_{i}" for i in range(len(coefs))]
        )
        return {name: float(w) for name, w in zip(names, coefs)}


# ---------------------------------------------------------------------------
# Model 2: Tree-Based Bust Classifier
# ---------------------------------------------------------------------------


class TreeBustModel(BaseBustModel):
    """Model 2: Random Forest probabilistic bust classifier.

    Captures non-linear feature interactions among ensemble metrics.
    """

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int = 4,
        random_state: int = 42,
    ) -> None:
        super().__init__(model_name="Model 2 — Random Forest Bust Model")
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.random_state = random_state
        self.classifier = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_leaf=2,
            random_state=random_state,
        )
        self._single_class_prob: Optional[float] = None

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: Optional[Sequence[str]] = None,
    ) -> "TreeBustModel":
        if len(y) == 0:
            raise ModelError("Cannot fit TreeBustModel on empty data.")
        self.feature_names = list(feature_names) if feature_names else []

        unique_classes = np.unique(y)
        if len(unique_classes) < 2:
            self._single_class_prob = float(unique_classes[0])
            self.is_fitted = True
            return self

        self.classifier.fit(X, y)
        self.is_fitted = True
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise ModelError("Model must be fitted before predict_proba().")
        if X.shape[0] == 0:
            return np.empty((0,), dtype=np.float64)

        if self._single_class_prob is not None:
            return np.full(X.shape[0], self._single_class_prob, dtype=np.float64)

        probs = self.classifier.predict_proba(X)[:, 1]
        return np.clip(probs, 0.0, 1.0)

    def get_feature_importances(self) -> Dict[str, float]:
        if not self.is_fitted or self._single_class_prob is not None:
            return {}
        importances = self.classifier.feature_importances_
        names = (
            self.feature_names
            if len(self.feature_names) == len(importances)
            else [f"feature_{i}" for i in range(len(importances))]
        )
        return {name: float(imp) for name, imp in zip(names, importances)}


# ---------------------------------------------------------------------------
# Continuous Error Regressor
# ---------------------------------------------------------------------------


class ContinuousErrorRegressor:
    """Predicts continuous expected error (RMSE in mm).

    Can also map predicted continuous error into ordinal SeverityLevel.
    """

    def __init__(
        self,
        alpha: float = 1.0,
        random_state: int = 42,
    ) -> None:
        self.model_name = "Ridge Error Regressor"
        self.alpha = alpha
        self.random_state = random_state
        self.regressor = Ridge(alpha=alpha, random_state=random_state)
        self.is_fitted = False
        self.feature_names: List[str] = []

    def fit(
        self,
        X: np.ndarray,
        y_continuous: np.ndarray,
        feature_names: Optional[Sequence[str]] = None,
    ) -> "ContinuousErrorRegressor":
        if len(y_continuous) == 0:
            raise ModelError("Cannot fit regressor on empty data.")
        valid = np.isfinite(y_continuous)
        if not np.any(valid):
            raise ModelError("All continuous targets are non-finite or missing.")

        self.regressor.fit(X[valid], y_continuous[valid])
        self.feature_names = list(feature_names) if feature_names else []
        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict expected continuous error (RMSE in mm)."""
        if not self.is_fitted:
            raise ModelError("Regressor must be fitted before predict().")
        if X.shape[0] == 0:
            return np.empty((0,), dtype=np.float64)
        pred = self.regressor.predict(X)
        # RMSE is physically non-negative
        return np.clip(pred, 0.0, None)

    def predict_severity(
        self,
        X: np.ndarray,
        thresholds: SeverityThresholds,
    ) -> List[SeverityLevel]:
        """Map predicted continuous error to ordinal SeverityLevel."""
        predictions = self.predict(X)
        return [thresholds.map(float(p)) for p in predictions]


# ---------------------------------------------------------------------------
# Ordinal / Multiclass Severity Classifier
# ---------------------------------------------------------------------------


class BustSeverityClassifier:
    """Predicts probability distribution across all 4 ordinal severity levels:

    [P(NORMAL), P(DEGRADED), P(MAJOR), P(SEVERE)]
    """

    SEVERITY_ORDER: Tuple[SeverityLevel, ...] = (
        SeverityLevel.NORMAL,
        SeverityLevel.DEGRADED,
        SeverityLevel.MAJOR,
        SeverityLevel.SEVERE,
    )

    def __init__(self, random_state: int = 42) -> None:
        self.model_name = "Multinomial Severity Classifier"
        self.random_state = random_state
        self.classifier = LogisticRegression(
            solver="lbfgs",
            max_iter=1000,
            random_state=random_state,
        )
        self.is_fitted = False
        self.classes_: List[int] = []
        self.feature_names: List[str] = []

    def fit(
        self,
        X: np.ndarray,
        severity_codes: np.ndarray,
        feature_names: Optional[Sequence[str]] = None,
    ) -> "BustSeverityClassifier":
        valid = severity_codes >= 0
        if not np.any(valid):
            raise ModelError("No valid severity codes to train classifier.")

        X_valid = X[valid]
        y_valid = severity_codes[valid]

        unique_classes = np.unique(y_valid)
        self.classes_ = list(unique_classes)
        self.feature_names = list(feature_names) if feature_names else []

        if len(unique_classes) > 1:
            self.classifier.fit(X_valid, y_valid)
        else:
            self.classifier = None
            self._single_class = int(unique_classes[0])

        self.is_fitted = True
        return self

    def predict_proba_severity(self, X: np.ndarray) -> np.ndarray:
        """Return probability matrix of shape (n_samples, 4)."""
        if not self.is_fitted:
            raise ModelError("Classifier must be fitted before predict.")
        n_samples = X.shape[0]
        full_probs = np.zeros((n_samples, 4), dtype=np.float64)

        if self.classifier is None:
            full_probs[:, self._single_class] = 1.0
            return full_probs

        probs = self.classifier.predict_proba(X)
        for idx, cls_code in enumerate(self.classifier.classes_):
            if 0 <= cls_code < 4:
                full_probs[:, cls_code] = probs[:, idx]

        return full_probs
