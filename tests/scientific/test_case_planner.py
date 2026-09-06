"""Tests for the Historical Experiment Planner.

All tests use synthetic configuration data only.
No network access, no file downloads, no real GRIB/IMD data required.
No scientific performance claims are made.
"""

import json
from datetime import datetime, timedelta, timezone

import pytest

from scientific.cases.planner import (
    ExperimentConfig,
    ExperimentConfigError,
    ExperimentPlan,
    ForecastCycle,
    PlannedCase,
    ResourceSummary,
    TrajectoryGroup,
    _make_case_id,
    _make_group_id,
    plan_experiment,
)

UTC = timezone.utc

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_START = datetime(2025, 9, 1, tzinfo=UTC)
_END   = datetime(2025, 9, 3, tzinfo=UTC)  # 3-day window
_CYCLE_00Z = ForecastCycle(hour=0)
_CYCLE_12Z = ForecastCycle(hour=12)


def _make_config(
    experiment_id: str = "exp_001",
    start_date: datetime = _START,
    end_date: datetime = _END,
    forecast_cycles=None,
    lead_hours=None,
    forecast_source: str = "NCMRWF",
    forecast_variable: str = "tp",
    observation_source: str = "IMD_DAILY",
    region: str = "India",
    observation_window_hours=None,
    min_consecutive_cycles: int = 1,
    forecast_path_template=None,
    observation_path_template=None,
) -> ExperimentConfig:
    if forecast_cycles is None:
        forecast_cycles = (_CYCLE_00Z,)
    if lead_hours is None:
        lead_hours = (24,)
    return ExperimentConfig(
        experiment_id=experiment_id,
        start_date=start_date,
        end_date=end_date,
        forecast_cycles=tuple(forecast_cycles),
        lead_hours=tuple(lead_hours),
        forecast_source=forecast_source,
        forecast_variable=forecast_variable,
        observation_source=observation_source,
        region=region,
        observation_window_hours=observation_window_hours,
        min_consecutive_cycles=min_consecutive_cycles,
        forecast_path_template=forecast_path_template,
        observation_path_template=observation_path_template,
    )


# ---------------------------------------------------------------------------
# TestForecastCycle
# ---------------------------------------------------------------------------


class TestForecastCycle:

    def test_00z_label(self):
        assert ForecastCycle(0).label() == "00Z"

    def test_12z_label(self):
        assert ForecastCycle(12).label() == "12Z"

    def test_with_minutes_label(self):
        assert ForecastCycle(6, 30).label() == "06Z30"

    def test_from_label_00z(self):
        c = ForecastCycle.from_label("00Z")
        assert c.hour == 0 and c.minute == 0

    def test_from_label_12z(self):
        c = ForecastCycle.from_label("12Z")
        assert c.hour == 12 and c.minute == 0

    def test_from_label_with_minutes(self):
        c = ForecastCycle.from_label("06Z30")
        assert c.hour == 6 and c.minute == 30

    def test_invalid_hour_raises(self):
        with pytest.raises(ValueError):
            ForecastCycle(24)

    def test_invalid_minute_raises(self):
        with pytest.raises(ValueError):
            ForecastCycle(0, 60)

    def test_from_label_invalid_raises(self):
        with pytest.raises(ValueError):
            ForecastCycle.from_label("25H")

    def test_frozen(self):
        c = ForecastCycle(0)
        with pytest.raises((AttributeError, TypeError)):
            c.hour = 12

    def test_to_dict_round_trip(self):
        c = ForecastCycle(6, 30)
        c2 = ForecastCycle.from_dict(c.to_dict())
        assert c2.hour == 6 and c2.minute == 30


# ---------------------------------------------------------------------------
# TestExperimentConfigValidation
# ---------------------------------------------------------------------------


class TestExperimentConfigValidation:

    def test_valid_config_accepted(self):
        config = _make_config()
        plan = plan_experiment(config)
        assert len(plan) > 0

    def test_empty_experiment_id_rejected(self):
        config = _make_config(experiment_id="")
        with pytest.raises(ExperimentConfigError) as exc:
            plan_experiment(config)
        assert any("experiment_id" in f for f, _ in exc.value.errors)

    def test_end_before_start_rejected(self):
        config = _make_config(
            start_date=datetime(2025, 9, 5, tzinfo=UTC),
            end_date=datetime(2025, 9, 1, tzinfo=UTC),
        )
        with pytest.raises(ExperimentConfigError) as exc:
            plan_experiment(config)
        assert any("end_date" in f for f, _ in exc.value.errors)

    def test_same_day_start_end_accepted(self):
        config = _make_config(
            start_date=datetime(2025, 9, 1, tzinfo=UTC),
            end_date=datetime(2025, 9, 1, tzinfo=UTC),
        )
        plan = plan_experiment(config)
        assert len(plan) >= 1

    def test_empty_cycles_rejected(self):
        config = _make_config(forecast_cycles=())
        with pytest.raises(ExperimentConfigError) as exc:
            plan_experiment(config)
        assert any("forecast_cycles" in f for f, _ in exc.value.errors)

    def test_duplicate_cycles_rejected(self):
        config = _make_config(
            forecast_cycles=(_CYCLE_00Z, ForecastCycle(0))
        )
        with pytest.raises(ExperimentConfigError) as exc:
            plan_experiment(config)
        assert any("forecast_cycles" in f for f, _ in exc.value.errors)

    def test_empty_lead_hours_rejected(self):
        config = _make_config(lead_hours=())
        with pytest.raises(ExperimentConfigError) as exc:
            plan_experiment(config)
        assert any("lead_hours" in f for f, _ in exc.value.errors)

    def test_negative_lead_hours_rejected(self):
        config = _make_config(lead_hours=(-1,))
        with pytest.raises(ExperimentConfigError) as exc:
            plan_experiment(config)
        assert any("lead_hours" in f for f, _ in exc.value.errors)

    def test_zero_lead_hours_accepted(self):
        config = _make_config(lead_hours=(0,))
        plan = plan_experiment(config)
        assert len(plan) >= 1

    def test_empty_forecast_source_rejected(self):
        config = _make_config(forecast_source="")
        with pytest.raises(ExperimentConfigError) as exc:
            plan_experiment(config)
        assert any("forecast_source" in f for f, _ in exc.value.errors)

    def test_empty_forecast_variable_rejected(self):
        config = _make_config(forecast_variable="")
        with pytest.raises(ExperimentConfigError) as exc:
            plan_experiment(config)
        assert any("forecast_variable" in f for f, _ in exc.value.errors)

    def test_empty_observation_source_rejected(self):
        config = _make_config(observation_source="")
        with pytest.raises(ExperimentConfigError) as exc:
            plan_experiment(config)
        assert any("observation_source" in f for f, _ in exc.value.errors)

    def test_empty_region_rejected(self):
        config = _make_config(region="")
        with pytest.raises(ExperimentConfigError) as exc:
            plan_experiment(config)
        assert any("region" in f for f, _ in exc.value.errors)

    def test_zero_observation_window_rejected(self):
        config = _make_config(observation_window_hours=0.0)
        with pytest.raises(ExperimentConfigError) as exc:
            plan_experiment(config)
        assert any("observation_window_hours" in f for f, _ in exc.value.errors)

    def test_negative_observation_window_rejected(self):
        config = _make_config(observation_window_hours=-1.0)
        with pytest.raises(ExperimentConfigError) as exc:
            plan_experiment(config)
        assert any("observation_window_hours" in f for f, _ in exc.value.errors)

    def test_all_errors_reported_together(self):
        config = _make_config(
            experiment_id="",
            forecast_source="",
            forecast_variable="",
        )
        with pytest.raises(ExperimentConfigError) as exc:
            plan_experiment(config)
        assert len(exc.value.errors) >= 3

    def test_config_is_frozen(self):
        config = _make_config()
        with pytest.raises((AttributeError, TypeError)):
            config.forecast_source = "OTHER"

    def test_config_round_trip(self):
        config = _make_config(
            forecast_cycles=(_CYCLE_00Z, _CYCLE_12Z),
            lead_hours=(24, 48),
        )
        config2 = ExperimentConfig.from_dict(config.to_dict())
        assert config2.experiment_id == config.experiment_id
        assert len(config2.forecast_cycles) == 2
        assert config2.lead_hours == (24, 48)


# ---------------------------------------------------------------------------
# TestPlanGeneration
# ---------------------------------------------------------------------------


class TestPlanGeneration:

    def test_single_day_single_cycle_single_lead(self):
        """1 day × 1 cycle × 1 lead = 1 case."""
        config = _make_config(
            start_date=datetime(2025, 9, 1, tzinfo=UTC),
            end_date=datetime(2025, 9, 1, tzinfo=UTC),
            forecast_cycles=(_CYCLE_00Z,),
            lead_hours=(24,),
        )
        plan = plan_experiment(config)
        assert len(plan) == 1

    def test_three_day_single_cycle_single_lead(self):
        """3 days × 1 cycle × 1 lead = 3 cases."""
        config = _make_config(
            start_date=datetime(2025, 9, 1, tzinfo=UTC),
            end_date=datetime(2025, 9, 3, tzinfo=UTC),
            forecast_cycles=(_CYCLE_00Z,),
            lead_hours=(24,),
        )
        plan = plan_experiment(config)
        assert len(plan) == 3

    def test_two_cycles_one_lead(self):
        """3 days × 2 cycles × 1 lead = 6 cases."""
        config = _make_config(
            start_date=datetime(2025, 9, 1, tzinfo=UTC),
            end_date=datetime(2025, 9, 3, tzinfo=UTC),
            forecast_cycles=(_CYCLE_00Z, _CYCLE_12Z),
            lead_hours=(24,),
        )
        plan = plan_experiment(config)
        assert len(plan) == 6

    def test_two_leads(self):
        """1 day × 1 cycle × 2 leads = 2 cases."""
        config = _make_config(
            start_date=datetime(2025, 9, 1, tzinfo=UTC),
            end_date=datetime(2025, 9, 1, tzinfo=UTC),
            forecast_cycles=(_CYCLE_00Z,),
            lead_hours=(24, 48),
        )
        plan = plan_experiment(config)
        assert len(plan) == 2

    def test_no_duplicate_case_ids(self):
        config = _make_config(
            forecast_cycles=(_CYCLE_00Z, _CYCLE_12Z),
            lead_hours=(24, 48),
        )
        plan = plan_experiment(config)
        ids = [c.case_id for c in plan]
        assert len(ids) == len(set(ids))

    def test_cases_ordered_by_init_time_then_lead(self):
        config = _make_config(
            start_date=datetime(2025, 9, 1, tzinfo=UTC),
            end_date=datetime(2025, 9, 2, tzinfo=UTC),
            forecast_cycles=(_CYCLE_00Z, _CYCLE_12Z),
            lead_hours=(24, 48),
        )
        plan = plan_experiment(config)
        for i in range(len(plan.cases) - 1):
            a, b = plan.cases[i], plan.cases[i + 1]
            assert (a.forecast_initialization_time, a.forecast_lead_hours) <= \
                   (b.forecast_initialization_time, b.forecast_lead_hours)

    def test_correct_initialization_times(self):
        """00Z cycle should produce init_time at midnight."""
        config = _make_config(
            start_date=datetime(2025, 9, 1, tzinfo=UTC),
            end_date=datetime(2025, 9, 1, tzinfo=UTC),
            forecast_cycles=(_CYCLE_00Z,),
            lead_hours=(24,),
        )
        plan = plan_experiment(config)
        assert plan.cases[0].forecast_initialization_time == datetime(2025, 9, 1, 0, 0, tzinfo=UTC)

    def test_12z_cycle_init_time(self):
        config = _make_config(
            start_date=datetime(2025, 9, 1, tzinfo=UTC),
            end_date=datetime(2025, 9, 1, tzinfo=UTC),
            forecast_cycles=(_CYCLE_12Z,),
            lead_hours=(24,),
        )
        plan = plan_experiment(config)
        assert plan.cases[0].forecast_initialization_time == datetime(2025, 9, 1, 12, 0, tzinfo=UTC)

    def test_forecast_accumulation_end_correct(self):
        """accum_end = init_time + lead_hours."""
        config = _make_config(
            start_date=datetime(2025, 9, 1, tzinfo=UTC),
            end_date=datetime(2025, 9, 1, tzinfo=UTC),
            forecast_cycles=(_CYCLE_00Z,),
            lead_hours=(24,),
        )
        plan = plan_experiment(config)
        case = plan.cases[0]
        expected_end = datetime(2025, 9, 1, 0, 0, tzinfo=UTC) + timedelta(hours=24)
        assert case.forecast_accumulation_end == expected_end

    def test_plan_is_frozen(self):
        plan = plan_experiment(_make_config())
        with pytest.raises((AttributeError, TypeError)):
            plan.cases = ()

    def test_planned_case_is_frozen(self):
        plan = plan_experiment(_make_config())
        with pytest.raises((AttributeError, TypeError)):
            plan.cases[0].case_id = "new"


# ---------------------------------------------------------------------------
# TestDeterministicIds
# ---------------------------------------------------------------------------


class TestDeterministicIds:

    def test_same_config_produces_same_ids(self):
        config = _make_config(
            forecast_cycles=(_CYCLE_00Z, _CYCLE_12Z),
            lead_hours=(24,),
        )
        p1 = plan_experiment(config, created_at=datetime(2025, 1, 1, tzinfo=UTC))
        p2 = plan_experiment(config, created_at=datetime(2026, 6, 15, tzinfo=UTC))
        assert [c.case_id for c in p1] == [c.case_id for c in p2]

    def test_different_source_different_id(self):
        id1 = _make_case_id("NCMRWF", "tp", datetime(2025, 9, 1, tzinfo=UTC), 24)
        id2 = _make_case_id("ECMWF", "tp", datetime(2025, 9, 1, tzinfo=UTC), 24)
        assert id1 != id2

    def test_different_init_time_different_id(self):
        id1 = _make_case_id("NCMRWF", "tp", datetime(2025, 9, 1, tzinfo=UTC), 24)
        id2 = _make_case_id("NCMRWF", "tp", datetime(2025, 9, 2, tzinfo=UTC), 24)
        assert id1 != id2

    def test_different_lead_different_id(self):
        id1 = _make_case_id("NCMRWF", "tp", datetime(2025, 9, 1, tzinfo=UTC), 24)
        id2 = _make_case_id("NCMRWF", "tp", datetime(2025, 9, 1, tzinfo=UTC), 48)
        assert id1 != id2

    def test_id_is_16_hex_chars(self):
        cid = _make_case_id("SRC", "tp", datetime(2025, 9, 1, tzinfo=UTC), 24)
        assert len(cid) == 16
        assert all(c in "0123456789abcdef" for c in cid)

    def test_repeated_call_same_result(self):
        cid1 = _make_case_id("NCMRWF", "tp", datetime(2025, 9, 1, tzinfo=UTC), 24)
        cid2 = _make_case_id("NCMRWF", "tp", datetime(2025, 9, 1, tzinfo=UTC), 24)
        assert cid1 == cid2


# ---------------------------------------------------------------------------
# TestTrajectoryGroups
# ---------------------------------------------------------------------------


class TestTrajectoryGroups:

    def test_trajectory_group_count(self):
        """One trajectory group per unique exact valid datetime."""
        config = _make_config(
            start_date=datetime(2025, 9, 1, tzinfo=UTC),
            end_date=datetime(2025, 9, 2, tzinfo=UTC),
            forecast_cycles=(_CYCLE_00Z,),
            lead_hours=(24,),
        )
        plan = plan_experiment(config)
        # 00Z day1 → valid day2; 00Z day2 → valid day3 → 2 groups
        assert len(plan.trajectory_groups) == 2

    def test_multiple_cycles_same_valid_datetime_in_same_group(self):
        """Different init times and leads targeting one datetime share a group."""
        # 2025-09-01 00Z + 24h → valid 2025-09-02
        # 2025-09-01 12Z + 12h → valid 2025-09-02
        config = _make_config(
            start_date=datetime(2025, 9, 1, tzinfo=UTC),
            end_date=datetime(2025, 9, 1, tzinfo=UTC),
            forecast_cycles=(_CYCLE_00Z, _CYCLE_12Z),
            lead_hours=(24, 12),
        )
        plan = plan_experiment(config)
        # Both cases have accum_end = 2025-09-02 00:00 or 2025-09-02 00:00
        # 00Z+24h → 2025-09-02 00:00
        # 12Z+12h → 2025-09-02 00:00
        matching_groups = [
            group for group in plan.trajectory_groups
            if group.valid_datetime == "2025-09-02T00:00:00+00:00"
        ]
        assert len(matching_groups) == 1
        group = matching_groups[0]
        assert [(case.forecast_initialization_time, case.forecast_lead_hours) for case in group] == [
            (datetime(2025, 9, 1, 0, tzinfo=UTC), 24),
            (datetime(2025, 9, 1, 12, tzinfo=UTC), 12),
        ]
        assert group.cases[0].predecessor_init_time is None
        assert group.cases[1].predecessor_init_time == datetime(2025, 9, 1, 0, tzinfo=UTC)

    def test_different_exact_valid_datetimes_on_same_date_are_different_groups(self):
        config = _make_config(
            start_date=datetime(2025, 9, 1, tzinfo=UTC),
            end_date=datetime(2025, 9, 1, tzinfo=UTC),
            forecast_cycles=(_CYCLE_00Z, _CYCLE_12Z),
            lead_hours=(24,),
        )
        plan = plan_experiment(config)
        assert [group.valid_datetime for group in plan.trajectory_groups] == [
            "2025-09-02T00:00:00+00:00",
            "2025-09-02T12:00:00+00:00",
        ]

    def test_sequence_index_ascending_within_group(self):
        """Cases within a group are ordered by init_time; indices are ascending."""
        config = _make_config(
            start_date=datetime(2025, 9, 1, tzinfo=UTC),
            end_date=datetime(2025, 9, 2, tzinfo=UTC),
            forecast_cycles=(_CYCLE_00Z, _CYCLE_12Z),
            lead_hours=(24,),
        )
        plan = plan_experiment(config)
        for group in plan.trajectory_groups:
            for i, case in enumerate(group.cases):
                assert case.sequence_index == i

    def test_predecessor_init_time_none_for_first(self):
        """First case in each group has predecessor_init_time = None."""
        config = _make_config(
            start_date=datetime(2025, 9, 1, tzinfo=UTC),
            end_date=datetime(2025, 9, 2, tzinfo=UTC),
            forecast_cycles=(_CYCLE_00Z, _CYCLE_12Z),
            lead_hours=(24,),
        )
        plan = plan_experiment(config)
        for group in plan.trajectory_groups:
            assert group.cases[0].predecessor_init_time is None

    def test_predecessor_init_time_set_for_later(self):
        """Subsequent cases record their predecessor's init_time."""
        config = _make_config(
            start_date=datetime(2025, 9, 1, tzinfo=UTC),
            end_date=datetime(2025, 9, 2, tzinfo=UTC),
            forecast_cycles=(_CYCLE_00Z, _CYCLE_12Z),
            lead_hours=(24,),
        )
        plan = plan_experiment(config)
        for group in plan.trajectory_groups:
            if len(group.cases) > 1:
                case = group.cases[1]
                expected_pred = group.cases[0].forecast_initialization_time
                assert case.predecessor_init_time == expected_pred

    def test_trajectory_group_id_deterministic(self):
        """Same valid datetime + source + variable → same group_id every time."""
        gid1 = _make_group_id("2025-09-02T00:00:00+00:00", "NCMRWF", "tp")
        gid2 = _make_group_id("2025-09-02T00:00:00+00:00", "NCMRWF", "tp")
        assert gid1 == gid2

    def test_different_valid_datetimes_different_group_ids(self):
        gid1 = _make_group_id("2025-09-02T00:00:00+00:00", "NCMRWF", "tp")
        gid2 = _make_group_id("2025-09-02T12:00:00+00:00", "NCMRWF", "tp")
        assert gid1 != gid2

    def test_trajectory_groups_ordered_by_valid_datetime(self):
        config = _make_config(
            start_date=datetime(2025, 9, 1, tzinfo=UTC),
            end_date=datetime(2025, 9, 5, tzinfo=UTC),
            forecast_cycles=(_CYCLE_00Z,),
            lead_hours=(24,),
        )
        plan = plan_experiment(config)
        valid_datetimes = [g.valid_datetime for g in plan.trajectory_groups]
        assert valid_datetimes == sorted(valid_datetimes)

    def test_linked_cycles_not_claimed_as_same_event(self):
        """Trajectory groups link by exact valid datetime only.
        The plan must NOT label them as the same meteorological event.
        """
        config = _make_config(
            forecast_cycles=(_CYCLE_00Z, _CYCLE_12Z),
            lead_hours=(24,),
        )
        plan = plan_experiment(config)
        for group in plan.trajectory_groups:
            # group_id is derived from valid_datetime + source + variable only
            assert "event" not in group.group_id
            # No 'event' field on PlannedCase
            for case in group.cases:
                assert not hasattr(case, "event_label")
                assert not hasattr(case, "is_same_event")

    def test_min_consecutive_cycles_complete_flag(self):
        """Groups with >= min_consecutive_cycles are flagged is_complete=True."""
        config = _make_config(
            start_date=datetime(2025, 9, 1, tzinfo=UTC),
            end_date=datetime(2025, 9, 3, tzinfo=UTC),
            forecast_cycles=(_CYCLE_00Z, _CYCLE_12Z),
            lead_hours=(24,),
            min_consecutive_cycles=2,
        )
        plan = plan_experiment(config)
        for group in plan.trajectory_groups:
            expected = len(group.cases) >= 2
            assert group.is_complete == expected

    def test_min_consecutive_1_all_complete(self):
        config = _make_config(min_consecutive_cycles=1)
        plan = plan_experiment(config)
        for group in plan.trajectory_groups:
            assert group.is_complete is True


# ---------------------------------------------------------------------------
# TestObservationWindowHandling
# ---------------------------------------------------------------------------


class TestObservationWindowHandling:

    def test_no_window_leaves_unspecified(self):
        """Without observation_window_hours, windows must remain None."""
        config = _make_config(observation_window_hours=None)
        plan = plan_experiment(config)
        for case in plan:
            assert case.observation_start is None
            assert case.observation_end is None
            assert case.observation_window_specified is False

    def test_observation_windows_specified_false_when_no_window(self):
        config = _make_config(observation_window_hours=None)
        plan = plan_experiment(config)
        assert plan.observation_windows_specified is False

    def test_with_window_sets_obs_start_end(self):
        """24h window → obs_end = accum_end, obs_start = accum_end - 24h."""
        config = _make_config(
            start_date=datetime(2025, 9, 1, tzinfo=UTC),
            end_date=datetime(2025, 9, 1, tzinfo=UTC),
            forecast_cycles=(_CYCLE_00Z,),
            lead_hours=(24,),
            observation_window_hours=24.0,
        )
        plan = plan_experiment(config)
        case = plan.cases[0]
        assert case.observation_window_specified is True
        assert case.observation_end == case.forecast_accumulation_end
        assert case.observation_start == case.forecast_accumulation_end - timedelta(hours=24)

    def test_observation_windows_specified_true_when_window_set(self):
        config = _make_config(observation_window_hours=24.0)
        plan = plan_experiment(config)
        assert plan.observation_windows_specified is True

    def test_observation_start_not_derived_from_date_string(self):
        """obs_start is derived from forecast_accumulation_end, not from a date string."""
        config = _make_config(
            start_date=datetime(2025, 9, 1, tzinfo=UTC),
            end_date=datetime(2025, 9, 1, tzinfo=UTC),
            forecast_cycles=(ForecastCycle(12),),
            lead_hours=(12,),
            observation_window_hours=24.0,
        )
        plan = plan_experiment(config)
        case = plan.cases[0]
        # init=12Z, lead=12h → accum_end = 2025-09-02 00:00
        # obs_start = 2025-09-01 00:00, obs_end = 2025-09-02 00:00
        assert case.observation_end == datetime(2025, 9, 2, 0, 0, tzinfo=UTC)
        assert case.observation_start == datetime(2025, 9, 1, 0, 0, tzinfo=UTC)

    def test_no_invented_observation_timestamps(self):
        """Without window_hours, no observation timestamps anywhere in the plan."""
        config = _make_config(observation_window_hours=None)
        plan = plan_experiment(config)
        d = plan.to_dict()
        for case_dict in d["cases"]:
            assert case_dict["observation_start"] is None
            assert case_dict["observation_end"] is None


# ---------------------------------------------------------------------------
# TestResourceSummary
# ---------------------------------------------------------------------------


class TestResourceSummary:

    def test_total_cases_correct(self):
        config = _make_config(
            start_date=datetime(2025, 9, 1, tzinfo=UTC),
            end_date=datetime(2025, 9, 3, tzinfo=UTC),
            forecast_cycles=(_CYCLE_00Z, _CYCLE_12Z),
            lead_hours=(24, 48),
        )
        plan = plan_experiment(config)
        assert plan.resource_summary.total_cases == len(plan.cases)

    def test_total_init_cycles_correct(self):
        config = _make_config(
            start_date=datetime(2025, 9, 1, tzinfo=UTC),
            end_date=datetime(2025, 9, 2, tzinfo=UTC),
            forecast_cycles=(_CYCLE_00Z, _CYCLE_12Z),
            lead_hours=(24,),
        )
        plan = plan_experiment(config)
        # 2 days × 2 cycles = 4 init times
        assert plan.resource_summary.total_initialization_cycles == 4

    def test_cases_per_cycle_equals_lead_count(self):
        config = _make_config(lead_hours=(24, 48, 72))
        plan = plan_experiment(config)
        assert plan.resource_summary.cases_per_cycle == 3

    def test_no_bytes_estimate_without_input(self):
        plan = plan_experiment(_make_config())
        assert plan.resource_summary.bytes_per_case is None
        assert plan.resource_summary.estimated_total_bytes is None

    def test_bytes_estimate_with_input(self):
        plan = plan_experiment(_make_config(), bytes_per_case=1_000_000.0)
        rs = plan.resource_summary
        assert rs.bytes_per_case == 1_000_000.0
        assert rs.estimated_total_bytes == float(rs.total_cases) * 1_000_000.0

    def test_bytes_estimate_not_invented(self):
        """The planner must not estimate bytes unless explicitly told bytes_per_case."""
        plan = plan_experiment(_make_config(), bytes_per_case=None)
        assert plan.resource_summary.estimated_total_bytes is None

    def test_trajectory_group_count_in_summary(self):
        config = _make_config(
            start_date=datetime(2025, 9, 1, tzinfo=UTC),
            end_date=datetime(2025, 9, 3, tzinfo=UTC),
            forecast_cycles=(_CYCLE_00Z,),
            lead_hours=(24,),
        )
        plan = plan_experiment(config)
        assert plan.resource_summary.total_trajectory_groups == len(plan.trajectory_groups)

    def test_resource_summary_to_dict(self):
        plan = plan_experiment(_make_config(), bytes_per_case=500.0)
        d = plan.resource_summary.to_dict()
        for key in ["total_cases", "total_initialization_cycles",
                    "total_trajectory_groups", "cases_per_cycle",
                    "bytes_per_case", "estimated_total_bytes"]:
            assert key in d


# ---------------------------------------------------------------------------
# TestPathTemplates
# ---------------------------------------------------------------------------


class TestPathTemplates:

    def test_no_template_paths_are_none(self):
        config = _make_config()
        plan = plan_experiment(config)
        for case in plan:
            assert case.forecast_path is None
            assert case.observation_path is None

    def test_forecast_path_template_rendered(self):
        template = "data/{forecast_source}/{init_date}_{lead_hours}h.grib"
        config = _make_config(
            start_date=datetime(2025, 9, 1, tzinfo=UTC),
            end_date=datetime(2025, 9, 1, tzinfo=UTC),
            forecast_cycles=(_CYCLE_00Z,),
            lead_hours=(24,),
            forecast_path_template=template,
        )
        plan = plan_experiment(config)
        path = plan.cases[0].forecast_path
        assert path is not None
        assert "NCMRWF" in path
        assert "20250901" in path
        assert "24h" in path

    def test_observation_path_template_rendered(self):
        template = "data/{observation_source}/{observation_date}.grd"
        config = _make_config(
            start_date=datetime(2025, 9, 1, tzinfo=UTC),
            end_date=datetime(2025, 9, 1, tzinfo=UTC),
            forecast_cycles=(_CYCLE_00Z,),
            lead_hours=(24,),
            observation_path_template=template,
        )
        plan = plan_experiment(config)
        path = plan.cases[0].observation_path
        assert path is not None
        assert "IMD_DAILY" in path

    def test_paths_are_deterministic(self):
        template = "data/{forecast_source}/{init_date}_{lead_hours}h.grib"
        config = _make_config(forecast_path_template=template)
        p1 = plan_experiment(config, created_at=datetime(2025, 1, 1, tzinfo=UTC))
        p2 = plan_experiment(config, created_at=datetime(2026, 6, 1, tzinfo=UTC))
        for c1, c2 in zip(p1.cases, p2.cases):
            assert c1.forecast_path == c2.forecast_path


# ---------------------------------------------------------------------------
# TestSerialization
# ---------------------------------------------------------------------------


class TestSerialization:

    def test_to_json_is_valid_json(self):
        plan = plan_experiment(_make_config())
        json_str = plan.to_json()
        parsed = json.loads(json_str)
        assert "cases" in parsed

    def test_deterministic_json_same_config(self):
        """Same config → identical JSON (excluding created_at)."""
        config = _make_config(
            forecast_cycles=(_CYCLE_00Z, _CYCLE_12Z),
            lead_hours=(24,),
        )
        fixed_time = datetime(2025, 9, 1, tzinfo=UTC)
        j1 = plan_experiment(config, created_at=fixed_time).to_json()
        j2 = plan_experiment(config, created_at=fixed_time).to_json()
        assert j1 == j2

    def test_json_without_created_at_is_stable(self):
        """Even with different created_at, to_json() (no include_created_at) is identical."""
        config = _make_config()
        j1 = plan_experiment(config, created_at=datetime(2025, 1, 1, tzinfo=UTC)).to_json()
        j2 = plan_experiment(config, created_at=datetime(2099, 1, 1, tzinfo=UTC)).to_json()
        assert j1 == j2

    def test_to_dict_contains_required_keys(self):
        plan = plan_experiment(_make_config())
        d = plan.to_dict()
        for key in ["experiment_id", "config", "total_cases", "cases",
                    "trajectory_groups", "resource_summary"]:
            assert key in d

    def test_trajectory_group_serialization_uses_valid_datetime(self):
        plan = plan_experiment(_make_config())
        group_dict = plan.to_dict()["trajectory_groups"][0]
        assert group_dict["valid_datetime"] == plan.trajectory_groups[0].valid_datetime
        assert "valid_date" not in group_dict

    def test_plan_case_to_dict_round_trip_fields(self):
        config = _make_config(observation_window_hours=24.0)
        plan = plan_experiment(config)
        case = plan.cases[0]
        d = case.to_dict()
        assert d["case_id"] == case.case_id
        assert d["forecast_lead_hours"] == case.forecast_lead_hours
        assert d["observation_window_specified"] is True
        assert d["trajectory_group_id"] == case.trajectory_group_id

    def test_created_at_excluded_by_default(self):
        plan = plan_experiment(_make_config(), created_at=datetime(2025, 9, 1, tzinfo=UTC))
        d = plan.to_dict()
        assert "plan_created_at" not in d

    def test_created_at_included_when_requested(self):
        plan = plan_experiment(_make_config(), created_at=datetime(2025, 9, 1, tzinfo=UTC))
        d = plan.to_dict(include_created_at=True)
        assert "plan_created_at" in d


# ---------------------------------------------------------------------------
# TestToCaseManifest
# ---------------------------------------------------------------------------


class TestToCaseManifest:

    def test_converts_to_manifest_when_windows_specified(self):
        config = _make_config(
            start_date=datetime(2025, 9, 1, tzinfo=UTC),
            end_date=datetime(2025, 9, 1, tzinfo=UTC),
            forecast_cycles=(_CYCLE_00Z,),
            lead_hours=(24,),
            observation_window_hours=24.0,
            forecast_path_template="data/raw/{forecast_source}/{init_date}.grib",
            observation_path_template="data/raw/{observation_source}/{observation_date}.grd",
        )
        plan = plan_experiment(config)
        manifest = plan.to_case_manifest()
        assert len(manifest) == 1
        spec = manifest[0]
        assert spec.case_id == plan.cases[0].case_id
        assert spec.observation_start is not None
        assert spec.observation_end is not None

    def test_converts_raises_when_no_window(self):
        config = _make_config(observation_window_hours=None)
        plan = plan_experiment(config)
        with pytest.raises(ValueError, match="observation windows"):
            plan.to_case_manifest()

    def test_manifest_case_ids_match_plan(self):
        config = _make_config(
            start_date=datetime(2025, 9, 1, tzinfo=UTC),
            end_date=datetime(2025, 9, 2, tzinfo=UTC),
            forecast_cycles=(_CYCLE_00Z,),
            lead_hours=(24,),
            observation_window_hours=24.0,
        )
        plan = plan_experiment(config)
        manifest = plan.to_case_manifest()
        plan_ids = [c.case_id for c in plan.cases if c.observation_window_specified]
        manifest_ids = manifest.case_ids()
        assert plan_ids == manifest_ids


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
