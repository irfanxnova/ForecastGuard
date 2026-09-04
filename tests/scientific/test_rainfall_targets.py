"""Tests for the leakage-safe rainfall target/label engine.

All tests use synthetic data only.  No scientific performance claims are made.
"""

import math
from datetime import datetime, timezone

import numpy as np
import pytest

from scientific.cases.rainfall_case import RainfallCaseResult, RainfallCaseStatus
from scientific.targets.rainfall import (
    LeakageError,
    RainfallTarget,
    RainfallTargetStatus,
    SeverityLevel,
    SeverityThresholds,
    build_rainfall_target,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_case_result(
    case_id: str = "test_case",
    status: RainfallCaseStatus = RainfallCaseStatus.ALIGNED,
    mae: float = 2.0,
    rmse: float = 3.0,
    bias: float = -0.5,
    forecast_mean: float = 5.0,
    observation_mean: float = 5.5,
    valid_cell_count: int = 100,
    missing_cell_count: int = 10,
    provenance: dict = None,
) -> RainfallCaseResult:
    """Construct a synthetic RainfallCaseResult for unit testing."""
    return RainfallCaseResult(
        case_id=case_id,
        status=status,
        forecast_metadata={},
        observation_metadata={},
        forecast_window={},
        observation_window={},
        valid_cell_count=valid_cell_count,
        missing_cell_count=missing_cell_count,
        error_statistics={
            "mae": mae,
            "rmse": rmse,
            "bias": bias,
            "forecast_mean": forecast_mean,
            "observation_mean": observation_mean,
        },
        provenance=provenance or {"reason": ""},
    )


def _make_blocked_result(
    case_id: str = "blocked_case",
    status: RainfallCaseStatus = RainfallCaseStatus.NOT_ALIGNED,
    reason: str = "Temporal mismatch",
) -> RainfallCaseResult:
    return RainfallCaseResult(
        case_id=case_id,
        status=status,
        forecast_metadata={},
        observation_metadata={},
        forecast_window={},
        observation_window={},
        valid_cell_count=0,
        missing_cell_count=0,
        error_statistics={},
        provenance={"reason": reason},
    )


# ---------------------------------------------------------------------------
# TestRainfallTargetStatus
# ---------------------------------------------------------------------------

class TestRainfallTargetStatus:
    """Verify the status enum values exist and are correctly named."""

    def test_valid_status_exists(self):
        assert RainfallTargetStatus.VALID.value == "VALID"

    def test_blocked_status_exists(self):
        assert RainfallTargetStatus.BLOCKED.value == "BLOCKED"

    def test_invalid_status_exists(self):
        assert RainfallTargetStatus.INVALID.value == "INVALID"


# ---------------------------------------------------------------------------
# TestSeverityLevel
# ---------------------------------------------------------------------------

class TestSeverityLevel:
    """Verify severity enum values and ordering."""

    def test_undefined_exists(self):
        assert SeverityLevel.UNDEFINED.value == "UNDEFINED"

    def test_all_defined_levels_exist(self):
        levels = [
            SeverityLevel.NORMAL,
            SeverityLevel.DEGRADED,
            SeverityLevel.MAJOR,
            SeverityLevel.SEVERE,
        ]
        assert len(levels) == 4


# ---------------------------------------------------------------------------
# TestSeverityThresholds
# ---------------------------------------------------------------------------

class TestSeverityThresholds:
    """Verify threshold validation and deterministic mapping."""

    def test_valid_thresholds_accepted(self):
        t = SeverityThresholds(t0=2.0, t1=5.0, t2=10.0)
        assert t.t0 == 2.0
        assert t.t1 == 5.0
        assert t.t2 == 10.0

    def test_zero_t0_accepted(self):
        """t0=0 is explicitly valid (zero RMSE is a perfect forecast)."""
        t = SeverityThresholds(t0=0.0, t1=1.0, t2=5.0)
        assert t.t0 == 0.0

    def test_non_monotone_t0_ge_t1_rejected(self):
        with pytest.raises(ValueError, match="t0 < t1"):
            SeverityThresholds(t0=5.0, t1=5.0, t2=10.0)

    def test_non_monotone_t0_gt_t1_rejected(self):
        with pytest.raises(ValueError, match="t0 < t1"):
            SeverityThresholds(t0=6.0, t1=5.0, t2=10.0)

    def test_non_monotone_t1_ge_t2_rejected(self):
        with pytest.raises(ValueError, match="t1 < t2"):
            SeverityThresholds(t0=2.0, t1=10.0, t2=10.0)

    def test_negative_t0_rejected(self):
        with pytest.raises(ValueError, match="t0 must be >= 0"):
            SeverityThresholds(t0=-1.0, t1=5.0, t2=10.0)

    def test_map_below_t0_is_normal(self):
        t = SeverityThresholds(t0=2.0, t1=5.0, t2=10.0)
        assert t.map(0.0) == SeverityLevel.NORMAL
        assert t.map(1.99) == SeverityLevel.NORMAL

    def test_map_at_t0_is_degraded(self):
        t = SeverityThresholds(t0=2.0, t1=5.0, t2=10.0)
        assert t.map(2.0) == SeverityLevel.DEGRADED

    def test_map_between_t0_t1_is_degraded(self):
        t = SeverityThresholds(t0=2.0, t1=5.0, t2=10.0)
        assert t.map(3.5) == SeverityLevel.DEGRADED

    def test_map_at_t1_is_major(self):
        t = SeverityThresholds(t0=2.0, t1=5.0, t2=10.0)
        assert t.map(5.0) == SeverityLevel.MAJOR

    def test_map_between_t1_t2_is_major(self):
        t = SeverityThresholds(t0=2.0, t1=5.0, t2=10.0)
        assert t.map(7.5) == SeverityLevel.MAJOR

    def test_map_at_t2_is_severe(self):
        t = SeverityThresholds(t0=2.0, t1=5.0, t2=10.0)
        assert t.map(10.0) == SeverityLevel.SEVERE

    def test_map_above_t2_is_severe(self):
        t = SeverityThresholds(t0=2.0, t1=5.0, t2=10.0)
        assert t.map(50.0) == SeverityLevel.SEVERE

    def test_map_non_finite_raises(self):
        t = SeverityThresholds(t0=2.0, t1=5.0, t2=10.0)
        with pytest.raises(ValueError):
            t.map(float("nan"))
        with pytest.raises(ValueError):
            t.map(float("inf"))

    def test_map_zero_error_is_normal(self):
        """Zero error (perfect forecast) must map to NORMAL."""
        t = SeverityThresholds(t0=2.0, t1=5.0, t2=10.0)
        assert t.map(0.0) == SeverityLevel.NORMAL

    def test_map_is_deterministic(self):
        """Same value always produces the same result."""
        t = SeverityThresholds(t0=2.0, t1=5.0, t2=10.0)
        results = {t.map(3.0) for _ in range(10)}
        assert len(results) == 1
        assert SeverityLevel.DEGRADED in results


# ---------------------------------------------------------------------------
# TestRainfallTargetStructure
# ---------------------------------------------------------------------------

class TestRainfallTargetStructure:
    """Verify the RainfallTarget dataclass is frozen and well-formed."""

    def test_target_is_immutable(self):
        target = RainfallTarget(
            case_id="t1",
            target_status=RainfallTargetStatus.VALID,
        )
        with pytest.raises((AttributeError, TypeError)):
            target.case_id = "new_id"

    def test_default_severity_is_undefined(self):
        target = RainfallTarget(
            case_id="t2",
            target_status=RainfallTargetStatus.VALID,
        )
        assert target.severity == SeverityLevel.UNDEFINED

    def test_has_continuous_target_false_by_default(self):
        target = RainfallTarget(
            case_id="t3",
            target_status=RainfallTargetStatus.VALID,
        )
        assert target.has_continuous_target() is False

    def test_has_severity_false_when_undefined(self):
        target = RainfallTarget(
            case_id="t4",
            target_status=RainfallTargetStatus.VALID,
            severity=SeverityLevel.UNDEFINED,
        )
        assert target.has_severity() is False

    def test_has_severity_true_when_defined(self):
        target = RainfallTarget(
            case_id="t5",
            target_status=RainfallTargetStatus.VALID,
            continuous_error=3.0,
            severity=SeverityLevel.DEGRADED,
        )
        assert target.has_severity() is True

    def test_construction_timestamp_is_set(self):
        before = datetime.utcnow()
        target = RainfallTarget(
            case_id="ts_test",
            target_status=RainfallTargetStatus.VALID,
        )
        after = datetime.utcnow()
        assert before <= target.construction_timestamp <= after


# ---------------------------------------------------------------------------
# TestBuildRainfallTargetValid
# ---------------------------------------------------------------------------

class TestBuildRainfallTargetValid:
    """Test build_rainfall_target with ALIGNED case results."""

    def test_valid_verified_result_produces_valid_target(self):
        result = _make_case_result()
        target = build_rainfall_target(result)
        assert target.target_status == RainfallTargetStatus.VALID
        assert target.case_id == "test_case"

    def test_continuous_error_equals_rmse(self):
        """continuous_error must equal rmse exactly (current metric choice)."""
        result = _make_case_result(rmse=4.567)
        target = build_rainfall_target(result)
        assert target.continuous_error == 4.567
        assert target.rmse == 4.567
        assert target.continuous_error == target.rmse

    def test_continuous_error_metric_is_rmse(self):
        result = _make_case_result()
        target = build_rainfall_target(result)
        assert target.continuous_error_metric == "rmse"

    def test_mae_preserved_exactly(self):
        result = _make_case_result(mae=1.234)
        target = build_rainfall_target(result)
        assert target.mae == 1.234

    def test_rmse_preserved_exactly(self):
        result = _make_case_result(rmse=2.345)
        target = build_rainfall_target(result)
        assert target.rmse == 2.345

    def test_bias_preserved_exactly(self):
        result = _make_case_result(bias=-0.75)
        target = build_rainfall_target(result)
        assert target.bias == -0.75

    def test_forecast_mean_preserved(self):
        result = _make_case_result(forecast_mean=8.1)
        target = build_rainfall_target(result)
        assert target.forecast_mean == 8.1

    def test_observation_mean_preserved(self):
        result = _make_case_result(observation_mean=9.2)
        target = build_rainfall_target(result)
        assert target.observation_mean == 9.2

    def test_valid_cell_count_preserved(self):
        result = _make_case_result(valid_cell_count=500)
        target = build_rainfall_target(result)
        assert target.valid_cell_count == 500

    def test_missing_cell_count_preserved(self):
        result = _make_case_result(missing_cell_count=42)
        target = build_rainfall_target(result)
        assert target.missing_cell_count == 42

    def test_has_continuous_target_true(self):
        result = _make_case_result(rmse=3.0)
        target = build_rainfall_target(result)
        assert target.has_continuous_target() is True

    def test_zero_error_produces_valid_target(self):
        """Zero RMSE (perfect forecast) must still produce a VALID target."""
        result = _make_case_result(rmse=0.0, mae=0.0, bias=0.0)
        target = build_rainfall_target(result)
        assert target.target_status == RainfallTargetStatus.VALID
        assert target.continuous_error == 0.0
        assert target.has_continuous_target() is True

    def test_zero_error_maps_to_normal_with_thresholds(self):
        """Zero RMSE with thresholds must map to NORMAL."""
        result = _make_case_result(rmse=0.0, mae=0.0, bias=0.0)
        t = SeverityThresholds(t0=2.0, t1=5.0, t2=10.0)
        target = build_rainfall_target(result, thresholds=t)
        assert target.severity == SeverityLevel.NORMAL

    def test_provenance_preserved(self):
        prov = {"alignment_status": "ALIGNED", "extra_key": "extra_val"}
        result = _make_case_result(provenance=prov)
        target = build_rainfall_target(result)
        assert target.provenance["extra_key"] == "extra_val"


# ---------------------------------------------------------------------------
# TestBuildRainfallTargetBlocked
# ---------------------------------------------------------------------------

class TestBuildRainfallTargetBlocked:
    """Blocked verification must produce BLOCKED target with no target values."""

    def _assert_no_targets(self, target: RainfallTarget) -> None:
        assert target.mae is None
        assert target.rmse is None
        assert target.bias is None
        assert target.forecast_mean is None
        assert target.observation_mean is None
        assert target.valid_cell_count is None
        assert target.missing_cell_count is None
        assert target.continuous_error is None
        assert target.continuous_error_metric is None
        assert target.severity == SeverityLevel.UNDEFINED
        assert target.has_continuous_target() is False
        assert target.has_severity() is False

    def test_temporal_mismatch_is_blocked(self):
        result = _make_blocked_result(status=RainfallCaseStatus.NOT_ALIGNED)
        target = build_rainfall_target(result)
        assert target.target_status == RainfallTargetStatus.BLOCKED
        self._assert_no_targets(target)

    def test_unspecified_window_is_blocked(self):
        result = _make_blocked_result(
            status=RainfallCaseStatus.BLOCKED_UNSPECIFIED_OBSERVATION_WINDOW,
            reason="Observation window not specified",
        )
        target = build_rainfall_target(result)
        assert target.target_status == RainfallTargetStatus.BLOCKED
        self._assert_no_targets(target)

    def test_forecast_read_error_is_blocked(self):
        result = _make_blocked_result(status=RainfallCaseStatus.FORECAST_READ_ERROR)
        target = build_rainfall_target(result)
        assert target.target_status == RainfallTargetStatus.BLOCKED
        self._assert_no_targets(target)

    def test_observation_read_error_is_blocked(self):
        result = _make_blocked_result(status=RainfallCaseStatus.OBSERVATION_READ_ERROR)
        target = build_rainfall_target(result)
        assert target.target_status == RainfallTargetStatus.BLOCKED
        self._assert_no_targets(target)

    def test_empty_valid_set_is_blocked(self):
        result = _make_blocked_result(status=RainfallCaseStatus.EMPTY_VALID_SET)
        target = build_rainfall_target(result)
        assert target.target_status == RainfallTargetStatus.BLOCKED
        self._assert_no_targets(target)

    def test_blocked_reason_preserved(self):
        result = _make_blocked_result(reason="Windows do not overlap")
        target = build_rainfall_target(result)
        assert "Windows do not overlap" in target.reason

    def test_blocked_with_thresholds_still_no_severity(self):
        """Supplying thresholds to a blocked case must not produce severity."""
        result = _make_blocked_result()
        t = SeverityThresholds(t0=2.0, t1=5.0, t2=10.0)
        target = build_rainfall_target(result, thresholds=t)
        assert target.severity == SeverityLevel.UNDEFINED


# ---------------------------------------------------------------------------
# TestBuildRainfallTargetInvalid
# ---------------------------------------------------------------------------

class TestBuildRainfallTargetInvalid:
    """Invalid verification must produce INVALID target with no target values."""

    def test_invalid_metadata_is_invalid(self):
        result = _make_blocked_result(status=RainfallCaseStatus.INVALID_METADATA)
        target = build_rainfall_target(result)
        assert target.target_status == RainfallTargetStatus.INVALID

    def test_no_tp_message_is_invalid(self):
        result = _make_blocked_result(status=RainfallCaseStatus.NO_TP_MESSAGE)
        target = build_rainfall_target(result)
        assert target.target_status == RainfallTargetStatus.INVALID

    def test_aligned_with_nan_rmse_demoted_to_invalid(self):
        """ALIGNED case with NaN RMSE must be demoted to INVALID."""
        result = RainfallCaseResult(
            case_id="nan_rmse",
            status=RainfallCaseStatus.ALIGNED,
            forecast_metadata={},
            observation_metadata={},
            forecast_window={},
            observation_window={},
            valid_cell_count=100,
            missing_cell_count=5,
            error_statistics={
                "mae": 2.0,
                "rmse": float("nan"),
                "bias": -0.5,
                "forecast_mean": 5.0,
                "observation_mean": 5.5,
            },
            provenance={},
        )
        target = build_rainfall_target(result)
        assert target.target_status == RainfallTargetStatus.INVALID
        assert target.continuous_error is None
        assert target.has_continuous_target() is False

    def test_aligned_with_missing_rmse_demoted_to_invalid(self):
        """ALIGNED case with None RMSE must be demoted to INVALID."""
        result = RainfallCaseResult(
            case_id="none_rmse",
            status=RainfallCaseStatus.ALIGNED,
            forecast_metadata={},
            observation_metadata={},
            forecast_window={},
            observation_window={},
            valid_cell_count=100,
            missing_cell_count=5,
            error_statistics={
                "mae": 2.0,
                "rmse": None,
                "bias": -0.5,
                "forecast_mean": 5.0,
                "observation_mean": 5.5,
            },
            provenance={},
        )
        target = build_rainfall_target(result)
        assert target.target_status == RainfallTargetStatus.INVALID
        assert target.continuous_error is None


# ---------------------------------------------------------------------------
# TestSeverityWithThresholds
# ---------------------------------------------------------------------------

class TestSeverityWithThresholds:
    """Test severity mapping when thresholds are explicitly supplied."""

    def _t(self) -> SeverityThresholds:
        return SeverityThresholds(t0=2.0, t1=5.0, t2=10.0)

    def test_no_thresholds_severity_is_undefined(self):
        result = _make_case_result(rmse=7.0)
        target = build_rainfall_target(result, thresholds=None)
        assert target.severity == SeverityLevel.UNDEFINED
        assert target.has_severity() is False

    def test_with_thresholds_normal(self):
        result = _make_case_result(rmse=1.0)
        target = build_rainfall_target(result, thresholds=self._t())
        assert target.severity == SeverityLevel.NORMAL

    def test_with_thresholds_degraded(self):
        result = _make_case_result(rmse=3.0)
        target = build_rainfall_target(result, thresholds=self._t())
        assert target.severity == SeverityLevel.DEGRADED

    def test_with_thresholds_major(self):
        result = _make_case_result(rmse=7.0)
        target = build_rainfall_target(result, thresholds=self._t())
        assert target.severity == SeverityLevel.MAJOR

    def test_with_thresholds_severe(self):
        result = _make_case_result(rmse=15.0)
        target = build_rainfall_target(result, thresholds=self._t())
        assert target.severity == SeverityLevel.SEVERE

    def test_severity_at_exact_boundary_t0(self):
        """Value exactly at t0 maps to DEGRADED (lower-bound semantics)."""
        result = _make_case_result(rmse=2.0)
        target = build_rainfall_target(result, thresholds=self._t())
        assert target.severity == SeverityLevel.DEGRADED

    def test_severity_at_exact_boundary_t1(self):
        result = _make_case_result(rmse=5.0)
        target = build_rainfall_target(result, thresholds=self._t())
        assert target.severity == SeverityLevel.MAJOR

    def test_severity_at_exact_boundary_t2(self):
        result = _make_case_result(rmse=10.0)
        target = build_rainfall_target(result, thresholds=self._t())
        assert target.severity == SeverityLevel.SEVERE

    def test_severity_mapping_is_deterministic(self):
        """Same case result with same thresholds always produces same severity."""
        result = _make_case_result(rmse=6.5)
        t = self._t()
        severities = {build_rainfall_target(result, thresholds=t).severity for _ in range(5)}
        assert len(severities) == 1

    def test_has_severity_true_when_thresholds_supplied(self):
        result = _make_case_result(rmse=3.0)
        target = build_rainfall_target(result, thresholds=self._t())
        assert target.has_severity() is True


# ---------------------------------------------------------------------------
# TestLeakageGuard
# ---------------------------------------------------------------------------

class TestLeakageGuard:
    """Predictor feature arrays must never enter target records."""

    def test_leakage_error_raised_for_named_feature_array(self):
        """Passing a named ensemble feature array raises LeakageError."""
        from scientific.targets.rainfall import LeakageError, _assert_no_feature_arrays
        with pytest.raises(LeakageError, match="ensemble_mean"):
            _assert_no_feature_arrays({"ensemble_mean": np.zeros((10, 10))})

    def test_leakage_error_raised_for_any_2d_array(self):
        """Any 2D numpy array in kwargs raises LeakageError."""
        from scientific.targets.rainfall import LeakageError, _assert_no_feature_arrays
        with pytest.raises(LeakageError, match="spatial arrays"):
            _assert_no_feature_arrays({"unknown_field": np.zeros((5, 5))})

    def test_scalar_float_does_not_raise(self):
        """Scalar floats (legitimate target statistics) must not raise."""
        from scientific.targets.rainfall import _assert_no_feature_arrays
        # Should not raise
        _assert_no_feature_arrays({"mae": 2.0, "rmse": 3.0, "bias": -0.5})

    def test_none_values_do_not_raise(self):
        """None values must not raise."""
        from scientific.targets.rainfall import _assert_no_feature_arrays
        _assert_no_feature_arrays({"mae": None, "rmse": None})

    def test_1d_array_of_size_1_does_not_raise(self):
        """A 0-d scalar numpy array (ndim==0) must not raise."""
        from scientific.targets.rainfall import _assert_no_feature_arrays
        scalar_array = np.float64(3.0)  # ndim == 0
        _assert_no_feature_arrays({"value": scalar_array})

    def test_all_24_feature_names_are_guarded(self):
        """Every known feature array name triggers LeakageError."""
        from scientific.targets.rainfall import (
            LeakageError,
            _assert_no_feature_arrays,
            _FEATURE_ARRAY_NAMES,
        )
        for name in _FEATURE_ARRAY_NAMES:
            with pytest.raises(LeakageError):
                _assert_no_feature_arrays({name: np.zeros((5, 5))})

    def test_target_record_stores_no_feature_fields(self):
        """A VALID RainfallTarget must not have any feature array attributes."""
        from scientific.targets.rainfall import _FEATURE_ARRAY_NAMES
        result = _make_case_result()
        target = build_rainfall_target(result)
        for name in _FEATURE_ARRAY_NAMES:
            assert not hasattr(target, name), (
                f"RainfallTarget must not have attribute '{name}' — "
                "it is a predictor feature, not a target."
            )


# ---------------------------------------------------------------------------
# TestProvenanceAndReason
# ---------------------------------------------------------------------------

class TestProvenanceAndReason:
    """Target provenance and reason fields must be preserved faithfully."""

    def test_valid_target_reason_is_empty(self):
        result = _make_case_result()
        target = build_rainfall_target(result)
        assert target.reason == ""

    def test_blocked_reason_from_provenance(self):
        result = _make_blocked_result(
            reason="Forecast window (00:00-00:00) does not match observation window (08:30-08:30)"
        )
        target = build_rainfall_target(result)
        assert "does not match" in target.reason

    def test_valid_provenance_dict_preserved(self):
        prov = {
            "alignment_status": "ALIGNED",
            "forecast_path": "data/raw/tigge/test.grib",
            "case_id": "prov_case",
        }
        result = _make_case_result(provenance=prov)
        target = build_rainfall_target(result)
        assert target.provenance["forecast_path"] == "data/raw/tigge/test.grib"
        assert target.provenance["alignment_status"] == "ALIGNED"

    def test_case_id_preserved(self):
        result = _make_case_result(case_id="audit_case_001")
        target = build_rainfall_target(result)
        assert target.case_id == "audit_case_001"

    def test_construction_timestamp_is_recent(self):
        before = datetime.utcnow()
        result = _make_case_result()
        target = build_rainfall_target(result)
        after = datetime.utcnow()
        assert before <= target.construction_timestamp <= after


# ---------------------------------------------------------------------------
# TestEdgeCases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Edge cases: NaN metrics, empty provenance, boundary values."""

    def test_empty_provenance_accepted(self):
        result = RainfallCaseResult(
            case_id="empty_prov",
            status=RainfallCaseStatus.ALIGNED,
            forecast_metadata={},
            observation_metadata={},
            forecast_window={},
            observation_window={},
            valid_cell_count=50,
            missing_cell_count=0,
            error_statistics={"mae": 1.0, "rmse": 1.5, "bias": 0.0,
                              "forecast_mean": 4.0, "observation_mean": 4.0},
            provenance={},
        )
        target = build_rainfall_target(result)
        assert target.target_status == RainfallTargetStatus.VALID

    def test_all_blocked_statuses_produce_no_targets(self):
        """Every blocked RainfallCaseStatus must produce no continuous target."""
        blocked_statuses = [
            RainfallCaseStatus.NOT_ALIGNED,
            RainfallCaseStatus.BLOCKED_UNSPECIFIED_OBSERVATION_WINDOW,
            RainfallCaseStatus.EMPTY_VALID_SET,
            RainfallCaseStatus.FORECAST_READ_ERROR,
            RainfallCaseStatus.OBSERVATION_READ_ERROR,
        ]
        for status in blocked_statuses:
            result = _make_blocked_result(status=status)
            target = build_rainfall_target(result)
            assert target.target_status == RainfallTargetStatus.BLOCKED, (
                f"Expected BLOCKED for {status}, got {target.target_status}"
            )
            assert target.continuous_error is None
            assert target.has_continuous_target() is False

    def test_all_invalid_statuses_produce_no_targets(self):
        """Every invalid RainfallCaseStatus must produce no continuous target."""
        invalid_statuses = [
            RainfallCaseStatus.INVALID_METADATA,
            RainfallCaseStatus.NO_TP_MESSAGE,
        ]
        for status in invalid_statuses:
            result = _make_blocked_result(status=status)
            target = build_rainfall_target(result)
            assert target.target_status == RainfallTargetStatus.INVALID
            assert target.continuous_error is None

    def test_large_rmse_accepted(self):
        """Very large RMSE (extreme bust) must not be rejected."""
        result = _make_case_result(rmse=999.9)
        target = build_rainfall_target(result)
        assert target.target_status == RainfallTargetStatus.VALID
        assert target.continuous_error == 999.9

    def test_very_small_positive_rmse_accepted(self):
        result = _make_case_result(rmse=1e-6)
        target = build_rainfall_target(result)
        assert target.target_status == RainfallTargetStatus.VALID
        assert math.isclose(target.continuous_error, 1e-6)

    def test_negative_bias_accepted(self):
        """Negative bias (forecast underestimates) is scientifically valid."""
        result = _make_case_result(bias=-10.0)
        target = build_rainfall_target(result)
        assert target.bias == -10.0

    def test_positive_bias_accepted(self):
        result = _make_case_result(bias=7.5)
        target = build_rainfall_target(result)
        assert target.bias == 7.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
