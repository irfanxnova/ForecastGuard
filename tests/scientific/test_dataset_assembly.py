"""Tests for the dataset assembly layer.

All tests use synthetic data only.  No scientific performance claims are made.
No filesystem operations.
"""

from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pytest

from scientific.dataset.assembly import (
    TARGET_METRIC_NAMES,
    AssembledSample,
    AssemblyError,
    AssemblyLeakageError,
    SampleStatus,
    _check_predictor_leakage,
    _extract_spatial_stats,
    assemble_sample,
    assemble_samples,
)
from scientific.dataset.builder import DatasetRecord, DatasetRecordStatus
from scientific.targets.rainfall import (
    RainfallTarget,
    RainfallTargetStatus,
    SeverityLevel,
    SeverityThresholds,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FEATURE_NAMES = [
    "ensemble_mean", "ensemble_median", "ensemble_min", "ensemble_max",
    "ensemble_std", "ensemble_range", "ensemble_iqr",
    "ensemble_p10", "ensemble_p25", "ensemble_p75", "ensemble_p90",
    "coefficient_of_variation", "ensemble_skewness",
    "probability_rain_gt_1mm", "probability_rain_gt_10mm",
    "probability_rain_gt_25mm", "probability_rain_gt_50mm",
    "probability_rain_gt_100mm",
    "gradient_magnitude", "latitude_gradient", "longitude_gradient",
    "mean_pairwise_member_difference", "maximum_ensemble_gap",
    "member_agreement_fraction",
]

_INIT_TIME = datetime(2025, 9, 1, 0, 0, tzinfo=timezone.utc)


def _make_feature_array(value: float = 5.0, shape=(4, 4)) -> np.ndarray:
    return np.full(shape, value, dtype=np.float64)


def _make_valid_record(
    case_id: str = "case_001",
    init_time: Optional[datetime] = _INIT_TIME,
    lead_hours: int = 24,
    member_count: int = 11,
) -> DatasetRecord:
    """Build a synthetic VALID DatasetRecord with 24 small feature arrays."""
    feature_arrays = {name: _make_feature_array() for name in _FEATURE_NAMES}
    return DatasetRecord(
        case_id=case_id,
        status=DatasetRecordStatus.VALID,
        forecast_initialization_time=init_time,
        forecast_lead_hours=lead_hours,
        forecast_source_model="NCMRWF",
        observation_source="IMD_DAILY",
        ensemble_member_count=member_count,
        grid_shape=(4, 4),
        mae=2.0,
        rmse=3.0,
        bias=-0.5,
        forecast_mean=5.0,
        observation_mean=5.5,
        valid_cell_count=16,
        missing_cell_count=0,
        feature_names=_FEATURE_NAMES,
        **feature_arrays,
    )


def _make_valid_target(
    case_id: str = "case_001",
    rmse: float = 3.0,
    thresholds: Optional[SeverityThresholds] = None,
) -> RainfallTarget:
    return RainfallTarget(
        case_id=case_id,
        target_status=RainfallTargetStatus.VALID,
        mae=2.0,
        rmse=rmse,
        bias=-0.5,
        forecast_mean=5.0,
        observation_mean=5.5,
        valid_cell_count=16,
        missing_cell_count=0,
        continuous_error=rmse,
        continuous_error_metric="rmse",
        severity=thresholds.map(rmse) if thresholds else SeverityLevel.UNDEFINED,
    )


def _make_blocked_target(
    case_id: str = "case_001",
    status: RainfallTargetStatus = RainfallTargetStatus.BLOCKED,
    reason: str = "Temporal mismatch",
) -> RainfallTarget:
    return RainfallTarget(
        case_id=case_id,
        target_status=status,
        reason=reason,
    )


def _make_blocked_record(case_id: str = "case_001") -> DatasetRecord:
    return DatasetRecord(
        case_id=case_id,
        status=DatasetRecordStatus.BLOCKED_TEMPORAL_MISMATCH,
        reason="Temporal mismatch",
        forecast_initialization_time=_INIT_TIME,
    )


# ---------------------------------------------------------------------------
# TestExtractSpatialStats
# ---------------------------------------------------------------------------


class TestExtractSpatialStats:
    """Verify scalar spatial statistics extraction from feature arrays."""

    def test_uniform_array_mean(self):
        arr = np.full((4, 4), 5.0)
        stats = _extract_spatial_stats(arr, "ensemble_mean")
        assert stats["ensemble_mean_mean"] == pytest.approx(5.0)

    def test_uniform_array_std(self):
        arr = np.full((4, 4), 5.0)
        stats = _extract_spatial_stats(arr, "ensemble_mean")
        assert stats["ensemble_mean_std"] == pytest.approx(0.0)

    def test_all_nan_produces_none(self):
        arr = np.full((4, 4), np.nan)
        stats = _extract_spatial_stats(arr, "ensemble_mean")
        for v in stats.values():
            assert v is None

    def test_returns_five_statistics(self):
        arr = np.arange(16, dtype=float).reshape(4, 4)
        stats = _extract_spatial_stats(arr, "some_feature")
        assert set(stats.keys()) == {
            "some_feature_mean",
            "some_feature_std",
            "some_feature_max",
            "some_feature_p10",
            "some_feature_p90",
        }

    def test_partial_nan_ignored(self):
        arr = np.array([[1.0, np.nan], [3.0, 4.0]])
        stats = _extract_spatial_stats(arr, "f")
        assert stats["f_mean"] == pytest.approx((1.0 + 3.0 + 4.0) / 3)


# ---------------------------------------------------------------------------
# TestLeakageGuard
# ---------------------------------------------------------------------------


class TestLeakageGuard:
    """TARGET_METRIC_NAMES must never enter predictor_dict."""

    def test_target_metric_names_is_nonempty(self):
        assert len(TARGET_METRIC_NAMES) > 0

    def test_rmse_rejected_from_predictors(self):
        with pytest.raises(AssemblyLeakageError, match="rmse"):
            _check_predictor_leakage({"rmse": 3.0})

    def test_mae_rejected_from_predictors(self):
        with pytest.raises(AssemblyLeakageError, match="mae"):
            _check_predictor_leakage({"mae": 2.0})

    def test_bias_rejected_from_predictors(self):
        with pytest.raises(AssemblyLeakageError, match="bias"):
            _check_predictor_leakage({"bias": -0.5})

    def test_observation_mean_rejected_from_predictors(self):
        with pytest.raises(AssemblyLeakageError):
            _check_predictor_leakage({"observation_mean": 5.5})

    def test_severity_rejected_from_predictors(self):
        with pytest.raises(AssemblyLeakageError):
            _check_predictor_leakage({"severity": "NORMAL"})

    def test_continuous_error_rejected_from_predictors(self):
        with pytest.raises(AssemblyLeakageError):
            _check_predictor_leakage({"continuous_error": 3.0})

    def test_2d_array_rejected_from_predictors(self):
        with pytest.raises(AssemblyLeakageError, match="spatial array"):
            _check_predictor_leakage({"unknown_field": np.zeros((5, 5))})

    def test_scalar_float_accepted_in_predictors(self):
        # Should not raise
        _check_predictor_leakage({
            "forecast_lead_hours": 24.0,
            "ensemble_member_count": 11.0,
            "grid_n_lat": 4.0,
            "grid_n_lon": 4.0,
        })

    def test_none_value_accepted_in_predictors(self):
        _check_predictor_leakage({"ensemble_mean_mean": None})


# ---------------------------------------------------------------------------
# TestAssembleSampleValid
# ---------------------------------------------------------------------------


class TestAssembleSampleValid:
    """A VALID record + VALID target must produce a VALID_TRAINABLE sample."""

    def test_valid_case_produces_valid_trainable(self):
        record = _make_valid_record()
        target = _make_valid_target()
        sample = assemble_sample(record, target)
        assert sample.sample_status == SampleStatus.VALID_TRAINABLE

    def test_case_id_preserved(self):
        record = _make_valid_record(case_id="case_xyz")
        target = _make_valid_target(case_id="case_xyz")
        sample = assemble_sample(record, target)
        assert sample.case_id == "case_xyz"

    def test_is_trainable(self):
        sample = assemble_sample(_make_valid_record(), _make_valid_target())
        assert sample.is_trainable() is True

    def test_has_predictors(self):
        sample = assemble_sample(_make_valid_record(), _make_valid_target())
        assert sample.has_predictors() is True

    def test_has_target(self):
        sample = assemble_sample(_make_valid_record(), _make_valid_target())
        assert sample.has_target() is True

    def test_predictor_names_nonempty(self):
        sample = assemble_sample(_make_valid_record(), _make_valid_target())
        assert len(sample.predictor_names) > 0

    def test_predictor_names_match_predictor_dict_keys(self):
        sample = assemble_sample(_make_valid_record(), _make_valid_target())
        assert set(sample.predictor_names) == set(sample.predictor_dict.keys())

    def test_predictor_count_is_120_plus_metadata(self):
        """24 feature arrays × 5 stats = 120, plus 4 metadata + 1 forecast_mean_spatial = 125."""
        sample = assemble_sample(_make_valid_record(), _make_valid_target())
        # 24 features × 5 stats = 120
        # metadata: forecast_lead_hours, ensemble_member_count, grid_n_lat, grid_n_lon = 4
        # forecast_mean_spatial = 1
        assert len(sample.predictor_dict) == 125

    def test_continuous_error_equals_rmse(self):
        target = _make_valid_target(rmse=4.567)
        sample = assemble_sample(_make_valid_record(), target)
        assert sample.continuous_error == pytest.approx(4.567)

    def test_forecast_init_time_preserved(self):
        sample = assemble_sample(_make_valid_record(), _make_valid_target())
        assert sample.forecast_initialization_time == _INIT_TIME

    def test_forecast_lead_hours_preserved(self):
        sample = assemble_sample(_make_valid_record(lead_hours=24), _make_valid_target())
        assert sample.forecast_lead_hours == 24

    def test_ensemble_member_count_preserved(self):
        sample = assemble_sample(_make_valid_record(member_count=11), _make_valid_target())
        assert sample.ensemble_member_count == 11

    def test_sample_is_frozen(self):
        sample = assemble_sample(_make_valid_record(), _make_valid_target())
        with pytest.raises((AttributeError, TypeError)):
            sample.case_id = "new_id"

    def test_assembly_timestamp_set(self):
        before = datetime.utcnow()
        sample = assemble_sample(_make_valid_record(), _make_valid_target())
        after = datetime.utcnow()
        assert before <= sample.assembly_timestamp <= after

    def test_deterministic_assembly(self):
        """Same inputs always produce identical predictor dicts."""
        record = _make_valid_record()
        target = _make_valid_target()
        s1 = assemble_sample(record, target)
        s2 = assemble_sample(record, target)
        assert s1.predictor_names == s2.predictor_names
        assert s1.predictor_dict == s2.predictor_dict
        assert s1.continuous_error == s2.continuous_error


# ---------------------------------------------------------------------------
# TestAssembleSampleLeakage
# ---------------------------------------------------------------------------


class TestAssembleSampleLeakage:
    """Predictor fields must never contain target metrics or spatial arrays."""

    def _get_sample(self) -> AssembledSample:
        return assemble_sample(_make_valid_record(), _make_valid_target())

    def test_rmse_not_in_predictor_dict(self):
        sample = self._get_sample()
        assert "rmse" not in sample.predictor_dict

    def test_mae_not_in_predictor_dict(self):
        sample = self._get_sample()
        assert "mae" not in sample.predictor_dict

    def test_bias_not_in_predictor_dict(self):
        sample = self._get_sample()
        assert "bias" not in sample.predictor_dict

    def test_observation_mean_not_in_predictor_dict(self):
        sample = self._get_sample()
        assert "observation_mean" not in sample.predictor_dict

    def test_continuous_error_not_in_predictor_dict(self):
        sample = self._get_sample()
        assert "continuous_error" not in sample.predictor_dict

    def test_severity_not_in_predictor_dict(self):
        sample = self._get_sample()
        assert "severity" not in sample.predictor_dict

    def test_all_predictor_values_are_scalars_or_none(self):
        """No predictor value should be a numpy ndarray."""
        sample = self._get_sample()
        for key, val in sample.predictor_dict.items():
            assert not (isinstance(val, np.ndarray) and val.ndim > 0), (
                f"Predictor '{key}' is a spatial array — leakage risk."
            )

    def test_target_dict_contains_no_arrays(self):
        sample = self._get_sample()
        for key, val in sample.target_dict.items():
            assert not (isinstance(val, np.ndarray) and val.ndim > 0), (
                f"Target field '{key}' is a spatial array."
            )

    def test_rmse_is_in_target_dict(self):
        sample = self._get_sample()
        assert "rmse" in sample.target_dict

    def test_observation_mean_is_in_target_dict(self):
        sample = self._get_sample()
        assert "observation_mean" in sample.target_dict

    def test_no_target_metric_appears_in_predictor_names(self):
        sample = self._get_sample()
        contaminated = TARGET_METRIC_NAMES & set(sample.predictor_names)
        assert not contaminated, (
            f"Target metrics found in predictor_names: {contaminated}"
        )

    def test_verification_accumulation_end_not_in_predictors(self):
        """Observation-window data must not enter predictor_dict.
        Only forecast_initialization_time and forecast_lead_hours are allowed
        as temporal predictors.
        """
        sample = self._get_sample()
        assert "forecast_accumulation_end" not in sample.predictor_dict
        assert "observation_accumulation_end" not in sample.predictor_dict
        assert "observation_accumulation_start" not in sample.predictor_dict
        assert "observation_window_metadata" not in sample.predictor_dict


# ---------------------------------------------------------------------------
# TestAssembleSampleBlocked
# ---------------------------------------------------------------------------


class TestAssembleSampleBlocked:
    """Blocked cases must produce BLOCKED samples with no predictors or targets."""

    def _blocked(self) -> AssembledSample:
        return assemble_sample(
            _make_blocked_record(),
            _make_blocked_target(),
        )

    def test_blocked_case_status(self):
        sample = self._blocked()
        assert sample.sample_status == SampleStatus.BLOCKED

    def test_blocked_not_trainable(self):
        assert self._blocked().is_trainable() is False

    def test_blocked_no_predictors(self):
        assert not self._blocked().has_predictors()

    def test_blocked_no_continuous_target(self):
        assert self._blocked().continuous_error is None
        assert not self._blocked().has_target()

    def test_blocked_reason_preserved(self):
        sample = assemble_sample(
            _make_blocked_record(),
            _make_blocked_target(reason="Window not specified"),
        )
        assert "Window not specified" in sample.reason

    def test_blocked_severity_undefined(self):
        assert self._blocked().severity == SeverityLevel.UNDEFINED

    def test_blocked_target_dict_empty(self):
        assert self._blocked().target_dict == {}

    def test_blocked_predictor_dict_empty(self):
        assert self._blocked().predictor_dict == {}


# ---------------------------------------------------------------------------
# TestAssembleSampleInvalid
# ---------------------------------------------------------------------------


class TestAssembleSampleInvalid:
    """Invalid targets must produce INVALID samples."""

    def test_invalid_target_produces_invalid_sample(self):
        record = _make_blocked_record()
        target = _make_blocked_target(status=RainfallTargetStatus.INVALID)
        sample = assemble_sample(record, target)
        assert sample.sample_status == SampleStatus.INVALID

    def test_invalid_not_trainable(self):
        record = _make_blocked_record()
        target = _make_blocked_target(status=RainfallTargetStatus.INVALID)
        sample = assemble_sample(record, target)
        assert sample.is_trainable() is False


# ---------------------------------------------------------------------------
# TestAssembleSampleValidNoTarget
# ---------------------------------------------------------------------------


class TestAssembleSampleValidNoTarget:
    """VALID record but continuous_error is None → VALID_NO_TARGET."""

    def test_valid_no_target_status(self):
        record = _make_valid_record()
        target = RainfallTarget(
            case_id="case_001",
            target_status=RainfallTargetStatus.VALID,
            continuous_error=None,   # missing
            continuous_error_metric=None,
        )
        sample = assemble_sample(record, target)
        assert sample.sample_status == SampleStatus.VALID_NO_TARGET
        assert sample.is_trainable() is False


# ---------------------------------------------------------------------------
# TestAssembleError
# ---------------------------------------------------------------------------


class TestAssembleError:
    """Assembly must raise AssemblyError on case_id mismatch."""

    def test_case_id_mismatch_raises(self):
        record = _make_valid_record(case_id="case_A")
        target = _make_valid_target(case_id="case_B")
        with pytest.raises(AssemblyError, match="mismatch"):
            assemble_sample(record, target)


# ---------------------------------------------------------------------------
# TestAssembleSamples
# ---------------------------------------------------------------------------


class TestAssembleSamples:
    """assemble_samples must process a sequence deterministically."""

    def test_empty_sequence(self):
        assert assemble_samples([]) == []

    def test_order_preserved(self):
        pairs = [
            (_make_valid_record(case_id=f"c{i}"), _make_valid_target(case_id=f"c{i}"))
            for i in range(5)
        ]
        samples = assemble_samples(pairs)
        assert [s.case_id for s in samples] == [f"c{i}" for i in range(5)]

    def test_mixed_statuses_assembled(self):
        pairs = [
            (_make_valid_record(case_id="valid"), _make_valid_target(case_id="valid")),
            (_make_blocked_record(case_id="blocked"), _make_blocked_target(case_id="blocked")),
        ]
        samples = assemble_samples(pairs)
        statuses = {s.case_id: s.sample_status for s in samples}
        assert statuses["valid"] == SampleStatus.VALID_TRAINABLE
        assert statuses["blocked"] == SampleStatus.BLOCKED

    def test_deterministic_repeated_call(self):
        pairs = [
            (_make_valid_record(case_id=f"c{i}"), _make_valid_target(case_id=f"c{i}"))
            for i in range(3)
        ]
        s1 = assemble_samples(pairs)
        s2 = assemble_samples(pairs)
        for a, b in zip(s1, s2):
            assert a.predictor_dict == b.predictor_dict
            assert a.continuous_error == b.continuous_error

    def test_blocked_not_silently_converted_to_trainable(self):
        """No blocked case should accidentally become VALID_TRAINABLE."""
        from scientific.dataset.builder import DatasetRecordStatus
        blocked_statuses = [
            DatasetRecordStatus.BLOCKED_TEMPORAL_MISMATCH,
            DatasetRecordStatus.BLOCKED_UNSPECIFIED_OBSERVATION_WINDOW,
            DatasetRecordStatus.BLOCKED_INVALID_METADATA,
            DatasetRecordStatus.BLOCKED_EMPTY_VALID_SET,
            DatasetRecordStatus.BLOCKED_FORECAST_READ_ERROR,
            DatasetRecordStatus.BLOCKED_OBSERVATION_READ_ERROR,
        ]
        for ds in blocked_statuses:
            record = DatasetRecord(
                case_id=f"blocked_{ds.value}",
                status=ds,
                reason="blocked",
            )
            target = RainfallTarget(
                case_id=f"blocked_{ds.value}",
                target_status=RainfallTargetStatus.BLOCKED,
                reason="blocked",
            )
            sample = assemble_sample(record, target)
            assert sample.sample_status != SampleStatus.VALID_TRAINABLE, (
                f"Blocked case {ds} must not become VALID_TRAINABLE"
            )

    def test_provenance_preserved(self):
        prov = {"key": "value", "forecast_path": "some/path"}
        record = _make_valid_record()
        target = RainfallTarget(
            case_id="case_001",
            target_status=RainfallTargetStatus.VALID,
            continuous_error=3.0,
            continuous_error_metric="rmse",
            provenance=prov,
        )
        sample = assemble_sample(record, target)
        assert sample.provenance["key"] == "value"


# ---------------------------------------------------------------------------
# TestForecastMeanSpatialPredictor
# ---------------------------------------------------------------------------


class TestForecastMeanSpatialPredictor:
    """forecast_mean_spatial must be a pure forecast-derived predictor.

    INVARIANT: forecast_mean_spatial is computed from record.ensemble_mean
    (the ensemble mean TP feature array) using only finite forecast values.
    It must be completely independent of observation values, observation
    validity masks, and all target/verification fields.
    """

    def _sample(
        self,
        ensemble_mean_values: float = 5.0,
        obs_mean_override: float = 5.5,
    ) -> AssembledSample:
        """Build a sample with a known ensemble_mean array value."""
        feature_arrays = {name: _make_feature_array(5.0) for name in _FEATURE_NAMES}
        feature_arrays["ensemble_mean"] = np.full((4, 4), ensemble_mean_values)
        record = DatasetRecord(
            case_id="fm_test",
            status=DatasetRecordStatus.VALID,
            forecast_initialization_time=_INIT_TIME,
            forecast_lead_hours=24,
            ensemble_member_count=11,
            grid_shape=(4, 4),
            mae=2.0,
            rmse=3.0,
            bias=-0.5,
            forecast_mean=ensemble_mean_values,   # verification-masked value
            observation_mean=obs_mean_override,
            valid_cell_count=16,
            missing_cell_count=0,
            feature_names=_FEATURE_NAMES,
            **feature_arrays,
        )
        target = RainfallTarget(
            case_id="fm_test",
            target_status=RainfallTargetStatus.VALID,
            mae=2.0,
            rmse=3.0,
            bias=-0.5,
            forecast_mean=ensemble_mean_values,
            observation_mean=obs_mean_override,
            valid_cell_count=16,
            missing_cell_count=0,
            continuous_error=3.0,
            continuous_error_metric="rmse",
        )
        return assemble_sample(record, target)

    def test_forecast_mean_spatial_present_in_predictors(self):
        """forecast_mean_spatial must appear in predictor_dict."""
        sample = self._sample()
        assert "forecast_mean_spatial" in sample.predictor_dict
        assert "forecast_mean_spatial" in sample.predictor_names

    def test_forecast_mean_spatial_value_matches_ensemble_mean(self):
        """Value must equal the mean of finite values in ensemble_mean array."""
        sample = self._sample(ensemble_mean_values=7.25)
        assert sample.predictor_dict["forecast_mean_spatial"] == pytest.approx(7.25)

    def test_forecast_mean_spatial_changes_when_forecast_changes(self):
        """forecast_mean_spatial must track changes in the forecast field."""
        s1 = self._sample(ensemble_mean_values=3.0)
        s2 = self._sample(ensemble_mean_values=9.0)
        assert s1.predictor_dict["forecast_mean_spatial"] == pytest.approx(3.0)
        assert s2.predictor_dict["forecast_mean_spatial"] == pytest.approx(9.0)

    def test_forecast_mean_spatial_unchanged_when_obs_mean_changes(self):
        """Changing observation_mean must NOT change forecast_mean_spatial.

        This is the core leakage test: the predictor is observation-independent.
        Same ensemble_mean array, different observation_mean in the target.
        """
        s1 = self._sample(ensemble_mean_values=5.0, obs_mean_override=3.0)
        s2 = self._sample(ensemble_mean_values=5.0, obs_mean_override=20.0)
        assert s1.predictor_dict["forecast_mean_spatial"] == pytest.approx(
            s2.predictor_dict["forecast_mean_spatial"]
        )

    def test_forecast_mean_spatial_unchanged_when_valid_cell_count_changes(self):
        """Changing valid_cell_count (observation-mask-derived) must NOT change
        forecast_mean_spatial.  The predictor uses ALL finite forecast values,
        not just those at observation-valid cells.
        """
        feature_arrays = {name: _make_feature_array(5.0) for name in _FEATURE_NAMES}
        feature_arrays["ensemble_mean"] = np.full((4, 4), 5.0)

        def make_with_cell_count(valid: int, missing: int) -> AssembledSample:
            record = DatasetRecord(
                case_id="cell_count_test",
                status=DatasetRecordStatus.VALID,
                forecast_initialization_time=_INIT_TIME,
                forecast_lead_hours=24,
                ensemble_member_count=11,
                grid_shape=(4, 4),
                mae=2.0, rmse=3.0, bias=0.0,
                forecast_mean=5.0,
                observation_mean=5.0,
                valid_cell_count=valid,
                missing_cell_count=missing,
                feature_names=_FEATURE_NAMES,
                **feature_arrays,
            )
            target = RainfallTarget(
                case_id="cell_count_test",
                target_status=RainfallTargetStatus.VALID,
                mae=2.0, rmse=3.0, bias=0.0,
                forecast_mean=5.0,
                observation_mean=5.0,
                valid_cell_count=valid,
                missing_cell_count=missing,
                continuous_error=3.0,
                continuous_error_metric="rmse",
            )
            return assemble_sample(record, target)

        s_full = make_with_cell_count(valid=16, missing=0)
        s_partial = make_with_cell_count(valid=8, missing=8)

        # forecast_mean_spatial is from ensemble_mean array (all 5.0) — unchanged
        assert s_full.predictor_dict["forecast_mean_spatial"] == pytest.approx(5.0)
        assert s_partial.predictor_dict["forecast_mean_spatial"] == pytest.approx(5.0)

    def test_forecast_mean_not_in_predictor_dict(self):
        """The verification-derived forecast_mean must NOT appear in predictors."""
        sample = self._sample()
        assert "forecast_mean" not in sample.predictor_dict

    def test_forecast_mean_remains_in_target_dict(self):
        """forecast_mean must still appear in target_dict (as verification metadata)."""
        sample = self._sample()
        assert "forecast_mean" in sample.target_dict

    def test_observation_mean_absent_from_predictor_dict(self):
        """observation_mean must never appear in predictor_dict."""
        sample = self._sample()
        assert "observation_mean" not in sample.predictor_dict

    def test_predictor_count_is_125(self):
        """24 × 5 stats = 120, + 4 metadata + 1 forecast_mean_spatial = 125."""
        sample = self._sample()
        assert len(sample.predictor_dict) == 125


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
