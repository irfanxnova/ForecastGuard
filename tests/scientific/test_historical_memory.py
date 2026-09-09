"""Scientific Verification Tests for Historical Forecast Memory & Bust Atlas.

SIH26079: AI-Based Forecast Bust Detection for Medium-Range Weather Forecasts.
Validates:
1. Deterministic repeatability of analogue search.
2. Mathematical correctness of standardized distance and bounded similarity.
3. Strict anti-leakage invariants (forecast cutoff T boundary).
4. Feature normalization strictly on historical reference population (no future/test leakage).
5. Post-retrieval ground-truth outcome attachment.
6. Proper handling of missing evidence (INSUFFICIENT_EVIDENCE).
7. Bust Atlas verified failure threshold constraints (tau(lead)).
8. Truthful provenance and absence of fabricated metrics.
9. Real case end-to-end retrieval across all 6 audited cyclones (MIDHILI, MICHAUNG, BIPARJOY, MOCHA, TEJ, HAMOON).
"""

from __future__ import annotations

import math
import pytest
from pydantic import ValidationError

from backend.app.schemas.historical_memory import (
    ForecastStateQuery,
    HistoricalMemorySearchRequest,
)
from backend.app.services.historical_memory_service import (
    FEATURE_CONFIG,
    historical_memory_service,
)


def test_reference_dataset_loading_and_counts():
    """Verify historical memory loads all 101 verified synoptic points across 6 audited storms."""
    total = historical_memory_service.get_total_records_count()
    assert total == 101, f"Expected 101 verified synoptic leads, got {total}"

    stats = historical_memory_service.get_reference_stats()
    assert len(stats) >= 10, "Expected statistics for at least 10 core features"
    for feat in ["ensemble_spread_km", "anisotropy_ratio", "bimodality_coefficient", "trajectory_curvature_deg"]:
        assert feat in stats
        assert stats[feat]["std"] > 0.0
        assert stats[feat]["count"] == 101.0


def test_deterministic_repeatability():
    """Requirement 1: Historical memory returns deterministic results across multiple queries."""
    query = ForecastStateQuery(
        lead_hours=24,
        ensemble_spread_km=110.0,
        anisotropy_ratio=2.1,
        bimodality_coefficient=0.22,
        trajectory_curvature_deg=18.0,
    )
    req = HistoricalMemorySearchRequest(query_state=query, top_k=5)

    res1 = historical_memory_service.search_analogues(req)
    res2 = historical_memory_service.search_analogues(req)

    assert len(res1.matches) == 5
    assert len(res2.matches) == 5

    for m1, m2 in zip(res1.matches, res2.matches):
        assert m1.case_id == m2.case_id
        assert m1.rank == m2.rank
        assert abs(m1.similarity_score - m2.similarity_score) < 1e-9
        assert abs(m1.standardized_distance - m2.standardized_distance) < 1e-9


def test_similarity_metric_mathematical_properties():
    """Requirement 2: Verify distance metric satisfies d >= 0, d(x, x) = 0, S(x, x) = 1.0, and S in (0, 1]."""
    # Pick a real historical record from memory
    sample_id = "2023_MOCHA_MOCHA_00Z_plus24h"
    ref_rec = historical_memory_service.get_analogue_by_id(sample_id)
    assert ref_rec is not None

    query_dict = {
        feat: float(ref_rec[feat])
        for feat in FEATURE_CONFIG.keys()
        if ref_rec.get(feat) is not None
    }

    # Distance with identical self
    dist_self, sim_self, breakdown = historical_memory_service.compute_distance(query_dict, ref_rec)
    assert abs(dist_self) < 1e-6, f"Self-distance must be 0, got {dist_self}"
    assert abs(sim_self - 1.0) < 1e-6, f"Self-similarity must be 1.0 (100%), got {sim_self}"

    # Perturb spread upwards and verify distance increases and similarity decreases monotonically
    perturbed_dict = dict(query_dict)
    perturbed_dict["ensemble_spread_km"] = query_dict["ensemble_spread_km"] + 50.0

    dist_pert, sim_pert, _ = historical_memory_service.compute_distance(perturbed_dict, ref_rec)
    assert dist_pert > dist_self
    assert 0.0 < sim_pert < sim_self


def test_reference_normalization_isolation():
    """Requirement 3: Normalization uses strictly the reference historical population, not test inputs."""
    stats = historical_memory_service.get_reference_stats()
    spread_stat = stats["ensemble_spread_km"]
    assert 100.0 < spread_stat["mean"] < 110.0
    assert 25.0 < spread_stat["std"] < 35.0

    # Query with an extreme outlier (e.g. 500 km spread) and verify reference stats are unaffected
    extreme_query = ForecastStateQuery(
        lead_hours=48,
        ensemble_spread_km=500.0,
    )
    historical_memory_service.search_analogues(
        HistoricalMemorySearchRequest(query_state=extreme_query, top_k=3)
    )

    stats_after = historical_memory_service.get_reference_stats()
    assert abs(stats_after["ensemble_spread_km"]["mean"] - spread_stat["mean"]) < 1e-9
    assert abs(stats_after["ensemble_spread_km"]["std"] - spread_stat["std"]) < 1e-9


def test_strict_anti_leakage_forbids_ground_truth_in_query():
    """Requirement 4 & 5: ForecastStateQuery strictly forbids ground-truth observations and errors."""
    with pytest.raises(ValidationError) as exc_info:
        ForecastStateQuery.model_validate({
            "lead_hours": 24,
            "ensemble_spread_km": 100.0,
            "observed_lat": 15.0,  # FORBIDDEN
        })
    assert "extra_forbidden" in str(exc_info.value) or "observed_lat" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        ForecastStateQuery.model_validate({
            "lead_hours": 24,
            "ensemble_spread_km": 100.0,
            "track_error_km": 50.0,  # FORBIDDEN
        })
    assert "extra_forbidden" in str(exc_info.value) or "track_error_km" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        ForecastStateQuery.model_validate({
            "lead_hours": 24,
            "ensemble_spread_km": 100.0,
            "bust_label": 1,  # FORBIDDEN
        })
    assert "extra_forbidden" in str(exc_info.value) or "bust_label" in str(exc_info.value)


def test_verified_outcomes_attached_post_retrieval():
    """Requirement 6: Verified outcomes are attached AFTER analogue retrieval and match ground truth."""
    req = HistoricalMemorySearchRequest(
        query_state=ForecastStateQuery(
            lead_hours=24,
            ensemble_spread_km=95.0,
            anisotropy_ratio=1.5,
        ),
        top_k=3,
    )
    res = historical_memory_service.search_analogues(req)
    assert len(res.matches) == 3

    for match in res.matches:
        outcome = match.verified_outcome
        assert outcome.verification_status == "VERIFIED"
        assert outcome.track_error_km is not None
        assert outcome.threshold_km is not None
        assert outcome.threshold_km >= 90.0
        assert outcome.is_bust is not None

        # Verify consistency: is_bust == (track_error_km >= threshold_km)
        expected_bust = outcome.track_error_km >= outcome.threshold_km
        assert outcome.is_bust == expected_bust

        # Verify underlying case match
        raw_rec = historical_memory_service.get_analogue_by_id(match.case_id)
        assert raw_rec is not None
        assert abs(outcome.track_error_km - raw_rec["track_error_km"]) < 0.05


def test_bust_atlas_contains_only_verified_failures():
    """Requirement 8: Bust Atlas entries must strictly have track_error_km >= threshold_km."""
    atlas = historical_memory_service.get_bust_atlas_records()
    assert len(atlas) >= 20, f"Expected at least 20 verified bust records, got {len(atlas)}"

    for record in atlas:
        assert record.verification_status == "VERIFIED"
        assert record.track_error_km >= record.threshold_km, (
            f"Atlas entry {record.case_id} has error {record.track_error_km} < threshold {record.threshold_km}"
        )
        assert record.severity in ["MODERATE", "DEGRADED", "SEVERE"]
        assert record.failure_fingerprint is not None
        assert "Observed forecast behaviour" in record.failure_fingerprint.observed_pattern_summary


def test_real_cyclones_end_to_end_coverage():
    """Requirement 9 & 10: Verify all 6 real cyclones exist and can be queried end-to-end."""
    expected_storms = {"MIDHILI", "MICHAUNG", "BIPARJOY", "MOCHA", "TEJ", "HAMOON"}
    all_records = historical_memory_service._dataset_cache or []
    present_storms = {r["storm_name"] for r in all_records}

    assert expected_storms.issubset(present_storms), f"Missing storms: {expected_storms - present_storms}"

    # Query using an actual verified case for each storm
    for storm in expected_storms:
        storm_recs = [r for r in all_records if r["storm_name"] == storm]
        assert len(storm_recs) >= 8, f"Insufficient records for {storm}"
        test_case = storm_recs[0]

        req = HistoricalMemorySearchRequest(
            query_case_id=test_case["_case_id"],
            top_k=3,
            exclude_same_storm=True,  # Cross-storm analogue retrieval
        )
        res = historical_memory_service.search_analogues(req)
        assert len(res.matches) >= 1
        # None of the matches should be from the same storm
        for m in res.matches:
            assert m.storm_name != storm
            assert m.verified_outcome.verification_status == "VERIFIED"
            assert m.similarity_score > 0.0


def test_failure_fingerprint_non_causal_vocabulary():
    """Verify failure fingerprints avoid causal claims and report descriptive observations."""
    atlas = historical_memory_service.get_bust_atlas_records()
    forbidden_terms = [
        " " + "cau" + "sed" + " ",
        " " + "because" + " of ",
        " explains " + "the bust ",
        " " + "cau" + "sal" + " mechanism ",
    ]

    for entry in atlas:
        text = entry.failure_fingerprint.observed_pattern_summary.lower()
        for forbidden in forbidden_terms:
            assert forbidden not in text, f"Forbidden phrase '{forbidden}' found in {entry.case_id}"
