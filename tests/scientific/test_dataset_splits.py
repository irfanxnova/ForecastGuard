"""Tests for chronological dataset splitting.

All tests use synthetic data only.  No filesystem operations.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

import pytest

from scientific.dataset.assembly import AssembledSample, SampleStatus
from scientific.dataset.splits import (
    ChronologicalSplitter,
    SplitConfigurationError,
    SplitDataError,
    SplitResult,
)
from scientific.targets.rainfall import RainfallTargetStatus, SeverityLevel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)


def _dt(days: int) -> datetime:
    return _BASE + timedelta(days=days)


def _make_sample(
    case_id: str,
    init_time: Optional[datetime],
    status: SampleStatus = SampleStatus.VALID_TRAINABLE,
) -> AssembledSample:
    return AssembledSample(
        case_id=case_id,
        sample_status=status,
        forecast_initialization_time=init_time,
        target_status=RainfallTargetStatus.VALID,
    )


def _make_dated_samples(n: int, step_days: int = 1) -> List[AssembledSample]:
    """n samples each with a distinct initialization time, step_days apart."""
    return [_make_sample(f"case_{i:03d}", _dt(i * step_days)) for i in range(n)]


# ---------------------------------------------------------------------------
# TestSplitConfigurationErrors
# ---------------------------------------------------------------------------


class TestSplitConfigurationErrors:
    """Invalid splitter configuration must be rejected at construction time."""

    def test_no_parameters_raises(self):
        with pytest.raises(SplitConfigurationError, match="boundary or ratio"):
            ChronologicalSplitter()

    def test_boundary_and_ratio_together_raises(self):
        with pytest.raises(SplitConfigurationError, match="not both"):
            ChronologicalSplitter(
                train_end=_dt(70),
                train_ratio=0.7,
                val_ratio=0.1,
                test_ratio=0.2,
            )

    def test_val_end_before_train_end_raises(self):
        with pytest.raises(SplitConfigurationError, match="after train_end"):
            ChronologicalSplitter(
                train_end=_dt(70),
                val_end=_dt(60),
            )

    def test_val_end_equal_train_end_raises(self):
        with pytest.raises(SplitConfigurationError, match="after train_end"):
            ChronologicalSplitter(
                train_end=_dt(70),
                val_end=_dt(70),
            )

    def test_ratios_not_summing_to_one_raises(self):
        with pytest.raises(SplitConfigurationError, match="sum to 1"):
            ChronologicalSplitter(
                train_ratio=0.7,
                val_ratio=0.2,
                test_ratio=0.2,
            )

    def test_zero_train_ratio_raises(self):
        with pytest.raises(SplitConfigurationError, match="train_ratio must be > 0"):
            ChronologicalSplitter(
                train_ratio=0.0,
                val_ratio=0.1,
                test_ratio=0.9,
            )

    def test_zero_test_ratio_raises(self):
        with pytest.raises(SplitConfigurationError, match="test_ratio must be > 0"):
            ChronologicalSplitter(
                train_ratio=0.9,
                val_ratio=0.1,
                test_ratio=0.0,
            )

    def test_negative_val_ratio_raises(self):
        with pytest.raises(SplitConfigurationError, match="val_ratio must be >= 0"):
            ChronologicalSplitter(
                train_ratio=0.7,
                val_ratio=-0.1,
                test_ratio=0.4,
            )

    def test_negative_purge_hours_raises(self):
        with pytest.raises(SplitConfigurationError, match="purge_hours must be >= 0"):
            ChronologicalSplitter(
                train_end=_dt(70),
                purge_hours=-1.0,
            )

    def test_missing_ratio_parameter_raises(self):
        with pytest.raises(SplitConfigurationError):
            ChronologicalSplitter(
                train_ratio=0.7,
                val_ratio=0.15,
                # test_ratio missing
            )


# ---------------------------------------------------------------------------
# TestBoundaryModeSplit
# ---------------------------------------------------------------------------


class TestBoundaryModeSplit:
    """Verify boundary-mode splitting behaves correctly."""

    def test_basic_train_test_split(self):
        """70 samples, boundary at day 50 → 50 train, 20 test."""
        samples = _make_dated_samples(70)
        splitter = ChronologicalSplitter(train_end=_dt(50))
        result = splitter.split(samples)
        assert len(result.train) == 50
        assert len(result.test) == 20
        assert len(result.validation) == 0

    def test_three_way_split(self):
        """100 samples, train<day60, val<day80, test>=day80."""
        samples = _make_dated_samples(100)
        splitter = ChronologicalSplitter(
            train_end=_dt(60),
            val_end=_dt(80),
        )
        result = splitter.split(samples)
        assert len(result.train) == 60
        assert len(result.validation) == 20
        assert len(result.test) == 20

    def test_train_always_before_validation(self):
        samples = _make_dated_samples(60)
        splitter = ChronologicalSplitter(train_end=_dt(40), val_end=_dt(50))
        result = splitter.split(samples)
        if result.train and result.validation:
            max_train = max(s.forecast_initialization_time for s in result.train)
            min_val = min(s.forecast_initialization_time for s in result.validation)
            assert max_train < min_val

    def test_validation_always_before_test(self):
        samples = _make_dated_samples(60)
        splitter = ChronologicalSplitter(train_end=_dt(40), val_end=_dt(50))
        result = splitter.split(samples)
        if result.validation and result.test:
            max_val = max(s.forecast_initialization_time for s in result.validation)
            min_test = min(s.forecast_initialization_time for s in result.test)
            assert max_val < min_test

    def test_train_always_before_test_no_validation(self):
        samples = _make_dated_samples(60)
        splitter = ChronologicalSplitter(train_end=_dt(40))
        result = splitter.split(samples)
        if result.train and result.test:
            max_train = max(s.forecast_initialization_time for s in result.train)
            min_test = min(s.forecast_initialization_time for s in result.test)
            assert max_train < min_test

    def test_no_overlap_between_partitions(self):
        samples = _make_dated_samples(90)
        splitter = ChronologicalSplitter(train_end=_dt(60), val_end=_dt(75))
        result = splitter.split(samples)
        train_ids = {s.case_id for s in result.train}
        val_ids = {s.case_id for s in result.validation}
        test_ids = {s.case_id for s in result.test}
        assert train_ids.isdisjoint(val_ids)
        assert train_ids.isdisjoint(test_ids)
        assert val_ids.isdisjoint(test_ids)

    def test_boundary_before_all_data_gives_empty_train(self):
        samples = _make_dated_samples(10)
        # boundary before all data
        splitter = ChronologicalSplitter(train_end=_dt(-5))
        result = splitter.split(samples)
        assert len(result.train) == 0
        assert len(result.test) == 10

    def test_boundary_after_all_data_gives_empty_test(self):
        samples = _make_dated_samples(10)
        splitter = ChronologicalSplitter(train_end=_dt(100))
        result = splitter.split(samples)
        assert len(result.train) == 10
        assert len(result.test) == 0

    def test_total_samples_conserved(self):
        """All non-undated, non-purged samples must land in exactly one partition."""
        samples = _make_dated_samples(90)
        splitter = ChronologicalSplitter(train_end=_dt(60), val_end=_dt(75))
        result = splitter.split(samples)
        assigned = len(result.train) + len(result.validation) + len(result.test)
        assert assigned == 90


# ---------------------------------------------------------------------------
# TestRatioModeSplit
# ---------------------------------------------------------------------------


class TestRatioModeSplit:
    """Verify ratio-mode splitting."""

    def test_basic_70_15_15_split(self):
        samples = _make_dated_samples(100)
        splitter = ChronologicalSplitter(
            train_ratio=0.7,
            val_ratio=0.15,
            test_ratio=0.15,
        )
        result = splitter.split(samples)
        assert len(result.train) > 0
        assert len(result.test) > 0
        assert len(result.train) + len(result.validation) + len(result.test) == 100

    def test_zero_val_ratio_no_validation(self):
        samples = _make_dated_samples(20)
        splitter = ChronologicalSplitter(
            train_ratio=0.8,
            val_ratio=0.0,
            test_ratio=0.2,
        )
        result = splitter.split(samples)
        assert len(result.validation) == 0
        assert len(result.train) + len(result.test) == 20

    def test_chronological_order_preserved_in_ratio_mode(self):
        samples = _make_dated_samples(30)
        splitter = ChronologicalSplitter(
            train_ratio=0.6,
            val_ratio=0.2,
            test_ratio=0.2,
        )
        result = splitter.split(samples)
        if result.train and result.test:
            max_train = max(s.forecast_initialization_time for s in result.train)
            min_test = min(s.forecast_initialization_time for s in result.test)
            assert max_train < min_test

    def test_empty_input_returns_empty_partitions(self):
        splitter = ChronologicalSplitter(
            train_ratio=0.7,
            val_ratio=0.15,
            test_ratio=0.15,
        )
        result = splitter.split([])
        assert result.total_samples() == 0
        assert len(result.undated) == 0

    def test_deterministic_repeated_split(self):
        """Same input + same splitter must produce identical results."""
        samples = _make_dated_samples(50)
        splitter = ChronologicalSplitter(
            train_ratio=0.7,
            val_ratio=0.15,
            test_ratio=0.15,
        )
        r1 = splitter.split(samples)
        r2 = splitter.split(samples)
        assert [s.case_id for s in r1.train] == [s.case_id for s in r2.train]
        assert [s.case_id for s in r1.validation] == [s.case_id for s in r2.validation]
        assert [s.case_id for s in r1.test] == [s.case_id for s in r2.test]


# ---------------------------------------------------------------------------
# TestSameCycleNotSplit
# ---------------------------------------------------------------------------


class TestSameCycleNotSplit:
    """Samples sharing the same init_time must land in the same partition."""

    def test_same_cycle_stays_together_across_boundary(self):
        """Two samples sharing init_time=day50 must both be in the same partition
        (train if < boundary, test if >= boundary).  The boundary is placed
        at day51 so day50 is entirely in train.
        """
        samples = [
            _make_sample("case_A", _dt(50)),
            _make_sample("case_B", _dt(50)),   # same cycle as case_A
            _make_sample("case_C", _dt(55)),
        ]
        splitter = ChronologicalSplitter(train_end=_dt(51))
        result = splitter.split(samples)
        train_ids = {s.case_id for s in result.train}
        test_ids = {s.case_id for s in result.test}
        # Both case_A and case_B (cycle=day50) must be in train
        assert "case_A" in train_ids
        assert "case_B" in train_ids
        assert "case_C" in test_ids
        # Neither straddles the boundary
        assert "case_A" not in test_ids
        assert "case_B" not in test_ids

    def test_no_cycle_in_multiple_partitions(self):
        """No forecast_initialization_time value should appear in more than
        one of train, validation, test."""
        # 30 samples, some sharing the same cycle
        samples = []
        for i in range(10):
            dt_i = _dt(i * 3)
            samples.append(_make_sample(f"c{i}a", dt_i))
            samples.append(_make_sample(f"c{i}b", dt_i))

        splitter = ChronologicalSplitter(train_end=_dt(15), val_end=_dt(22))
        result = splitter.split(samples)

        train_cycles = {s.forecast_initialization_time for s in result.train}
        val_cycles = {s.forecast_initialization_time for s in result.validation}
        test_cycles = {s.forecast_initialization_time for s in result.test}

        assert train_cycles.isdisjoint(val_cycles)
        assert train_cycles.isdisjoint(test_cycles)
        assert val_cycles.isdisjoint(test_cycles)


# ---------------------------------------------------------------------------
# TestPurgeGap
# ---------------------------------------------------------------------------


class TestPurgeGap:
    """Purge period excludes cycles immediately after partition boundaries."""

    def test_purge_removes_samples_near_boundary(self):
        # 30 samples, one per day; boundary at day 20; purge 2 days
        samples = _make_dated_samples(30)
        splitter = ChronologicalSplitter(train_end=_dt(20), purge_hours=48.0)
        result = splitter.split(samples)
        # Days 0–19 → train (20 samples)
        # Days 20–21 → purged (2 samples, within 48h of boundary)
        # Days 22–29 → test (8 samples)
        assert len(result.train) == 20
        assert len(result.purged) == 2
        assert len(result.test) == 8

    def test_purge_samples_in_purged_list(self):
        samples = _make_dated_samples(30)
        splitter = ChronologicalSplitter(train_end=_dt(20), purge_hours=48.0)
        result = splitter.split(samples)
        purged_ids = {s.case_id for s in result.purged}
        assert "case_020" in purged_ids  # day 20
        assert "case_021" in purged_ids  # day 21

    def test_purge_zero_no_samples_excluded(self):
        samples = _make_dated_samples(30)
        splitter = ChronologicalSplitter(train_end=_dt(20), purge_hours=0.0)
        result = splitter.split(samples)
        assert len(result.purged) == 0
        assert len(result.train) + len(result.test) == 30

    def test_purge_hours_recorded_in_result(self):
        samples = _make_dated_samples(30)
        splitter = ChronologicalSplitter(train_end=_dt(20), purge_hours=24.0)
        result = splitter.split(samples)
        assert result.purge_hours == 24.0


# ---------------------------------------------------------------------------
# TestUndatedSamples
# ---------------------------------------------------------------------------


class TestUndatedSamples:
    """Samples without forecast_initialization_time must go to undated."""

    def test_undated_excluded_from_primary_split(self):
        dated = _make_dated_samples(10)
        undated = [_make_sample("no_time", None)]
        splitter = ChronologicalSplitter(train_end=_dt(5))
        result = splitter.split(dated + undated)
        undated_ids = {s.case_id for s in result.undated}
        train_ids = {s.case_id for s in result.train}
        test_ids = {s.case_id for s in result.test}
        assert "no_time" in undated_ids
        assert "no_time" not in train_ids
        assert "no_time" not in test_ids

    def test_dated_count_unaffected_by_undated(self):
        dated = _make_dated_samples(10)
        undated = [_make_sample(f"u{i}", None) for i in range(5)]
        splitter = ChronologicalSplitter(train_end=_dt(7))
        result = splitter.split(dated + undated)
        assert len(result.train) + len(result.test) == 10
        assert len(result.undated) == 5


# ---------------------------------------------------------------------------
# TestDuplicateCaseIds
# ---------------------------------------------------------------------------


class TestDuplicateCaseIds:
    """Duplicate case_ids must be detected and rejected."""

    def test_duplicate_ids_raise(self):
        samples = [
            _make_sample("dup", _dt(1)),
            _make_sample("dup", _dt(2)),
        ]
        splitter = ChronologicalSplitter(train_end=_dt(5))
        with pytest.raises(SplitDataError, match="Duplicate"):
            splitter.split(samples)


# ---------------------------------------------------------------------------
# TestSplitResult
# ---------------------------------------------------------------------------


class TestSplitResult:
    """SplitResult methods and audit trail."""

    def test_partition_sizes_sum(self):
        samples = _make_dated_samples(50)
        splitter = ChronologicalSplitter(
            train_ratio=0.7, val_ratio=0.1, test_ratio=0.2
        )
        result = splitter.split(samples)
        sizes = result.partition_sizes()
        assert sizes["train"] + sizes["validation"] + sizes["test"] == 50

    def test_total_samples(self):
        samples = _make_dated_samples(50)
        splitter = ChronologicalSplitter(
            train_ratio=0.7, val_ratio=0.1, test_ratio=0.2
        )
        result = splitter.split(samples)
        assert result.total_samples() == 50

    def test_split_metadata_contains_mode(self):
        samples = _make_dated_samples(30)
        splitter = ChronologicalSplitter(train_end=_dt(20))
        result = splitter.split(samples)
        assert "split_mode" in result.split_metadata
        assert result.split_metadata["split_mode"] == "boundary"

    def test_split_metadata_ratio_mode(self):
        samples = _make_dated_samples(30)
        splitter = ChronologicalSplitter(
            train_ratio=0.6, val_ratio=0.2, test_ratio=0.2
        )
        result = splitter.split(samples)
        assert result.split_metadata["split_mode"] == "ratio"
        assert "train_ratio" in result.split_metadata

    def test_split_result_is_frozen(self):
        samples = _make_dated_samples(10)
        splitter = ChronologicalSplitter(train_end=_dt(7))
        result = splitter.split(samples)
        with pytest.raises((AttributeError, TypeError)):
            result.train = []

    def test_train_boundary_recorded(self):
        samples = _make_dated_samples(20)
        splitter = ChronologicalSplitter(train_end=_dt(15))
        result = splitter.split(samples)
        assert result.train_boundary == _dt(15)

    def test_cycle_counts_recorded(self):
        samples = _make_dated_samples(20)
        splitter = ChronologicalSplitter(train_end=_dt(15))
        result = splitter.split(samples)
        assert result.train_cycle_count == 15
        assert result.test_cycle_count == 5

    def test_split_before_model_fitting_invariant(self):
        """The split function is a pure data transform with no model objects.
        Asserting it returns a SplitResult (not a fitted model) enforces the
        principle that split construction happens before any model fitting.
        """
        samples = _make_dated_samples(20)
        splitter = ChronologicalSplitter(train_end=_dt(15))
        result = splitter.split(samples)
        assert isinstance(result, SplitResult)
        # SplitResult must not have model attributes
        assert not hasattr(result, "model")
        assert not hasattr(result, "predict")
        assert not hasattr(result, "fit")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
