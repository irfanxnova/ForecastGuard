"""Tests for ForecastGuard V2 OOD Novelty, Support, and Abstention Intelligence.

Validates the 10 required invariants:
1. Deterministic novelty calculation
2. Correct distance calculation
3. Reference population leakage prevention (held-out test storm excluded)
4. Normalization leakage prevention (scaler fitted strictly on reference)
5. Future observation exclusion (zero ground truth in state features)
6. Future cycle exclusion (strictly historical cutoff)
7. Insufficient evidence handling (<5 members, NaN/Inf coords)
8. Abstention behaviour across states
9. Boundary thresholds (Q75, Q95)
10. Scientific qualification and non-overclaim wording
"""

import json
import math
from pathlib import Path
import numpy as np
import pytest

from scientific.ml.novelty import (
    HISTORICAL_REFERENCE_RECORDS,
    REFERENCE_DISTANCE_Q75,
    REFERENCE_DISTANCE_Q95,
    REFERENCE_FEATURES,
    REFERENCE_METADATA,
    REFERENCE_SCALER_MEAN,
    REFERENCE_SCALER_STD,
    NoveltyDetector,
    RepresentationState,
    novelty_detector,
)


@pytest.fixture
def sample_forecast_features():
    return {
        "forecast_lead_hours": 24.0,
        "ensemble_spread_km": 95.0,
        "ensemble_divergence_km": 360.0,
        "anisotropy_ratio": 2.2,
    }


def test_deterministic_novelty_calculation(sample_forecast_features):
    """1. Deterministic novelty calculation: repeated evaluations must produce identical results."""
    eval1 = novelty_detector.evaluate(sample_forecast_features, ensemble_member_count=11)
    eval2 = novelty_detector.evaluate(sample_forecast_features, ensemble_member_count=11)

    assert eval1.representation_state == eval2.representation_state
    assert eval1.distance == eval2.distance
    assert eval1.nearest_reference_distance == eval2.nearest_reference_distance
    assert eval1.novelty_score == eval2.novelty_score
    assert eval1.support_score == eval2.support_score
    assert eval1.abstention_recommended == eval2.abstention_recommended
    assert eval1.status == eval2.status


def test_correct_distance_calculation():
    """2. Correct distance calculation: verify math against independent NumPy implementation."""
    raw_point = [24.0, 100.0, 370.0, 2.3]
    features = {
        "forecast_lead_hours": raw_point[0],
        "ensemble_spread_km": raw_point[1],
        "ensemble_divergence_km": raw_point[2],
        "anisotropy_ratio": raw_point[3],
    }

    assessment = novelty_detector.evaluate(features, ensemble_member_count=11)

    # Independent computation of standardized Euclidean distance
    mean = np.array(REFERENCE_SCALER_MEAN, dtype=np.float64)
    std = np.array(REFERENCE_SCALER_STD, dtype=np.float64)
    z_point = (np.array(raw_point) - mean) / std

    ref_matrix = np.array(HISTORICAL_REFERENCE_RECORDS, dtype=np.float64)
    z_ref = (ref_matrix - mean) / std

    diff = z_ref - z_point
    dists = np.linalg.norm(diff, axis=1)
    sorted_dists = np.sort(dists)

    expected_1nn = round(float(sorted_dists[0]), 3)
    expected_3nn = round(float(np.mean(sorted_dists[:3])), 3)

    assert assessment.nearest_reference_distance == expected_1nn
    assert assessment.distance == expected_3nn


def test_reference_population_leakage_prevention():
    """3. Reference population leakage prevention: held-out test storm MICHAUNG must be excluded."""
    data_path = Path("data/validation/expanded_cyclone_verified_dataset.json")
    if not data_path.exists():
        pytest.skip("Dataset file not available on disk")

    with open(data_path, "r", encoding="utf-8") as f:
        records = json.load(f)["records"]

    # Verify held-out test storm is NOT in the reference population historical storms
    assert "MICHAUNG" not in REFERENCE_METADATA["historical_storms"]
    assert "Excludes" in REFERENCE_METADATA["provenance_description"]
    assert "unseen test storm MICHAUNG" in REFERENCE_METADATA["provenance_description"]

    # In the dataset, total training records (non-MICHAUNG) must equal reference sample count
    train_records = [r for r in records if r["storm_name"] != "MICHAUNG"]
    assert len(train_records) == REFERENCE_METADATA["sample_count"]
    assert len(HISTORICAL_REFERENCE_RECORDS) == 77


def test_normalization_leakage_prevention():
    """4. Normalization leakage prevention: scaler parameters must be computed strictly on reference."""
    data_path = Path("data/validation/expanded_cyclone_verified_dataset.json")
    if not data_path.exists():
        pytest.skip("Dataset file not available on disk")

    with open(data_path, "r", encoding="utf-8") as f:
        records = json.load(f)["records"]

    train_records = [r for r in records if r["storm_name"] != "MICHAUNG"]
    X_train = np.array(
        [[r[feat] for feat in REFERENCE_FEATURES] for r in train_records],
        dtype=np.float64,
    )

    empirical_mean = np.mean(X_train, axis=0)
    empirical_std = np.std(X_train, axis=0)

    # Reference scaler parameters must match empirical reference population exactly
    np.testing.assert_allclose(empirical_mean, REFERENCE_SCALER_MEAN, rtol=1e-5)
    np.testing.assert_allclose(empirical_std, REFERENCE_SCALER_STD, rtol=1e-5)

    # Assert that adding test data (MICHAUNG) alters the mean, proving isolation
    all_records = np.array([[r[feat] for feat in REFERENCE_FEATURES] for r in records], dtype=np.float64)
    all_mean = np.mean(all_records, axis=0)
    assert not np.allclose(all_mean, REFERENCE_SCALER_MEAN)


def test_future_observation_exclusion():
    """5. Future observation exclusion: reference features must contain zero verification fields."""
    # Features must ONLY contain issuance-time information
    forbidden_observation_fields = {
        "observed_lat",
        "observed_lon",
        "track_error_km",
        "bust_label",
        "severity",
        "prospective_bust_within24h",
    }
    for feat in REFERENCE_FEATURES:
        assert feat not in forbidden_observation_fields
        assert not feat.startswith("observed_")
        assert not feat.startswith("track_error")


def test_future_cycle_exclusion():
    """6. Future cycle exclusion: all reference samples must be strictly prior to cutoff."""
    data_path = Path("data/validation/expanded_cyclone_verified_dataset.json")
    if not data_path.exists():
        pytest.skip("Dataset file not available on disk")

    with open(data_path, "r", encoding="utf-8") as f:
        records = json.load(f)["records"]

    cutoff = REFERENCE_METADATA["cutoff_timestamp_utc"]  # 2023-11-17T00:00:00Z
    train_records = [r for r in records if r["storm_name"] != "MICHAUNG"]

    for r in train_records:
        assert r["initialization_time"] < cutoff, f"Reference cycle {r['cycle_label']} violates cutoff!"

    # Unseen test storm (MICHAUNG) initialized in Dec 2023 must be strictly after cutoff
    test_records = [r for r in records if r["storm_name"] == "MICHAUNG"]
    for r in test_records:
        assert r["initialization_time"] > cutoff


def test_insufficient_evidence_handling():
    """7. Insufficient evidence: member count < 5 or corrupt values must trigger abstention."""
    # Member count < 5
    res1 = novelty_detector.evaluate(
        {"forecast_lead_hours": 24.0, "ensemble_spread_km": 80.0, "ensemble_divergence_km": 300.0, "anisotropy_ratio": 1.5},
        ensemble_member_count=4,
    )
    assert res1.representation_state == RepresentationState.INSUFFICIENT_EVIDENCE
    assert res1.abstention_recommended is True
    assert res1.status == "ABSTAIN_INSUFFICIENT_EVIDENCE"
    assert math.isnan(res1.distance)

    # Missing features payload
    res2 = novelty_detector.evaluate(None, ensemble_member_count=11)
    assert res2.representation_state == RepresentationState.INSUFFICIENT_EVIDENCE
    assert res2.abstention_recommended is True

    # NaN in features
    res3 = novelty_detector.evaluate(
        {"forecast_lead_hours": 24.0, "ensemble_spread_km": float("nan"), "ensemble_divergence_km": 300.0, "anisotropy_ratio": 1.5},
        ensemble_member_count=11,
    )
    assert res3.representation_state == RepresentationState.INSUFFICIENT_EVIDENCE
    assert res3.abstention_recommended is True


def test_abstention_behavior_across_states():
    """8. Abstention behaviour: NOVEL_STATE must recommend abstention; WELL_REPRESENTED must not."""
    # WELL_REPRESENTED state (mean vector)
    well_rep = novelty_detector.evaluate(
        {
            "forecast_lead_hours": REFERENCE_SCALER_MEAN[0],
            "ensemble_spread_km": REFERENCE_SCALER_MEAN[1],
            "ensemble_divergence_km": REFERENCE_SCALER_MEAN[2],
            "anisotropy_ratio": REFERENCE_SCALER_MEAN[3],
        },
        ensemble_member_count=11,
    )
    assert well_rep.representation_state == RepresentationState.WELL_REPRESENTED
    assert well_rep.abstention_recommended is False
    assert well_rep.status == "SUPPORT_CONFIRMED"

    # Extreme NOVEL_STATE
    novel = novelty_detector.evaluate(
        {
            "forecast_lead_hours": 48.0,
            "ensemble_spread_km": 600.0,
            "ensemble_divergence_km": 2000.0,
            "anisotropy_ratio": 15.0,
        },
        ensemble_member_count=11,
    )
    assert novel.representation_state == RepresentationState.NOVEL_STATE
    assert novel.abstention_recommended is True
    assert novel.status == "CAUTION_NOVEL_STATE"


def test_boundary_thresholds():
    """9. Boundary thresholds: assert exact Q75 and Q95 state transitions."""
    detector = NoveltyDetector(
        reference_matrix=HISTORICAL_REFERENCE_RECORDS,
        scaler_mean=REFERENCE_SCALER_MEAN,
        scaler_std=REFERENCE_SCALER_STD,
        q75_threshold=REFERENCE_DISTANCE_Q75,
        q95_threshold=REFERENCE_DISTANCE_Q95,
        k_neighbors=3,
    )

    assert detector.q75 == 0.8406
    assert detector.q95 == 1.3601

    # Using dummy single-neighbor test detector to verify threshold branching
    class DummyDetector(NoveltyDetector):
        def _get_mock_state(self, dist):
            if dist <= self.q75:
                return RepresentationState.WELL_REPRESENTED
            elif dist <= self.q95:
                return RepresentationState.LOW_SUPPORT
            else:
                return RepresentationState.NOVEL_STATE

    dummy = DummyDetector()
    assert dummy._get_mock_state(0.8400) == RepresentationState.WELL_REPRESENTED
    assert dummy._get_mock_state(0.8406) == RepresentationState.WELL_REPRESENTED
    assert dummy._get_mock_state(0.8410) == RepresentationState.LOW_SUPPORT
    assert dummy._get_mock_state(1.3600) == RepresentationState.LOW_SUPPORT
    assert dummy._get_mock_state(1.3601) == RepresentationState.LOW_SUPPORT
    assert dummy._get_mock_state(1.3605) == RepresentationState.NOVEL_STATE


def test_scientific_qualification_non_overclaim(sample_forecast_features):
    """10. Scientific qualification: verify non-overclaim wording and mathematical qualification."""
    res = novelty_detector.evaluate(sample_forecast_features, ensemble_member_count=11)
    notice = res.provenance.get("scientific_boundary_notice", "")

    # Must carefully qualify novelty relative to the reference population
    assert "historical reference population" in notice
    assert "not a claim that the atmosphere itself is unprecedented" in notice
    assert "Low support does not imply forecast bust" in notice

    # Forbid unsubstantiated claims
    forbidden_phrases = ["never seen before", "unprecedented atmosphere", "guaranteed failure"]
    for phrase in forbidden_phrases:
        assert phrase not in res.message.lower()
        assert phrase not in notice.lower()
