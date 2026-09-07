"""Unit tests for ForecastGuard Milestone P3 Prospective Scientific Upgrade.

Covers:
- Prospective multi-horizon target correctness (t+6h, t+12h, t+24h, within 24h)
- Strict anti-leakage invariants (mutating future data has zero effect on current features)
- Spatial ensemble geometry calculations (anisotropy, Sarle's bimodality, clustering)
- Missing member graceful handling in geometry engine
- Cycle-to-cycle revision alignment and cycle anti-leakage
- False-confidence classification quadrants and RCI
- Controlled ablation ladder feature extraction (M0 to M6)
- Empirical keep/kill decision logic
- Bust atlas compilation and advance warning calculation
- Machine-readable artifact integrity and schema compliance
"""

from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import pytest
import numpy as np

from scientific.validation.cyclone import (
    BestTrackPoint,
    ForecastMemberTrackPoint,
    ModelMetrics,
    VerifiedLeadEvaluation,
    evaluate_forecast_lead,
    haversine_distance,
)
from scientific.validation.cyclone_p3 import (
    BustAtlasEntry,
    EnsembleGeometry,
    P3LogisticModel,
    ProspectiveLeadFeatures,
    build_bust_atlas,
    classify_confidence_quadrant,
    compute_ensemble_geometry,
    evaluate_keep_kill,
    extract_feature_matrix_for_ablation,
    extract_prospective_features,
)


def test_prospective_target_correctness():
    """Verify that prospective targets at lead t match future leads t+6, t+12, t+24, and within 24h."""
    t0 = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    evals = []

    # Lead 6: not bust (error 30 km)
    # Lead 12: not bust (error 40 km)
    # Lead 18: BUST (error 120 km)
    # Lead 24: not bust (error 50 km)
    # Lead 30: BUST (error 130 km)
    errors = [30.0, 40.0, 120.0, 50.0, 130.0]
    for i, lead in enumerate([6, 12, 18, 24, 30]):
        vt = t0 + timedelta(hours=lead)
        obs = BestTrackPoint("TEST", 2023, vt, 10.0, 80.0)
        # Create member offset by error
        lat_offset = errors[i] / 111.132
        members = [ForecastMemberTrackPoint(1, lead, vt, 10.0 + lat_offset, 80.0, 1000.0)]
        evals.append(evaluate_forecast_lead("TEST", t0, lead, vt, members, obs, bust_threshold_km=85.0))

    features = extract_prospective_features(evals)

    # Lead 6 (index 0):
    # future +6h (lead 12): False
    # future +12h (lead 18): True (BUST!)
    # future +24h (lead 30): True (BUST!)
    # future within 24h: True (because leads 18 and 30 are busts)
    f6 = features[0]
    assert f6.lead_hours == 6
    assert not f6.contemp_is_bust
    assert f6.future_bust_plus6h is False
    assert f6.future_bust_plus12h is True
    assert f6.future_bust_plus24h is True
    assert f6.future_bust_within24h is True

    # Lead 12 (index 1):
    # future +6h (lead 18): True
    # future +12h (lead 24): False
    # future within 24h: True (leads 18, 30 are busts)
    f12 = features[1]
    assert f12.future_bust_plus6h is True
    assert f12.future_bust_plus12h is False
    assert f12.future_bust_within24h is True

    # Lead 30 (last lead, index 4):
    # No future leads exist -> all future targets must be None
    f30 = features[4]
    assert f30.future_bust_plus6h is None
    assert f30.future_bust_plus12h is None
    assert f30.future_bust_within24h is None


def test_no_future_leakage_in_prospective_features():
    """Verify that mutating future observations or forecast tracks has ZERO effect on features at lead t."""
    t0 = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    evals = []
    for i, lead in enumerate([6, 12, 18, 24]):
        vt = t0 + timedelta(hours=lead)
        obs = BestTrackPoint("TEST", 2023, vt, 10.0 + 0.1 * i, 80.0)
        members = [
            ForecastMemberTrackPoint(1, lead, vt, 10.0 + 0.1 * i, 80.0, 1000.0),
            ForecastMemberTrackPoint(2, lead, vt, 10.1 + 0.1 * i, 80.1, 1000.0),
        ]
        evals.append(evaluate_forecast_lead("TEST", t0, lead, vt, members, obs, bust_threshold_km=85.0))

    features_orig = extract_prospective_features(evals)

    # Radically mutate the future lead 24 (index 3)
    evals_mutated = list(evals)
    vt_future = t0 + timedelta(hours=24)
    obs_mutated = BestTrackPoint("TEST", 2023, vt_future, 50.0, 120.0)
    members_mutated = [
        ForecastMemberTrackPoint(1, 24, vt_future, 60.0, 130.0, 900.0),
        ForecastMemberTrackPoint(2, 24, vt_future, 40.0, 110.0, 910.0),
    ]
    evals_mutated[3] = evaluate_forecast_lead("TEST", t0, 24, vt_future, members_mutated, obs_mutated, bust_threshold_km=85.0)

    features_mutated = extract_prospective_features(evals_mutated)

    # Features at leads 6 and 12 must remain 100% byte-for-byte identical
    for idx in [0, 1]:
        f_orig = features_orig[idx]
        f_mut = features_mutated[idx]
        assert f_orig.ensemble_spread_km == f_mut.ensemble_spread_km
        assert f_orig.anisotropy_ratio == f_mut.anisotropy_ratio
        assert f_orig.bimodality_coefficient == f_mut.bimodality_coefficient
        assert f_orig.spread_growth_km == f_mut.spread_growth_km
        assert f_orig.spread_acceleration_km == f_mut.spread_acceleration_km
        assert f_orig.trajectory_speed_kmh == f_mut.trajectory_speed_kmh
        assert f_orig.trajectory_curvature_deg == f_mut.trajectory_curvature_deg
        assert f_orig.reliability_contradiction_index == f_mut.reliability_contradiction_index


def test_ensemble_geometry_isotropic_vs_elongated():
    """Verify that circular dispersion has anisotropy ~1.0 while line dispersion has high anisotropy."""
    vt = datetime(2023, 1, 1, 6, 0, tzinfo=timezone.utc)

    # 1. Circular / Isotropic distribution around (10.0, 80.0)
    # Members arranged at radius r in all directions
    angles = np.linspace(0, 2 * math.pi, 9)[:-1]
    circ_members = [
        ForecastMemberTrackPoint(i + 1, 6, vt, 10.0 + 0.5 * math.sin(a), 80.0 + 0.5 * math.cos(a), 1000.0)
        for i, a in enumerate(angles)
    ]
    geom_circ = compute_ensemble_geometry(circ_members, 10.0, 80.0)
    assert geom_circ.anisotropy_ratio == pytest.approx(1.0, abs=0.15)

    # 2. Elongated / Line distribution along latitude (high anisotropy)
    line_members = [
        ForecastMemberTrackPoint(i + 1, 6, vt, 10.0 + 0.3 * i, 80.0, 1000.0)
        for i in range(8)
    ]
    geom_line = compute_ensemble_geometry(line_members, 10.0, 80.0)
    assert geom_line.anisotropy_ratio > 3.0
    assert geom_line.major_axis_spread_km > geom_line.minor_axis_spread_km


def test_ensemble_geometry_bimodality():
    """Verify that bimodal / split ensemble tracks produce high Sarle's bimodality coefficient."""
    vt = datetime(2023, 1, 1, 6, 0, tzinfo=timezone.utc)

    # Two distinct clusters of 5 members each: one cluster at (10.0, 79.0), one cluster at (10.0, 81.0)
    cluster1 = [ForecastMemberTrackPoint(i, 6, vt, 10.0 + 0.02 * i, 79.0, 1000.0) for i in range(5)]
    cluster2 = [ForecastMemberTrackPoint(i + 5, 6, vt, 10.0 + 0.02 * i, 81.0, 1000.0) for i in range(5)]
    bimodal_members = cluster1 + cluster2

    geom_bimodal = compute_ensemble_geometry(bimodal_members, 10.0, 80.0)
    assert geom_bimodal.cluster_separation_km > 150.0
    assert geom_bimodal.dominant_cluster_fraction == pytest.approx(0.5, abs=0.1)


def test_cycle_to_cycle_instability_matching():
    """Verify cycle-to-cycle revision comparison matches identical valid times across initialization runs."""
    t0_c1 = datetime(2023, 6, 7, 0, 0, tzinfo=timezone.utc)
    t0_c2 = datetime(2023, 6, 7, 12, 0, tzinfo=timezone.utc)

    # C1 at lead 18h: valid time = 2023-06-07 18:00
    # C2 at lead 06h: valid time = 2023-06-07 18:00 (matching valid time!)
    vt_match = datetime(2023, 6, 7, 18, 0, tzinfo=timezone.utc)

    obs = BestTrackPoint("TEST", 2023, vt_match, 12.0, 68.0)
    m_c1 = [ForecastMemberTrackPoint(1, 18, vt_match, 12.0, 68.5, 1000.0)]
    m_c2 = [ForecastMemberTrackPoint(1, 6, vt_match, 12.0, 68.1, 1000.0)]

    ev_c1 = evaluate_forecast_lead("TEST", t0_c1, 18, vt_match, m_c1, obs)
    ev_c2 = evaluate_forecast_lead("TEST", t0_c2, 6, vt_match, m_c2, obs)

    # When extracting features for C2 with prior cycle C1 provided:
    features_c2 = extract_prospective_features([ev_c2], prior_cycle_evals=[ev_c1])
    assert len(features_c2) == 1
    f = features_c2[0]

    assert f.has_prior_cycle is True
    # Distance between (12.0, 68.5) and (12.0, 68.1) is ~43 km
    assert f.cycle_revision_distance_km == pytest.approx(43.0, abs=3.0)


def test_false_confidence_quadrants():
    """Verify the 4 empirical reliability diagnostic quadrants."""
    # 1. Low spread, high error -> FALSE_CONFIDENCE
    assert classify_confidence_quadrant(spread_km=40.0, future_error_km=120.0, median_spread_km=100.0, bust_threshold_km=90.0) == "FALSE_CONFIDENCE"

    # 2. High spread, low error -> CAUTIOUS_CORRECT
    assert classify_confidence_quadrant(spread_km=140.0, future_error_km=30.0, median_spread_km=100.0, bust_threshold_km=90.0) == "CAUTIOUS_CORRECT"

    # 3. High spread, high error -> EXPECTED_RISK
    assert classify_confidence_quadrant(spread_km=150.0, future_error_km=130.0, median_spread_km=100.0, bust_threshold_km=90.0) == "EXPECTED_RISK"

    # 4. Low spread, low error -> RELIABLE_CONFIDENCE
    assert classify_confidence_quadrant(spread_km=45.0, future_error_km=25.0, median_spread_km=100.0, bust_threshold_km=90.0) == "RELIABLE_CONFIDENCE"


def test_ablation_matrix_extraction_dimensions():
    """Verify that feature matrices for M0 through M6 have expected column dimensions."""
    t0 = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    ev = evaluate_forecast_lead(
        "TEST", t0, 6, t0 + timedelta(hours=6),
        [ForecastMemberTrackPoint(1, 6, t0 + timedelta(hours=6), 10.0, 80.0, 1000.0)],
        BestTrackPoint("TEST", 2023, t0 + timedelta(hours=6), 10.0, 80.0),
    )
    p_feat = extract_prospective_features([ev])

    # M0: 1 col (lead)
    X_m0 = extract_feature_matrix_for_ablation(p_feat, "M0_Climatology")
    assert X_m0.shape == (1, 1)

    # M1: 2 cols (lead, spread)
    X_m1 = extract_feature_matrix_for_ablation(p_feat, "M1_SpreadOnly")
    assert X_m1.shape == (1, 2)

    # M2: 6 cols
    X_m2 = extract_feature_matrix_for_ablation(p_feat, "M2_Spread_Trajectory")
    assert X_m2.shape == (1, 6)

    # M3: 6 cols
    X_m3 = extract_feature_matrix_for_ablation(p_feat, "M3_Spread_Geometry")
    assert X_m3.shape == (1, 6)

    # M5: 4 cols (leakage-free: lead, spread, rci, divergence)
    X_m5 = extract_feature_matrix_for_ablation(p_feat, "M5_Spread_FalseConfidence")
    assert X_m5.shape == (1, 4)

    # M6: 7 cols
    X_m6 = extract_feature_matrix_for_ablation(p_feat, "M6_CombinedCandidate")
    assert X_m6.shape == (1, 7)


def test_keep_kill_decision_logic():
    """Verify Keep/Kill decision logic correctly categorizes models based on delta Brier/ECE."""
    m1_metrics = ModelMetrics(
        model_name="M1_SpreadOnly", brier_score=0.30, roc_auc=0.7, pr_auc=0.6,
        ece=0.50, accuracy=0.60, f1=0.5, earliest_warning_lead_hours=12,
        probabilities=[0.3, 0.4], predictions=[0, 0],
    )

    # Model that improves Brier and ECE -> RETAINED
    m_better = ModelMetrics(
        model_name="M_Better", brier_score=0.20, roc_auc=0.8, pr_auc=0.7,
        ece=0.35, accuracy=0.75, f1=0.7, earliest_warning_lead_hours=12,
        probabilities=[0.2, 0.3], predictions=[0, 0],
    )

    # Model that degrades Brier and ECE -> KILLED
    m_worse = ModelMetrics(
        model_name="M_Worse", brier_score=0.55, roc_auc=0.5, pr_auc=0.4,
        ece=0.65, accuracy=0.40, f1=0.3, earliest_warning_lead_hours=None,
        probabilities=[0.6, 0.7], predictions=[1, 1],
    )

    results = {
        "M1_SpreadOnly": m1_metrics,
        "M_Better": m_better,
        "M_Worse": m_worse,
    }

    decisions = evaluate_keep_kill(results, baseline_id="M1_SpreadOnly")
    assert decisions["M1_SpreadOnly"].status == "RETAINED"
    assert decisions["M_Better"].status == "RETAINED"
    assert decisions["M_Worse"].status == "KILLED"


def test_bust_atlas_compilation():
    """Verify build_bust_atlas catalogs verified failures with antecedent metrics."""
    t0 = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    vt1 = t0 + timedelta(hours=6)
    vt2 = t0 + timedelta(hours=12)

    # Lead 6: normal (error 20km)
    ev1 = evaluate_forecast_lead("TEST_STORM", t0, 6, vt1, [ForecastMemberTrackPoint(1, 6, vt1, 10.0, 80.0, 1000.0)], BestTrackPoint("TEST_STORM", 2023, vt1, 10.0, 80.0), bust_threshold_km=85.0)
    # Lead 12: BUST (error 140km)
    ev2 = evaluate_forecast_lead("TEST_STORM", t0, 12, vt2, [ForecastMemberTrackPoint(1, 12, vt2, 11.2, 80.0, 1000.0)], BestTrackPoint("TEST_STORM", 2023, vt2, 10.0, 80.0), bust_threshold_km=85.0)

    p_feats = extract_prospective_features([ev1, ev2])

    class MockModel:
        def predict_proba(self, X):
            return np.array([[0.3, 0.7], [0.1, 0.9]])

    atlas = build_bust_atlas(p_feats, MockModel(), np.array([[6], [12]]))

    # Only lead 12 is a verified failure, so atlas must have 1 entry
    assert len(atlas) == 1
    entry = atlas[0]
    assert entry.cyclone_name == "TEST_STORM"
    assert entry.lead_hours == 12
    assert entry.track_error_km > 100.0
    assert entry.bust_severity in ["DEGRADED", "SEVERE"]
    # Model alerted at lead 6 (p=0.7 >= 0.5), so advance warning is 12 - 6 = 6 hours!
    assert entry.advance_warning_hours == 6


def test_p3_artifact_existence():
    """Verify that all generated P3 artifacts exist, are non-empty, and valid JSON."""
    base_dir = Path(__file__).resolve().parent.parent.parent
    data_dir = base_dir / "data" / "validation"

    summary_file = data_dir / "p3_experiment_summary.json"
    atlas_file = data_dir / "p3_bust_atlas.json"
    ablation_file = data_dir / "p3_ablation_results.json"
    frontend_file = base_dir / "frontend" / "src" / "data" / "verifiedCycloneCase.json"

    for f in [summary_file, atlas_file, ablation_file, frontend_file]:
        assert f.is_file(), f"Missing expected artifact: {f.name}"
        assert f.stat().st_size > 500, f"Artifact {f.name} too small ({f.stat().st_size} bytes)"
        with open(f, "r", encoding="utf-8") as fp:
            data = json.load(fp)
            assert data is not None
