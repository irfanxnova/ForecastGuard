"""Tests for the historical case manifest.

All tests use synthetic data only.  No filesystem writes unless testing
to_json_file/from_json_file (uses tmp_path fixture).
No scientific performance claims are made.
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from scientific.cases.manifest import (
    CaseManifest,
    CaseSpec,
    ManifestSerializationError,
    ManifestValidationError,
    _validate_spec,
)
from scientific.cases.planner import PlannedCase


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_UTC = timezone.utc
_OBS_START = datetime(2025, 9, 1, 0, 0, tzinfo=_UTC)
_OBS_END   = datetime(2025, 9, 2, 0, 0, tzinfo=_UTC)
_INIT_TIME = datetime(2025, 9, 1, 0, 0, tzinfo=_UTC)


def _make_spec(
    case_id: str = "case_001",
    forecast_path: str = "data/raw/tigge/forecast.grib",
    observation_path: str = "data/raw/observations/imd_daily/obs.grd",
    observation_date: str = "2025-09-01",
    observation_start: datetime = _OBS_START,
    observation_end: datetime = _OBS_END,
    forecast_initialization_time: datetime = _INIT_TIME,
    forecast_lead_hours: int = 24,
    forecast_source: str = "NCMRWF",
    forecast_variable: str = "tp",
    region: str = "India",
) -> CaseSpec:
    return CaseSpec(
        case_id=case_id,
        forecast_path=forecast_path,
        observation_path=observation_path,
        observation_date=observation_date,
        observation_start=observation_start,
        observation_end=observation_end,
        forecast_initialization_time=forecast_initialization_time,
        forecast_lead_hours=forecast_lead_hours,
        forecast_source=forecast_source,
        forecast_variable=forecast_variable,
        region=region,
    )


# ---------------------------------------------------------------------------
# TestCaseSpec
# ---------------------------------------------------------------------------


class TestCaseSpec:
    """CaseSpec construction, immutability, and serialization."""

    def test_valid_spec_constructs(self):
        spec = _make_spec()
        assert spec.case_id == "case_001"
        assert spec.forecast_lead_hours == 24

    def test_imd_daily_product_factory_supplies_explicit_window_and_provenance(self):
        spec = CaseSpec.for_imd_daily_merged_satellite_gauge(
            case_id="imd_window_case",
            forecast_path="data/raw/tigge/forecast.grib",
            observation_path="data/raw/observations/imd_daily/obs.grd",
            observation_date="2025-09-02",
            forecast_initialization_time=datetime(2025, 9, 1, 3, tzinfo=_UTC),
            forecast_lead_hours=24,
            forecast_source="NCMRWF",
            forecast_variable="tp",
        )

        assert spec.observation_start == datetime(2025, 9, 1, 3, tzinfo=_UTC)
        assert spec.observation_end == datetime(2025, 9, 2, 3, tzinfo=_UTC)
        assert spec.observation_window_metadata is not None
        assert "0830 IST" in spec.observation_window_metadata["basis"]
        assert CaseSpec.from_dict(spec.to_dict()).observation_window_metadata == (
            spec.observation_window_metadata
        )

    def test_planned_case_factory_preserves_matching_exact_timestamps(self):
        planned_case = PlannedCase(
            case_id="planned_valid",
            forecast_initialization_time=datetime(2025, 9, 1, 3, tzinfo=_UTC),
            forecast_lead_hours=24,
            forecast_source="NCMRWF",
            forecast_variable="tp",
            observation_source="IMD_DAILY",
            observation_date="2025-09-02",
            region="India",
            observation_start=None,
            observation_end=None,
            observation_window_specified=False,
            forecast_path=None,
            observation_path=None,
            trajectory_group_id="tg_valid",
            sequence_index=0,
            predecessor_init_time=None,
            cycle_label="03Z",
            forecast_accumulation_end=datetime(2025, 9, 2, 3, tzinfo=_UTC),
        )

        spec = CaseSpec.from_planned_case_for_imd_daily_merged_satellite_gauge(
            planned_case,
            forecast_path="data/raw/tigge/matching.grib",
            observation_path="data/raw/observations/imd_daily/02092025.grd",
        )

        assert spec.forecast_accumulation_start == datetime(2025, 9, 1, 3, tzinfo=_UTC)
        assert spec.forecast_accumulation_end == datetime(2025, 9, 2, 3, tzinfo=_UTC)
        assert spec.observation_start == spec.forecast_accumulation_start
        assert spec.observation_end == spec.forecast_accumulation_end
        assert spec.to_dict() == CaseSpec.from_dict(spec.to_dict()).to_dict()

    def test_planned_00z_24h_case_is_rejected_for_imd_03z_target(self):
        planned_case = PlannedCase(
            case_id="known_mismatch",
            forecast_initialization_time=datetime(2025, 9, 1, 0, tzinfo=_UTC),
            forecast_lead_hours=24,
            forecast_source="NCMRWF",
            forecast_variable="tp",
            observation_source="IMD_DAILY",
            observation_date="2025-09-02",
            region="India",
            observation_start=None,
            observation_end=None,
            observation_window_specified=False,
            forecast_path=None,
            observation_path=None,
            trajectory_group_id="tg_mismatch",
            sequence_index=0,
            predecessor_init_time=None,
            cycle_label="00Z",
            forecast_accumulation_end=datetime(2025, 9, 2, 0, tzinfo=_UTC),
        )

        with pytest.raises(ValueError, match="accumulation windows differ"):
            CaseSpec.from_planned_case_for_imd_daily_merged_satellite_gauge(
                planned_case,
                forecast_path="data/raw/tigge/mismatch.grib",
                observation_path="data/raw/observations/imd_daily/02092025.grd",
            )

    def test_spec_is_frozen(self):
        spec = _make_spec()
        with pytest.raises((AttributeError, TypeError)):
            spec.case_id = "new_id"

    def test_to_dict_contains_all_fields(self):
        spec = _make_spec()
        d = spec.to_dict()
        for key in [
            "case_id", "forecast_path", "observation_path", "observation_date",
            "observation_start", "observation_end", "forecast_initialization_time",
            "forecast_lead_hours", "forecast_source", "forecast_variable",
        ]:
            assert key in d, f"Missing field '{key}' in to_dict() output"

    def test_to_dict_datetimes_are_strings(self):
        spec = _make_spec()
        d = spec.to_dict()
        assert isinstance(d["observation_start"], str)
        assert isinstance(d["observation_end"], str)
        assert isinstance(d["forecast_initialization_time"], str)

    def test_to_dict_preserves_timezone(self):
        spec = _make_spec()
        d = spec.to_dict()
        assert "+00:00" in d["observation_start"] or "Z" in d["observation_start"]

    def test_round_trip_from_dict(self):
        spec = _make_spec()
        d = spec.to_dict()
        spec2 = CaseSpec.from_dict(d)
        assert spec2.case_id == spec.case_id
        assert spec2.observation_start == spec.observation_start
        assert spec2.observation_end == spec.observation_end
        assert spec2.forecast_initialization_time == spec.forecast_initialization_time
        assert spec2.forecast_lead_hours == spec.forecast_lead_hours

    def test_from_dict_missing_required_field_raises(self):
        d = _make_spec().to_dict()
        del d["observation_start"]
        with pytest.raises(ManifestSerializationError, match="missing required fields"):
            CaseSpec.from_dict(d)

    def test_from_dict_malformed_datetime_raises(self):
        d = _make_spec().to_dict()
        d["observation_start"] = "not-a-date"
        with pytest.raises(ManifestSerializationError):
            CaseSpec.from_dict(d)

    def test_from_dict_naive_datetime_raises(self):
        """Timezone-naive datetimes must be rejected."""
        d = _make_spec().to_dict()
        d["observation_start"] = "2025-09-01T00:00:00"  # no tzinfo
        with pytest.raises(ManifestSerializationError, match="timezone"):
            CaseSpec.from_dict(d)

    def test_from_dict_non_integer_lead_raises(self):
        d = _make_spec().to_dict()
        d["forecast_lead_hours"] = "twenty-four"
        with pytest.raises(ManifestSerializationError):
            CaseSpec.from_dict(d)

    def test_region_and_notes_optional(self):
        spec = CaseSpec(
            case_id="no_region",
            forecast_path="f.grib",
            observation_path="o.grd",
            observation_date="2025-09-01",
            observation_start=_OBS_START,
            observation_end=_OBS_END,
            forecast_initialization_time=_INIT_TIME,
            forecast_lead_hours=24,
            forecast_source="NCMRWF",
            forecast_variable="tp",
        )
        assert spec.region is None
        assert spec.notes is None


# ---------------------------------------------------------------------------
# TestValidateSpec
# ---------------------------------------------------------------------------


class TestValidateSpec:
    """_validate_spec must detect every validation error."""

    def test_valid_spec_no_errors(self):
        assert _validate_spec(_make_spec()) == []

    def test_empty_case_id_rejected(self):
        spec = _make_spec(case_id="")
        errors = _validate_spec(spec)
        assert any("case_id" in f for _, f, _ in errors)

    def test_empty_forecast_path_rejected(self):
        spec = _make_spec(forecast_path="")
        errors = _validate_spec(spec)
        assert any("forecast_path" in f for _, f, _ in errors)

    def test_empty_observation_path_rejected(self):
        spec = _make_spec(observation_path="")
        errors = _validate_spec(spec)
        assert any("observation_path" in f for _, f, _ in errors)

    def test_invalid_observation_date_format_rejected(self):
        spec = _make_spec(observation_date="01-09-2025")
        errors = _validate_spec(spec)
        assert any("observation_date" in f for _, f, _ in errors)

    def test_observation_end_before_start_rejected(self):
        spec = _make_spec(
            observation_start=_OBS_END,
            observation_end=_OBS_START,
        )
        errors = _validate_spec(spec)
        assert any("observation_end" in f for _, f, _ in errors)

    def test_observation_end_equal_start_rejected(self):
        spec = _make_spec(
            observation_start=_OBS_START,
            observation_end=_OBS_START,
        )
        errors = _validate_spec(spec)
        assert any("observation_end" in f for _, f, _ in errors)

    def test_negative_lead_hours_rejected(self):
        spec = _make_spec(forecast_lead_hours=-1)
        errors = _validate_spec(spec)
        assert any("forecast_lead_hours" in f for _, f, _ in errors)

    def test_zero_lead_hours_accepted(self):
        """Lead time of 0 hours is valid (analysis-time verification)."""
        spec = _make_spec(forecast_lead_hours=0)
        assert _validate_spec(spec) == []

    def test_empty_forecast_source_rejected(self):
        spec = _make_spec(forecast_source="")
        errors = _validate_spec(spec)
        assert any("forecast_source" in f for _, f, _ in errors)

    def test_empty_forecast_variable_rejected(self):
        spec = _make_spec(forecast_variable="")
        errors = _validate_spec(spec)
        assert any("forecast_variable" in f for _, f, _ in errors)


# ---------------------------------------------------------------------------
# TestCaseManifest
# ---------------------------------------------------------------------------


class TestCaseManifest:
    """CaseManifest construction, validation, and iteration."""

    def test_valid_manifest_constructs(self):
        specs = [_make_spec(case_id=f"c{i}") for i in range(3)]
        manifest = CaseManifest.from_specs(specs)
        assert len(manifest) == 3

    def test_manifest_is_iterable(self):
        specs = [_make_spec(case_id=f"c{i}") for i in range(3)]
        manifest = CaseManifest.from_specs(specs)
        ids = [s.case_id for s in manifest]
        assert ids == ["c0", "c1", "c2"]

    def test_manifest_indexable(self):
        specs = [_make_spec(case_id=f"c{i}") for i in range(3)]
        manifest = CaseManifest.from_specs(specs)
        assert manifest[0].case_id == "c0"
        assert manifest[2].case_id == "c2"

    def test_case_ids(self):
        specs = [_make_spec(case_id=f"c{i}") for i in range(3)]
        manifest = CaseManifest.from_specs(specs)
        assert manifest.case_ids() == ["c0", "c1", "c2"]

    def test_manifest_is_frozen(self):
        manifest = CaseManifest.from_specs([_make_spec()])
        with pytest.raises((AttributeError, TypeError)):
            manifest.specs = ()

    def test_duplicate_case_ids_rejected(self):
        specs = [_make_spec(case_id="dup"), _make_spec(case_id="dup")]
        with pytest.raises(ManifestValidationError, match="Duplicate"):
            CaseManifest.from_specs(specs)

    def test_invalid_spec_rejected(self):
        invalid = _make_spec(forecast_lead_hours=-5)
        with pytest.raises(ManifestValidationError):
            CaseManifest.from_specs([invalid])

    def test_multiple_errors_reported_together(self):
        """All validation errors must be reported, not just the first."""
        specs = [
            _make_spec(case_id="dup"),
            _make_spec(case_id="dup"),       # duplicate
            _make_spec(case_id="bad_lead", forecast_lead_hours=-1),
        ]
        with pytest.raises(ManifestValidationError) as exc_info:
            CaseManifest.from_specs(specs)
        assert len(exc_info.value.errors) >= 2

    def test_empty_manifest_accepted(self):
        manifest = CaseManifest.from_specs([])
        assert len(manifest) == 0

    def test_validate_false_skips_validation(self):
        """validate=False must allow invalid specs through."""
        invalid = _make_spec(forecast_lead_hours=-1)
        manifest = CaseManifest.from_specs([invalid], validate=False)
        assert len(manifest) == 1

    def test_created_at_set_automatically(self):
        before = datetime.now(_UTC)
        manifest = CaseManifest.from_specs([_make_spec()])
        after = datetime.now(_UTC)
        assert before <= manifest.created_at <= after

    def test_manifest_id_and_description_preserved(self):
        manifest = CaseManifest.from_specs(
            [_make_spec()],
            manifest_id="test_v1",
            description="Unit test manifest",
        )
        assert manifest.manifest_id == "test_v1"
        assert manifest.description == "Unit test manifest"


# ---------------------------------------------------------------------------
# TestCaseManifestSerialization
# ---------------------------------------------------------------------------


class TestCaseManifestSerialization:
    """Deterministic JSON round-trip."""

    def test_to_dict_contains_specs(self):
        specs = [_make_spec(case_id=f"c{i}") for i in range(2)]
        manifest = CaseManifest.from_specs(specs)
        d = manifest.to_dict()
        assert "specs" in d
        assert len(d["specs"]) == 2

    def test_to_dict_case_count(self):
        specs = [_make_spec(case_id=f"c{i}") for i in range(5)]
        manifest = CaseManifest.from_specs(specs)
        assert manifest.to_dict()["case_count"] == 5

    def test_to_json_is_valid_json(self):
        manifest = CaseManifest.from_specs([_make_spec()])
        json_str = manifest.to_json()
        parsed = json.loads(json_str)
        assert "specs" in parsed

    def test_json_round_trip_preserves_all_fields(self):
        spec = _make_spec()
        manifest = CaseManifest.from_specs([spec], manifest_id="rt_test")
        json_str = manifest.to_json()
        manifest2 = CaseManifest.from_json(json_str)
        assert manifest2.manifest_id == "rt_test"
        assert len(manifest2) == 1
        s = manifest2[0]
        assert s.case_id == spec.case_id
        assert s.observation_start == spec.observation_start
        assert s.forecast_lead_hours == spec.forecast_lead_hours

    def test_serialization_is_deterministic(self):
        """Same specs always produce identical JSON."""
        specs = [_make_spec(case_id=f"c{i}") for i in range(3)]
        m1 = CaseManifest.from_specs(
            specs,
            created_at=datetime(2025, 9, 1, tzinfo=_UTC),
        )
        m2 = CaseManifest.from_specs(
            specs,
            created_at=datetime(2025, 9, 1, tzinfo=_UTC),
        )
        assert m1.to_json() == m2.to_json()

    def test_from_json_invalid_json_raises(self):
        with pytest.raises(ManifestSerializationError, match="Invalid JSON"):
            CaseManifest.from_json("{not valid json")

    def test_from_json_missing_specs_key_raises(self):
        with pytest.raises(ManifestSerializationError, match="specs"):
            CaseManifest.from_json('{"manifest_id": "x"}')

    def test_from_json_specs_not_list_raises(self):
        with pytest.raises(ManifestSerializationError, match="list"):
            CaseManifest.from_json('{"specs": "not a list"}')

    def test_from_json_bad_spec_raises(self):
        payload = json.dumps({
            "specs": [{"case_id": "x"}]  # missing required fields
        })
        with pytest.raises(ManifestSerializationError):
            CaseManifest.from_json(payload)

    def test_file_round_trip(self, tmp_path):
        manifest = CaseManifest.from_specs(
            [_make_spec(case_id="file_rt")],
            manifest_id="file_test",
            created_at=datetime(2025, 9, 1, tzinfo=_UTC),
        )
        path = tmp_path / "manifest.json"
        manifest.to_json_file(path)
        assert path.exists()
        loaded = CaseManifest.from_json_file(path)
        assert loaded.manifest_id == "file_test"
        assert len(loaded) == 1
        assert loaded[0].case_id == "file_rt"

    def test_from_json_file_missing_file_raises(self, tmp_path):
        with pytest.raises(ManifestSerializationError):
            CaseManifest.from_json_file(tmp_path / "nonexistent.json")


# ---------------------------------------------------------------------------
# TestNoInventedTimestamps
# ---------------------------------------------------------------------------


class TestNoInventedTimestamps:
    """Observation timestamps must never be inferred from observation_date."""

    def test_observation_start_required_explicitly(self):
        """Cannot construct a valid CaseSpec without explicit observation_start."""
        # observation_date alone is not enough — observation_start/end must be supplied
        spec = _make_spec()
        assert spec.observation_start is not None
        assert spec.observation_end is not None
        # The observation_date field is a separate string, not a computed datetime
        assert isinstance(spec.observation_date, str)
        assert isinstance(spec.observation_start, datetime)

    def test_observation_start_not_derived_from_date(self):
        """observation_start must be exactly what was supplied."""
        custom_start = datetime(2025, 9, 1, 8, 30, tzinfo=_UTC)
        spec = _make_spec(observation_start=custom_start)
        assert spec.observation_start == custom_start
        # observation_date is "2025-09-01" but start is 08:30 — they are independent
        assert spec.observation_start.hour == 8

    def test_round_trip_preserves_exact_observation_window(self):
        """Serialization/deserialization must not alter the observation window."""
        custom_start = datetime(2025, 9, 1, 3, 0, tzinfo=_UTC)
        custom_end   = datetime(2025, 9, 2, 3, 0, tzinfo=_UTC)
        spec = _make_spec(observation_start=custom_start, observation_end=custom_end)
        spec2 = CaseSpec.from_dict(spec.to_dict())
        assert spec2.observation_start == custom_start
        assert spec2.observation_end == custom_end


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
