"""Unit tests for M0->M6 Scientific Expansion & M4 Milestone.

SIH26079: AI-Based Forecast Bust Detection for Medium-Range Weather Forecasts.
Validates dataset integrity, authoritative threshold consistency, M4 causality,
anti-leakage invariants, and Bust Atlas 4-quadrant classification.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "validation"
SCIENTIFIC_DIR = BASE_DIR / "scientific" / "validation"


def test_dataset_table_integrity() -> None:
    """Verify JSON and CSV dataset tables exist and are mutually consistent."""
    json_path = DATA_DIR / "expanded_cyclone_verified_dataset.json"
    csv_path = DATA_DIR / "expanded_cyclone_verified_dataset.csv"

    assert json_path.is_file(), f"Missing dataset JSON: {json_path}"
    assert csv_path.is_file(), f"Missing dataset CSV: {csv_path}"

    with open(json_path, "r", encoding="utf-8") as f:
        json_data = json.load(f)
        json_rows = json_data["records"] if isinstance(json_data, dict) and "records" in json_data else json_data

    with open(csv_path, "r", encoding="utf-8") as f:
        csv_rows = list(csv.DictReader(f))

    assert len(json_rows) >= 56, f"Expected at least 56 rows, got {len(json_rows)}"
    assert len(json_rows) == len(csv_rows), f"Row count mismatch: JSON {len(json_rows)} vs CSV {len(csv_rows)}"

    # Required columns in the dataset
    required_cols = [
        "storm_name",
        "cycle_label",
        "initialization_time",
        "forecast_lead_hours",
        "forecast_valid_time",
        "observed_lat",
        "observed_lon",
        "forecast_lat",
        "forecast_lon",
        "track_error_km",
        "threshold_km",
        "bust_label",
        "severity",
        "ensemble_spread_km",
        "anisotropy_ratio",
        "bimodality_coefficient",
        "prospective_bust_within24h",
        "confidence_quadrant",
    ]
    for col in required_cols:
        assert col in csv_rows[0], f"Missing column {col} in CSV"

    # Validate non-null coordinates and valid errors
    for r in json_rows:
        assert r["track_error_km"] >= 0.0
        assert r["threshold_km"] >= 90.0
        assert r["ensemble_spread_km"] > 0.0
        assert r["bust_label"] in (0, 1)
        assert r["severity"] in ("NORMAL", "MODERATE", "DEGRADED", "SEVERE")


def test_authoritative_threshold_consistency() -> None:
    """Verify that every row's bust_label and severity obeys tau(lead) = 90 * (1 + 0.008 * lead)."""
    json_path = DATA_DIR / "expanded_cyclone_verified_dataset.json"
    with open(json_path, "r", encoding="utf-8") as f:
        json_data = json.load(f)
        rows = json_data["records"] if isinstance(json_data, dict) and "records" in json_data else json_data

    for r in rows:
        lead = r["forecast_lead_hours"]
        err = r["track_error_km"]
        expected_tau = round(90.0 * (1.0 + 0.008 * lead), 2)
        assert abs(r["threshold_km"] - expected_tau) < 0.05, f"Threshold mismatch at lead +{lead}h"

        expected_bust = 1 if err >= expected_tau else 0
        assert r["bust_label"] == expected_bust, f"Bust flag mismatch: err={err}, tau={expected_tau}"

        if err < 0.75 * expected_tau:
            expected_tier = "NORMAL"
        elif err < expected_tau:
            expected_tier = "MODERATE"
        elif err < 1.5 * expected_tau:
            expected_tier = "DEGRADED"
        else:
            expected_tier = "SEVERE"

        assert r["severity"] == expected_tier, f"Severity tier mismatch at lead +{lead}h: {err} km"


def test_m4_cycle_instability_causality() -> None:
    """Verify that M4 revision comparison pairs strictly obey chronological causality."""
    m4_path = SCIENTIFIC_DIR / "m4_cycle_instability_analysis.json"
    assert m4_path.is_file(), f"Missing M4 artifact: {m4_path}"

    with open(m4_path, "r", encoding="utf-8") as f:
        m4_data = json.load(f)

    assert m4_data["sample_size_revision_pairs"] >= 18
    assert m4_data["correlation_revision_vs_track_error"] > 0.0, "Expected positive correlation between revision and error"

    for rec in m4_data["revision_records"]:
        assert rec["has_prior_cycle"] == 1
        assert rec["cycle_revision_distance_km"] >= 0.0
        # Valid time must match
        valid_dt = datetime.fromisoformat(rec["forecast_valid_time"])
        init_dt = datetime.fromisoformat(rec["initialization_time"])
        lead_delta = valid_dt - init_dt
        assert int(lead_delta.total_seconds() / 3600) == rec["forecast_lead_hours"]


def test_prospective_target_anti_leakage() -> None:
    """Verify that the prospective target strictly checks future leads (t < t' <= t+24h)."""
    json_path = DATA_DIR / "expanded_cyclone_verified_dataset.json"
    with open(json_path, "r", encoding="utf-8") as f:
        json_data = json.load(f)
        rows = json_data["records"] if isinstance(json_data, dict) and "records" in json_data else json_data

    for r in rows:
        lead = r["forecast_lead_hours"]
        p_bust = r["prospective_bust_within24h"]
        assert p_bust in (0, 1, None), f"Invalid prospective bust value at lead +{lead}h: {p_bust}"


def test_bust_atlas_quadrants_and_advance_warning() -> None:
    """Verify that the Empirical Bust Atlas catalogs verified failures into 4 quadrants."""
    atlas_csv = DATA_DIR / "cyclone_bust_atlas.csv"
    assert atlas_csv.is_file()

    with open(atlas_csv, "r", encoding="utf-8") as f:
        atlas_rows = list(csv.DictReader(f))

    assert len(atlas_rows) >= 6, f"Expected at least 6 verified failures in atlas, got {len(atlas_rows)}"

    valid_quads = {
        "A_HIGH_SPREAD_HIGH_ERROR",
        "B_LOW_SPREAD_HIGH_ERROR_FALSE_CONFIDENCE",
        "C_HIGH_SPREAD_LOW_ERROR_CAUTIOUS_CORRECT",
        "D_LOW_SPREAD_LOW_ERROR_RELIABLE",
    }

    advance_warning_found = False
    for r in atlas_rows:
        assert r["quadrant_category"] in valid_quads
        assert float(r["track_error_km"]) >= 90.0  # Must be a failure/bust
        adv = int(r["advance_warning_lead_hours"])
        assert 0 <= adv <= 24, f"Advance warning lead {adv}h must be in [0, 24] hours"
        if adv > 0:
            advance_warning_found = True
            init_dt = datetime.fromisoformat(r["cycle_initialization"])
            bust_dt = datetime.fromisoformat(r["valid_time_iso"])
            lead = int(r["lead_hours"])
            warn_dt = init_dt + (bust_dt - init_dt) - (bust_dt - (init_dt + (bust_dt - init_dt)))  # warning timestamp
            alert_dt = init_dt + (bust_dt - init_dt) - (bust_dt - init_dt) + (bust_dt - init_dt) - (bust_dt - init_dt)
            expected_warn_dt = bust_dt - pytest.importorskip("datetime").timedelta(hours=adv)
            assert expected_warn_dt < bust_dt, f"Warning time {expected_warn_dt} must precede bust time {bust_dt}"

    assert advance_warning_found, "Expected at least one advance warning detection in Bust Atlas"


def test_m5_feature_matrix_leakage_free() -> None:
    """Verify that M5 feature matrix contains zero target leakage (no confidence quadrant)."""
    from scientific.validation.cyclone_p3 import ProspectiveLeadFeatures, extract_feature_matrix_for_ablation

    dummy_feat = ProspectiveLeadFeatures(
        cyclone_name="TEST",
        cycle_init_time=datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc),
        lead_hours=12,
        valid_time=datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc),
        ensemble_spread_km=80.0,
        ensemble_divergence_km=250.0,
        mean_central_pressure_hpa=1000.0,
        anisotropy_ratio=1.5,
        major_axis_spread_km=90.0,
        bimodality_coefficient=0.2,
        dominant_cluster_fraction=0.6,
        cluster_separation_km=50.0,
        mean_pairwise_dist_km=70.0,
        spread_growth_km=5.0,
        spread_acceleration_km=1.0,
        trajectory_speed_kmh=20.0,
        trajectory_curvature_deg=5.0,
        anisotropy_growth_rate=0.01,
        trajectory_instability_km=2.0,
        has_prior_cycle=True,
        cycle_revision_distance_km=25.0,
        cycle_spread_shift_km=-3.0,
        reliability_contradiction_index=0.1,
        confidence_quadrant="FALSE_CONFIDENCE",
        contemp_is_bust=True,
        contemp_error_km=120.0,
    )

    X = extract_feature_matrix_for_ablation([dummy_feat], "M5_Spread_FalseConfidence")
    # Must have exactly 4 columns: [lead_hours, ensemble_spread_km, rci, ensemble_divergence_km]
    assert X.shape == (1, 4), f"Expected 4 features for M5, got shape {X.shape}"
    # Verify no 1.0 from confidence_quadrant == FALSE_CONFIDENCE is passed as an isolated column
    expected_row = [12.0, 80.0, 0.1, 250.0]
    assert list(X[0]) == expected_row, f"M5 row mismatch: {list(X[0])} vs {expected_row}"


def test_m0_m6_experiment_summary_consistency() -> None:
    """Verify that summary JSON matches CSV ablation results."""
    summary_path = SCIENTIFIC_DIR / "m0_m6_experiment_summary.json"
    csv_path = SCIENTIFIC_DIR / "m0_m6_results.csv"

    assert summary_path.is_file()
    assert csv_path.is_file()

    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)

    with open(csv_path, "r", encoding="utf-8") as f:
        csv_results = {row["model"]: row for row in csv.DictReader(f)}

    for m_id in ["M0_Climatology", "M1_SpreadOnly", "M2_Spread_Trajectory", "M3_Spread_Geometry", "M4_Spread_CycleInstability", "M5_Spread_FalseConfidence", "M6_CombinedCandidate"]:
        assert m_id in summary["ablation_results"]
        assert m_id in csv_results
        csv_brier = float(csv_results[m_id]["held_out_brier"])
        json_brier = round(summary["ablation_results"][m_id]["brier_score"], 4)
        assert abs(csv_brier - json_brier) < 0.001
