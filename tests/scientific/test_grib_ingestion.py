"""Tests for real GRIB2 ingestion, QC, and manifest generation."""

from pathlib import Path
import json
import pytest

import scientific.ingestion.grib as grib_module
from scientific.ingestion.grib import (
    GribMessageMetadata,
    GribQCReport,
    generate_manifest,
    group_messages,
    perform_qc,
    read_grib_file,
)

SAMPLE_GRIB_PATH = Path("data/raw/tigge/67603f4734166cde0f2c2962323ad8e4.grib")


# ---------------------------------------------------------------------------
# Unit tests using minimal mock metadata objects (not dependent on external files)
# ---------------------------------------------------------------------------

def test_mock_metadata_object_and_dict() -> None:
    """Verify GribMessageMetadata properties and dictionary serialization."""
    meta = GribMessageMetadata(
        message_index=1,
        edition=2,
        short_name="tp",
        name="Total Precipitation",
        units="kg m**-2",
        data_date=20250901,
        data_time=0,
        step=24,
        step_type="accum",
        start_step=0,
        end_step=24,
        forecast_type="pf",
        member=1,
        grid_type="regular_ll",
        ni=112,
        nj=83,
        number_of_values=9296,
        min_value=0.0,
        max_value=150.0,
        mean_value=12.5,
        nan_count=0,
        negative_count=0,
    )

    data = meta.to_dict()
    assert data["short_name"] == "tp"
    assert data["units"] == "kg m**-2"
    assert data["step_type"] == "accum"
    assert data["start_step"] == 0
    assert data["end_step"] == 24
    assert data["number_of_values"] == 9296


def test_qc_evaluates_clean_messages_as_pass() -> None:
    """Verify perform_qc returns PASS when messages have no NaNs and no invalid negatives."""
    meta = GribMessageMetadata(
        message_index=1,
        edition=2,
        short_name="tp",
        grid_type="regular_ll",
        data_date=20250901,
        number_of_values=100,
        nan_count=0,
        negative_count=0,
    )
    qc = perform_qc([meta], can_open=True)
    assert qc.status == "PASS"
    assert qc.can_open is True
    assert qc.total_messages_parsed == 1
    assert qc.unexpected_nan_count == 0
    assert qc.tp_negative_count == 0
    assert len(qc.issues) == 0


def test_qc_detects_negative_precipitation_and_warns() -> None:
    """Verify perform_qc flags negative precipitation as a warning without crashing."""
    meta = GribMessageMetadata(
        message_index=1,
        edition=2,
        short_name="tp",
        grid_type="regular_ll",
        data_date=20250901,
        number_of_values=100,
        nan_count=0,
        negative_count=3,
    )
    qc = perform_qc([meta], can_open=True)
    assert qc.status == "WARN"
    assert qc.tp_negative_count == 3
    assert any("negative values in total precipitation" in issue for issue in qc.issues)


def test_qc_fails_on_unopenable_file() -> None:
    """Verify perform_qc correctly marks unopenable files as FAIL."""
    qc = perform_qc([], can_open=False, open_error="Simulated I/O Error")
    assert qc.status == "FAIL"
    assert qc.can_open is False
    assert qc.total_messages_parsed == 0


def test_group_messages_organizes_hierarchy() -> None:
    """Verify group_messages includes initialization time in its hierarchy."""
    m1 = GribMessageMetadata(
        message_index=1,
        edition=2,
        short_name="tp",
        name="Total Precipitation",
        units="kg m**-2",
        step=24,
        step_type="accum",
        start_step=0,
        end_step=24,
        forecast_type="pf",
        member=1,
        number_of_values=100,
        min_value=0.0,
        max_value=50.0,
        mean_value=5.0,
    )
    m2 = GribMessageMetadata(
        message_index=2,
        edition=2,
        short_name="tp",
        name="Total Precipitation",
        units="kg m**-2",
        step=24,
        step_type="accum",
        start_step=0,
        end_step=24,
        forecast_type="pf",
        member=2,
        number_of_values=100,
        min_value=0.0,
        max_value=70.0,
        mean_value=7.0,
    )
    grouped = group_messages([m1, m2])
    init_groups = grouped["0 0000 UTC"]["variables"]
    assert "tp" in init_groups
    assert "pf" in init_groups["tp"]["forecast_types"]
    assert "step_24" in init_groups["tp"]["forecast_types"]["pf"]
    members = init_groups["tp"]["forecast_types"]["pf"]["step_24"]["members"]
    assert 1 in members
    assert 2 in members
    assert members[1]["max"] == 50.0
    assert members[2]["max"] == 70.0


def test_group_messages_separates_initialization_times() -> None:
    """Verify messages from different forecast cycles remain in separate groups."""
    base = GribMessageMetadata(
        message_index=1,
        edition=2,
        short_name="tp",
        data_date=20250901,
        data_time=0,
        forecast_type="pf",
        member=1,
        number_of_values=100,
    )
    later = GribMessageMetadata(
        **{**base.to_dict(), "message_index": 2, "data_time": 1200}
    )

    grouped = group_messages([base, later])

    assert set(grouped) == {"20250901 0000 UTC", "20250901 1200 UTC"}
    assert grouped["20250901 0000 UTC"]["variables"]["tp"]
    assert grouped["20250901 1200 UTC"]["variables"]["tp"]


def test_mid_file_parsing_failure_fails_qc(monkeypatch, tmp_path) -> None:
    """Verify a parsing failure after one message prevents a successful partial result."""
    input_path = tmp_path / "mid_file_failure.grib"
    input_path.write_bytes(b"not used by the patched reader")
    handles = iter([object(), object(), None])

    monkeypatch.setattr(grib_module.eccodes, "codes_grib_new_from_file", lambda _: next(handles))
    monkeypatch.setattr(grib_module.eccodes, "codes_release", lambda _: None)
    monkeypatch.setattr(
        grib_module,
        "parse_grib_message",
        lambda handle, index, compute_stats: (
            GribMessageMetadata(
                message_index=index,
                edition=2,
                short_name="tp",
                grid_type="regular_ll",
                data_date=20250901,
                number_of_values=100,
            )
            if index == 1
            else (_ for _ in ()).throw(RuntimeError("simulated mid-file parse failure"))
        ),
    )

    messages, qc = read_grib_file(input_path)

    assert len(messages) == 1
    assert qc.status == "FAIL"
    assert any("simulated mid-file parse failure" in issue for issue in qc.issues)


# ---------------------------------------------------------------------------
# Integration tests on the real NCMRWF/TIGGE sample file
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def sample_grib_data():
    """Fixture providing parsed messages and QC report from the real sample file."""
    if not SAMPLE_GRIB_PATH.exists():
        pytest.skip(f"Real sample GRIB not found at {SAMPLE_GRIB_PATH}. Skipping real data test.")
    messages, qc = read_grib_file(SAMPLE_GRIB_PATH, compute_stats=True)
    return messages, qc


def test_real_grib_file_parsed_successfully(sample_grib_data) -> None:
    """Verify real GRIB file can be opened and parsed with clean QC."""
    messages, qc = sample_grib_data
    assert qc.can_open is True
    assert qc.status == "PASS"
    assert qc.unexpected_nan_count == 0
    assert qc.tp_negative_count == 0


def test_real_grib_total_message_count(sample_grib_data) -> None:
    """Verify sample file contains exactly 44 messages."""
    messages, _ = sample_grib_data
    assert len(messages) == 44


def test_real_grib_unique_variables(sample_grib_data) -> None:
    """Verify all four expected variables (2t, msl, tcc, tp) are present."""
    messages, _ = sample_grib_data
    variables = sorted(list({m.short_name for m in messages}))
    assert variables == ["2t", "msl", "tcc", "tp"]


def test_real_grib_ensemble_members(sample_grib_data) -> None:
    """Verify perturbed forecast members span exactly 1 through 11."""
    messages, _ = sample_grib_data
    members = sorted(list({m.member for m in messages if m.member is not None}))
    assert members == list(range(1, 12))
    assert len(members) == 11

    forecast_types = {m.forecast_type for m in messages}
    assert forecast_types == {"pf"}


def test_real_grib_tp_metadata_and_accumulation(sample_grib_data) -> None:
    """Verify total precipitation metadata, units, and 0-24h accumulation semantics."""
    messages, _ = sample_grib_data
    tp_messages = [m for m in messages if m.short_name == "tp"]
    assert len(tp_messages) == 11

    for m in tp_messages:
        assert m.short_name == "tp"
        assert m.name == "Total Precipitation"
        assert m.units == "kg m**-2"
        assert m.step == 24
        assert m.step_type == "accum"
        assert m.start_step == 0
        assert m.end_step == 24
        assert m.forecast_type == "pf"
        assert m.data_date == 20250901
        assert m.data_time == 0


def test_real_grib_grid_dimensions(sample_grib_data) -> None:
    """Verify spatial grid attributes (regular_ll, Ni=112, Nj=83, increments)."""
    messages, _ = sample_grib_data
    for m in messages:
        assert m.grid_type == "regular_ll"
        assert m.ni == 112
        assert m.nj == 83
        assert m.number_of_values == 9296  # 112 * 83
        assert pytest.approx(m.first_lat, abs=1e-3) == 19.92
        assert pytest.approx(m.first_lon, abs=1e-3) == 70.02
        assert pytest.approx(m.last_lat, abs=1e-3) == 10.08
        assert pytest.approx(m.last_lon, abs=1e-3) == 90.00
        assert pytest.approx(m.i_increment, abs=1e-3) == 0.18
        assert pytest.approx(m.j_increment, abs=1e-3) == 0.12


def test_real_grib_tp_member_1_statistics(sample_grib_data) -> None:
    """Verify TP member 1 numerical values and statistics match manual inspection benchmark."""
    messages, _ = sample_grib_data
    tp_m1 = next((m for m in messages if m.short_name == "tp" and m.member == 1), None)
    assert tp_m1 is not None

    assert tp_m1.number_of_values == 9296
    assert tp_m1.nan_count == 0
    assert tp_m1.negative_count == 0

    # Benchmark: min=0.00177001953125, max=164.741455078125, mean=12.199371452791144
    assert pytest.approx(tp_m1.min_value, rel=1e-5) == 0.0017700195
    assert pytest.approx(tp_m1.max_value, rel=1e-5) == 164.741455
    assert pytest.approx(tp_m1.mean_value, rel=1e-5) == 12.199371


def test_generate_manifest_creates_valid_json(tmp_path) -> None:
    """Verify generate_manifest creates a valid, deterministic JSON manifest file."""
    if not SAMPLE_GRIB_PATH.exists():
        pytest.skip(f"Real sample GRIB not found at {SAMPLE_GRIB_PATH}")

    manifest_file = generate_manifest(SAMPLE_GRIB_PATH, output_dir=tmp_path)
    assert manifest_file.exists()
    assert manifest_file.name == f"{SAMPLE_GRIB_PATH.stem}_manifest.json"

    with open(manifest_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["source_file_name"] == SAMPLE_GRIB_PATH.name
    assert data["source_file_size_bytes"] == 1235344
    assert data["source_file_sha256"] == "37cfccaac79bc952bb00641b3b9bf3b07e4d984ba867b950dd727624bca46d0b"
    assert data["total_message_count"] == 44
    assert data["unique_variables"] == ["2t", "msl", "tcc", "tp"]
    assert data["ensemble_members"] == list(range(1, 12))
    assert data["forecast_steps"] == [24]
    assert data["qc_summary"]["status"] == "PASS"
    assert len(data["messages"]) == 44
    assert "runtime_metadata" in data


def test_generate_manifest_is_deterministic(tmp_path) -> None:
    """Verify unchanged input produces identical manifest JSON on repeated generation."""
    if not SAMPLE_GRIB_PATH.exists():
        pytest.skip(f"Real sample GRIB not found at {SAMPLE_GRIB_PATH}")

    manifest_file = generate_manifest(SAMPLE_GRIB_PATH, output_dir=tmp_path)
    first_content = manifest_file.read_text(encoding="utf-8")
    generate_manifest(SAMPLE_GRIB_PATH, output_dir=tmp_path)
    second_content = manifest_file.read_text(encoding="utf-8")

    assert first_content == second_content
    assert json.loads(first_content) == json.loads(second_content)
