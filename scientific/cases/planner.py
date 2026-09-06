"""Historical Experiment Planner.

Converts an explicit ExperimentConfig into an auditable ExperimentPlan —
a deterministic list of PlannedCase objects describing WHICH historical
forecast cases should be acquired.

SCIENTIFIC PURPOSE
------------------
Forecast-bust detection requires studying consecutive forecast cycles so we
can characterise:

  * forecast error vs lead time
  * ensemble spread vs actual error
  * run-to-run persistence and jumpiness
  * forecast trajectory evolution
  * early warning lead time
  * false-confidence events (low spread + high eventual error)
  * spatial concentration of failure
  * different rainfall regimes

The planner makes these relationships explicit in the output plan by:
  1. grouping cases into trajectory groups (one group per exact valid datetime)
  2. ordering cases within each group by initialization time (ascending)
  3. recording each case's sequence_index and predecessor_init_time

IMPORTANT CONSTRAINTS
---------------------
The planner generates REQUESTED cases, not confirmed-available cases.
It does NOT contact any external data source.
It does NOT guess file sizes or storage costs (unless bytes_per_case is
explicitly supplied by the caller).
It does NOT invent observation accumulation windows; if the caller does not
supply explicit window hours, observation_start and observation_end are left
None in every PlannedCase.

DETERMINISM
-----------
Same ExperimentConfig (excluding plan_created_at) → identical JSON output
every time.  Case IDs are derived from a deterministic hash of:
  <forecast_source>_<variable>_<init_time_iso>_<lead_hours>
using SHA-256 truncated to 12 hex chars.

PATH TEMPLATES
--------------
The planner supports optional caller-supplied path templates.  If provided,
forecast_path_template and observation_path_template are rendered for each
case using Python str.format_map with a well-documented key set.  If not
provided, forecast_path and observation_path are left None — the plan is
still usable before local storage conventions are known.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple

UTC = timezone.utc


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ExperimentConfigError(Exception):
    """Raised when an ExperimentConfig fails validation.

    The ``errors`` attribute lists (field, message) pairs for all failures.
    """

    def __init__(self, errors: List[Tuple[str, str]]) -> None:
        self.errors = errors
        lines = [f"  [{f}]: {m}" for f, m in errors]
        super().__init__("ExperimentConfig validation failed:\n" + "\n".join(lines))


class PlanSerializationError(Exception):
    """Raised when a plan cannot be serialised or deserialised."""


# ---------------------------------------------------------------------------
# ForecastCycle
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ForecastCycle:
    """One daily forecast issuance time (hour, minute).

    Parameters
    ----------
    hour : int
        UTC hour (0–23).
    minute : int
        UTC minute (0–59).  Default 0.
    """

    hour: int
    minute: int = 0

    def __post_init__(self) -> None:
        if not (0 <= self.hour <= 23):
            raise ValueError(f"ForecastCycle hour must be 0–23, got {self.hour}")
        if not (0 <= self.minute <= 59):
            raise ValueError(f"ForecastCycle minute must be 0–59, got {self.minute}")

    def label(self) -> str:
        """Return a compact label, e.g. '00Z', '12Z', '06Z30'."""
        if self.minute == 0:
            return f"{self.hour:02d}Z"
        return f"{self.hour:02d}Z{self.minute:02d}"

    def to_dict(self) -> Dict[str, int]:
        return {"hour": self.hour, "minute": self.minute}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ForecastCycle":
        return cls(hour=int(d["hour"]), minute=int(d.get("minute", 0)))

    @classmethod
    def from_label(cls, label: str) -> "ForecastCycle":
        """Parse a label such as '00Z', '12Z', '06Z30'."""
        label = label.strip().upper()
        if not label.endswith("Z") and "Z" not in label:
            raise ValueError(f"ForecastCycle label must contain 'Z': '{label}'")
        try:
            if label.endswith("Z"):
                return cls(hour=int(label[:-1]))
            # e.g. "06Z30"
            parts = label.split("Z")
            return cls(hour=int(parts[0]), minute=int(parts[1]))
        except (ValueError, IndexError) as exc:
            raise ValueError(f"Cannot parse ForecastCycle from '{label}'") from exc


# ---------------------------------------------------------------------------
# ExperimentConfig
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExperimentConfig:
    """Immutable configuration for a historical experiment.

    Parameters
    ----------
    experiment_id : str
        Unique identifier for this experiment.

    start_date : datetime
        First day to include (UTC, date-level; time component ignored).

    end_date : datetime
        Last day to include (inclusive, UTC; time component ignored).

    forecast_cycles : Tuple[ForecastCycle, ...]
        Daily issuance cycles to include (e.g. 00Z and 12Z).
        Must not be empty.  Duplicates are rejected.

    lead_hours : Tuple[int, ...]
        Forecast lead times in hours (each >= 0).  Must not be empty.

    forecast_source : str
        Forecast model/source identifier (e.g. 'NCMRWF', 'TIGGE_ECMWF').

    forecast_variable : str
        Forecast variable (e.g. 'tp').

    observation_source : str
        Observation dataset identifier (e.g. 'IMD_DAILY').

    region : str
        Region identifier or description.

    observation_window_hours : Optional[float]
        If supplied, observation accumulation window length in hours.
        The planner will derive observation_start and observation_end for each
        case as:
            observation_start = forecast_accumulation_end - observation_window_hours
            observation_end   = forecast_accumulation_end
        If None, observation windows are left unspecified in the plan.

    min_consecutive_cycles : int
        Minimum consecutive cycles required per trajectory group.
        Groups with fewer cycles than this are flagged
        (but still included — filtering is the caller's responsibility).
        Default 1 (no minimum enforced).

    forecast_path_template : Optional[str]
        Optional Python str.format_map template for forecast file paths.
        Available keys:
            {forecast_source}, {forecast_variable}, {init_date}, {init_time},
            {lead_hours}, {region}, {case_id}
        Example:
            "data/raw/{forecast_source}/{init_date}_{init_time}_{lead_hours}h.grib"
        If None, planned cases have forecast_path = None.

    observation_path_template : Optional[str]
        Optional Python str.format_map template for observation file paths.
        Available keys:
            {observation_source}, {observation_date}, {region}, {case_id}
        If None, planned cases have observation_path = None.

    description : str
        Optional human-readable description.

    notes : str
        Optional notes for the experiment record.
    """

    experiment_id: str
    start_date: datetime
    end_date: datetime
    forecast_cycles: Tuple[ForecastCycle, ...]
    lead_hours: Tuple[int, ...]
    forecast_source: str
    forecast_variable: str
    observation_source: str
    region: str
    observation_window_hours: Optional[float] = None
    min_consecutive_cycles: int = 1
    forecast_path_template: Optional[str] = None
    observation_path_template: Optional[str] = None
    description: str = ""
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "forecast_cycles": [c.to_dict() for c in self.forecast_cycles],
            "lead_hours": list(self.lead_hours),
            "forecast_source": self.forecast_source,
            "forecast_variable": self.forecast_variable,
            "observation_source": self.observation_source,
            "region": self.region,
            "observation_window_hours": self.observation_window_hours,
            "min_consecutive_cycles": self.min_consecutive_cycles,
            "forecast_path_template": self.forecast_path_template,
            "observation_path_template": self.observation_path_template,
            "description": self.description,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ExperimentConfig":
        """Deserialise from a dictionary.  Does not run validation."""
        cycles = tuple(ForecastCycle.from_dict(c) for c in d["forecast_cycles"])
        leads = tuple(int(x) for x in d["lead_hours"])
        return cls(
            experiment_id=str(d["experiment_id"]),
            start_date=datetime.fromisoformat(d["start_date"]),
            end_date=datetime.fromisoformat(d["end_date"]),
            forecast_cycles=cycles,
            lead_hours=leads,
            forecast_source=str(d["forecast_source"]),
            forecast_variable=str(d["forecast_variable"]),
            observation_source=str(d["observation_source"]),
            region=str(d["region"]),
            observation_window_hours=d.get("observation_window_hours"),
            min_consecutive_cycles=int(d.get("min_consecutive_cycles", 1)),
            forecast_path_template=d.get("forecast_path_template"),
            observation_path_template=d.get("observation_path_template"),
            description=str(d.get("description", "")),
            notes=str(d.get("notes", "")),
        )


# ---------------------------------------------------------------------------
# PlannedCase
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PlannedCase:
    """One planned forecast case within an experiment.

    Attributes
    ----------
    case_id : str
        Deterministic, unique identifier derived from forecast metadata.

    forecast_initialization_time : datetime
        Forecast initialization time (UTC, timezone-aware).

    forecast_lead_hours : int
        Forecast lead time in hours.

    forecast_source : str
        Forecast model/source identifier.

    forecast_variable : str
        Forecast variable short name.

    observation_source : str
        Observation dataset identifier.

    observation_date : str
        Date string (YYYY-MM-DD) for the observation lookup.
        Derived from forecast_accumulation_end.

    region : str
        Region identifier.

    observation_start : Optional[datetime]
        Observation accumulation window start (UTC).
        None if the caller did not supply observation_window_hours.

    observation_end : Optional[datetime]
        Observation accumulation window end (UTC).
        None if the caller did not supply observation_window_hours.

    observation_window_specified : bool
        True if observation_start/observation_end are set.
        False means the window is unspecified — caller must supply it before
        creating a CaseSpec/CaseManifest.

    forecast_path : Optional[str]
        Rendered path from forecast_path_template, or None.

    observation_path : Optional[str]
        Rendered path from observation_path_template, or None.

    trajectory_group_id : str
        Identifier of the trajectory group this case belongs to.
        All cases sharing the EXACT same forecast_accumulation_end datetime
        belong to the same group.

    sequence_index : int
        Zero-based index of this case within its trajectory group,
        ordered by forecast_initialization_time ascending.

    predecessor_init_time : Optional[datetime]
        Initialization time of the immediately preceding case in the same
        trajectory group.  None for the first case in each group.

    cycle_label : str
        Human-readable cycle label (e.g. '00Z', '12Z').

    forecast_accumulation_end : datetime
        End of the forecast accumulation window.
        = forecast_initialization_time + timedelta(hours=forecast_lead_hours)
    """

    case_id: str
    forecast_initialization_time: datetime
    forecast_lead_hours: int
    forecast_source: str
    forecast_variable: str
    observation_source: str
    observation_date: str
    region: str

    observation_start: Optional[datetime]
    observation_end: Optional[datetime]
    observation_window_specified: bool

    forecast_path: Optional[str]
    observation_path: Optional[str]

    trajectory_group_id: str
    sequence_index: int
    predecessor_init_time: Optional[datetime]
    cycle_label: str
    forecast_accumulation_end: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "forecast_initialization_time": self.forecast_initialization_time.isoformat(),
            "forecast_lead_hours": self.forecast_lead_hours,
            "forecast_source": self.forecast_source,
            "forecast_variable": self.forecast_variable,
            "observation_source": self.observation_source,
            "observation_date": self.observation_date,
            "region": self.region,
            "observation_start": (
                self.observation_start.isoformat() if self.observation_start else None
            ),
            "observation_end": (
                self.observation_end.isoformat() if self.observation_end else None
            ),
            "observation_window_specified": self.observation_window_specified,
            "forecast_path": self.forecast_path,
            "observation_path": self.observation_path,
            "trajectory_group_id": self.trajectory_group_id,
            "sequence_index": self.sequence_index,
            "predecessor_init_time": (
                self.predecessor_init_time.isoformat()
                if self.predecessor_init_time else None
            ),
            "cycle_label": self.cycle_label,
            "forecast_accumulation_end": self.forecast_accumulation_end.isoformat(),
        }


# ---------------------------------------------------------------------------
# TrajectoryGroup
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TrajectoryGroup:
    """A group of PlannedCases sharing the EXACT same forecast_accumulation_end.

    Scientific intent:
    A trajectory represents successive forecast initialization cycles all
    predicting the SAME exact valid datetime.  For example:

        2025-09-01 00Z + 48h → 2025-09-03 00:00 UTC
        2025-09-01 12Z + 36h → 2025-09-03 00:00 UTC
        2025-09-02 00Z + 24h → 2025-09-03 00:00 UTC
        2025-09-02 12Z + 12h → 2025-09-03 00:00 UTC

    These four cases belong to one trajectory group because they all verify
    at exactly 2025-09-03 00:00 UTC.

    A case verifying at 2025-09-03 12:00 UTC belongs to a DIFFERENT group,
    even though it falls on the same calendar day.

    NOTE: Sharing a valid datetime does NOT imply these cases describe the
    same meteorological event.  The linkage is purely temporal.

    Attributes
    ----------
    group_id : str
        Unique identifier for this group.

    valid_datetime : str
        The shared exact forecast accumulation end datetime (ISO 8601, UTC).

    cases : Tuple[PlannedCase, ...]
        All planned cases in this group, ordered by forecast_initialization_time.

    is_complete : bool
        True if the group has >= min_consecutive_cycles cases.
        False means the group has fewer cycles than the minimum requested.
    """

    group_id: str
    valid_datetime: str
    cases: Tuple[PlannedCase, ...]
    is_complete: bool

    def __len__(self) -> int:
        return len(self.cases)

    def __iter__(self) -> Iterator[PlannedCase]:
        return iter(self.cases)


# ---------------------------------------------------------------------------
# ResourceSummary
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResourceSummary:
    """Summary of the planned resource requirements.

    Attributes
    ----------
    total_cases : int
        Total number of planned cases.

    total_initialization_cycles : int
        Number of distinct forecast initialization datetimes.

    total_trajectory_groups : int
        Number of distinct trajectory groups (one per exact valid datetime).

    cases_per_cycle : int
        Number of lead-hour cases per initialization cycle.

    complete_trajectory_groups : int
        Number of groups with >= min_consecutive_cycles.

    incomplete_trajectory_groups : int
        Number of groups with fewer than min_consecutive_cycles.

    bytes_per_case : Optional[float]
        Caller-supplied estimate; None if not provided.

    estimated_total_bytes : Optional[float]
        total_cases * bytes_per_case if bytes_per_case was supplied.
        None otherwise.  The planner NEVER invents a bytes estimate.
    """

    total_cases: int
    total_initialization_cycles: int
    total_trajectory_groups: int
    cases_per_cycle: int
    complete_trajectory_groups: int
    incomplete_trajectory_groups: int
    bytes_per_case: Optional[float] = None
    estimated_total_bytes: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_cases": self.total_cases,
            "total_initialization_cycles": self.total_initialization_cycles,
            "total_trajectory_groups": self.total_trajectory_groups,
            "cases_per_cycle": self.cases_per_cycle,
            "complete_trajectory_groups": self.complete_trajectory_groups,
            "incomplete_trajectory_groups": self.incomplete_trajectory_groups,
            "bytes_per_case": self.bytes_per_case,
            "estimated_total_bytes": self.estimated_total_bytes,
        }


# ---------------------------------------------------------------------------
# ExperimentPlan
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExperimentPlan:
    """Deterministic output of the experiment planner.

    Attributes
    ----------
    experiment_id : str
        Experiment identifier from the config.

    config : ExperimentConfig
        The configuration that produced this plan.

    cases : Tuple[PlannedCase, ...]
        All planned cases, ordered by:
          1. forecast_initialization_time ascending
          2. forecast_lead_hours ascending

    trajectory_groups : Tuple[TrajectoryGroup, ...]
        All trajectory groups, ordered by valid_datetime ascending.

    resource_summary : ResourceSummary
        High-level resource summary.

    observation_windows_specified : bool
        True if every case has its observation window specified.
        False if any case has observation_window_specified = False.

    plan_created_at : Optional[datetime]
        UTC timestamp of plan creation.  Excluded from deterministic
        serialisation comparisons.
    """

    experiment_id: str
    config: ExperimentConfig
    cases: Tuple[PlannedCase, ...]
    trajectory_groups: Tuple[TrajectoryGroup, ...]
    resource_summary: ResourceSummary
    observation_windows_specified: bool
    plan_created_at: Optional[datetime] = None

    def __len__(self) -> int:
        return len(self.cases)

    def __iter__(self) -> Iterator[PlannedCase]:
        return iter(self.cases)

    def to_dict(self, include_created_at: bool = False) -> Dict[str, Any]:
        """Serialise to a JSON-compatible dictionary.

        Parameters
        ----------
        include_created_at : bool
            If True, include plan_created_at.  Default False so that
            two plans from the same config produce identical dicts.
        """
        d: Dict[str, Any] = {
            "experiment_id": self.experiment_id,
            "config": self.config.to_dict(),
            "total_cases": len(self.cases),
            "observation_windows_specified": self.observation_windows_specified,
            "resource_summary": self.resource_summary.to_dict(),
            "trajectory_groups": [
                {
                    "group_id": g.group_id,
                    "valid_datetime": g.valid_datetime,
                    "case_count": len(g),
                    "is_complete": g.is_complete,
                    "case_ids": [c.case_id for c in g.cases],
                }
                for g in self.trajectory_groups
            ],
            "cases": [c.to_dict() for c in self.cases],
        }
        if include_created_at and self.plan_created_at is not None:
            d["plan_created_at"] = self.plan_created_at.isoformat()
        return d

    def to_json(self, indent: int = 2, include_created_at: bool = False) -> str:
        return json.dumps(
            self.to_dict(include_created_at=include_created_at),
            indent=indent,
            sort_keys=False,
        )

    def to_case_manifest(self):
        """Convert all fully-specified cases to a CaseManifest.

        Only cases with observation_window_specified=True are included.
        Cases without observation windows cannot be converted to CaseSpecs.

        Returns
        -------
        CaseManifest
            A manifest containing only the fully-specified cases.

        Raises
        ------
        ValueError
            If no cases have observation windows specified.
        """
        from scientific.cases.manifest import CaseManifest, CaseSpec

        specifiable = [c for c in self.cases if c.observation_window_specified]
        if not specifiable:
            raise ValueError(
                "No cases in this plan have observation windows specified. "
                "Supply observation_window_hours in ExperimentConfig before "
                "converting to a CaseManifest."
            )

        specs = [
            CaseSpec(
                case_id=c.case_id,
                forecast_path=c.forecast_path or f"UNRESOLVED:{c.case_id}",
                observation_path=c.observation_path or f"UNRESOLVED:{c.case_id}",
                observation_date=c.observation_date,
                observation_start=c.observation_start,
                observation_end=c.observation_end,
                forecast_initialization_time=c.forecast_initialization_time,
                forecast_lead_hours=c.forecast_lead_hours,
                forecast_source=c.forecast_source,
                forecast_variable=c.forecast_variable,
                region=c.region,
                notes=f"trajectory_group={c.trajectory_group_id} seq={c.sequence_index}",
            )
            for c in specifiable
        ]

        return CaseManifest.from_specs(
            specs,
            manifest_id=self.experiment_id,
            description=self.config.description,
        )


# ---------------------------------------------------------------------------
# ID generation
# ---------------------------------------------------------------------------


def _make_case_id(
    forecast_source: str,
    forecast_variable: str,
    init_time: datetime,
    lead_hours: int,
) -> str:
    """Generate a deterministic, stable case ID.

    Uses SHA-256 of the canonical string:
        ``{source}|{variable}|{init_iso}|{lead_hours}``
    truncated to 16 hex characters.

    Two identical inputs always produce the same ID.
    """
    raw = f"{forecast_source}|{forecast_variable}|{init_time.isoformat()}|{lead_hours}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return digest[:16]


def _make_group_id(valid_datetime: str, forecast_source: str, forecast_variable: str) -> str:
    """Generate a deterministic trajectory group ID."""
    raw = f"{forecast_source}|{forecast_variable}|{valid_datetime}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"tg_{digest[:12]}"


# ---------------------------------------------------------------------------
# Path rendering
# ---------------------------------------------------------------------------


def _render_forecast_path(
    template: str,
    case: PlannedCase,
) -> Optional[str]:
    """Render a forecast path from a template and case metadata."""
    init_date = case.forecast_initialization_time.strftime("%Y%m%d")
    init_time = case.forecast_initialization_time.strftime("%H%M")
    try:
        return template.format_map({
            "forecast_source": case.forecast_source,
            "forecast_variable": case.forecast_variable,
            "init_date": init_date,
            "init_time": init_time,
            "lead_hours": case.forecast_lead_hours,
            "region": case.region,
            "case_id": case.case_id,
        })
    except KeyError:
        return None


def _render_observation_path(
    template: str,
    case: PlannedCase,
) -> Optional[str]:
    """Render an observation path from a template and case metadata."""
    try:
        return template.format_map({
            "observation_source": case.observation_source,
            "observation_date": case.observation_date,
            "region": case.region,
            "case_id": case.case_id,
        })
    except KeyError:
        return None


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_config(config: ExperimentConfig) -> List[Tuple[str, str]]:
    """Return (field, message) pairs for all validation failures."""
    errors: List[Tuple[str, str]] = []

    if not config.experiment_id or not config.experiment_id.strip():
        errors.append(("experiment_id", "experiment_id must not be empty"))

    # Dates
    start = config.start_date.replace(tzinfo=UTC) if config.start_date.tzinfo is None \
        else config.start_date
    end = config.end_date.replace(tzinfo=UTC) if config.end_date.tzinfo is None \
        else config.end_date

    if end < start:
        errors.append((
            "end_date",
            f"end_date ({end.date()}) must be >= start_date ({start.date()})"
        ))

    # Cycles
    if not config.forecast_cycles:
        errors.append(("forecast_cycles", "forecast_cycles must not be empty"))
    else:
        seen_cycles: set = set()
        for c in config.forecast_cycles:
            key = (c.hour, c.minute)
            if key in seen_cycles:
                errors.append((
                    "forecast_cycles",
                    f"Duplicate cycle {c.label()} in forecast_cycles"
                ))
            seen_cycles.add(key)

    # Lead hours
    if not config.lead_hours:
        errors.append(("lead_hours", "lead_hours must not be empty"))
    else:
        for lh in config.lead_hours:
            if lh < 0:
                errors.append((
                    "lead_hours",
                    f"All lead_hours must be >= 0; got {lh}"
                ))

    # Source / variable / region
    if not config.forecast_source or not config.forecast_source.strip():
        errors.append(("forecast_source", "forecast_source must not be empty"))

    if not config.forecast_variable or not config.forecast_variable.strip():
        errors.append(("forecast_variable", "forecast_variable must not be empty"))

    if not config.observation_source or not config.observation_source.strip():
        errors.append(("observation_source", "observation_source must not be empty"))

    if not config.region or not config.region.strip():
        errors.append(("region", "region must not be empty"))

    # Observation window
    if config.observation_window_hours is not None:
        if config.observation_window_hours <= 0:
            errors.append((
                "observation_window_hours",
                f"observation_window_hours must be > 0 if supplied; "
                f"got {config.observation_window_hours}"
            ))

    # Min consecutive cycles
    if config.min_consecutive_cycles < 1:
        errors.append((
            "min_consecutive_cycles",
            f"min_consecutive_cycles must be >= 1; got {config.min_consecutive_cycles}"
        ))

    return errors


# ---------------------------------------------------------------------------
# Core planning function
# ---------------------------------------------------------------------------


def plan_experiment(
    config: ExperimentConfig,
    bytes_per_case: Optional[float] = None,
    created_at: Optional[datetime] = None,
) -> ExperimentPlan:
    """Generate a deterministic ExperimentPlan from an ExperimentConfig.

    Parameters
    ----------
    config : ExperimentConfig
        Validated experiment configuration.
    bytes_per_case : Optional[float]
        Caller-supplied estimate of bytes per GRIB case.
        If provided, estimated_total_bytes = total_cases * bytes_per_case.
        The planner NEVER invents a bytes estimate.
    created_at : Optional[datetime]
        UTC timestamp to embed in the plan.  If None, uses utcnow().
        Does not affect determinism of case IDs or ordering.

    Returns
    -------
    ExperimentPlan
        Immutable, deterministic plan.

    Raises
    ------
    ExperimentConfigError
        If the configuration fails validation.
    """
    errors = _validate_config(config)
    if errors:
        raise ExperimentConfigError(errors)

    if created_at is None:
        created_at = datetime.now(UTC)

    # Normalise dates to UTC midnight
    start = config.start_date.replace(
        hour=0, minute=0, second=0, microsecond=0,
        tzinfo=UTC if config.start_date.tzinfo is None else config.start_date.tzinfo,
    )
    end = config.end_date.replace(
        hour=0, minute=0, second=0, microsecond=0,
        tzinfo=UTC if config.end_date.tzinfo is None else config.end_date.tzinfo,
    )

    # Sort cycles and lead hours for determinism
    sorted_cycles = sorted(config.forecast_cycles, key=lambda c: (c.hour, c.minute))
    sorted_leads = sorted(config.lead_hours)

    # Build all (init_time, lead_hours) pairs grouped by exact valid datetime.
    # valid_datetime = ISO representation of forecast_accumulation_end.
    # trajectory_group_id = sha256(source|variable|valid_datetime)[:12]

    # Dict: valid_datetime_str -> list of (init_time, lead_hours) in init_time order
    groups_map: Dict[str, List[Tuple[datetime, int]]] = {}

    current = start
    while current <= end:
        for cycle in sorted_cycles:
            init_time = current.replace(
                hour=cycle.hour, minute=cycle.minute,
                second=0, microsecond=0,
            )
            for lead in sorted_leads:
                accum_end = init_time + timedelta(hours=lead)
                valid_datetime_str = accum_end.isoformat()
                if valid_datetime_str not in groups_map:
                    groups_map[valid_datetime_str] = []
                groups_map[valid_datetime_str].append((init_time, lead))
        current += timedelta(days=1)

    # Build PlannedCase objects
    # For each valid_datetime group, sort by (init_time, lead_hours), assign indices
    all_cases: List[PlannedCase] = []
    trajectory_groups: List[TrajectoryGroup] = []

    for valid_datetime_str in sorted(groups_map.keys()):
        group_entries = sorted(groups_map[valid_datetime_str], key=lambda x: (x[0], x[1]))
        group_id = _make_group_id(
            valid_datetime_str, config.forecast_source, config.forecast_variable
        )

        group_cases: List[PlannedCase] = []
        prev_init: Optional[datetime] = None

        for seq_idx, (init_time, lead) in enumerate(group_entries):
            case_id = _make_case_id(
                config.forecast_source,
                config.forecast_variable,
                init_time,
                lead,
            )

            accum_end = init_time + timedelta(hours=lead)
            obs_date_str = accum_end.strftime("%Y-%m-%d")

            # Observation window
            obs_start: Optional[datetime] = None
            obs_end: Optional[datetime] = None
            obs_specified = False
            if config.observation_window_hours is not None:
                obs_end = accum_end
                obs_start = accum_end - timedelta(hours=config.observation_window_hours)
                obs_specified = True

            # Build a temporary case (without paths) to render templates
            temp_case = PlannedCase(
                case_id=case_id,
                forecast_initialization_time=init_time,
                forecast_lead_hours=lead,
                forecast_source=config.forecast_source,
                forecast_variable=config.forecast_variable,
                observation_source=config.observation_source,
                observation_date=obs_date_str,
                region=config.region,
                observation_start=obs_start,
                observation_end=obs_end,
                observation_window_specified=obs_specified,
                forecast_path=None,
                observation_path=None,
                trajectory_group_id=group_id,
                sequence_index=seq_idx,
                predecessor_init_time=prev_init,
                cycle_label=ForecastCycle(
                    hour=init_time.hour, minute=init_time.minute
                ).label(),
                forecast_accumulation_end=accum_end,
            )

            # Render paths if templates provided
            fcst_path: Optional[str] = None
            obs_path: Optional[str] = None
            if config.forecast_path_template:
                fcst_path = _render_forecast_path(config.forecast_path_template, temp_case)
            if config.observation_path_template:
                obs_path = _render_observation_path(config.observation_path_template, temp_case)

            case = PlannedCase(
                case_id=case_id,
                forecast_initialization_time=init_time,
                forecast_lead_hours=lead,
                forecast_source=config.forecast_source,
                forecast_variable=config.forecast_variable,
                observation_source=config.observation_source,
                observation_date=obs_date_str,
                region=config.region,
                observation_start=obs_start,
                observation_end=obs_end,
                observation_window_specified=obs_specified,
                forecast_path=fcst_path,
                observation_path=obs_path,
                trajectory_group_id=group_id,
                sequence_index=seq_idx,
                predecessor_init_time=prev_init,
                cycle_label=ForecastCycle(
                    hour=init_time.hour, minute=init_time.minute
                ).label(),
                forecast_accumulation_end=accum_end,
            )

            group_cases.append(case)
            prev_init = init_time

        is_complete = len(group_cases) >= config.min_consecutive_cycles
        tg = TrajectoryGroup(
            group_id=group_id,
            valid_datetime=valid_datetime_str,
            cases=tuple(group_cases),
            is_complete=is_complete,
        )
        trajectory_groups.append(tg)
        all_cases.extend(group_cases)

    # Sort all_cases: primary by init_time, secondary by lead_hours
    all_cases_sorted = sorted(
        all_cases,
        key=lambda c: (c.forecast_initialization_time, c.forecast_lead_hours),
    )

    # Verify uniqueness
    seen_ids: set = set()
    for c in all_cases_sorted:
        if c.case_id in seen_ids:
            raise RuntimeError(
                f"BUG: Duplicate case_id generated: {c.case_id}. "
                "This should never happen — please file a bug report."
            )
        seen_ids.add(c.case_id)

    # Observation window flag
    obs_fully_specified = all(c.observation_window_specified for c in all_cases_sorted)

    # Resource summary
    n_init_cycles = len({c.forecast_initialization_time for c in all_cases_sorted})
    n_leads = len(sorted_leads)
    total = len(all_cases_sorted)
    n_groups = len(trajectory_groups)
    n_complete = sum(1 for g in trajectory_groups if g.is_complete)
    estimated_bytes: Optional[float] = None
    if bytes_per_case is not None:
        estimated_bytes = float(total) * bytes_per_case

    resource_summary = ResourceSummary(
        total_cases=total,
        total_initialization_cycles=n_init_cycles,
        total_trajectory_groups=n_groups,
        cases_per_cycle=n_leads,
        complete_trajectory_groups=n_complete,
        incomplete_trajectory_groups=n_groups - n_complete,
        bytes_per_case=bytes_per_case,
        estimated_total_bytes=estimated_bytes,
    )

    return ExperimentPlan(
        experiment_id=config.experiment_id,
        config=config,
        cases=tuple(all_cases_sorted),
        trajectory_groups=tuple(
            sorted(trajectory_groups, key=lambda g: g.valid_datetime)
        ),
        resource_summary=resource_summary,
        observation_windows_specified=obs_fully_specified,
        plan_created_at=created_at,
    )
