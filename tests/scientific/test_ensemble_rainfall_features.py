"""Tests for ensemble rainfall feature extraction."""

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

from scientific.features.ensemble_rainfall import (
    EnsembleRainfallFeatures,
    extract_ensemble_rainfall_features,
)
from scientific.ingestion.grib import read_grib_file


# ---------------------------------------------------------------------------
# Unit Tests: Synthetic Ensembles
# ---------------------------------------------------------------------------


def test_synthetic_ensemble_correct_mean() -> None:
    """Verify ensemble_mean calculation on known synthetic data."""
    # Create a simple 2x2 grid, 3 members
    ensemble_members = {
        1: (np.array([1.0, 2.0, 3.0, 4.0]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 2, "nj": 2}),
        2: (np.array([2.0, 3.0, 4.0, 5.0]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 2, "nj": 2}),
        3: (np.array([3.0, 4.0, 5.0, 6.0]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 2, "nj": 2}),
    }
    grid_meta = {"ni": 2, "nj": 2}

    features = extract_ensemble_rainfall_features(ensemble_members, grid_meta)

    expected_mean = np.array([[2.0, 3.0], [4.0, 5.0]])
    np.testing.assert_allclose(features.ensemble_mean, expected_mean, rtol=1e-10)
    assert features.member_count == 3


def test_synthetic_ensemble_correct_std() -> None:
    """Verify ensemble_std calculation (sample standard deviation)."""
    # 3 members with known std
    ensemble_members = {
        1: (np.array([1.0, 1.0]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 1, "nj": 2}),
        2: (np.array([2.0, 2.0]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 1, "nj": 2}),
        3: (np.array([3.0, 3.0]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 1, "nj": 2}),
    }
    grid_meta = {"ni": 1, "nj": 2}

    features = extract_ensemble_rainfall_features(ensemble_members, grid_meta)

    # std of [1, 2, 3] with ddof=1: sqrt(((1-2)^2 + (2-2)^2 + (3-2)^2) / (3-1)) = sqrt(2/2) = 1.0
    expected_std = np.ones((2, 1))
    np.testing.assert_allclose(features.ensemble_std, expected_std, rtol=1e-10)


def test_synthetic_ensemble_correct_percentiles() -> None:
    """Verify percentile calculations."""
    # Members: [1, 2, 3, 4, 5]
    ensemble_members = {i: (np.array([float(i)]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 1, "nj": 1}) for i in range(1, 6)}
    grid_meta = {"ni": 1, "nj": 1}

    features = extract_ensemble_rainfall_features(ensemble_members, grid_meta)

    # p10 ≈ 1.4, p25 = 2.0, p75 = 4.0, p90 ≈ 4.6
    assert pytest.approx(features.ensemble_p10[0, 0], abs=0.1) == 1.4
    assert pytest.approx(features.ensemble_p25[0, 0], abs=0.01) == 2.0
    assert pytest.approx(features.ensemble_p75[0, 0], abs=0.01) == 4.0
    assert pytest.approx(features.ensemble_p90[0, 0], abs=0.1) == 4.6


def test_synthetic_ensemble_correct_range_and_iqr() -> None:
    """Verify range and IQR calculations."""
    ensemble_members = {
        1: (np.array([10.0]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 1, "nj": 1}),
        2: (np.array([20.0]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 1, "nj": 1}),
        3: (np.array([50.0]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 1, "nj": 1}),
    }
    grid_meta = {"ni": 1, "nj": 1}

    features = extract_ensemble_rainfall_features(ensemble_members, grid_meta)

    assert features.ensemble_range[0, 0] == pytest.approx(40.0)  # 50 - 10
    # IQR = p75 - p25 = 35 - 15 = 20
    assert features.ensemble_iqr[0, 0] == pytest.approx(20.0, abs=0.5)


def test_synthetic_ensemble_event_probabilities() -> None:
    """Verify rain event probability calculations."""
    # 5 members: [0.5, 1.5, 5.0, 15.0, 25.0]
    ensemble_members = {
        1: (np.array([0.5]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 1, "nj": 1}),
        2: (np.array([1.5]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 1, "nj": 1}),
        3: (np.array([5.0]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 1, "nj": 1}),
        4: (np.array([15.0]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 1, "nj": 1}),
        5: (np.array([25.0]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 1, "nj": 1}),
    }
    grid_meta = {"ni": 1, "nj": 1}

    features = extract_ensemble_rainfall_features(ensemble_members, grid_meta)

    # >1mm: [1.5, 5, 15, 25] = 4/5 = 0.8
    assert features.probability_rain_gt_1mm[0, 0] == pytest.approx(0.8)
    # >10mm: [15, 25] = 2/5 = 0.4
    assert features.probability_rain_gt_10mm[0, 0] == pytest.approx(0.4)
    # >25mm: [] = 0/5 = 0.0
    assert features.probability_rain_gt_25mm[0, 0] == pytest.approx(0.0)


def test_synthetic_ensemble_nan_handling() -> None:
    """Verify NaN members are properly ignored in statistics."""
    # 3 members: [1.0, NaN, 3.0]
    ensemble_members = {
        1: (np.array([1.0]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 1, "nj": 1}),
        2: (np.array([np.nan]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 1, "nj": 1}),
        3: (np.array([3.0]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 1, "nj": 1}),
    }
    grid_meta = {"ni": 1, "nj": 1}

    features = extract_ensemble_rainfall_features(ensemble_members, grid_meta)

    # Mean should be (1 + 3) / 2 = 2.0, ignoring NaN
    assert features.ensemble_mean[0, 0] == pytest.approx(2.0)
    assert features.member_count == 3
    assert features.valid_member_count == 1  # 1 grid point with valid data


def test_synthetic_ensemble_all_nan_cell() -> None:
    """Verify all-NaN grid cells remain NaN in all features."""
    ensemble_members = {
        1: (np.array([np.nan, 1.0]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 1, "nj": 2}),
        2: (np.array([np.nan, 2.0]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 1, "nj": 2}),
    }
    grid_meta = {"ni": 1, "nj": 2}

    features = extract_ensemble_rainfall_features(ensemble_members, grid_meta)

    # Cell (0, 0) should be all NaN
    assert np.isnan(features.ensemble_mean[0, 0])
    assert np.isnan(features.ensemble_std[0, 0])
    assert np.isnan(features.ensemble_skewness[0, 0])
    assert np.isnan(features.probability_rain_gt_1mm[0, 0])

    # Cell (1, 0) should be valid
    assert features.ensemble_mean[1, 0] == pytest.approx(1.5)


def test_synthetic_ensemble_zero_rainfall() -> None:
    """Verify zero rainfall is treated as valid data, not NaN."""
    ensemble_members = {
        1: (np.array([0.0]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 1, "nj": 1}),
        2: (np.array([0.0]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 1, "nj": 1}),
    }
    grid_meta = {"ni": 1, "nj": 1}

    features = extract_ensemble_rainfall_features(ensemble_members, grid_meta)

    assert features.ensemble_mean[0, 0] == pytest.approx(0.0)
    assert features.ensemble_std[0, 0] == pytest.approx(0.0)
    assert features.probability_rain_gt_1mm[0, 0] == pytest.approx(0.0)


def test_coefficient_of_variation_zero_mean() -> None:
    """Verify CV remains NaN where mean ≈ 0."""
    ensemble_members = {
        1: (np.array([0.0, 0.00001]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 2, "nj": 1}),
        2: (np.array([0.0, 0.00002]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 2, "nj": 1}),
    }
    grid_meta = {"ni": 2, "nj": 1}

    features = extract_ensemble_rainfall_features(ensemble_members, grid_meta)

    # Zero-mean cell: CV should be NaN
    assert np.isnan(features.coefficient_of_variation[0, 0])

    # Non-zero mean cell: CV should be defined
    assert not np.isnan(features.coefficient_of_variation[0, 1])
    cv_expected = features.ensemble_std[0, 1] / features.ensemble_mean[0, 1]
    assert features.coefficient_of_variation[0, 1] == pytest.approx(cv_expected)


def test_ensemble_skewness_zero_variance() -> None:
    """Verify skewness remains NaN where variance ≈ 0."""
    ensemble_members = {
        1: (np.array([1.0, 5.0]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 2, "nj": 1}),
        2: (np.array([1.0, 5.1]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 2, "nj": 1}),
        3: (np.array([1.0, 4.9]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 2, "nj": 1}),
    }
    grid_meta = {"ni": 2, "nj": 1}

    features = extract_ensemble_rainfall_features(ensemble_members, grid_meta)

    # Zero-variance cell: skewness should be NaN
    assert np.isnan(features.ensemble_skewness[0, 0])

    # Non-zero variance cell: skewness should be defined
    assert not np.isnan(features.ensemble_skewness[0, 1])


def test_mean_pairwise_member_difference() -> None:
    """Verify mean pairwise member difference calculation."""
    # 3 members: [0, 1, 2]
    # Pairs: (0,1)=1, (0,2)=2, (1,2)=1 → mean = 4/3 ≈ 1.333
    ensemble_members = {
        1: (np.array([0.0]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 1, "nj": 1}),
        2: (np.array([1.0]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 1, "nj": 1}),
        3: (np.array([2.0]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 1, "nj": 1}),
    }
    grid_meta = {"ni": 1, "nj": 1}

    features = extract_ensemble_rainfall_features(ensemble_members, grid_meta)

    assert features.mean_pairwise_member_difference[0, 0] == pytest.approx(4.0 / 3.0)


def test_maximum_ensemble_gap() -> None:
    """Verify maximum gap in sorted ensemble members calculation."""
    # 4 members: [0, 1, 10, 11], sorted gaps: [1, 9, 1]
    # Maximum gap = 9 (indicates ensemble clustering/bimodality)
    ensemble_members = {
        1: (np.array([0.0]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 1, "nj": 1}),
        2: (np.array([1.0]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 1, "nj": 1}),
        3: (np.array([10.0]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 1, "nj": 1}),
        4: (np.array([11.0]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 1, "nj": 1}),
    }
    grid_meta = {"ni": 1, "nj": 1}

    features = extract_ensemble_rainfall_features(ensemble_members, grid_meta)

    # Maximum gap should be 9 (between members 1 and 10)
    assert features.maximum_ensemble_gap[0, 0] == pytest.approx(9.0)


def test_maximum_ensemble_gap_consensus() -> None:
    """Verify maximum gap is zero when all ensemble members agree."""
    # 3 members all with value 5.0: gaps all zero
    ensemble_members = {
        1: (np.array([5.0]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 1, "nj": 1}),
        2: (np.array([5.0]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 1, "nj": 1}),
        3: (np.array([5.0]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 1, "nj": 1}),
    }
    grid_meta = {"ni": 1, "nj": 1}

    features = extract_ensemble_rainfall_features(ensemble_members, grid_meta)

    # Maximum gap should be 0 (ensemble consensus)
    assert features.maximum_ensemble_gap[0, 0] == pytest.approx(0.0)


def test_maximum_ensemble_gap_uniform_spread() -> None:
    """Verify maximum gap with uniformly spaced ensemble members."""
    # 5 members: [0, 1, 2, 3, 4], all gaps equal to 1
    ensemble_members = {i: (np.array([float(i - 1)]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 1, "nj": 1}) for i in range(1, 6)}
    grid_meta = {"ni": 1, "nj": 1}

    features = extract_ensemble_rainfall_features(ensemble_members, grid_meta)

    # Maximum gap should be 1 (uniform spacing)
    assert features.maximum_ensemble_gap[0, 0] == pytest.approx(1.0)



def test_member_agreement_fraction() -> None:
    """Verify member agreement fraction calculation."""
    # 3 members: [10, 11, 12], mean = 11, threshold = 0.25 * 11 = 2.75
    # Pairs: (10,11)=1<2.75✓, (10,12)=2<2.75✓, (11,12)=1<2.75✓ → 3/3 = 1.0
    ensemble_members = {
        1: (np.array([10.0]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 1, "nj": 1}),
        2: (np.array([11.0]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 1, "nj": 1}),
        3: (np.array([12.0]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 1, "nj": 1}),
    }
    grid_meta = {"ni": 1, "nj": 1}

    features = extract_ensemble_rainfall_features(ensemble_members, grid_meta)

    assert features.member_agreement_fraction[0, 0] == pytest.approx(1.0)


def test_member_agreement_fraction_zero_mean() -> None:
    """Verify member agreement uses absolute threshold for zero-mean cells."""
    # 2 members: [0.005, 0.006], mean ≈ 0.0055 < 1e-3 mm
    # Should use absolute threshold 0.01 mm: |0.005 - 0.006| = 0.001 < 0.01 ✓ → 1/1 = 1.0
    ensemble_members = {
        1: (np.array([0.005]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 1, "nj": 1}),
        2: (np.array([0.006]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 1, "nj": 1}),
    }
    grid_meta = {"ni": 1, "nj": 1}

    features = extract_ensemble_rainfall_features(ensemble_members, grid_meta)

    assert features.member_agreement_fraction[0, 0] == pytest.approx(1.0)


def test_provenance_preservation() -> None:
    """Verify source metadata and timestamps are preserved."""
    ensemble_members = {
        1: (
            np.array([1.0]),
            {
                "data_date": 20250901,
                "data_time": 0,
                "step": 24,
                "step_type": "accum",
                "short_name": "tp",
                "ni": 1,
                "nj": 1,
            },
        ),
    }
    grid_meta = {"ni": 1, "nj": 1}
    extraction_time = datetime(2025, 9, 1, 6, 0, 0, tzinfo=timezone.utc)

    features = extract_ensemble_rainfall_features(ensemble_members, grid_meta, extraction_time)

    assert features.forecast_date == 20250901
    assert features.forecast_time == 0
    assert features.forecast_step == 24
    assert features.extraction_timestamp == extraction_time
    assert features.source_metadata["short_name"] == "tp"


def test_feature_names_complete() -> None:
    """Verify feature_names list is complete and matches feature arrays."""
    ensemble_members = {
        1: (np.array([1.0]), {"data_date": 20250901, "data_time": 0, "step": 24, "step_type": "accum", "ni": 1, "nj": 1}),
    }
    grid_meta = {"ni": 1, "nj": 1}

    features = extract_ensemble_rainfall_features(ensemble_members, grid_meta)

    assert len(features.feature_names) == 24
    assert "ensemble_mean" in features.feature_names
    assert "member_agreement_fraction" in features.feature_names
    assert features.feature_names == features.feature_array_names()


# ---------------------------------------------------------------------------
# Integration Tests: Real GRIB Data
# ---------------------------------------------------------------------------

SAMPLE_GRIB_PATH = Path("data/raw/tigge/67603f4734166cde0f2c2962323ad8e4.grib")


@pytest.fixture(scope="module")
def sample_grib_tp_ensemble():
    """Fixture providing TP ensemble from real sample file."""
    if not SAMPLE_GRIB_PATH.exists():
        pytest.skip(f"Real sample GRIB not found at {SAMPLE_GRIB_PATH}")

    messages, qc = read_grib_file(SAMPLE_GRIB_PATH, compute_stats=True)
    assert qc.status == "PASS", f"QC failed: {qc.issues}"

    # Filter to TP messages (short_name == "tp")
    tp_messages = [m for m in messages if m.short_name == "tp"]
    assert len(tp_messages) == 11, f"Expected 11 TP members, got {len(tp_messages)}"

    return messages, tp_messages


def test_real_grib_feature_extraction_smoke_test(sample_grib_tp_ensemble) -> None:
    """Verify features can be extracted from real GRIB sample without errors.

    This is a smoke test: it checks that extraction works, not that values are correct.
    Correct values cannot be verified without external data.
    """
    messages, tp_messages = sample_grib_tp_ensemble

    # Build ensemble dict: member_id -> (values_1d, metadata_dict)
    ensemble_members = {}
    for msg in tp_messages:
        values_1d = np.full(msg.number_of_values, np.nan, dtype=np.float64)

        # Read actual values using eccodes
        import eccodes
        with open(SAMPLE_GRIB_PATH, "rb") as f:
            for _ in range(msg.message_index - 1):
                handle = eccodes.codes_grib_new_from_file(f)
                if handle:
                    eccodes.codes_release(handle)

            handle = eccodes.codes_grib_new_from_file(f)
            if handle:
                raw_vals = eccodes.codes_get_values(handle)
                values_1d = np.asarray(raw_vals, dtype=np.float64)
                eccodes.codes_release(handle)

        ensemble_members[msg.member] = (
            values_1d,
            msg.to_dict(),
        )

    grid_meta = {
        "ni": tp_messages[0].ni,
        "nj": tp_messages[0].nj,
        "first_lat": tp_messages[0].first_lat,
        "first_lon": tp_messages[0].first_lon,
        "last_lat": tp_messages[0].last_lat,
        "last_lon": tp_messages[0].last_lon,
        "lat_increment": tp_messages[0].j_increment,
        "lon_increment": tp_messages[0].i_increment,
    }

    features = extract_ensemble_rainfall_features(ensemble_members, grid_meta)

    # Smoke test: check that all features are populated correctly
    assert features.member_count == 11
    assert features.valid_member_count > 0
    assert features.grid_shape == (83, 112)

    # Check that ensemble_mean has reasonable values (ensemble forecasts typically predict rainfall)
    valid_mean = features.ensemble_mean[~np.isnan(features.ensemble_mean)]
    assert len(valid_mean) > 0
    assert np.all(valid_mean >= 0), "TP should not be negative"

    # Check ranges
    assert np.nanmin(features.ensemble_mean) >= 0
    assert np.nanmax(features.ensemble_mean) <= 200  # Reasonable upper bound for 24h accumulation

    # All required features should be present and not all NaN
    for feature_name in features.feature_array_names():
        feature_array = getattr(features, feature_name)
        assert feature_array.shape == features.grid_shape
        # At least some values should be valid (not all NaN)
        assert not np.all(np.isnan(feature_array)), f"{feature_name} is all NaN"


def test_real_grib_feature_statistics_reasonable(sample_grib_tp_ensemble) -> None:
    """Verify feature statistics are within reasonable ranges for rainfall forecasts."""
    messages, tp_messages = sample_grib_tp_ensemble

    ensemble_members = {}
    import eccodes
    with open(SAMPLE_GRIB_PATH, "rb") as f:
        all_handles = []
        while True:
            handle = eccodes.codes_grib_new_from_file(f)
            if handle is None:
                break
            all_handles.append(handle)

        for msg in tp_messages:
            handle = all_handles[msg.message_index - 1]
            raw_vals = eccodes.codes_get_values(handle)
            values_1d = np.asarray(raw_vals, dtype=np.float64)
            ensemble_members[msg.member] = (values_1d, msg.to_dict())

        for handle in all_handles:
            eccodes.codes_release(handle)

    grid_meta = {
        "ni": tp_messages[0].ni,
        "nj": tp_messages[0].nj,
        "first_lat": tp_messages[0].first_lat,
        "first_lon": tp_messages[0].first_lon,
        "last_lat": tp_messages[0].last_lat,
        "last_lon": tp_messages[0].last_lon,
        "lat_increment": tp_messages[0].j_increment,
        "lon_increment": tp_messages[0].i_increment,
    }

    features = extract_ensemble_rainfall_features(ensemble_members, grid_meta)

    # Spread should be ≥ 0
    assert np.nanmin(features.ensemble_std) >= 0
    assert np.nanmin(features.ensemble_range) >= 0
    assert np.nanmin(features.ensemble_iqr) >= 0

    # Percentiles should be ordered
    p_cells = ~np.isnan(features.ensemble_p10)
    if np.any(p_cells):
        assert np.all(features.ensemble_p10[p_cells] <= features.ensemble_p25[p_cells])
        assert np.all(features.ensemble_p25[p_cells] <= features.ensemble_median[p_cells])
        assert np.all(features.ensemble_median[p_cells] <= features.ensemble_p75[p_cells])
        assert np.all(features.ensemble_p75[p_cells] <= features.ensemble_p90[p_cells])

    # CV should be ≥ 0 (or NaN)
    valid_cv = features.coefficient_of_variation[~np.isnan(features.coefficient_of_variation)]
    assert np.all(valid_cv >= 0)

    # Probabilities should be in [0, 1]
    valid_prob = features.probability_rain_gt_1mm[~np.isnan(features.probability_rain_gt_1mm)]
    assert np.all((valid_prob >= 0) & (valid_prob <= 1))
