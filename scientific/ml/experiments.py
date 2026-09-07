"""End-to-end experiment orchestration and artifact generation for ForecastGuard ML.

Manages the workflow:
SplitResult (or AssembledSamples)
  -> MLDataset extraction
  -> Leakage-safe preprocessor fitting (train only)
  -> Model training (Climatology, Spread-only, Calibrated Logistic, Tree)
  -> Verification and calibration metrics computation
  -> Deterministic experiment artifact serialization.

Constitutional guarantee:
If zero valid trainable cases exist, reports "NO_SCIENTIFIC_TRAINING_DATA"
without fabricating predictions, labels, or performance scores.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

import numpy as np

from scientific.dataset.assembly import AssembledSample
from scientific.dataset.splits import ChronologicalSplitter, SplitResult
from scientific.ml.data import FeaturePreprocessor, MLDataset, extract_ml_dataset
from scientific.ml.metrics import evaluate_probabilistic_bust_forecast
from scientific.ml.models import (
    BaseBustModel,
    CalibratedLogisticModel,
    ClimatologyBaseline,
    SpreadOnlyBaseline,
    TreeBustModel,
)


@dataclass(frozen=True)
class ExperimentArtifact:
    """Audit-ready record of a complete machine-learning experiment."""

    experiment_id: str
    status: str  # "COMPLETED" or "NO_SCIENTIFIC_TRAINING_DATA"
    model_name: str
    features_used: List[str]
    target: str
    split_definition: Dict[str, Any]
    training_sample_count: int
    validation_sample_count: int
    test_sample_count: int
    metrics: Dict[str, Any]
    calibration_info: Dict[str, Any]
    feature_importances: Dict[str, float]
    scientific_disclaimer: str
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert artifact to dictionary."""
        return asdict(self)

    def to_json_file(self, path: Union[str, Path]) -> Path:
        """Write JSON artifact to file."""
        target_path = Path(path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        return target_path


def run_probabilistic_bust_experiment(
    samples_or_split: Union[Sequence[AssembledSample], SplitResult],
    *,
    experiment_id: str = "exp_bust_baseline",
    model_type: str = "calibrated_logistic",  # "logistic", "spread_only", "climatology", "tree"
    bust_threshold: Optional[float] = None,
    purge_hours: float = 24.0,
    random_state: int = 42,
    output_dir: Optional[Union[str, Path]] = None,
) -> ExperimentArtifact:
    """Run an end-to-end probabilistic bust detection experiment.

    Parameters
    ----------
    samples_or_split : Union[Sequence[AssembledSample], SplitResult]
        Either an existing SplitResult or a list of AssembledSample objects to split.
    experiment_id : str
        Identifier for this experiment run.
    model_type : str
        Algorithm to train ("climatology", "spread_only", "calibrated_logistic", "tree").
    bust_threshold : Optional[float]
        Continuous RMSE threshold in mm defining a bust. If None, uses severity labels.
    purge_hours : float
        Gap between chronological partitions (default 24h).
    random_state : int
        Seed for deterministic training.
    output_dir : Optional[Union[str, Path]]
        Optional directory to persist JSON artifact and model file.
    """
    # 1. Resolve chronological split
    if isinstance(samples_or_split, SplitResult):
        split = samples_or_split
    else:
        trainable_samples = [s for s in samples_or_split if s.is_trainable()]
        if not trainable_samples:
            artifact = ExperimentArtifact(
                experiment_id=experiment_id,
                status="NO_SCIENTIFIC_TRAINING_DATA",
                model_name=model_type,
                features_used=[],
                target=f"RMSE >= {bust_threshold}mm" if bust_threshold else "MAJOR/SEVERE",
                split_definition={"mode": "empty"},
                training_sample_count=0,
                validation_sample_count=0,
                test_sample_count=0,
                metrics={},
                calibration_info={},
                feature_importances={},
                scientific_disclaimer=(
                    "Zero valid real training cases currently exist in the dataset. "
                    "In strict accordance with the ForecastGuard Constitution (AGENTS.md), "
                    "no synthetic data or risk scores are presented as real scientific results."
                ),
            )
            if output_dir is not None:
                Path(output_dir).mkdir(parents=True, exist_ok=True)
                artifact.to_json_file(Path(output_dir) / f"{experiment_id}_artifact.json")
            return artifact
        try:
            splitter = ChronologicalSplitter(
                train_ratio=0.7,
                val_ratio=0.15,
                test_ratio=0.15,
                purge_hours=purge_hours,
            )
            split = splitter.split(trainable_samples)
        except Exception as exc:
            artifact = ExperimentArtifact(
                experiment_id=experiment_id,
                status="NO_SCIENTIFIC_TRAINING_DATA",
                model_name=model_type,
                features_used=[],
                target=f"RMSE >= {bust_threshold}mm" if bust_threshold else "MAJOR/SEVERE",
                split_definition={"error": str(exc)},
                training_sample_count=0,
                validation_sample_count=0,
                test_sample_count=0,
                metrics={},
                calibration_info={},
                feature_importances={},
                scientific_disclaimer=f"Chronological split could not be performed: {exc}",
            )
            if output_dir is not None:
                Path(output_dir).mkdir(parents=True, exist_ok=True)
                artifact.to_json_file(Path(output_dir) / f"{experiment_id}_artifact.json")
            return artifact

    # 2. Extract ML datasets per partition
    train_data = extract_ml_dataset(
        split.train,
        bust_threshold=bust_threshold,
        require_trainable=True,
    )
    val_data = extract_ml_dataset(
        split.validation,
        feature_names=train_data.feature_names,
        bust_threshold=bust_threshold,
        require_trainable=True,
    )
    test_data = extract_ml_dataset(
        split.test,
        feature_names=train_data.feature_names,
        bust_threshold=bust_threshold,
        require_trainable=True,
    )

    if train_data.sample_count == 0:
        return ExperimentArtifact(
            experiment_id=experiment_id,
            status="NO_SCIENTIFIC_TRAINING_DATA",
            model_name=model_type,
            features_used=[],
            target=f"RMSE >= {bust_threshold}mm" if bust_threshold else "MAJOR/SEVERE",
            split_definition=split.split_metadata,
            training_sample_count=0,
            validation_sample_count=val_data.sample_count,
            test_sample_count=test_data.sample_count,
            metrics={},
            calibration_info={},
            feature_importances={},
            scientific_disclaimer=(
                "Training partition contains 0 valid samples. "
                "No scientific model training was performed."
            ),
        )

    # 3. Fit preprocessor on training features only
    preprocessor = FeaturePreprocessor(with_scaling=True)
    X_train = preprocessor.fit_transform(train_data.X, train_data.feature_names)
    X_val = preprocessor.transform(val_data.X)
    X_test = preprocessor.transform(test_data.X)

    y_train = train_data.binary_targets
    y_val = val_data.binary_targets
    y_test = test_data.binary_targets

    # 4. Instantiate chosen model
    model: BaseBustModel
    if model_type == "climatology":
        model = ClimatologyBaseline()
        model.fit(X_train, y_train, feature_names=train_data.feature_names)
    elif model_type == "spread_only":
        model = SpreadOnlyBaseline(random_state=random_state)
        model.fit(X_train, y_train, feature_names=train_data.feature_names)
    elif model_type == "tree":
        model = TreeBustModel(random_state=random_state)
        model.fit(X_train, y_train, feature_names=train_data.feature_names)
    else:
        # Default: calibrated_logistic
        logistic = CalibratedLogisticModel(random_state=random_state)
        logistic.fit(
            X_train,
            y_train,
            feature_names=train_data.feature_names,
            X_val=X_val if val_data.sample_count > 0 else None,
            y_val=y_val if val_data.sample_count > 0 else None,
        )
        model = logistic

    # 5. Evaluate on test partition (or validation if test is empty)
    eval_X = X_test if test_data.sample_count > 0 else X_val
    eval_y = y_test if test_data.sample_count > 0 else y_val

    clim_ref = float(np.mean(y_train == 1))
    metrics_dict: Dict[str, Any] = {}
    calibration_info: Dict[str, Any] = {}

    if len(eval_y) > 0:
        y_prob = model.predict_proba(eval_X)
        eval_metrics = evaluate_probabilistic_bust_forecast(
            eval_y,
            y_prob,
            climatology_prob=clim_ref,
        )
        metrics_dict = eval_metrics.to_dict()
        calibration_info = eval_metrics.reliability_curve

    # 6. Extract feature importances
    importances = model.get_feature_importances()

    artifact = ExperimentArtifact(
        experiment_id=experiment_id,
        status="COMPLETED",
        model_name=model.model_name,
        features_used=train_data.feature_names,
        target=f"RMSE >= {bust_threshold}mm" if bust_threshold else "MAJOR/SEVERE",
        split_definition=split.split_metadata,
        training_sample_count=train_data.sample_count,
        validation_sample_count=val_data.sample_count,
        test_sample_count=test_data.sample_count,
        metrics=metrics_dict,
        calibration_info=calibration_info,
        feature_importances=importances,
        scientific_disclaimer=(
            "Trained and evaluated strictly with chronological separation. "
            "Feature weights indicate statistical association, not causal mechanisms."
        ),
    )

    if output_dir is not None:
        out_path = Path(output_dir)
        artifact.to_json_file(out_path / f"{experiment_id}_artifact.json")
        model.save(out_path / f"{experiment_id}_model.pkl")

    return artifact
