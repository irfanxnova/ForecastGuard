"""Explicit, reproducible ECDS acquisition for small NCMRWF/TIGGE requests.

This module requests archive data only. It does not inspect, transform, or
verify returned GRIB fields. Archive availability is determined by the ECDS API.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional, Sequence, Tuple, Union
from uuid import uuid4

TIGGE_DATASET = "tigge-forecasts"
TIGGE_CLASS = "ti"
NCMRWF_TIGGE_ORIGIN = "dems"
TIGGE_FORECAST_TYPE = "pf"
TIGGE_LEVEL_TYPE = "sfc"
TIGGE_TP_PARAMETER = "228228"
TIGGE_VARIABLE_PARAMETERS = {"tp": TIGGE_TP_PARAMETER}
DEFAULT_SMOKE_MEMBERS = (1,)
DEFAULT_SMOKE_AREA = (20.0, 70.0, 10.0, 90.0)


class TiggeAcquisitionError(RuntimeError):
    """Raised when an explicit TIGGE acquisition cannot safely proceed."""


class TiggeConfigurationError(TiggeAcquisitionError):
    """Raised when ECDS API configuration is absent or incomplete."""


@dataclass(frozen=True)
class TiggeCredentials:
    """ECDS API endpoint and token loaded outside source control."""

    url: str
    key: str

    @classmethod
    def from_environment(cls, environ: Optional[Mapping[str, str]] = None) -> "TiggeCredentials":
        """Load ECDS_API_* or standard CDSAPI_* variables without logging secrets."""
        values = os.environ if environ is None else environ
        url = values.get("ECDS_API_URL") or values.get("CDSAPI_URL")
        key = values.get("ECDS_API_KEY") or values.get("CDSAPI_KEY")
        if not url or not key:
            raise TiggeConfigurationError(
                "ECDS credentials are required for retrieval. Set ECDS_API_URL and "
                "ECDS_API_KEY (or CDSAPI_URL and CDSAPI_KEY); dry-run needs neither."
            )
        return cls(url=url, key=key)


def _parse_request_date(value: Union[date, str]) -> date:
    if isinstance(value, datetime):
        raise ValueError("initialization_date must be a calendar date, not a datetime")
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("initialization_date must be YYYY-MM-DD") from exc
    raise TypeError("initialization_date must be a date or YYYY-MM-DD string")


def _format_number(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)


def format_members(members: Sequence[int]) -> str:
    """Format exactly the requested perturbed-member identifiers for MARS."""
    if not members:
        raise ValueError("members must contain at least one perturbed member")
    if any(not isinstance(member, int) or member < 1 for member in members):
        raise ValueError("members must contain positive integer identifiers")
    if len(set(members)) != len(members):
        raise ValueError("members must not contain duplicates")
    return "/".join(str(member) for member in members)


def format_area(area: Sequence[float]) -> str:
    """Format a north/west/south/east geographic bounding box for MARS."""
    if len(area) != 4:
        raise ValueError("area must contain north, west, south, east")
    north, west, south, east = (float(value) for value in area)
    if not -90 <= south < north <= 90:
        raise ValueError("area latitude bounds must satisfy -90 <= south < north <= 90")
    if not -180 <= west <= 180 or not -180 <= east <= 180:
        raise ValueError("area longitude bounds must be within -180 to 180")
    return "/".join(_format_number(value) for value in (north, west, south, east))


@dataclass(frozen=True)
class TiggeRequest:
    """One explicit NCMRWF/TIGGE perturbed-forecast acquisition request."""

    initialization_date: Union[date, str]
    cycle_hour: int
    lead_hours: int
    variable: str
    members: Tuple[int, ...] = DEFAULT_SMOKE_MEMBERS
    area: Tuple[float, float, float, float] = DEFAULT_SMOKE_AREA
    output_path: Union[Path, str] = Path("data/raw/tigge")
    dataset: str = TIGGE_DATASET
    origin: str = NCMRWF_TIGGE_ORIGIN

    def __post_init__(self) -> None:
        parsed_date = _parse_request_date(self.initialization_date)
        if self.cycle_hour not in (0, 12):
            raise ValueError("cycle_hour must be 0 or 12 UTC")
        if not isinstance(self.lead_hours, int) or self.lead_hours < 0:
            raise ValueError("lead_hours must be a non-negative integer")
        if self.variable not in TIGGE_VARIABLE_PARAMETERS:
            raise ValueError(f"Unsupported TIGGE variable '{self.variable}'; supported: tp")
        format_members(self.members)
        format_area(self.area)
        object.__setattr__(self, "initialization_date", parsed_date)
        object.__setattr__(self, "output_path", Path(self.output_path))

    @classmethod
    def from_planned_case(
        cls,
        planned_case: Any,
        *,
        members: Tuple[int, ...] = DEFAULT_SMOKE_MEMBERS,
        area: Tuple[float, float, float, float] = DEFAULT_SMOKE_AREA,
        output_path: Union[Path, str] = Path("data/raw/tigge"),
    ) -> "TiggeRequest":
        """Create an acquisition request from an existing planner case.

        Only NCMRWF TP cases with an explicitly UTC forecast initialization are
        accepted. The planner's initialization and lead are copied exactly.
        """
        if planned_case.forecast_source != "NCMRWF":
            raise ValueError(
                "TIGGE acquisition accepts PlannedCase.forecast_source='NCMRWF' only"
            )
        initialization = planned_case.forecast_initialization_time
        if initialization.tzinfo is None or initialization.utcoffset().total_seconds() != 0:
            raise ValueError("PlannedCase forecast_initialization_time must be UTC-aware")
        return cls(
            initialization_date=initialization.date(),
            cycle_hour=initialization.hour,
            lead_hours=planned_case.forecast_lead_hours,
            variable=planned_case.forecast_variable,
            members=members,
            area=area,
            output_path=output_path,
        )

    @property
    def initialization_time(self) -> datetime:
        return datetime(self.initialization_date.year, self.initialization_date.month,
                        self.initialization_date.day, self.cycle_hour, tzinfo=timezone.utc)

    @property
    def output_file(self) -> Path:
        output = self.output_path
        if output.suffix:
            return output
        member_label = "-".join(f"{member:03d}" for member in self.members)
        area_label = "_".join(
            name + _format_number(value).replace("-", "m").replace(".", "p")
            for name, value in zip(("n", "w", "s", "e"), self.area)
        )
        return output / (
            f"tigge_{self.origin}_{self.variable}_{TIGGE_FORECAST_TYPE}_"
            f"{self.initialization_date:%Y%m%d}_{self.cycle_hour:02d}_"
            f"step{self.lead_hours:03d}_m{member_label}_{area_label}.grib"
        )

    def to_cds_request(self) -> Dict[str, str]:
        """Build the documented CDS API MARS-style request without I/O."""
        return {
            "class": TIGGE_CLASS, "date": self.initialization_date.isoformat(),
            "expver": "prod", "levtype": TIGGE_LEVEL_TYPE, "origin": self.origin,
            "param": TIGGE_VARIABLE_PARAMETERS[self.variable], "step": str(self.lead_hours),
            "time": f"{self.cycle_hour:02d}:00:00", "type": TIGGE_FORECAST_TYPE,
            "number": format_members(self.members), "area": format_area(self.area),
        }

    def to_provenance_request(self) -> Dict[str, Any]:
        return {
            "source": "NCMRWF/TIGGE", "centre_identifier": self.origin,
            "dataset": self.dataset, "initialization_time": self.initialization_time.isoformat(),
            "lead_hours": self.lead_hours, "requested_variable": self.variable,
            "requested_members": list(self.members), "area": list(self.area),
            "request_parameters": self.to_cds_request(), "output_path": str(self.output_file),
        }


@dataclass(frozen=True)
class TiggeAcquisitionResult:
    status: str
    request: TiggeRequest
    output_file: Path
    provenance_file: Path

    def to_dict(self) -> Dict[str, Any]:
        return {"status": self.status, "output_file": str(self.output_file),
                "provenance_file": str(self.provenance_file),
                "request": self.request.to_provenance_request()}


def provenance_path(output_file: Path) -> Path:
    return Path(f"{output_file}.request.json")


def _read_matching_provenance(request: TiggeRequest, sidecar: Path) -> bool:
    try:
        existing = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return existing.get("request") == request.to_provenance_request()


def _atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.partial")
    try:
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _make_client(credentials: TiggeCredentials) -> Any:
    try:
        import cdsapi
    except ImportError as exc:
        raise TiggeAcquisitionError(
            "The official 'cdsapi' client is required for retrieval."
        ) from exc
    return cdsapi.Client(url=credentials.url, key=credentials.key, quiet=True, progress=False)


def acquire_tigge_forecast(
    request: TiggeRequest,
    *,
    dry_run: bool = False,
    credentials: Optional[TiggeCredentials] = None,
    client_factory: Optional[Callable[[TiggeCredentials], Any]] = None,
) -> TiggeAcquisitionResult:
    """Retrieve an exact request; dry-runs use neither credentials nor network.

    Existing data are skipped only with a matching sidecar. An unproven output
    is never overwritten. Returned GRIB semantics remain untouched for ingestion.
    """
    output_file = request.output_file
    sidecar = provenance_path(output_file)
    if dry_run:
        return TiggeAcquisitionResult("DRY_RUN", request, output_file, sidecar)
    if output_file.exists():
        if _read_matching_provenance(request, sidecar):
            return TiggeAcquisitionResult("SKIPPED_EXISTING", request, output_file, sidecar)
        raise FileExistsError(
            f"Refusing to overwrite output without matching provenance: {output_file}"
        )
    resolved_credentials = credentials or TiggeCredentials.from_environment()
    output_file.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_file.with_name(f".{output_file.name}.{uuid4().hex}.partial")
    try:
        client = (client_factory or _make_client)(resolved_credentials)
        client.retrieve(request.dataset, request.to_cds_request(), str(temporary))
        if not temporary.is_file() or temporary.stat().st_size == 0:
            raise TiggeAcquisitionError("ECDS retrieval completed without a non-empty output file")
        os.replace(temporary, output_file)
        _atomic_write_json(sidecar, {
            "retrieval_timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "DOWNLOADED", "request": request.to_provenance_request(),
            "returned_members": None,
            "returned_metadata_status": "not_inspected; inspect returned GRIB metadata separately",
            "file_sha256": hashlib.sha256(output_file.read_bytes()).hexdigest(),
        })
    finally:
        if temporary.exists():
            temporary.unlink()
    return TiggeAcquisitionResult("DOWNLOADED", request, output_file, sidecar)


def _parse_members(value: str) -> Tuple[int, ...]:
    try:
        return tuple(int(member.strip()) for member in value.split(",") if member.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError("members must be comma-separated integers") from exc


def _parse_area(value: str) -> Tuple[float, float, float, float]:
    try:
        parsed = tuple(float(item.strip()) for item in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("area must be north,west,south,east") from exc
    if len(parsed) != 4:
        raise argparse.ArgumentTypeError("area must be north,west,south,east")
    return parsed


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Acquire an explicit NCMRWF/TIGGE forecast via ECDS")
    parser.add_argument("--date", required=True, help="Initialization date (YYYY-MM-DD)")
    parser.add_argument("--cycle", type=int, choices=(0, 12), default=0)
    parser.add_argument("--lead", type=int, default=24)
    parser.add_argument("--variable", default="tp")
    parser.add_argument("--members", type=_parse_members, default=DEFAULT_SMOKE_MEMBERS)
    parser.add_argument("--area", type=_parse_area, default=DEFAULT_SMOKE_AREA)
    parser.add_argument("--output", default="data/raw/tigge")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        request = TiggeRequest(
            args.date, args.cycle, args.lead, args.variable,
            args.members, args.area, args.output,
        )
        result = acquire_tigge_forecast(request, dry_run=args.dry_run)
    except (TiggeAcquisitionError, ValueError, TypeError, FileExistsError) as exc:
        parser.error(str(exc))
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
