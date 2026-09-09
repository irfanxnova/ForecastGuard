"""Tests for Regional Probabilistic Calibration Engine.

Strictly verifies AGENTS.md requirements:
- Rule 2: Never fabricate machine-learning predictions, calibration, or scientific results.
- Rule 5: Preserve chronological train/validation/test separation.
- Rule 6: Every prediction must use only information available at forecast lead.
- Rule 10: Prefer simple models before complex models.
- Rule 11: No model is promoted unless validation shows measurable value over baseline.
"""

import pytest
import numpy as np

from scientific.ml.regional_calibration import (
    RegionalCalibrator,
    compute_ece,
    regional_calibrator,
)


def test_chronological_calibration_experiment_metrics():
    """Verify chronological train/test separation and calibration metrics."""
    results = regional_calibrator.evaluate_calibration_experiment()
    assert "train" in results
    assert "test" in results

    train = results["train"]
    test = results["test"]

    # Sample counts
    assert train.sample_count == 56
    assert test.sample_count == 45
    assert train.sample_count + test.sample_count == 101

    # Base rates
    assert 0.20 <= train.base_rate <= 0.25
    assert 0.20 <= test.base_rate <= 0.26

    # Test Brier Score Improvement on UNSEEN split
    assert test.post_calibration_brier < test.pre_calibration_brier
    assert test.brier_improvement_percent > 15.0  # ~18.3% improvement

    # Test Expected Calibration Error (ECE) reduction on UNSEEN split
    assert test.post_calibration_ece < 0.05
    assert test.post_calibration_ece < test.pre_calibration_ece

    # Model discrimination preserved
    assert test.roc_auc > 0.65


def test_platt_scaling_monotonicity_and_bounds():
    """Verify Platt scaling produces strictly monotonic, bounded probabilities."""
    scores = np.linspace(0.05, 0.95, 20)
    calibrated_probs = []

    for s in scores:
        prob = regional_calibrator.calibrate_score(
            raw_score=float(s),
            region_id="MAR_BOB",
            lead_hours=24,
            is_verified_case=True,
        )
        assert prob is not None
        assert 0.02 <= prob <= 0.98
        calibrated_probs.append(prob)

    # Strictly monotonic: higher raw score -> higher calibrated probability
    for i in range(len(calibrated_probs) - 1):
        assert calibrated_probs[i + 1] > calibrated_probs[i]


def test_calibrate_score_honesty_guards():
    """Verify calibrator refuses to calibrate unsupported regions or unverified cases."""
    # Unverified case -> None
    prob_unver = regional_calibrator.calibrate_score(
        raw_score=0.5,
        region_id="MAR_BOB",
        lead_hours=24,
        is_verified_case=False,
    )
    assert prob_unver is None

    # Unsupported region outside verified storm domain -> None
    prob_unsupported_reg = regional_calibrator.calibrate_score(
        raw_score=0.5,
        region_id="IND_NW",  # Northwest India has no verified cyclone center records
        lead_hours=24,
        is_verified_case=True,
    )
    assert prob_unsupported_reg is None

    # Unsupported lead hour (e.g. 120h / D+5) -> None
    prob_unsupported_lead = regional_calibrator.calibrate_score(
        raw_score=0.5,
        region_id="MAR_BOB",
        lead_hours=120,
        is_verified_case=True,
    )
    assert prob_unsupported_lead is None


def test_compute_ece_calculation():
    """Verify ECE calculation with known synthetic distributions."""
    # Perfectly calibrated predictions: pred == labels
    probs = np.array([0.1, 0.1, 0.9, 0.9])
    labels = np.array([0, 0, 1, 1])
    ece = compute_ece(probs, labels, n_bins=2)
    assert round(ece, 4) == 0.1

    # Completely uncalibrated: pred 0.99 for all 0s
    probs_bad = np.array([0.99, 0.99, 0.99, 0.99])
    labels_bad = np.array([0, 0, 0, 0])
    ece_bad = compute_ece(probs_bad, labels_bad, n_bins=2)
    assert ece_bad > 0.9
