"""Automated tests for scientific validation pipeline (Milestone P1).

Verifies strict scientific contracts:
- Exact timestamp alignment
- Unit consistency and conversions (Kelvin to Celsius, Pa to hPa)
- Station / grid spatial matching (nearest neighbour)
- Missing-value and QC rejection
- Provenance completeness
- Rejection of mismatched accumulation windows (e.g. 00Z->24Z vs 03Z->03Z)
"""

from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pytest

from scientific.validation.pipeline import (
    ForecastRecord,
    ObservationRecord,
    ValidationResult,
    ValidationStatus,
    align_and_verify_case,
    extract_forecast_record_from_grib,
    load_imd_gridded_rainfall_record,
    load_wis2box_synop_record,
)


@pytest.fixture
def sample_forecast_grid() -> ForecastRecord:
    """Synthetic 2m temperature forecast grid over India (20-30N, 70-80E)."""
    lats = np.linspace(20.0, 30.0, 11)  # 1 degree spacing
    lons = np.linspace(70.0, 80.0, 11)
    values = np.full((11, 11), 300.15)  # 300.15 K = 27.0 C

    init_time = datetime(2024, 9, 1, 0, 0, tzinfo=timezone.utc)
    valid_time = datetime(2024, 9, 2, 0, 0, tzinfo=timezone.utc)

    return ForecastRecord(
        source="NCMRWF_TIGGE",
        variable="2t",
        units="K",
        initialization_time=init_time,
        lead_hours=24,
        valid_time=valid_time,
        grid_type="regular_ll",
        lats=lats,
        lons=lons,
        values=values,
        member=1,
        step_type="instant",
    )


@pytest.fixture
def sample_accum_forecast_grid() -> ForecastRecord:
    """Forecast 24h accumulated rainfall (00Z to 24Z)."""
    lats = np.linspace(20.0, 30.0, 11)
    lons = np.linspace(70.0, 80.0, 11)
    values = np.full((11, 11), 15.0)  # 15 mm = 15 kg m**-2

    init_time = datetime(2024, 9, 1, 0, 0, tzinfo=timezone.utc)
    valid_time = datetime(2024, 9, 2, 0, 0, tzinfo=timezone.utc)

    return ForecastRecord(
        source="NCMRWF_TIGGE",
        variable="tp",
        units="kg m**-2",
        initialization_time=init_time,
        lead_hours=24,
        valid_time=valid_time,
        grid_type="regular_ll",
        lats=lats,
        lons=lons,
        values=values,
        member=1,
        step_type="accum",
        accumulation_start=init_time,
        accumulation_end=valid_time,
    )


def test_timestamp_alignment_exact_match(sample_forecast_grid):
    """Instantaneous observation with exact UTC timestamp matches successfully."""
    obs = ObservationRecord(
        source="IMD_SYNOP",
        variable="air_temperature",
        units="Celsius",
        value=25.0,
        timestamp=datetime(2024, 9, 2, 0, 0, tzinfo=timezone.utc),
        latitude=25.0,
        longitude=75.0,
        station_id="42492",
        station_name="PATNA",
    )

    res = align_and_verify_case(sample_forecast_grid, obs)
    assert res.status == ValidationStatus.REAL_ALIGNED_CASE
    assert res.is_aligned is True
    assert res.standardized_units == "Celsius"
    # Forecast = 300.15 K -> 27.0 C. Obs = 25.0 C. Error = +2.0 C
    assert pytest.approx(res.forecast_std_value, 0.01) == 27.0
    assert pytest.approx(res.observation_std_value, 0.01) == 25.0
    assert pytest.approx(res.error, 0.01) == 2.0
    assert pytest.approx(res.absolute_error, 0.01) == 2.0
    assert res.matched_grid_lat == 25.0
    assert res.matched_grid_lon == 75.0


def test_timestamp_alignment_mismatch_rejected(sample_forecast_grid):
    """Temporal mismatch between forecast valid time and observation time must be rejected."""
    obs = ObservationRecord(
        source="IMD_SYNOP",
        variable="air_temperature",
        units="Celsius",
        value=25.0,
        timestamp=datetime(2024, 9, 2, 3, 0, tzinfo=timezone.utc),  # 03 UTC != 00 UTC
        latitude=25.0,
        longitude=75.0,
    )

    res = align_and_verify_case(sample_forecast_grid, obs)
    assert res.status == ValidationStatus.BLOCKED_TEMPORAL_MISMATCH
    assert res.is_aligned is False
    assert "Instantaneous timestamp mismatch" in res.blocking_reason
    assert res.error is None


def test_rejection_of_mismatched_accumulation_windows(sample_accum_forecast_grid):
    """Accumulation window 00Z->24Z vs IMD 03Z->03Z must be strictly rejected."""
    # IMD daily rainfall is 03Z to 03Z
    obs_start = datetime(2024, 9, 1, 3, 0, tzinfo=timezone.utc)
    obs_end = datetime(2024, 9, 2, 3, 0, tzinfo=timezone.utc)

    obs = ObservationRecord(
        source="IMD_GRIDDED",
        variable="rainfall",
        units="mm",
        value=12.0,
        timestamp=obs_end,
        latitude=25.0,
        longitude=75.0,
        accumulation_start=obs_start,
        accumulation_end=obs_end,
    )

    res = align_and_verify_case(sample_accum_forecast_grid, obs)
    assert res.status == ValidationStatus.BLOCKED_ACCUMULATION_WINDOW_MISMATCH
    assert res.is_aligned is False
    assert "Accumulation window mismatch" in res.blocking_reason
    assert res.error is None


def test_rejection_of_undefined_observation_accumulation_window(sample_accum_forecast_grid):
    """Accumulation forecast evaluated against obs with undefined window must be rejected."""
    obs = ObservationRecord(
        source="IMD_GRIDDED",
        variable="rainfall",
        units="mm",
        value=12.0,
        timestamp=datetime(2024, 9, 2, 0, 0, tzinfo=timezone.utc),
        latitude=25.0,
        longitude=75.0,
        accumulation_start=None,  # undefined
        accumulation_end=None,
    )

    res = align_and_verify_case(sample_accum_forecast_grid, obs)
    assert res.status == ValidationStatus.BLOCKED_ACCUMULATION_WINDOW_MISMATCH
    assert res.is_aligned is False
    assert "undefined accumulation" in res.blocking_reason.lower()


def test_unit_consistency_temperature_kelvin_to_celsius(sample_forecast_grid):
    """Forecast 2t in Kelvin is accurately converted to Celsius for comparison."""
    obs = ObservationRecord(
        source="IMD_SYNOP",
        variable="air_temperature",
        units="Celsius",
        value=27.0,
        timestamp=datetime(2024, 9, 2, 0, 0, tzinfo=timezone.utc),
        latitude=25.0,
        longitude=75.0,
    )

    res = align_and_verify_case(sample_forecast_grid, obs)
    assert res.status == ValidationStatus.REAL_ALIGNED_CASE
    assert res.standardized_units == "Celsius"
    assert pytest.approx(res.forecast_std_value, 0.001) == 27.0
    assert pytest.approx(res.observation_std_value, 0.001) == 27.0
    assert pytest.approx(res.error, 0.001) == 0.0


def test_unit_consistency_mslp_pa_to_hpa():
    """Forecast MSLP in Pa is accurately converted to hPa for comparison with observation in hPa."""
    lats = np.linspace(20.0, 30.0, 5)
    lons = np.linspace(70.0, 80.0, 5)
    values = np.full((5, 5), 101325.0)  # 101325 Pa = 1013.25 hPa

    fcst = ForecastRecord(
        source="NCMRWF_TIGGE",
        variable="msl",
        units="Pa",
        initialization_time=datetime(2024, 9, 1, 0, 0, tzinfo=timezone.utc),
        lead_hours=24,
        valid_time=datetime(2024, 9, 2, 0, 0, tzinfo=timezone.utc),
        grid_type="regular_ll",
        lats=lats,
        lons=lons,
        values=values,
        member=1,
    )

    obs = ObservationRecord(
        source="IMD_WIS2BOX",
        variable="pressure_reduced_to_mean_sea_level",
        units="hPa",
        value=1010.25,
        timestamp=datetime(2024, 9, 2, 0, 0, tzinfo=timezone.utc),
        latitude=25.0,
        longitude=75.0,
    )

    res = align_and_verify_case(fcst, obs)
    assert res.status == ValidationStatus.REAL_ALIGNED_CASE
    assert res.standardized_units == "hPa"
    assert pytest.approx(res.forecast_std_value, 0.01) == 1013.25
    assert pytest.approx(res.observation_std_value, 0.01) == 1010.25
    assert pytest.approx(res.error, 0.01) == 3.0


def test_incompatible_variables_rejected(sample_forecast_grid):
    """Comparing temperature forecast with pressure observation must be blocked."""
    obs = ObservationRecord(
        source="IMD_WIS2BOX",
        variable="pressure_reduced_to_mean_sea_level",
        units="hPa",
        value=1010.0,
        timestamp=datetime(2024, 9, 2, 0, 0, tzinfo=timezone.utc),
        latitude=25.0,
        longitude=75.0,
    )

    res = align_and_verify_case(sample_forecast_grid, obs)
    assert res.status == ValidationStatus.BLOCKED_VARIABLE_MISMATCH
    assert res.is_aligned is False
    assert "Incompatible variable pair" in res.blocking_reason


def test_station_grid_matching_nearest_neighbour(sample_forecast_grid):
    """Station coordinate is matched to the nearest grid node."""
    # Lat 24.8, Lon 75.2 should match grid node at (25.0, 75.0)
    obs = ObservationRecord(
        source="IMD_SYNOP",
        variable="air_temperature",
        units="Celsius",
        value=26.0,
        timestamp=datetime(2024, 9, 2, 0, 0, tzinfo=timezone.utc),
        latitude=24.8,
        longitude=75.2,
    )

    res = align_and_verify_case(sample_forecast_grid, obs, matching_method="nearest_neighbour")
    assert res.status == ValidationStatus.REAL_ALIGNED_CASE
    assert res.matched_grid_lat == 25.0
    assert res.matched_grid_lon == 75.0


def test_station_grid_matching_out_of_bounds_rejected(sample_forecast_grid):
    """Station located outside forecast domain must be blocked."""
    obs = ObservationRecord(
        source="IMD_SYNOP",
        variable="air_temperature",
        units="Celsius",
        value=26.0,
        timestamp=datetime(2024, 9, 2, 0, 0, tzinfo=timezone.utc),
        latitude=15.0,  # Below minimum grid lat (20.0)
        longitude=75.0,
    )

    res = align_and_verify_case(sample_forecast_grid, obs)
    assert res.status == ValidationStatus.BLOCKED_SPATIAL_OUT_OF_BOUNDS
    assert res.is_aligned is False
    assert "out of grid bounds" in res.blocking_reason.lower()


def test_missing_value_handling_nan_rejected(sample_forecast_grid):
    """NaN observation value must be blocked without fabricating fallback."""
    obs = ObservationRecord(
        source="IMD_SYNOP",
        variable="air_temperature",
        units="Celsius",
        value=np.nan,
        timestamp=datetime(2024, 9, 2, 0, 0, tzinfo=timezone.utc),
        latitude=25.0,
        longitude=75.0,
    )

    res = align_and_verify_case(sample_forecast_grid, obs)
    assert res.status == ValidationStatus.BLOCKED_MISSING_VALUE
    assert res.is_aligned is False
    assert "missing value" in res.blocking_reason.lower()


def test_missing_value_handling_flag_999_rejected(sample_forecast_grid):
    """Flag value -999.0 must be blocked."""
    obs = ObservationRecord(
        source="IMD_SYNOP",
        variable="air_temperature",
        units="Celsius",
        value=-999.0,
        timestamp=datetime(2024, 9, 2, 0, 0, tzinfo=timezone.utc),
        latitude=25.0,
        longitude=75.0,
    )

    res = align_and_verify_case(sample_forecast_grid, obs)
    assert res.status == ValidationStatus.BLOCKED_MISSING_VALUE
    assert res.is_aligned is False


def test_provenance_completeness(sample_forecast_grid):
    """Result provenance records complete audit metadata."""
    obs = ObservationRecord(
        source="IMD_SYNOP",
        variable="air_temperature",
        units="Celsius",
        value=25.0,
        timestamp=datetime(2024, 9, 2, 0, 0, tzinfo=timezone.utc),
        latitude=25.0,
        longitude=75.0,
        station_id="42492",
        station_name="PATNA",
    )

    res = align_and_verify_case(sample_forecast_grid, obs)
    prov = res.provenance
    assert "forecast_source" in prov
    assert "observation_source" in prov
    assert "forecast_initialization" in prov
    assert "forecast_valid_time" in prov
    assert "observation_timestamp" in prov
    assert "forecast_raw_value" in prov
    assert "observation_raw_value" in prov
    assert "forecast_std_value" in prov
    assert "observation_std_value" in prov
    assert "computed_error" in prov
    assert "standardized_units" in prov


def test_real_grib_extraction():
    """Extract forecast record directly from real downloaded TIGGE GRIB file."""
    grib_path = Path("data/validation/p1_foundation/tigge_dems_2t_20240901_00_step024.grib")
    if not grib_path.exists():
        pytest.skip("TIGGE 2024 GRIB file not available locally")

    fcst = extract_forecast_record_from_grib(grib_path, target_variable="2t", member=1)
    assert fcst.source == "NCMRWF_TIGGE"
    assert fcst.variable == "2t"
    assert fcst.units == "K"
    assert fcst.initialization_time == datetime(2024, 9, 1, 0, 0, tzinfo=timezone.utc)
    assert fcst.lead_hours == 24
    assert fcst.valid_time == datetime(2024, 9, 2, 0, 0, tzinfo=timezone.utc)
    assert fcst.values.shape == (fcst.lats.size, fcst.lons.size)
    assert not np.isnan(fcst.values).all()
