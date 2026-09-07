"""Unit and integration tests for ForecastGuard ML layer (Milestone M4).

NOTE: Tests use synthetic test fixtures strictly to verify software mechanics,
contract enforcement, leakage rejection, and numeric bounds.
NO SCIENTIFIC PERFORMANCE OR ACCURACY CLAIMS ARE MADE FROM THESE TESTS.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional
import tempfile

import numpy as np
import pytest

from scientific.dataset.assembly import AssembledSample, SampleStatus
from scientific.dataset.splits import ChronologicalSplitter, SplitResult
from scientific.ml.data import (
    FeaturePreprocessor,
    MLDataError,
    MLDataLeakageError,
    extract_ml_dataset,
)
from scientific.ml.experiments import (
    ExperimentArtifact,
    run_probabilistic_bust_experiment,
)
from scientific.ml.metrics import (
    compute_expected_calibration_error,
    compute_recall_at_alert_rates,
    evaluate_probabilistic_bust_forecast,
)
from scientific.ml.models import (
    BustSeverityClassifier,
    CalibratedLogisticModel,
    ClimatologyBaseline,
    ContinuousErrorRegressor,
    ModelError,
    SpreadOnlyBaseline,
    TreeBustModel,
)
from scientific.targets.rainfall import RainfallTargetStatus, SeverityLevel, SeverityThresholds

UTC = timezone.utc


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------


def _dt(day_offset: int) -> datetime:
    """Generate a UTC datetime offset from 2025-09-01."""
    return datetime(2025, 9, 1, 0, 0, tzinfo=UTC) + timedelta(days=day_offset)


def _make_test_sample(
    case_id: str,
    init_time: datetime,
    rmse: float,
    spread: float = 2.0,
    severity: SeverityLevel = SeverityLevel.NORMAL,
    status: SampleStatus = SampleStatus.VALID_TRAINABLE,
    contaminated_feature: Optional[str] = None,
) -> AssembledSample:
    """Create a synthetic AssembledSample fixture for testing."""
    predictors = {
        "ensemble_mean_mean": 10.0,
        "ensemble_mean_std": 1.5,
        "ensemble_std_mean": spread,
        "ensemble_range_mean": spread * 3.0,
        "forecast_mean_spatial": 10.0,
    }
    if contaminated_feature:
        predictors[contaminated_feature] = 5.0

    return AssembledSample(
        case_id=case_id,
        sample_status=status,
        forecast_initialization_time=init_time,
        forecast_lead_hours=24,
        forecast_source_model="NCMRWF",
        ensemble_member_count=11,
        predictor_names=sorted(predictors.keys()),
        predictor_dict=predictors,
        target_status=RainfallTargetStatus.VALID,
        continuous_error=rmse,
        continuous_error_metric="rmse",
        severity=severity,
        target_dict={"rmse": rmse, "severity": severity.value},
    )


def _make_synthetic_sample_cohort(n_cycles: int = 10) -> List[AssembledSample]:
    """Generate a cohort of synthetic samples across distinct daily cycles."""
    samples = []
    for i in range(n_cycles):
        # Even cycles normal, odd cycles degraded/bust
        is_bust = (i % 2 == 1)
        rmse = 18.0 if is_bust else 4.0
        spread = 6.0 if is_bust else 1.5
        sev = SeverityLevel.MAJOR if is_bust else SeverityLevel.NORMAL
        samples.append(_make_test_sample(f"case_{i:03d}", _dt(i), rmse, spread, sev))
    return samples


# ---------------------------------------------------------------------------
# 1. MLData Tests (Extraction & Leakage)
# ---------------------------------------------------------------------------


class TestMLDataExtraction:
    """Tests data extraction and strict leakage prevention."""

    def test_extraction_dimensions_and_target_alignment(self):
        samples = _make_synthetic_sample_cohort(5)
        dataset = extract_ml_dataset(samples, bust_threshold=10.0)

        assert dataset.sample_count == 5
        assert dataset.feature_count == 5
        assert dataset.X.shape == (5, 5)
        assert len(dataset.continuous_targets) == 5
        assert len(dataset.binary_targets) == 5
        # Alternating 0 and 1
        assert np.array_equal(dataset.binary_targets, [0, 1, 0, 1, 0])

    def test_leakage_detection_raises_error(self):
        """Target metric names in predictors must immediately raise MLDataLeakageError."""
        leaky_sample = _make_test_sample(
            "leaky_001",
            _dt(0),
            rmse=5.0,
            contaminated_feature="mae",  # from TARGET_METRIC_NAMES
        )
        with pytest.raises(MLDataLeakageError, match="Target metrics must never enter predictors"):
            extract_ml_dataset([leaky_sample])

    def test_empty_input_produces_empty_dataset(self):
        dataset = extract_ml_dataset([])
        assert dataset.sample_count == 0
        assert dataset.feature_count == 0
        assert dataset.X.shape == (0, 0)

    def test_non_trainable_samples_filtered(self):
        valid = _make_test_sample("valid", _dt(0), 5.0)
        blocked = _make_test_sample(
            "blocked", _dt(1), 5.0, status=SampleStatus.BLOCKED
        )
        dataset = extract_ml_dataset([valid, blocked], require_trainable=True)
        assert dataset.sample_count == 1
        assert dataset.case_ids == ["valid"]

    def test_preprocessor_imputation_and_scaling(self):
        X_train = np.array([[1.0, 2.0], [np.nan, 4.0], [5.0, 6.0]])
        X_test = np.array([[np.nan, 2.0], [3.0, np.nan]])

        preprocessor = FeaturePreprocessor(with_scaling=True)
        X_train_trans = preprocessor.fit_transform(X_train)
        X_test_trans = preprocessor.transform(X_test)

        assert not np.isnan(X_train_trans).any()
        assert not np.isnan(X_test_trans).any()
        assert X_train_trans.shape == (3, 2)
        assert X_test_trans.shape == (2, 2)


# ---------------------------------------------------------------------------
# 2. Baseline Model Tests
# ---------------------------------------------------------------------------


class TestBaselineModels:
    """Tests Model 0, Model 1, Model 2 and Regressor."""

    def test_climatology_baseline_predicts_base_rate(self):
        X = np.ones((10, 3))
        y = np.array([0, 0, 0, 1, 1, 0, 0, 0, 0, 0])  # 20% base rate

        model = ClimatologyBaseline()
        model.fit(X, y)
        probs = model.predict_proba(X)

        assert np.allclose(probs, 0.2)
        assert np.all(probs >= 0.0) and np.all(probs <= 1.0)
        assert model.get_feature_importances() == {}

    def test_spread_only_baseline_probabilities(self):
        X = np.array([[1.0], [2.0], [5.0], [8.0], [9.0]])
        y = np.array([0, 0, 1, 1, 1])

        model = SpreadOnlyBaseline(spread_feature_name="feature_0")
        model.fit(X, y, feature_names=["feature_0"])
        probs = model.predict_proba(X)

        assert len(probs) == 5
        assert np.all(probs >= 0.0) and np.all(probs <= 1.0)
        # Higher spread should correlate with higher bust probability
        assert probs[-1] > probs[0]
        assert "feature_0" in model.get_feature_importances()

    def test_calibrated_logistic_probabilities_and_weights(self):
        X = np.array([[1.0, 0.5], [2.0, 0.6], [5.0, 1.2], [7.0, 2.0], [8.0, 2.5], [9.0, 3.0]])
        y = np.array([0, 0, 0, 1, 1, 1])

        model = CalibratedLogisticModel(random_state=42)
        model.fit(X, y, feature_names=["feat_a", "feat_b"])
        probs = model.predict_proba(X)

        assert len(probs) == 6
        assert np.all(probs >= 0.0) and np.all(probs <= 1.0)
        assert probs[-1] > probs[0]

        importances = model.get_feature_importances()
        assert "feat_a" in importances
        assert "feat_b" in importances

    def test_tree_bust_model_probabilistic_predictions(self):
        X = np.array([[1.0, 0.5], [2.0, 0.6], [5.0, 1.2], [7.0, 2.0], [8.0, 2.5], [9.0, 3.0]])
        y = np.array([0, 0, 0, 1, 1, 1])

        model = TreeBustModel(n_estimators=20, max_depth=2, random_state=42)
        model.fit(X, y, feature_names=["feat_a", "feat_b"])
        probs = model.predict_proba(X)

        assert len(probs) == 6
        assert np.all(probs >= 0.0) and np.all(probs <= 1.0)
        importances = model.get_feature_importances()
        assert sum(importances.values()) == pytest.approx(1.0)

    def test_continuous_error_regressor(self):
        X = np.array([[1.0], [2.0], [3.0], [4.0]])
        y_rmse = np.array([2.5, 4.8, 7.2, 9.5])

        reg = ContinuousErrorRegressor()
        reg.fit(X, y_rmse)
        preds = reg.predict(X)

        assert len(preds) == 4
        assert np.all(preds >= 0.0)  # RMSE physically non-negative
        assert preds[-1] > preds[0]

        thresholds = SeverityThresholds(t0=4.0, t1=7.0, t2=12.0)
        severities = reg.predict_severity(X, thresholds)
        assert severities[0] == SeverityLevel.NORMAL
        assert severities[-1] == SeverityLevel.MAJOR

    def test_bust_severity_multiclass_classifier(self):
        X = np.array([[1.0], [3.0], [6.0], [10.0]])
        # Codes: NORMAL=0, DEGRADED=1, MAJOR=2, SEVERE=3
        y_codes = np.array([0, 1, 2, 3])

        classifier = BustSeverityClassifier(random_state=42)
        classifier.fit(X, y_codes, feature_names=["feat"])
        probs = classifier.predict_proba_severity(X)

        assert probs.shape == (4, 4)
        assert np.allclose(np.sum(probs, axis=1), 1.0)
        assert np.all(probs >= 0.0) and np.all(probs <= 1.0)

    def test_single_class_fallback_safe(self):
        """When training data contains only 1 class, models must not crash."""
        X = np.ones((5, 2))
        y_all_zeros = np.zeros(5, dtype=int)

        logistic = CalibratedLogisticModel()
        logistic.fit(X, y_all_zeros)
        probs = logistic.predict_proba(X)
        assert np.allclose(probs, 0.0)

        tree = TreeBustModel()
        tree.fit(X, y_all_zeros)
        probs_tree = tree.predict_proba(X)
        assert np.allclose(probs_tree, 0.0)

    def test_model_serialization_and_loading(self, tmp_path):
        X = np.array([[1.0], [2.0], [5.0], [8.0]])
        y = np.array([0, 0, 1, 1])

        model = CalibratedLogisticModel(random_state=42)
        model.fit(X, y, feature_names=["feat"])

        model_path = tmp_path / "model.pkl"
        model.save(model_path, metadata={"test": "ok"})

        loaded = CalibratedLogisticModel.load(model_path)
        assert loaded.model_name == model.model_name
        assert loaded.is_fitted is True
        assert np.allclose(model.predict_proba(X), loaded.predict_proba(X))


# ---------------------------------------------------------------------------
# 3. Metrics Tests
# ---------------------------------------------------------------------------


class TestEvaluationMetrics:
    """Tests evaluation metrics, ECE, and alert rate calculation."""

    def test_evaluation_metrics_standard(self):
        y_true = [0, 0, 0, 1, 1, 1]
        y_prob = [0.1, 0.2, 0.4, 0.6, 0.8, 0.9]

        metrics = evaluate_probabilistic_bust_forecast(y_true, y_prob, climatology_prob=0.5)

        assert metrics.sample_count == 6
        assert metrics.positive_count == 3
        assert metrics.brier_score < 0.15
        assert metrics.brier_skill_score is not None
        assert metrics.brier_skill_score > 0.0  # better than climatology
        assert metrics.roc_auc == 1.0
        assert metrics.pr_auc == 1.0
        assert 0.0 <= metrics.expected_calibration_error <= 1.0

    def test_recall_at_alert_rates(self):
        y_true = np.array([0, 0, 0, 0, 0, 1, 1, 1, 1, 1])  # 5 busts out of 10
        y_prob = np.linspace(0.1, 1.0, 10)  # perfectly ranked

        alert_recall = compute_recall_at_alert_rates(y_true, y_prob, alert_rates=(0.20, 0.50))
        # Top 20% (top 2 samples): both are busts -> recall = 2/5 = 0.40
        assert alert_recall["top_20%"] == pytest.approx(0.40)
        # Top 50% (top 5 samples): all 5 are busts -> recall = 5/5 = 1.00
        assert alert_recall["top_50%"] == pytest.approx(1.00)

    def test_expected_calibration_error_bounds(self):
        y_true = np.array([1, 1, 0, 0])
        # Perfectly calibrated probabilities
        y_prob = np.array([1.0, 1.0, 0.0, 0.0])
        ece, curve = compute_expected_calibration_error(y_true, y_prob, n_bins=5)
        assert ece == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# 4. Experiment Orchestration Tests
# ---------------------------------------------------------------------------


class TestExperimentOrchestration:
    """Tests end-to-end experiment pipeline and constitutional guarantees."""

    def test_experiment_with_zero_samples_reports_no_scientific_data(self):
        """Constitutional guarantee: zero samples must report NO_SCIENTIFIC_TRAINING_DATA."""
        artifact = run_probabilistic_bust_experiment(
            samples_or_split=[],
            experiment_id="test_zero_cases",
        )
        assert artifact.status == "NO_SCIENTIFIC_TRAINING_DATA"
        assert artifact.training_sample_count == 0
        assert "no synthetic data" in artifact.scientific_disclaimer.lower()

    def test_experiment_end_to_end_software_smoke_test(self, tmp_path):
        """Verify pipeline execution mechanics using synthetic test fixtures.

        MARKER: Software mechanics validation only.
        """
        # Create 14 synthetic cycles to support a 3-way chronological split
        samples = _make_synthetic_sample_cohort(n_cycles=14)

        artifact = run_probabilistic_bust_experiment(
            samples_or_split=samples,
            experiment_id="software_smoke_test",
            model_type="calibrated_logistic",
            bust_threshold=10.0,
            purge_hours=0.0,  # no purge for compact test fixture
            output_dir=tmp_path,
        )

        assert artifact.status == "COMPLETED"
        assert artifact.training_sample_count > 0
        assert len(artifact.features_used) > 0
        assert artifact.metrics is not None
        assert (tmp_path / "software_smoke_test_artifact.json").exists()
        assert (tmp_path / "software_smoke_test_model.pkl").exists()

    def test_chronological_split_integrity_in_experiment(self):
        """Ensure training samples strictly precede validation/test samples."""
        samples = _make_synthetic_sample_cohort(n_cycles=10)
        splitter = ChronologicalSplitter(train_ratio=0.6, val_ratio=0.2, test_ratio=0.2)
        split = splitter.split(samples)

        max_train_time = max(s.forecast_initialization_time for s in split.train)
        min_val_time = min(s.forecast_initialization_time for s in split.validation)
        min_test_time = min(s.forecast_initialization_time for s in split.test)

        assert max_train_time < min_val_time
        assert min_val_time < min_test_time
