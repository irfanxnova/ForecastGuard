"""Tests for the historical case batch processor.

All tests use synthetic data and mocking only.  No real GRIB or IMD files
are read.  No scientific performance claims are made.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from scientific.cases.batch import (
    BatchCaseResult,
    BatchCaseStatus,
    BatchProcessor,
    BatchResult,
    _build_provenance,
    _check_inputs_exist,
    _spec_to_rainfall_case,
    process_case,
)
from scientific.cases.manifest import CaseManifest, CaseSpec
from scientific.cases.rainfall_case import RainfallCaseResult, RainfallCaseStatus
from scientific.dataset.assembly import AssembledSample, SampleStatus
from scientific.dataset.builder import DatasetRecord, DatasetRecordStatus
from scientific.targets.rainfall import (
    RainfallTarget,
    RainfallTargetStatus,
    SeverityLevel,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_UTC = timezone.utc
_OBS_START = datetime(2025, 9, 1, 0, 0, tzinfo=_UTC)
_OBS_END   = datetime(2025, 9, 2, 0, 0, tzinfo=_UTC)
_INIT_TIME = datetime(2025, 9, 1, 0, 0, tzinfo=_UTC)

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


def _make_spec(
    case_id: str = "case_001",
    forecast_path: str = "data/raw/tigge/test.grib",
    observation_path: str = "data/raw/observations/imd_daily/test.grd",
) -> CaseSpec:
    return CaseSpec(
        case_id=case_id,
        forecast_path=forecast_path,
        observation_path=observation_path,
        observation_date="2025-09-01",
        observation_start=_OBS_START,
        observation_end=_OBS_END,
        forecast_initialization_time=_INIT_TIME,
        forecast_lead_hours=24,
        forecast_source="NCMRWF",
        forecast_variable="tp",
    )


def _make_manifest(n: int = 2, base_id: str = "c") -> CaseManifest:
    specs = [_make_spec(case_id=f"{base_id}{i}") for i in range(n)]
    return CaseManifest.from_specs(specs)


def _make_aligned_case_result(case_id: str) -> RainfallCaseResult:
    return RainfallCaseResult(
        case_id=case_id,
        status=RainfallCaseStatus.ALIGNED,
        forecast_metadata={
            "data_date": 20250901, "data_time": 0, "step": 24,
        },
        observation_metadata={"source": "IMD_DAILY"},
        forecast_window={
            "start": "2025-09-01T00:00:00+00:00",
            "end":   "2025-09-02T00:00:00+00:00",
        },
        observation_window={
            "start": "2025-09-01T00:00:00+00:00",
            "end":   "2025-09-02T00:00:00+00:00",
            "supplied": True,
        },
        valid_cell_count=100,
        missing_cell_count=5,
        error_statistics={
            "mae": 2.0, "rmse": 3.0, "bias": -0.5,
            "forecast_mean": 5.0, "observation_mean": 5.5,
        },
        provenance={"alignment_status": "ALIGNED"},
    )


def _make_blocked_case_result(case_id: str) -> RainfallCaseResult:
    return RainfallCaseResult(
        case_id=case_id,
        status=RainfallCaseStatus.BLOCKED_UNSPECIFIED_OBSERVATION_WINDOW,
        forecast_metadata={},
        observation_metadata={},
        forecast_window={},
        observation_window={},
        valid_cell_count=0,
        missing_cell_count=0,
        error_statistics={},
        provenance={"reason": "Observation window not specified"},
    )


def _make_valid_dataset_record(case_id: str) -> DatasetRecord:
    feature_arrays = {name: np.full((4, 4), 5.0) for name in _FEATURE_NAMES}
    return DatasetRecord(
        case_id=case_id,
        status=DatasetRecordStatus.VALID,
        forecast_initialization_time=_INIT_TIME,
        forecast_lead_hours=24,
        forecast_source_model="NCMRWF",
        ensemble_member_count=11,
        grid_shape=(4, 4),
        mae=2.0, rmse=3.0, bias=-0.5,
        forecast_mean=5.0, observation_mean=5.5,
        valid_cell_count=100, missing_cell_count=5,
        feature_names=_FEATURE_NAMES,
        **feature_arrays,
    )


def _make_blocked_dataset_record(case_id: str) -> DatasetRecord:
    return DatasetRecord(
        case_id=case_id,
        status=DatasetRecordStatus.BLOCKED_TEMPORAL_MISMATCH,
        reason="Blocked",
    )


def _make_valid_target(case_id: str) -> RainfallTarget:
    return RainfallTarget(
        case_id=case_id,
        target_status=RainfallTargetStatus.VALID,
        mae=2.0, rmse=3.0, bias=-0.5,
        forecast_mean=5.0, observation_mean=5.5,
        valid_cell_count=100, missing_cell_count=5,
        continuous_error=3.0,
        continuous_error_metric="rmse",
    )


def _make_blocked_target(case_id: str) -> RainfallTarget:
    return RainfallTarget(
        case_id=case_id,
        target_status=RainfallTargetStatus.BLOCKED,
        reason="Blocked by alignment",
    )


# ---------------------------------------------------------------------------
# TestCheckInputsExist
# ---------------------------------------------------------------------------


class TestCheckInputsExist:
    """_check_inputs_exist must detect missing files."""

    def test_both_files_exist(self, tmp_path):
        f = tmp_path / "forecast.grib"
        o = tmp_path / "obs.grd"
        f.write_bytes(b"")
        o.write_bytes(b"")
        spec = _make_spec(
            forecast_path=str(f),
            observation_path=str(o),
        )
        assert _check_inputs_exist(spec) is None

    def test_forecast_missing(self, tmp_path):
        o = tmp_path / "obs.grd"
        o.write_bytes(b"")
        spec = _make_spec(
            forecast_path=str(tmp_path / "missing.grib"),
            observation_path=str(o),
        )
        reason = _check_inputs_exist(spec)
        assert reason is not None
        assert "forecast_path" in reason

    def test_observation_missing(self, tmp_path):
        f = tmp_path / "forecast.grib"
        f.write_bytes(b"")
        spec = _make_spec(
            forecast_path=str(f),
            observation_path=str(tmp_path / "missing.grd"),
        )
        reason = _check_inputs_exist(spec)
        assert reason is not None
        assert "observation_path" in reason

    def test_both_missing(self, tmp_path):
        spec = _make_spec(
            forecast_path=str(tmp_path / "a.grib"),
            observation_path=str(tmp_path / "b.grd"),
        )
        reason = _check_inputs_exist(spec)
        assert reason is not None
        assert "forecast_path" in reason
        assert "observation_path" in reason


# ---------------------------------------------------------------------------
# TestSpecToRainfallCase
# ---------------------------------------------------------------------------


class TestSpecToRainfallCase:
    """CaseSpec must convert correctly to RainfallCase."""

    def test_fields_transferred(self):
        spec = _make_spec(case_id="convert_test")
        from scientific.cases.rainfall_case import RainfallCase
        rc = _spec_to_rainfall_case(spec)
        assert isinstance(rc, RainfallCase)
        assert rc.case_id == "convert_test"
        assert rc.observation_start == _OBS_START
        assert rc.observation_end == _OBS_END

    def test_imd_window_metadata_is_transferred_to_case_runner(self):
        spec = CaseSpec.for_imd_daily_merged_satellite_gauge(
            case_id="imd_window_case",
            forecast_path="data/raw/tigge/test.grib",
            observation_path="data/raw/observations/imd_daily/test.grd",
            observation_date="2025-09-02",
            forecast_initialization_time=datetime(2025, 9, 1, 3, tzinfo=_UTC),
            forecast_lead_hours=24,
            forecast_source="NCMRWF",
            forecast_variable="tp",
        )

        rainfall_case = _spec_to_rainfall_case(spec)
        assert rainfall_case.observation_start == spec.observation_start
        assert rainfall_case.observation_end == spec.observation_end
        assert rainfall_case.observation_window_metadata == spec.observation_window_metadata

    def test_forecast_path_is_path_object(self):
        spec = _make_spec()
        rc = _spec_to_rainfall_case(spec)
        assert isinstance(rc.forecast_path, Path)


# ---------------------------------------------------------------------------
# TestProcessCaseMissingInput
# ---------------------------------------------------------------------------


class TestProcessCaseMissingInput:
    """Missing input files must produce MISSING_INPUT without running pipeline."""

    def test_missing_forecast_gives_missing_input(self, tmp_path):
        obs = tmp_path / "obs.grd"
        obs.write_bytes(b"")
        spec = _make_spec(
            forecast_path=str(tmp_path / "no_forecast.grib"),
            observation_path=str(obs),
        )
        result = process_case(spec)
        assert result.batch_status == BatchCaseStatus.MISSING_INPUT
        assert result.case_result is None
        assert result.sample is None
        assert "forecast_path" in result.reason

    def test_missing_observation_gives_missing_input(self, tmp_path):
        fcst = tmp_path / "forecast.grib"
        fcst.write_bytes(b"")
        spec = _make_spec(
            forecast_path=str(fcst),
            observation_path=str(tmp_path / "no_obs.grd"),
        )
        result = process_case(spec)
        assert result.batch_status == BatchCaseStatus.MISSING_INPUT
        assert result.case_result is None

    def test_missing_input_provenance_preserved(self, tmp_path):
        spec = _make_spec(
            forecast_path=str(tmp_path / "no.grib"),
            observation_path=str(tmp_path / "no.grd"),
        )
        result = process_case(spec)
        assert result.provenance["case_id"] == spec.case_id
        assert result.provenance["forecast_path"] == spec.forecast_path


# ---------------------------------------------------------------------------
# TestProcessCaseWithMocks
# ---------------------------------------------------------------------------


_BATCH_MODULE = "scientific.cases.batch"


class TestProcessCaseWithMocks:
    """Unit-test process_case with mocked pipeline stages."""

    def _mock_pipeline(
        self,
        case_id: str,
        case_result: RainfallCaseResult,
        record: DatasetRecord,
        target: RainfallTarget,
        tmp_path,
    ):
        """Create real files so _check_inputs_exist passes, then mock pipeline."""
        fcst = tmp_path / "forecast.grib"
        obs  = tmp_path / "obs.grd"
        fcst.write_bytes(b"")
        obs.write_bytes(b"")
        spec = _make_spec(
            case_id=case_id,
            forecast_path=str(fcst),
            observation_path=str(obs),
        )
        return spec

    def test_valid_pipeline_produces_valid_result(self, tmp_path):
        cid = "valid_mock"
        case_result = _make_aligned_case_result(cid)
        record = _make_valid_dataset_record(cid)
        target = _make_valid_target(cid)
        spec = self._mock_pipeline(cid, case_result, record, target, tmp_path)

        with (
            patch(f"{_BATCH_MODULE}.run_rainfall_case", return_value=case_result),
            patch(f"{_BATCH_MODULE}.build_dataset_record", return_value=record),
            patch(f"{_BATCH_MODULE}.build_rainfall_target", return_value=target),
        ):
            result = process_case(spec)

        assert result.batch_status == BatchCaseStatus.VALID
        assert result.case_id == cid
        assert result.case_result is case_result
        assert result.dataset_record is record
        assert result.target is target
        assert result.sample is not None
        assert result.is_trainable()

    def test_blocked_pipeline_produces_blocked_result(self, tmp_path):
        cid = "blocked_mock"
        case_result = _make_blocked_case_result(cid)
        record = _make_blocked_dataset_record(cid)
        target = _make_blocked_target(cid)
        spec = self._mock_pipeline(cid, case_result, record, target, tmp_path)

        with (
            patch(f"{_BATCH_MODULE}.run_rainfall_case", return_value=case_result),
            patch(f"{_BATCH_MODULE}.build_dataset_record", return_value=record),
            patch(f"{_BATCH_MODULE}.build_rainfall_target", return_value=target),
        ):
            result = process_case(spec)

        assert result.batch_status == BatchCaseStatus.BLOCKED
        assert not result.is_trainable()

    def test_exception_in_case_runner_gives_processing_error(self, tmp_path):
        cid = "error_mock"
        spec = self._mock_pipeline(cid, None, None, None, tmp_path)

        with patch(f"{_BATCH_MODULE}.run_rainfall_case", side_effect=RuntimeError("boom")):
            result = process_case(spec)

        assert result.batch_status == BatchCaseStatus.PROCESSING_ERROR
        assert "boom" in result.error_traceback
        assert result.sample is None

    def test_processing_error_does_not_raise(self, tmp_path):
        """process_case must never propagate exceptions."""
        spec = self._mock_pipeline("err2", None, None, None, tmp_path)
        with patch(f"{_BATCH_MODULE}.run_rainfall_case", side_effect=ValueError("oops")):
            result = process_case(spec)
        assert result.batch_status == BatchCaseStatus.PROCESSING_ERROR

    def test_provenance_contains_forecast_path(self, tmp_path):
        cid = "prov_mock"
        case_result = _make_aligned_case_result(cid)
        record = _make_valid_dataset_record(cid)
        target = _make_valid_target(cid)
        spec = self._mock_pipeline(cid, case_result, record, target, tmp_path)

        with (
            patch(f"{_BATCH_MODULE}.run_rainfall_case", return_value=case_result),
            patch(f"{_BATCH_MODULE}.build_dataset_record", return_value=record),
            patch(f"{_BATCH_MODULE}.build_rainfall_target", return_value=target),
        ):
            result = process_case(spec)

        assert "forecast_path" in result.provenance
        assert "observation_path" in result.provenance
        assert result.provenance["case_id"] == cid

    def test_provenance_contains_stages_completed(self, tmp_path):
        cid = "stages_mock"
        case_result = _make_aligned_case_result(cid)
        record = _make_valid_dataset_record(cid)
        target = _make_valid_target(cid)
        spec = self._mock_pipeline(cid, case_result, record, target, tmp_path)

        with (
            patch(f"{_BATCH_MODULE}.run_rainfall_case", return_value=case_result),
            patch(f"{_BATCH_MODULE}.build_dataset_record", return_value=record),
            patch(f"{_BATCH_MODULE}.build_rainfall_target", return_value=target),
        ):
            result = process_case(spec)

        assert "stages_completed" in result.provenance
        assert "case_runner" in result.provenance["stages_completed"]

    def test_no_target_metrics_in_predictors(self, tmp_path):
        """Assembled sample must not contain target metrics in predictor_dict."""
        from scientific.dataset.assembly import TARGET_METRIC_NAMES
        cid = "leakage_mock"
        case_result = _make_aligned_case_result(cid)
        record = _make_valid_dataset_record(cid)
        target = _make_valid_target(cid)
        spec = self._mock_pipeline(cid, case_result, record, target, tmp_path)

        with (
            patch(f"{_BATCH_MODULE}.run_rainfall_case", return_value=case_result),
            patch(f"{_BATCH_MODULE}.build_dataset_record", return_value=record),
            patch(f"{_BATCH_MODULE}.build_rainfall_target", return_value=target),
        ):
            result = process_case(spec)

        assert result.sample is not None
        contaminated = TARGET_METRIC_NAMES & set(result.sample.predictor_dict.keys())
        assert not contaminated, f"Target metrics in predictors: {contaminated}"

    def test_observation_mean_not_in_predictors(self, tmp_path):
        cid = "obs_leak_mock"
        case_result = _make_aligned_case_result(cid)
        record = _make_valid_dataset_record(cid)
        target = _make_valid_target(cid)
        spec = self._mock_pipeline(cid, case_result, record, target, tmp_path)

        with (
            patch(f"{_BATCH_MODULE}.run_rainfall_case", return_value=case_result),
            patch(f"{_BATCH_MODULE}.build_dataset_record", return_value=record),
            patch(f"{_BATCH_MODULE}.build_rainfall_target", return_value=target),
        ):
            result = process_case(spec)

        assert "observation_mean" not in result.sample.predictor_dict

    def test_processing_timestamp_is_set(self, tmp_path):
        before = datetime.utcnow()
        cid = "ts_mock"
        case_result = _make_aligned_case_result(cid)
        record = _make_valid_dataset_record(cid)
        target = _make_valid_target(cid)
        spec = self._mock_pipeline(cid, case_result, record, target, tmp_path)

        with (
            patch(f"{_BATCH_MODULE}.run_rainfall_case", return_value=case_result),
            patch(f"{_BATCH_MODULE}.build_dataset_record", return_value=record),
            patch(f"{_BATCH_MODULE}.build_rainfall_target", return_value=target),
        ):
            result = process_case(spec)
        after = datetime.utcnow()
        assert before <= result.processing_timestamp <= after


# ---------------------------------------------------------------------------
# TestBatchProcessor
# ---------------------------------------------------------------------------


class TestBatchProcessor:
    """BatchProcessor.run() must process all cases deterministically."""

    def _make_all_missing_manifest(self, n: int = 3) -> CaseManifest:
        specs = [_make_spec(case_id=f"miss_{i}") for i in range(n)]
        return CaseManifest.from_specs(specs)

    def test_empty_manifest_returns_empty_result(self):
        manifest = CaseManifest.from_specs([])
        processor = BatchProcessor()
        result = processor.run(manifest)
        assert len(result) == 0
        assert result.total_cases == 0

    def test_all_missing_input_cases_return_missing_status(self):
        manifest = self._make_all_missing_manifest(3)
        processor = BatchProcessor()
        result = processor.run(manifest)
        assert len(result) == 3
        assert result.missing_input_count == 3
        for r in result:
            assert r.batch_status == BatchCaseStatus.MISSING_INPUT

    def test_order_preserved(self):
        manifest = self._make_all_missing_manifest(5)
        processor = BatchProcessor()
        result = processor.run(manifest)
        ids = [r.case_id for r in result]
        assert ids == [f"miss_{i}" for i in range(5)]

    def test_one_failure_does_not_prevent_later_cases(self, tmp_path):
        """A PROCESSING_ERROR on case N must not stop cases N+1, N+2, ..."""
        # Case 0: will raise an exception in run_rainfall_case
        # Case 1 and 2: MISSING_INPUT (files don't exist) — still processed
        specs = [_make_spec(case_id=f"seq_{i}") for i in range(3)]
        manifest = CaseManifest.from_specs(specs)
        processor = BatchProcessor()
        result = processor.run(manifest)
        # All 3 cases must have been attempted
        assert len(result) == 3
        case_ids = {r.case_id for r in result}
        assert case_ids == {"seq_0", "seq_1", "seq_2"}

    def test_counts_are_correct(self):
        manifest = self._make_all_missing_manifest(4)
        processor = BatchProcessor()
        result = processor.run(manifest)
        assert result.total_cases == 4
        assert result.missing_input_count == 4
        assert result.valid_count == 0
        assert result.error_count == 0

    def test_processing_timestamps_recorded(self):
        manifest = self._make_all_missing_manifest(2)
        processor = BatchProcessor()
        result = processor.run(manifest)
        assert result.processing_start <= result.processing_end
        for r in result:
            assert r.processing_timestamp is not None

    def test_summary_dict_structure(self):
        manifest = self._make_all_missing_manifest(2)
        processor = BatchProcessor()
        result = processor.run(manifest)
        summary = result.summary()
        for key in ["total_cases", "valid", "blocked", "missing_input",
                    "processing_errors", "processing_duration_seconds"]:
            assert key in summary

    def test_trainable_samples_empty_when_all_missing(self):
        manifest = self._make_all_missing_manifest(3)
        processor = BatchProcessor()
        result = processor.run(manifest)
        assert result.trainable_samples() == []

    def test_deterministic_ordering_repeated_run(self):
        manifest = self._make_all_missing_manifest(5)
        processor = BatchProcessor()
        r1 = processor.run(manifest)
        r2 = processor.run(manifest)
        assert [r.case_id for r in r1] == [r.case_id for r in r2]
        assert [r.batch_status for r in r1] == [r.batch_status for r in r2]

    def test_manifest_id_preserved(self):
        specs = [_make_spec(case_id="mid_case")]
        manifest = CaseManifest.from_specs(specs, manifest_id="batch_v1")
        processor = BatchProcessor()
        result = processor.run(manifest)
        assert result.manifest_id == "batch_v1"

    def test_progress_callback_called(self):
        manifest = self._make_all_missing_manifest(3)
        calls = []
        processor = BatchProcessor(
            on_progress=lambda i, total, r: calls.append((i, total))
        )
        processor.run(manifest)
        assert len(calls) == 3
        assert calls[0] == (0, 3)
        assert calls[2] == (2, 3)

    def test_progress_callback_error_does_not_corrupt_batch(self):
        """An exception in on_progress must not stop the batch."""
        manifest = self._make_all_missing_manifest(3)

        def bad_callback(i, total, r):
            raise RuntimeError("callback exploded")

        processor = BatchProcessor(on_progress=bad_callback)
        result = processor.run(manifest)
        assert len(result) == 3  # all cases still processed

    def test_iter_process_yields_one_per_case(self):
        manifest = self._make_all_missing_manifest(4)
        processor = BatchProcessor()
        results = list(processor.iter_process(manifest))
        assert len(results) == 4

    def test_iter_process_order_matches_manifest(self):
        manifest = self._make_all_missing_manifest(4)
        processor = BatchProcessor()
        ids = [r.case_id for r in processor.iter_process(manifest)]
        assert ids == [s.case_id for s in manifest]


# ---------------------------------------------------------------------------
# TestBatchCaseResultSummary
# ---------------------------------------------------------------------------


class TestBatchCaseResultSummary:
    """BatchCaseResult.to_summary_dict must not include large arrays."""

    def test_summary_dict_contains_required_keys(self):
        spec = _make_spec()
        result = BatchCaseResult(
            case_id="s1",
            batch_status=BatchCaseStatus.MISSING_INPUT,
            spec=spec,
            reason="No files",
        )
        d = result.to_summary_dict()
        for key in [
            "case_id", "batch_status", "reason", "processing_timestamp",
            "forecast_path", "observation_path", "is_trainable",
        ]:
            assert key in d

    def test_summary_dict_has_no_arrays(self):
        spec = _make_spec()
        result = BatchCaseResult(
            case_id="s2",
            batch_status=BatchCaseStatus.MISSING_INPUT,
            spec=spec,
            reason="No files",
        )
        d = result.to_summary_dict()
        for key, val in d.items():
            assert not isinstance(val, np.ndarray), (
                f"summary_dict field '{key}' is a numpy array"
            )

    def test_is_trainable_false_for_missing(self):
        spec = _make_spec()
        result = BatchCaseResult(
            case_id="s3",
            batch_status=BatchCaseStatus.MISSING_INPUT,
            spec=spec,
        )
        assert result.is_trainable() is False

    def test_batch_result_is_frozen(self):
        manifest = CaseManifest.from_specs([_make_spec()])
        processor = BatchProcessor()
        result = processor.run(manifest)
        with pytest.raises((AttributeError, TypeError)):
            result.total_cases = 999


# ---------------------------------------------------------------------------
# TestNoRawFileModification
# ---------------------------------------------------------------------------


class TestNoRawFileModification:
    """Raw data files must not be modified during batch processing."""

    def test_input_files_unchanged_after_missing_input(self, tmp_path):
        """Even for MISSING_INPUT, no files should be created or deleted."""
        spec = _make_spec(
            forecast_path=str(tmp_path / "no.grib"),
            observation_path=str(tmp_path / "no.grd"),
        )
        files_before = set(tmp_path.iterdir())
        process_case(spec)
        files_after = set(tmp_path.iterdir())
        assert files_before == files_after, (
            "process_case must not create or delete files in the raw data directory"
        )

    def test_existing_files_not_modified(self, tmp_path):
        """If input files exist, their content must not be altered."""
        fcst = tmp_path / "forecast.grib"
        obs  = tmp_path / "obs.grd"
        fcst.write_bytes(b"original_forecast_content")
        obs.write_bytes(b"original_obs_content")

        spec = _make_spec(
            forecast_path=str(fcst),
            observation_path=str(obs),
        )
        # Will fail in run_rainfall_case (invalid GRIB content) → some non-VALID status
        result = process_case(spec)

        # Files must be unchanged
        assert fcst.read_bytes() == b"original_forecast_content"
        assert obs.read_bytes() == b"original_obs_content"
        # Result must be a handled non-VALID outcome, not a file corruption
        assert result.batch_status != BatchCaseStatus.VALID
        assert result.sample is None or not result.sample.is_trainable()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
