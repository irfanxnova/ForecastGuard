"""Unit tests for explicit, offline NCMRWF/TIGGE ECDS acquisition."""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from scientific.ingestion.tigge import (
    NCMRWF_TIGGE_ORIGIN,
    TIGGE_DATASET,
    TiggeConfigurationError,
    TiggeCredentials,
    TiggeRequest,
    acquire_tigge_forecast,
    format_area,
    format_members,
    main,
    provenance_path,
)
from scientific.cases.planner import PlannedCase


UTC = timezone.utc


def _request(output_path: Path) -> TiggeRequest:
    return TiggeRequest(
        initialization_date="2025-09-01",
        cycle_hour=0,
        lead_hours=24,
        variable="tp",
        members=(1, 2, 3),
        area=(20.0, 70.0, 10.0, 90.0),
        output_path=output_path,
    )


def test_request_construction_preserves_exact_tigge_parameters(tmp_path: Path) -> None:
    request = _request(tmp_path)

    assert request.dataset == TIGGE_DATASET
    assert request.origin == NCMRWF_TIGGE_ORIGIN
    assert request.initialization_time == datetime(2025, 9, 1, 0, tzinfo=UTC)
    assert request.to_cds_request() == {
        "class": "ti", "date": "2025-09-01", "expver": "prod", "levtype": "sfc",
        "origin": "dems", "param": "228228", "step": "24", "time": "00:00:00",
        "type": "pf", "number": "1/2/3", "area": "20/70/10/90",
    }


def test_request_can_reuse_exact_planner_initialization_and_lead(tmp_path: Path) -> None:
    planned_case = PlannedCase(
        case_id="planned_001",
        forecast_initialization_time=datetime(2025, 9, 1, 12, tzinfo=UTC),
        forecast_lead_hours=36,
        forecast_source="NCMRWF",
        forecast_variable="tp",
        observation_source="IMD_DAILY",
        observation_date="2025-09-03",
        region="India",
        observation_start=None,
        observation_end=None,
        observation_window_specified=False,
        forecast_path=None,
        observation_path=None,
        trajectory_group_id="tg_test",
        sequence_index=0,
        predecessor_init_time=None,
        cycle_label="12Z",
        forecast_accumulation_end=datetime(2025, 9, 3, tzinfo=UTC),
    )

    request = TiggeRequest.from_planned_case(planned_case, output_path=tmp_path)
    assert request.initialization_time == planned_case.forecast_initialization_time
    assert request.lead_hours == planned_case.forecast_lead_hours


def test_credentials_require_url_and_key() -> None:
    with pytest.raises(TiggeConfigurationError, match="ECDS credentials"):
        TiggeCredentials.from_environment({})

    credentials = TiggeCredentials.from_environment(
        {"ECDS_API_URL": "https://example.invalid/api", "ECDS_API_KEY": "token"}
    )
    assert credentials.url == "https://example.invalid/api"
    assert credentials.key == "token"


def test_output_name_is_deterministic(tmp_path: Path) -> None:
    first = _request(tmp_path).output_file
    second = _request(tmp_path).output_file

    assert first == second
    assert first.name == "tigge_dems_tp_pf_20250901_00_step024_m001-002-003_n20_w70_s10_e90.grib"


def test_member_and_area_formatting_preserve_requested_values() -> None:
    assert format_members((1, 3, 11)) == "1/3/11"
    assert format_area((20, 70, 10, 90)) == "20/70/10/90"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"initialization_date": "not-a-date"}, {"cycle_hour": 6},
        {"lead_hours": -1}, {"variable": "t2m"},
        {"members": (1, 1)}, {"members": (0,)}, {"area": (10, 70, 20, 90)},
    ],
)
def test_invalid_parameters_are_rejected(tmp_path: Path, kwargs: dict) -> None:
    parameters = {
        "initialization_date": "2025-09-01", "cycle_hour": 0, "lead_hours": 24,
        "variable": "tp", "members": (1,), "area": (20, 70, 10, 90),
        "output_path": tmp_path,
    }
    parameters.update(kwargs)
    with pytest.raises(ValueError):
        TiggeRequest(**parameters)


def test_dry_run_requires_neither_credentials_nor_network(tmp_path: Path) -> None:
    result = acquire_tigge_forecast(_request(tmp_path), dry_run=True)

    assert result.status == "DRY_RUN"
    assert not result.output_file.exists()
    assert not result.provenance_file.exists()


def test_existing_exact_output_is_skipped_without_client(tmp_path: Path) -> None:
    request = _request(tmp_path)
    request.output_file.write_bytes(b"existing mocked payload")
    provenance_path(request.output_file).write_text(
        json.dumps({"request": request.to_provenance_request()}), encoding="utf-8"
    )

    result = acquire_tigge_forecast(request)
    assert result.status == "SKIPPED_EXISTING"


def test_download_writes_atomic_output_and_provenance_sidecar(tmp_path: Path) -> None:
    request = _request(tmp_path)
    calls = []

    class FakeClient:
        def retrieve(self, dataset: str, parameters: dict, target: str) -> None:
            calls.append((dataset, parameters, target))
            Path(target).write_bytes(b"mocked ECDS response")

    result = acquire_tigge_forecast(
        request,
        credentials=TiggeCredentials("https://example.invalid/api", "token"),
        client_factory=lambda _: FakeClient(),
    )

    assert result.status == "DOWNLOADED"
    assert request.output_file.read_bytes() == b"mocked ECDS response"
    assert len(calls) == 1
    assert calls[0][0] == TIGGE_DATASET
    assert calls[0][1] == request.to_cds_request()
    assert calls[0][2].endswith(".partial")
    sidecar = json.loads(result.provenance_file.read_text(encoding="utf-8"))
    assert sidecar["request"] == request.to_provenance_request()
    assert sidecar["returned_members"] is None
    assert not list(tmp_path.glob("*.partial"))


def test_cli_dry_run_prints_exact_request_without_credentials(tmp_path: Path, capsys) -> None:
    status = main([
        "--dry-run", "--date", "2025-09-01", "--cycle", "0", "--lead", "24",
        "--variable", "tp", "--members", "1,2,3", "--area", "20,70,10,90",
        "--output", str(tmp_path),
    ])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["status"] == "DRY_RUN"
    assert payload["request"]["request_parameters"]["number"] == "1/2/3"


def test_module_cli_dry_run_emits_no_runtime_warning(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable, "-W", "error::RuntimeWarning", "-m",
            "scientific.ingestion.tigge", "--dry-run", "--date", "2025-09-01",
            "--output", str(tmp_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "found in sys.modules" not in completed.stderr
