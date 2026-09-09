"""ForecastGuard Machine Learning and Calibration Layer (Milestone M4).

Exports:
- Baseline Models: ClimatologyBaseline, SpreadOnlyBaseline, CalibratedLogisticModel,
  TreeBustModel, ContinuousErrorRegressor, BustSeverityClassifier
- Data Pipeline: MLDataset, extract_ml_dataset, FeaturePreprocessor, MLDataLeakageError
- Evaluation: evaluate_probabilistic_bust_forecast, EvaluationMetrics,
  compute_expected_calibration_error, compute_recall_at_alert_rates
- Experiments: ExperimentArtifact, run_probabilistic_bust_experiment
"""

from scientific.ml.data import (
    FeaturePreprocessor,
    MLDataError,
    MLDataLeakageError,
    MLDataset,
    extract_ml_dataset,
)
from scientific.ml.experiments import (
    ExperimentArtifact,
    run_probabilistic_bust_experiment,
)
from scientific.ml.metrics import (
    EvaluationMetrics,
    compute_expected_calibration_error,
    compute_recall_at_alert_rates,
    evaluate_probabilistic_bust_forecast,
)
from scientific.ml.models import (
    BaseBustModel,
    BustSeverityClassifier,
    CalibratedLogisticModel,
    ClimatologyBaseline,
    ContinuousErrorRegressor,
    ModelError,
    SpreadOnlyBaseline,
    TreeBustModel,
)
from scientific.ml.novelty import (
    NoveltyAssessment,
    NoveltyDetector,
    RepresentationState,
    novelty_detector,
)
from scientific.ml.multimodel import (
    ModelForecastFix,
    MultiModelAgreementEngine,
    MultiModelAgreementResult,
    MultiModelAgreementState,
    NWPModelAuditEntry,
    NWPModelStatus,
    NWP_DATA_AUDIT_CATALOG,
    multimodel_engine,
)

__all__ = [
    # Models
    "BaseBustModel",
    "ClimatologyBaseline",
    "SpreadOnlyBaseline",
    "CalibratedLogisticModel",
    "TreeBustModel",
    "ContinuousErrorRegressor",
    "BustSeverityClassifier",
    "ModelError",
    # Novelty & Abstention
    "NoveltyAssessment",
    "NoveltyDetector",
    "RepresentationState",
    "novelty_detector",
    # Multi-Model Agreement
    "MultiModelAgreementState",
    "NWPModelStatus",
    "NWPModelAuditEntry",
    "ModelForecastFix",
    "MultiModelAgreementResult",
    "MultiModelAgreementEngine",
    "multimodel_engine",
    "NWP_DATA_AUDIT_CATALOG",
    # Data
    "MLDataset",
    "extract_ml_dataset",
    "FeaturePreprocessor",
    "MLDataError",
    "MLDataLeakageError",
    # Metrics
    "EvaluationMetrics",
    "evaluate_probabilistic_bust_forecast",
    "compute_expected_calibration_error",
    "compute_recall_at_alert_rates",
    # Experiments
    "ExperimentArtifact",
    "run_probabilistic_bust_experiment",
]
