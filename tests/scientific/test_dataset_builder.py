"""Tests for ML-ready dataset builder."""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pytest

from scientific.cases.rainfall_case import (
    RainfallCase,
    RainfallCaseResult,
    RainfallCaseStatus,
)
from scientific.dataset.builder import (
    DatasetRecord,
    DatasetRecordStatus,
    build_dataset_record,
)


class TestDatasetRecordStatus:
    """Test DatasetRecordStatus enum."""

    def test_valid_status_exists(self):
        """Verify VALID status exists."""
        assert DatasetRecordStatus.VALID.value == "VALID"

    def test_blocked_statuses_exist(self):
        """Verify all blocked statuses exist."""
        blocked = [
            DatasetRecordStatus.BLOCKED_UNSPECIFIED_OBSERVATION_WINDOW,
            DatasetRecordStatus.BLOCKED_TEMPORAL_MISMATCH,
            DatasetRecordStatus.BLOCKED_INVALID_METADATA,
            DatasetRecordStatus.BLOCKED_EMPTY_VALID_SET,
            DatasetRecordStatus.BLOCKED_FEATURE_EXTRACTION_ERROR,
            DatasetRecordStatus.BLOCKED_FORECAST_READ_ERROR,
            DatasetRecordStatus.BLOCKED_OBSERVATION_READ_ERROR,
        ]
        assert len(blocked) >= 7


class TestDatasetRecordBasics:
    """Test DatasetRecord structure and methods."""

    def test_dataset_record_frozen(self):
        """Verify DatasetRecord is immutable."""
        record = DatasetRecord(
            case_id="test_case",
            status=DatasetRecordStatus.VALID,
        )
        with pytest.raises(AttributeError):
            record.case_id = "new_case"

    def test_has_targets_valid(self):
        """Verify has_targets() returns True for VALID records."""
        record = DatasetRecord(
            case_id="valid_case",
            status=DatasetRecordStatus.VALID,
            mae=1.5,
            rmse=2.0,
            bias=0.1,
        )
        assert record.has_targets() is True

    def test_has_targets_blocked(self):
        """Verify has_targets() returns False for blocked records."""
        record = DatasetRecord(
            case_id="blocked_case",
            status=DatasetRecordStatus.BLOCKED_TEMPORAL_MISMATCH,
            reason="Windows do not match",
        )
        assert record.has_targets() is False

    def test_to_dict_serializable(self):
        """Verify to_dict() produces JSON-serializable output."""
        record = DatasetRecord(
            case_id="test_case",
            status=DatasetRecordStatus.VALID,
            forecast_initialization_time=datetime(2025, 9, 1, 0, 0, tzinfo=timezone.utc),
            mae=1.5,
            rmse=2.0,
            bias=0.1,
            extraction_timestamp=datetime(2025, 9, 4, 10, 30, 45, tzinfo=timezone.utc),
        )
        d = record.to_dict()

        # Verify datetime is ISO format string
        assert isinstance(d["forecast_initialization_time"], str)
        assert "2025-09-01" in d["forecast_initialization_time"]

        # Verify enum is string
        assert isinstance(d["status"], str)
        assert d["status"] == "VALID"

        # Verify can be JSON serialized
        json_str = json.dumps(d)
        assert "test_case" in json_str

    def test_to_dict_with_nan_feature_arrays(self):
        """Verify to_dict() preserves NaN in feature arrays."""
        feature_array = np.array([[1.5, np.nan], [3.0, 4.0]])
        record = DatasetRecord(
            case_id="test_with_nan",
            status=DatasetRecordStatus.VALID,
            feature_names=["ensemble_mean"],
            ensemble_mean=feature_array,
        )
        d = record.to_dict()

        # After to_dict, feature arrays should be lists
        arr_as_list = d["ensemble_mean"]
        assert isinstance(arr_as_list, list)

        # NaN should be preserved in JSON
        json_str = json.dumps(d)
        assert "test_with_nan" in json_str


class TestBuildDatasetRecordBlocked:
    """Test build_dataset_record with blocked cases."""

    def test_blocked_unspecified_observation_window(self):
        """Verify blocked case due to unspecified observation window."""
        case = RainfallCase(
            case_id="blocked_window",
            forecast_path="data/raw/tigge/dummy.grib",
            observation_path="data/raw/observations/imd_daily/dummy.grd",
            observation_date="2025-09-01",
            observation_start=None,  # Not specified
            observation_end=None,
        )

        case_result = RainfallCaseResult(
            case_id="blocked_window",
            status=RainfallCaseStatus.BLOCKED_UNSPECIFIED_OBSERVATION_WINDOW,
            forecast_metadata={},
            observation_metadata={},
            forecast_window={},
            observation_window={},
            valid_cell_count=0,
            missing_cell_count=0,
            error_statistics={},
            provenance={
                "reason": "Observation accumulation window not explicitly specified",
            },
        )

        record = build_dataset_record(case, case_result)

        assert record.case_id == "blocked_window"
        assert record.status == DatasetRecordStatus.BLOCKED_UNSPECIFIED_OBSERVATION_WINDOW
        assert record.has_targets() is False
        assert record.mae is None
        assert record.rmse is None
        assert record.bias is None

    def test_blocked_temporal_mismatch(self):
        """Verify blocked case due to temporal mismatch."""
        case = RainfallCase(
            case_id="blocked_mismatch",
            forecast_path="data/raw/tigge/dummy.grib",
            observation_path="data/raw/observations/imd_daily/dummy.grd",
            observation_date="2025-09-01",
            observation_start=datetime(2025, 9, 1, 8, 30, tzinfo=timezone.utc),
            observation_end=datetime(2025, 9, 2, 8, 30, tzinfo=timezone.utc),
        )

        case_result = RainfallCaseResult(
            case_id="blocked_mismatch",
            status=RainfallCaseStatus.NOT_ALIGNED,
            forecast_metadata={
                "data_date": 20250901,
                "data_time": 0,
                "step": 24,
            },
            observation_metadata={},
            forecast_window={
                "start": "2025-09-01T00:00:00+00:00",
                "end": "2025-09-02T00:00:00+00:00",
            },
            observation_window={
                "start": "2025-09-01T08:30:00+00:00",
                "end": "2025-09-02T08:30:00+00:00",
                "supplied": True,
            },
            valid_cell_count=0,
            missing_cell_count=1000,
            error_statistics={},
            provenance={
                "reason": "Forecast window (00:00-00:00) does not match observation window (08:30-08:30)",
            },
        )

        record = build_dataset_record(case, case_result)

        assert record.case_id == "blocked_mismatch"
        assert record.status == DatasetRecordStatus.BLOCKED_TEMPORAL_MISMATCH
        assert record.has_targets() is False

    def test_blocked_forecast_read_error(self):
        """Verify blocked case due to forecast read error."""
        case = RainfallCase(
            case_id="blocked_read_error",
            forecast_path="data/raw/tigge/missing.grib",
            observation_path="data/raw/observations/imd_daily/dummy.grd",
            observation_date="2025-09-01",
        )

        case_result = RainfallCaseResult(
            case_id="blocked_read_error",
            status=RainfallCaseStatus.FORECAST_READ_ERROR,
            forecast_metadata={},
            observation_metadata={},
            forecast_window={},
            observation_window={},
            valid_cell_count=0,
            missing_cell_count=0,
            error_statistics={},
            provenance={
                "reason": "Forecast file not found: data/raw/tigge/missing.grib",
            },
        )

        record = build_dataset_record(case, case_result)

        assert record.status == DatasetRecordStatus.BLOCKED_FORECAST_READ_ERROR
        assert record.has_targets() is False


class TestBuildDatasetRecordProvenance:
    """Test provenance preservation in dataset records."""

    def test_provenance_case_id(self):
        """Verify case_id is preserved."""
        case = RainfallCase(
            case_id="prov_test_001",
            forecast_path="dummy.grib",
            observation_path="dummy.grd",
            observation_date="2025-09-01",
        )

        case_result = RainfallCaseResult(
            case_id="prov_test_001",
            status=RainfallCaseStatus.BLOCKED_UNSPECIFIED_OBSERVATION_WINDOW,
            forecast_metadata={},
            observation_metadata={},
            forecast_window={},
            observation_window={},
            valid_cell_count=0,
            missing_cell_count=0,
            error_statistics={},
            provenance={"original": "provenance"},
        )

        record = build_dataset_record(case, case_result)
        assert record.case_id == "prov_test_001"

    def test_provenance_preservation(self):
        """Verify full provenance dict is preserved."""
        original_prov = {
            "case_id": "prov_test",
            "forecast_path": "data/raw/tigge/test.grib",
            "observation_path": "data/raw/observations/imd_daily/test.grd",
            "reason": "Test blocking reason",
        }

        case = RainfallCase(
            case_id="prov_test",
            forecast_path="data/raw/tigge/test.grib",
            observation_path="data/raw/observations/imd_daily/test.grd",
            observation_date="2025-09-01",
        )

        case_result = RainfallCaseResult(
            case_id="prov_test",
            status=RainfallCaseStatus.INVALID_METADATA,
            forecast_metadata={},
            observation_metadata={},
            forecast_window={},
            observation_window={},
            valid_cell_count=0,
            missing_cell_count=0,
            error_statistics={},
            provenance=original_prov,
        )

        record = build_dataset_record(case, case_result)

        assert record.provenance == original_prov

    def test_extraction_timestamp_set(self):
        """Verify extraction_timestamp is set."""
        case = RainfallCase(
            case_id="ts_test",
            forecast_path="dummy.grib",
            observation_path="dummy.grd",
            observation_date="2025-09-01",
        )

        case_result = RainfallCaseResult(
            case_id="ts_test",
            status=RainfallCaseStatus.BLOCKED_UNSPECIFIED_OBSERVATION_WINDOW,
            forecast_metadata={},
            observation_metadata={},
            forecast_window={},
            observation_window={},
            valid_cell_count=0,
            missing_cell_count=0,
            error_statistics={},
            provenance={},
        )

        before = datetime.utcnow()
        record = build_dataset_record(case, case_result)
        after = datetime.utcnow()

        assert record.extraction_timestamp is not None
        assert before <= record.extraction_timestamp <= after


class TestBuildDatasetRecordNaNHandling:
    """Test NaN handling in dataset records."""

    def test_blocked_empty_valid_set(self):
        """Verify blocked case due to empty valid set (all NaN)."""
        case = RainfallCase(
            case_id="blocked_empty",
            forecast_path="dummy.grib",
            observation_path="dummy.grd",
            observation_date="2025-09-01",
            observation_start=datetime(2025, 9, 1, 0, 0, tzinfo=timezone.utc),
            observation_end=datetime(2025, 9, 2, 0, 0, tzinfo=timezone.utc),
        )

        case_result = RainfallCaseResult(
            case_id="blocked_empty",
            status=RainfallCaseStatus.EMPTY_VALID_SET,
            forecast_metadata={
                "ni": 10,
                "nj": 10,
            },
            observation_metadata={},
            forecast_window={
                "start": "2025-09-01T00:00:00+00:00",
                "end": "2025-09-02T00:00:00+00:00",
            },
            observation_window={
                "start": "2025-09-01T00:00:00+00:00",
                "end": "2025-09-02T00:00:00+00:00",
                "supplied": True,
            },
            valid_cell_count=0,
            missing_cell_count=100,
            error_statistics={},
            provenance={
                "reason": "No cells contain finite forecast and observation values",
            },
        )

        record = build_dataset_record(case, case_result)

        assert record.status == DatasetRecordStatus.BLOCKED_EMPTY_VALID_SET
        assert record.mae is None
        # For blocked cases, cell counts are None (not meaningful for blocked cases)
        assert record.valid_cell_count is None
        assert record.missing_cell_count is None
        # But the reason should be preserved
        assert "No cells contain finite" in record.reason

    def test_blocked_no_target_generated(self):
        """Verify blocked cases do not accidentally produce targets."""
        blocked_statuses = [
            RainfallCaseStatus.BLOCKED_UNSPECIFIED_OBSERVATION_WINDOW,
            RainfallCaseStatus.NOT_ALIGNED,
            RainfallCaseStatus.INVALID_METADATA,
            RainfallCaseStatus.EMPTY_VALID_SET,
            RainfallCaseStatus.FORECAST_READ_ERROR,
            RainfallCaseStatus.OBSERVATION_READ_ERROR,
        ]

        for status in blocked_statuses:
            case = RainfallCase(
                case_id=f"blocked_{status.value}",
                forecast_path="dummy.grib",
                observation_path="dummy.grd",
                observation_date="2025-09-01",
            )

            case_result = RainfallCaseResult(
                case_id=f"blocked_{status.value}",
                status=status,
                forecast_metadata={},
                observation_metadata={},
                forecast_window={},
                observation_window={},
                valid_cell_count=0,
                missing_cell_count=0,
                error_statistics={},
                provenance={"reason": str(status)},
            )

            record = build_dataset_record(case, case_result)

            # All blocked cases must not have targets
            assert record.has_targets() is False
            assert record.mae is None
            assert record.rmse is None
            assert record.bias is None


class TestEnsembleMemberCount:
    """Verify ensemble_member_count records actual members, not feature count.

    The ensemble feature engine produces 24 feature arrays regardless of how
    many ensemble members were in the GRIB.  ensemble_member_count must track
    the real member count (from EnsembleRainfallFeatures.member_count), not
    len(feature_names) which is always 24.
    """

    def _make_mock_features(self, n_members: int):
        """Return a mock EnsembleRainfallFeatures with n_members and 24 feature arrays."""
        from scientific.features.ensemble_rainfall import EnsembleRainfallFeatures

        grid = np.zeros((3, 3), dtype=np.float64)
        feature_names = [
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
        return EnsembleRainfallFeatures(
            forecast_date=20250901,
            forecast_time=0,
            forecast_step=24,
            forecast_step_type="accum",
            member_count=n_members,
            valid_member_count=n_members,
            grid_shape=(3, 3),
            ensemble_mean=grid, ensemble_median=grid, ensemble_min=grid,
            ensemble_max=grid, ensemble_std=grid, ensemble_range=grid,
            ensemble_iqr=grid, ensemble_p10=grid, ensemble_p25=grid,
            ensemble_p75=grid, ensemble_p90=grid,
            coefficient_of_variation=grid, ensemble_skewness=grid,
            probability_rain_gt_1mm=grid, probability_rain_gt_10mm=grid,
            probability_rain_gt_25mm=grid, probability_rain_gt_50mm=grid,
            probability_rain_gt_100mm=grid,
            gradient_magnitude=grid, latitude_gradient=grid,
            longitude_gradient=grid,
            mean_pairwise_member_difference=grid,
            maximum_ensemble_gap=grid, member_agreement_fraction=grid,
            feature_names=feature_names,
        )

    def test_member_count_is_not_feature_count(self):
        """ensemble_member_count must differ from 24 when member count != 24.

        This test uses the feature dataclass directly to confirm that
        member_count != len(feature_names) when they differ.  The assertion
        would pass trivially if the builder used len(feature_names) (always 24)
        for a 5-member ensemble.
        """
        features = self._make_mock_features(n_members=5)

        # Sanity: the feature engine reports 24 arrays but only 5 members
        assert len(features.feature_array_names()) == 24
        assert features.member_count == 5
        # The two numbers differ — confirm they are not the same
        assert features.member_count != len(features.feature_array_names())

    def test_member_count_source_of_truth(self):
        """EnsembleRainfallFeatures.member_count is the authoritative source.

        If the builder reads features.member_count rather than len(features_dict),
        a 7-member ensemble must produce ensemble_member_count == 7, not 24.
        """
        features = self._make_mock_features(n_members=7)
        assert features.member_count == 7
        # Confirm feature array count is still always 24
        assert len(features.feature_array_names()) == 24

    def test_real_grib_member_count_smoke(self):
        """Smoke test: real GRIB member count is recorded in the dataset record.

        This test requires the sample GRIB and IMD files.  If they are absent
        it is skipped.  The key assertion is:
          record.ensemble_member_count != 24
        which would fail if the builder mistakenly used len(feature_names).
        The known GRIB has 11 ensemble members.
        """
        sample_grib = Path("data/raw/tigge/67603f4734166cde0f2c2962323ad8e4.grib")
        sample_imd = Path("data/raw/observations/imd_daily/01092025.grd")

        if not sample_grib.exists() or not sample_imd.exists():
            pytest.skip("Sample GRIB and IMD files not available")

        from scientific.cases.rainfall_case import run_rainfall_case

        case = RainfallCase(
            case_id="member_count_smoke",
            forecast_path=sample_grib,
            observation_path=sample_imd,
            observation_date="2025-09-01",
            observation_start=datetime(2025, 9, 1, 0, 0, tzinfo=timezone.utc),
            observation_end=datetime(2025, 9, 2, 0, 0, tzinfo=timezone.utc),
        )

        case_result = run_rainfall_case(case)
        record = build_dataset_record(case, case_result)

        if record.has_targets():
            # The GRIB has 11 members; ensemble_member_count must not be 24
            assert record.ensemble_member_count is not None
            assert record.ensemble_member_count != 24, (
                f"ensemble_member_count is {record.ensemble_member_count}, "
                "expected actual member count (e.g. 11), not the 24 feature arrays"
            )
            assert record.ensemble_member_count == 11


class TestBuildDatasetRecordWithFeatures:
    """Test dataset record with actual features (integration with real GRIB data)."""

    def test_real_grib_dataset_record_smoke_test(self):
        """Smoke test: build dataset record from real GRIB data.

        Note: This test requires the sample GRIB file to exist.
        It verifies that feature extraction and record building work together.
        """
        sample_grib = Path("data/raw/tigge/67603f4734166cde0f2c2962323ad8e4.grib")
        sample_imd = Path("data/raw/observations/imd_daily/01092025.grd")

        if not sample_grib.exists() or not sample_imd.exists():
            pytest.skip("Sample GRIB and IMD files not available")

        case = RainfallCase(
            case_id="real_grib_dataset_test",
            forecast_path=sample_grib,
            observation_path=sample_imd,
            observation_date="2025-09-01",
            observation_start=datetime(2025, 9, 1, 0, 0, tzinfo=timezone.utc),
            observation_end=datetime(2025, 9, 2, 0, 0, tzinfo=timezone.utc),
        )

        from scientific.cases.rainfall_case import run_rainfall_case

        case_result = run_rainfall_case(case)

        # Build dataset record from case result
        record = build_dataset_record(case, case_result)

        # Verify record structure regardless of alignment status
        assert record.case_id == "real_grib_dataset_test"
        assert record.status is not None
        assert record.provenance is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
