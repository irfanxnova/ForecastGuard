"""Tests verifying strict scientific honesty, window validation, and live vs demo state isolation.

Rules enforced:
1. Mismatched forecast and observation accumulation windows MUST be rejected.
2. TIGGE NCMRWF (dems) does not output 3-hourly steps; no synthetic steps may be invented.
3. Live pipeline states MUST NEVER contain fabricated model predictions, scores, or fake hotspots.
4. Demo scenario values MUST remain strictly quarantined to demo mode.
"""

from datetime import datetime, timezone
from pathlib import Path
import json

import pytest

from scientific.alignment import AlignmentStatus, validate_rainfall_alignment
from scientific.ingestion.grib import GribMessageMetadata
from scientific.ingestion.mera import MeraObservation

UTC = timezone.utc


def _make_forecast_metadata(start_step: int = 0, end_step: int = 24) -> GribMessageMetadata:
    return GribMessageMetadata(
        message_index=1,
        edition=2,
        short_name="tp",
        data_date=20250901,
        data_time=0,  # 00:00 UTC
        step_type="accum",
        start_step=start_step,
        end_step=end_step,
        grid_type="regular_ll",
        ni=2,
        nj=2,
        first_lat=20.0,
        last_lat=10.0,
        first_lon=70.0,
        last_lon=71.0,
        i_increment=1.0,
        j_increment=-10.0,
    )


def _make_dummy_obs() -> MeraObservation:
    import numpy as np
    return MeraObservation(
        source_file="test.nc",
        dimensions={"time": 1, "latitude": 2, "longitude": 2},
        latitude=np.array([20.0, 10.0]),
        longitude=np.array([70.0, 71.0]),
        time=np.array([np.datetime64("2025-09-01T00:00:00")]),
        rainfall=np.zeros((1, 2, 2), dtype=np.float32),
        rainfall_units="mm",
        statistics={"number_of_values": 4, "nan_count": 0, "negative_count": 0},
        global_attributes={},
    )


def test_imd_03z_observation_window_rejects_00z_forecast():
    """Verify that a 00Z->24Z (00Z->00Z) forecast step 24 is REJECTED against IMD 03Z->03Z window."""
    forecast_meta = _make_forecast_metadata(start_step=0, end_step=24)
    obs = _make_dummy_obs()

    # IMD daily observation window: 2025-09-01 03:00 UTC to 2025-09-02 03:00 UTC
    imd_start = datetime(2025, 9, 1, 3, 0, tzinfo=UTC)
    imd_end = datetime(2025, 9, 2, 3, 0, tzinfo=UTC)

    result = validate_rainfall_alignment(
        forecast_meta,
        obs,
        observation_accumulation_start=imd_start,
        observation_accumulation_end=imd_end,
    )

    # Must be strictly NOT_ALIGNED
    assert result.status is AlignmentStatus.NOT_ALIGNED
    assert result.forecast_accumulation_start == datetime(2025, 9, 1, 0, 0, tzinfo=UTC)
    assert result.forecast_accumulation_end == datetime(2025, 9, 2, 0, 0, tzinfo=UTC)
    assert result.observation_accumulation_start == imd_start
    assert result.observation_accumulation_end == imd_end
    assert "differ" in result.reason.lower()


def test_hypothetical_03z_to_03z_forecast_aligns_correctly():
    """Verify that if step 3 to step 27 could exist, it would align with 03Z->03Z window."""
    forecast_meta = _make_forecast_metadata(start_step=3, end_step=27)
    obs = _make_dummy_obs()

    imd_start = datetime(2025, 9, 1, 3, 0, tzinfo=UTC)
    imd_end = datetime(2025, 9, 2, 3, 0, tzinfo=UTC)

    result = validate_rainfall_alignment(
        forecast_meta,
        obs,
        observation_accumulation_start=imd_start,
        observation_accumulation_end=imd_end,
    )

    assert result.status is AlignmentStatus.ALIGNED
    assert result.forecast_accumulation_start == imd_start
    assert result.forecast_accumulation_end == imd_end


def test_live_dashboard_state_contains_zero_fabricated_metrics():
    """Verify that frontend live operational state does not leak scenario demo values."""
    data_file = Path("frontend/src/data/operationalData.ts")
    assert data_file.exists(), "operationalData.ts must exist"
    content = data_file.read_text(encoding="utf-8")

    # OPERATIONAL_LIVE_STATE must have isDemoMode: false
    assert "isDemoMode: false" in content

    # Bust risk in live state must be null (not 78% or any hardcoded number)
    assert "bustRiskPercent: null" in content

    # Hotspot in live state must be null (no fake red bubble)
    assert "hotspot: null" in content

    # Historical analogues and evidence factors must be empty in live state
    assert "historicalAnalogues: []" in content
    assert "evidenceFactors: []" in content


def test_south_asia_borders_geometry_is_valid_and_non_empty():
    """Verify that the geographic boundaries file contains real paths for all South Asian countries."""
    borders_file = Path("frontend/src/data/south_asia_borders.json")
    assert borders_file.exists(), "south_asia_borders.json must exist"

    borders = json.loads(borders_file.read_text(encoding="utf-8"))
    required_countries = ["India", "Pakistan", "Nepal", "Bhutan", "Bangladesh", "Sri Lanka", "Myanmar"]

    for country in required_countries:
        assert country in borders, f"Country {country} must be present in borders"
        assert len(borders[country]) > 0, f"Country {country} must have SVG path definitions"
        assert borders[country][0].startswith("M "), f"Path for {country} must be valid SVG path"
