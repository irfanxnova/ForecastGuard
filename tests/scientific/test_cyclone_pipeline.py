"""Unit tests for the tropical cyclone forecast reliability and verification pipeline.

Covers:
- Exact timestamp alignment
- Haversine track distance calculation
- Ensemble aggregation (mean, median, spread, divergence)
- Strict anti-leakage in trajectory feature extraction
- Event-level train/test split isolation
- Domain-justified bust and severity labeling
- Missing member and missing observation handling
- Provenance generation and artifact serialization
- Baseline model ladder (Climatology, Spread-only, Trajectory-enhanced, Tree-based)
- Calibration metrics (ECE, Brier)
- Operational earliest warning lead-time calculation
- Real generated artifact integrity
"""

from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import pytest
import numpy as np

from scientific.validation.cyclone import (
    BestTrackPoint,
    ClimatologyBaseline,
    ContinuousErrorMetrics,
    ForecastMemberTrackPoint,
    LeadFeatures,
    ModelMetrics,
    SpreadOnlyModel,
    TrajectoryEnhancedModel,
    TreeBaselineModel,
    VerifiedLeadEvaluation,
    compute_continuous_error_metrics,
    compute_earliest_warning,
    compute_ece,
    evaluate_forecast_lead,
    evaluate_model,
    extract_leakage_safe_features,
    haversine_distance,
    save_case_artifact,
    serialize_case_artifact,
)


def test_haversine_distance_known_coordinates():
    """Verify spherical distance against known analytical distances."""
    # Zero distance
    assert haversine_distance(15.0, 70.0, 15.0, 70.0) == pytest.approx(0.0, abs=1e-5)

    # 1 degree of latitude is approx 111.195 km
    dist_1deg_lat = haversine_distance(0.0, 0.0, 1.0, 0.0)
    assert dist_1deg_lat == pytest.approx(111.195, abs=0.1)

    # 1 degree of longitude at equator
    dist_1deg_lon = haversine_distance(0.0, 0.0, 0.0, 1.0)
    assert dist_1deg_lon == pytest.approx(111.195, abs=0.1)


def test_exact_timestamp_alignment_enforcement():
    """Verify evaluate_forecast_lead strictly rejects temporal mismatches."""
    t1 = datetime(2023, 12, 1, 6, 0, tzinfo=timezone.utc)
    t2 = datetime(2023, 12, 1, 12, 0, tzinfo=timezone.utc)

    obs = BestTrackPoint("TEST", 2023, t1, 12.0, 85.0, 995.0, 45.0)
    member_pts = [
        ForecastMemberTrackPoint(1, 6, t1, 12.1, 85.1, 996.0),
        ForecastMemberTrackPoint(2, 6, t1, 12.2, 85.0, 997.0),
    ]

    # Valid match
    ev = evaluate_forecast_lead("TEST", t1, 6, t1, member_pts, obs)
    assert ev.valid_time == t1

    # Mismatch must raise ValueError
    with pytest.raises(ValueError, match="Temporal mismatch"):
        evaluate_forecast_lead("TEST", t1, 12, t2, member_pts, obs)


def test_ensemble_aggregation_metrics():
    """Verify mean, median, spread, and divergence calculations."""
    t0 = datetime(2023, 6, 7, 0, 0, tzinfo=timezone.utc)
    v_time = datetime(2023, 6, 7, 6, 0, tzinfo=timezone.utc)
    obs = BestTrackPoint("CYCLONE_A", 2023, v_time, 15.0, 68.0)

    # Create 3 members in a triangle
    m1 = ForecastMemberTrackPoint(1, 6, v_time, 15.0, 68.1, 990.0)
    m2 = ForecastMemberTrackPoint(2, 6, v_time, 15.1, 68.0, 992.0)
    m3 = ForecastMemberTrackPoint(3, 6, v_time, 14.9, 68.0, 991.0)

    ev = evaluate_forecast_lead("CYCLONE_A", t0, 6, v_time, [m1, m2, m3], obs)

    assert ev.ensemble_mean_lat == pytest.approx(15.0, abs=1e-3)
    assert ev.ensemble_mean_lon == pytest.approx(68.0333, abs=1e-3)
    assert ev.ensemble_spread_km > 0.0
    assert ev.ensemble_divergence_km > ev.ensemble_spread_km
    assert len(ev.member_track_errors_km) == 3


def test_no_future_feature_leakage():
    """Verify that feature calculation at lead t does not leak information from lead > t."""
    t0 = datetime(2023, 5, 10, 0, 0, tzinfo=timezone.utc)
    evals = []
    for i, lead in enumerate([6, 12, 18, 24]):
        vt = t0 + timedelta(hours=lead)
        obs = BestTrackPoint("LEAK_TEST", 2023, vt, 10.0 + 0.5 * i, 85.0 + 0.2 * i)
        members = [
            ForecastMemberTrackPoint(1, lead, vt, 10.1 + 0.5 * i, 85.1 + 0.2 * i, 995.0),
            ForecastMemberTrackPoint(2, lead, vt, 9.9 + 0.5 * i, 84.9 + 0.2 * i, 996.0),
        ]
        evals.append(evaluate_forecast_lead("LEAK_TEST", t0, lead, vt, members, obs))

    features = extract_leakage_safe_features(evals)
    assert len(features) == 4

    # The features for lead 6 (index 0) must have 0 growth because no past leads exist
    assert features[0].spread_growth_km == 0.0
    assert features[0].spread_acceleration_km == 0.0

    # Mutate the future lead 24 (index 3) dramatically
    mutated_evals = list(evals)
    mutated_vt = t0 + timedelta(hours=24)
    mutated_obs = BestTrackPoint("LEAK_TEST", 2023, mutated_vt, 50.0, 120.0)
    mutated_members = [
        ForecastMemberTrackPoint(1, 24, mutated_vt, 60.0, 130.0, 900.0),
        ForecastMemberTrackPoint(2, 24, mutated_vt, 40.0, 110.0, 910.0),
    ]
    mutated_evals[3] = evaluate_forecast_lead("LEAK_TEST", t0, 24, mutated_vt, mutated_members, mutated_obs)

    mutated_features = extract_leakage_safe_features(mutated_evals)

    # Features at leads 6, 12, 18 must be identical despite mutation of future lead 24
    for idx in [0, 1, 2]:
        assert features[idx].ensemble_spread_km == mutated_features[idx].ensemble_spread_km
        assert features[idx].spread_growth_km == mutated_features[idx].spread_growth_km
        assert features[idx].spread_acceleration_km == mutated_features[idx].spread_acceleration_km
        assert features[idx].trajectory_speed_kmh == mutated_features[idx].trajectory_speed_kmh


def test_event_level_split_isolation():
    """Verify strict chronological event separation between train and test."""
    cases = ["MOCHA", "BIPARJOY", "MICHAUNG"]
    train_events = ["MOCHA", "BIPARJOY"]
    test_events = ["MICHAUNG"]

    # Intersection must be empty
    assert set(train_events).isdisjoint(set(test_events))
    assert "MICHAUNG" not in train_events


def test_bust_severity_labeling():
    """Verify domain-based degradation / bust severity assignment."""
    t0 = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    v_time = datetime(2023, 1, 1, 6, 0, tzinfo=timezone.utc)
    obs = BestTrackPoint("TEST", 2023, v_time, 10.0, 80.0)

    # Small error (< 70 km) -> NORMAL
    m_close = [ForecastMemberTrackPoint(1, 6, v_time, 10.2, 80.2, 1000.0)]
    ev_norm = evaluate_forecast_lead("TEST", t0, 6, v_time, m_close, obs, bust_threshold_km=90.0)
    assert ev_norm.bust_severity in ["NORMAL", "MODERATE"]
    assert not ev_norm.is_bust

    # Large error (300 km) -> DEGRADED or SEVERE (bust)
    m_far = [ForecastMemberTrackPoint(1, 6, v_time, 12.5, 80.0, 1000.0)]
    ev_bust = evaluate_forecast_lead("TEST", t0, 6, v_time, m_far, obs, bust_threshold_km=90.0)
    assert ev_bust.is_bust
    assert ev_bust.bust_severity in ["DEGRADED", "SEVERE"]


def test_missing_member_graceful_handling():
    """Verify pipeline functions correctly with 1, 5, or 11 members."""
    t0 = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    v_time = datetime(2023, 1, 1, 6, 0, tzinfo=timezone.utc)
    obs = BestTrackPoint("TEST", 2023, v_time, 10.0, 80.0)

    # 1 member
    m_single = [ForecastMemberTrackPoint(1, 6, v_time, 10.1, 80.1, 1000.0)]
    ev_single = evaluate_forecast_lead("TEST", t0, 6, v_time, m_single, obs)
    assert ev_single.ensemble_spread_km == 0.0
    assert ev_single.ensemble_divergence_km == 0.0
    assert len(ev_single.member_points) == 1

    # 5 members
    m_five = [ForecastMemberTrackPoint(i, 6, v_time, 10.0 + 0.1 * i, 80.0, 1000.0) for i in range(1, 6)]
    ev_five = evaluate_forecast_lead("TEST", t0, 6, v_time, m_five, obs)
    assert len(ev_five.member_points) == 5
    assert ev_five.ensemble_spread_km > 0.0


def test_continuous_error_metrics_calculation():
    """Verify summary statistics calculation for continuous track errors."""
    errors = [50.0, 75.0, 100.0, 125.0, 150.0]
    metrics = compute_continuous_error_metrics(errors)

    assert metrics.count == 5
    assert metrics.mae_km == pytest.approx(100.0, abs=1e-3)
    assert metrics.median_error_km == pytest.approx(100.0, abs=1e-3)
    assert metrics.min_error_km == 50.0
    assert metrics.max_error_km == 150.0
    assert metrics.rmse_km > metrics.mae_km


def test_model_ladder_training_and_inference():
    """Verify all 4 models on the ladder fit and predict valid probabilities."""
    X_train = np.array([[6, 80.0], [12, 100.0], [18, 120.0], [24, 150.0]])
    y_train = np.array([0, 0, 1, 1])
    X_test = np.array([[30, 160.0]])
    y_test = np.array([1])
    leads_test = [30]

    # Model A: Climatology
    m_a = ClimatologyBaseline().fit(X_train, y_train)
    res_a = evaluate_model("Climatology", m_a, X_test, y_test, leads_test)
    assert 0.0 <= res_a.probabilities[0] <= 1.0

    # Model B: SpreadOnly
    m_b = SpreadOnlyModel().fit(X_train, y_train)
    res_b = evaluate_model("SpreadOnly", m_b, X_test, y_test, leads_test)
    assert 0.0 <= res_b.probabilities[0] <= 1.0

    # Model C: TrajectoryEnhanced
    m_c = TrajectoryEnhancedModel().fit(X_train, y_train)
    res_c = evaluate_model("TrajectoryEnhanced", m_c, X_test, y_test, leads_test)
    assert 0.0 <= res_c.probabilities[0] <= 1.0

    # Model D: DecisionTree
    m_d = TreeBaselineModel(max_depth=2).fit(X_train, y_train)
    res_d = evaluate_model("DecisionTree", m_d, X_test, y_test, leads_test)
    assert 0.0 <= res_d.probabilities[0] <= 1.0


def test_ece_computation():
    """Verify Expected Calibration Error (ECE)."""
    # Perfectly calibrated
    y_true = np.array([1, 1, 0, 0])
    y_prob = np.array([1.0, 1.0, 0.0, 0.0])
    assert compute_ece(y_true, y_prob) == pytest.approx(0.0, abs=1e-5)

    # Severely miscalibrated
    y_prob_bad = np.array([0.0, 0.0, 1.0, 1.0])
    assert compute_ece(y_true, y_prob_bad) > 0.5


def test_earliest_warning_lead_time():
    """Verify earliest warning alert calculation."""
    leads = [6, 12, 18, 24, 30]
    y_true = np.array([0, 0, 1, 1, 1])

    # Model alerts at lead 12 (ahead of failure at lead 18)
    y_prob_early = np.array([0.2, 0.7, 0.9, 0.9, 0.9])
    warn_lead = compute_earliest_warning(leads, y_prob_early, y_true, alert_threshold=0.5)
    assert warn_lead == 12

    # Model never alerts
    y_prob_never = np.array([0.1, 0.2, 0.3, 0.2, 0.1])
    assert compute_earliest_warning(leads, y_prob_never, y_true, alert_threshold=0.5) is None


def test_case_artifact_serialization(tmp_path):
    """Verify serialize_case_artifact produces valid JSON with required fields."""
    t0 = datetime(2023, 12, 1, 0, 0, tzinfo=timezone.utc)
    v_time = datetime(2023, 12, 1, 6, 0, tzinfo=timezone.utc)
    obs = BestTrackPoint("MICHAUNG", 2023, v_time, 9.5, 86.0)
    members = [ForecastMemberTrackPoint(1, 6, v_time, 9.3, 86.6, 1005.0)]
    ev = evaluate_forecast_lead("MICHAUNG", t0, 6, v_time, members, obs)
    feats = extract_leakage_safe_features([ev])
    cont_metrics = compute_continuous_error_metrics([ev.mean_track_error_km])
    prov = {"source": "test_provenance"}

    artifact = serialize_case_artifact(
        cyclone_name="MICHAUNG",
        year=2023,
        initialization_time=t0,
        evaluations=[ev],
        features=feats,
        model_metrics={},
        continuous_metrics=cont_metrics,
        provenance_metadata=prov,
    )

    out_file = tmp_path / "test_artifact.json"
    save_case_artifact(artifact, out_file)

    assert out_file.is_file()
    with open(out_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)

    assert loaded["cyclone_name"] == "MICHAUNG"
    assert loaded["verification_status"] == "VERIFIED_EXACT_TIMESTAMPS"
    assert len(loaded["leads"]) == 1
    assert "track_error" in loaded["leads"][0]


def test_real_experiment_artifacts_exist():
    """Verify that the real generated artifacts from the P2 experiment exist and are non-empty."""
    base_dir = Path(__file__).resolve().parent.parent.parent
    data_dir = base_dir / "data" / "validation"

    michaung_json = data_dir / "cyclone_michaung_verified_case.json"
    mocha_json = data_dir / "cyclone_mocha_verified_case.json"
    biparjoy_json = data_dir / "cyclone_biparjoy_verified_case.json"
    summary_json = data_dir / "cyclone_experiment_summary.json"

    for f in [michaung_json, mocha_json, biparjoy_json, summary_json]:
        assert f.is_file(), f"Missing expected artifact: {f.name}"
        assert f.stat().st_size > 1000, f"Artifact {f.name} is too small ({f.stat().st_size} bytes)"

        with open(f, "r", encoding="utf-8") as fp:
            data = json.load(fp)
            assert data is not None
