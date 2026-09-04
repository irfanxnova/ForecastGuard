"""Historical case manifest — immutable, validated specification of forecast/observation pairs.

A CaseSpec describes one historical forecast case: which forecast file to read,
which observation to compare against, and the exact temporal alignment metadata.
A CaseManifest is a validated, duplicate-free collection of CaseSpecs.

SCIENTIFIC RULES ENFORCED
--------------------------
- observation_start and observation_end must be supplied explicitly.
  They must never be inferred from a filename or observation_date alone.
- observation_end must be strictly after observation_start.
- forecast_lead_hours must be non-negative.
- forecast_initialization_time must not be in the future relative to the
  observation window start (no future-information leakage via timestamp).
- Duplicate case_ids are rejected at manifest construction time.
- Serialization/deserialization is deterministic: same specs always produce
  the same JSON representation.

DESIGN
------
CaseSpec is a frozen dataclass — immutable after construction.
CaseManifest wraps an ordered tuple of validated CaseSpecs.
Validation is explicit and reports all errors, not just the first.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ManifestValidationError(Exception):
    """Raised when one or more CaseSpecs fail validation.

    The ``errors`` attribute lists (case_id, field, message) triples.
    """

    def __init__(self, errors: List[Tuple[str, str, str]]) -> None:
        self.errors = errors
        lines = [f"  [{cid}] {f}: {m}" for cid, f, m in errors]
        super().__init__("Manifest validation failed:\n" + "\n".join(lines))


class ManifestSerializationError(Exception):
    """Raised when manifest JSON cannot be parsed or is structurally invalid."""


# ---------------------------------------------------------------------------
# CaseSpec
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CaseSpec:
    """Immutable specification of one historical forecast case.

    All temporal fields must be timezone-aware UTC datetimes or None.
    Paths are stored as strings to allow JSON round-trips; callers may
    use ``Path(spec.forecast_path)`` when opening files.

    Fields
    ------
    case_id : str
        Unique identifier for this case.  Must be non-empty.

    forecast_path : str
        Path to the GRIB forecast file (relative or absolute).

    observation_path : str
        Path to the IMD daily observation file.

    observation_date : str
        Observation date as an ISO date string (YYYY-MM-DD).
        Used by ``read_imd_daily_file``; does not imply an accumulation window.

    observation_start : datetime
        Explicit start of the observation accumulation window (UTC).
        Must be timezone-aware.  Never inferred from observation_date.

    observation_end : datetime
        Explicit end of the observation accumulation window (UTC).
        Must be strictly after observation_start.

    forecast_initialization_time : datetime
        Datetime of forecast initialization (UTC, timezone-aware).

    forecast_lead_hours : int
        Forecast lead time in hours (>= 0).

    forecast_source : str
        Forecast model/source identifier (e.g. 'NCMRWF', 'TIGGE_ECMWF').

    forecast_variable : str
        Forecast variable short name (e.g. 'tp').

    region : Optional[str]
        Optional region identifier or description (e.g. 'India', 'Bay of Bengal').
        None if not applicable.

    notes : Optional[str]
        Optional free-text notes for auditability.
    """

    case_id: str
    forecast_path: str
    observation_path: str
    observation_date: str
    observation_start: datetime
    observation_end: datetime
    forecast_initialization_time: datetime
    forecast_lead_hours: int
    forecast_source: str
    forecast_variable: str
    region: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a JSON-compatible dictionary.

        Datetime fields are serialised as ISO 8601 strings with UTC offset.
        """
        return {
            "case_id": self.case_id,
            "forecast_path": self.forecast_path,
            "observation_path": self.observation_path,
            "observation_date": self.observation_date,
            "observation_start": self.observation_start.isoformat(),
            "observation_end": self.observation_end.isoformat(),
            "forecast_initialization_time": self.forecast_initialization_time.isoformat(),
            "forecast_lead_hours": self.forecast_lead_hours,
            "forecast_source": self.forecast_source,
            "forecast_variable": self.forecast_variable,
            "region": self.region,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CaseSpec":
        """Deserialise from a dictionary (e.g. from JSON).

        Raises
        ------
        ManifestSerializationError
            If required fields are missing or datetime strings are malformed.
        """
        required = [
            "case_id", "forecast_path", "observation_path", "observation_date",
            "observation_start", "observation_end",
            "forecast_initialization_time", "forecast_lead_hours",
            "forecast_source", "forecast_variable",
        ]
        missing = [f for f in required if f not in d or d[f] is None]
        if missing:
            cid = d.get("case_id", "<unknown>")
            raise ManifestSerializationError(
                f"CaseSpec '{cid}' is missing required fields: {missing}"
            )

        def _parse_dt(key: str, value: str) -> datetime:
            try:
                dt = datetime.fromisoformat(value)
                if dt.tzinfo is None:
                    raise ManifestSerializationError(
                        f"Field '{key}' has no timezone info: '{value}'. "
                        "All datetimes must be UTC-aware."
                    )
                return dt
            except ValueError as exc:
                raise ManifestSerializationError(
                    f"Field '{key}' is not a valid ISO datetime: '{value}'"
                ) from exc

        try:
            lead = int(d["forecast_lead_hours"])
        except (TypeError, ValueError) as exc:
            raise ManifestSerializationError(
                f"Field 'forecast_lead_hours' must be an integer: {d['forecast_lead_hours']!r}"
            ) from exc

        return cls(
            case_id=str(d["case_id"]),
            forecast_path=str(d["forecast_path"]),
            observation_path=str(d["observation_path"]),
            observation_date=str(d["observation_date"]),
            observation_start=_parse_dt("observation_start", d["observation_start"]),
            observation_end=_parse_dt("observation_end", d["observation_end"]),
            forecast_initialization_time=_parse_dt(
                "forecast_initialization_time", d["forecast_initialization_time"]
            ),
            forecast_lead_hours=lead,
            forecast_source=str(d["forecast_source"]),
            forecast_variable=str(d["forecast_variable"]),
            region=d.get("region"),
            notes=d.get("notes"),
        )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_spec(spec: CaseSpec) -> List[Tuple[str, str, str]]:
    """Return a list of (case_id, field, message) validation errors for one spec."""
    errors: List[Tuple[str, str, str]] = []
    cid = spec.case_id

    if not cid or not cid.strip():
        errors.append((cid, "case_id", "case_id must be a non-empty string"))

    if not spec.forecast_path or not spec.forecast_path.strip():
        errors.append((cid, "forecast_path", "forecast_path must not be empty"))

    if not spec.observation_path or not spec.observation_path.strip():
        errors.append((cid, "observation_path", "observation_path must not be empty"))

    if not spec.observation_date or not spec.observation_date.strip():
        errors.append((cid, "observation_date", "observation_date must not be empty"))
    else:
        # Validate date format YYYY-MM-DD
        try:
            datetime.strptime(spec.observation_date, "%Y-%m-%d")
        except ValueError:
            errors.append((
                cid, "observation_date",
                f"observation_date must be YYYY-MM-DD, got '{spec.observation_date}'"
            ))

    if spec.observation_start.tzinfo is None:
        errors.append((cid, "observation_start", "observation_start must be UTC-aware"))

    if spec.observation_end.tzinfo is None:
        errors.append((cid, "observation_end", "observation_end must be UTC-aware"))

    if spec.observation_end <= spec.observation_start:
        errors.append((
            cid, "observation_end",
            f"observation_end ({spec.observation_end.isoformat()}) must be strictly "
            f"after observation_start ({spec.observation_start.isoformat()})"
        ))

    if spec.forecast_initialization_time.tzinfo is None:
        errors.append((
            cid, "forecast_initialization_time",
            "forecast_initialization_time must be UTC-aware"
        ))

    if spec.forecast_lead_hours < 0:
        errors.append((
            cid, "forecast_lead_hours",
            f"forecast_lead_hours must be >= 0, got {spec.forecast_lead_hours}"
        ))

    if not spec.forecast_source or not spec.forecast_source.strip():
        errors.append((cid, "forecast_source", "forecast_source must not be empty"))

    if not spec.forecast_variable or not spec.forecast_variable.strip():
        errors.append((cid, "forecast_variable", "forecast_variable must not be empty"))

    return errors


# ---------------------------------------------------------------------------
# CaseManifest
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CaseManifest:
    """An immutable, validated collection of CaseSpecs.

    Constructed via ``CaseManifest.from_specs()`` or ``CaseManifest.from_json()``.
    Direct construction bypasses validation and is not recommended.

    Attributes
    ----------
    specs : Tuple[CaseSpec, ...]
        Ordered tuple of validated case specifications.
    manifest_id : str
        Optional identifier for this manifest (e.g. a hash or version string).
    description : str
        Optional human-readable description.
    created_at : Optional[datetime]
        UTC datetime when this manifest was created.
    """

    specs: Tuple[CaseSpec, ...]
    manifest_id: str = ""
    description: str = ""
    created_at: Optional[datetime] = None

    def __len__(self) -> int:
        return len(self.specs)

    def __iter__(self) -> Iterator[CaseSpec]:
        return iter(self.specs)

    def __getitem__(self, index: int) -> CaseSpec:
        return self.specs[index]

    def case_ids(self) -> List[str]:
        """Return ordered list of all case_ids in this manifest."""
        return [s.case_id for s in self.specs]

    @classmethod
    def from_specs(
        cls,
        specs: Sequence[CaseSpec],
        manifest_id: str = "",
        description: str = "",
        created_at: Optional[datetime] = None,
        validate: bool = True,
    ) -> "CaseManifest":
        """Construct a CaseManifest from a sequence of CaseSpecs.

        Parameters
        ----------
        specs : Sequence[CaseSpec]
            Case specifications to include.
        manifest_id : str
            Optional manifest identifier.
        description : str
            Optional description.
        created_at : Optional[datetime]
            UTC creation timestamp.  Defaults to utcnow() if not provided.
        validate : bool
            If True (default), validate all specs and raise ManifestValidationError
            if any fail.

        Raises
        ------
        ManifestValidationError
            If validate=True and any spec fails validation, or if duplicate
            case_ids are detected.
        """
        if created_at is None:
            created_at = datetime.now(timezone.utc)

        if validate:
            all_errors: List[Tuple[str, str, str]] = []

            # Check for duplicates first
            seen_ids: Dict[str, int] = {}
            for spec in specs:
                seen_ids[spec.case_id] = seen_ids.get(spec.case_id, 0) + 1
            for cid, count in seen_ids.items():
                if count > 1:
                    all_errors.append((
                        cid, "case_id",
                        f"Duplicate case_id '{cid}' appears {count} times"
                    ))

            # Per-spec validation
            for spec in specs:
                all_errors.extend(_validate_spec(spec))

            if all_errors:
                raise ManifestValidationError(all_errors)

        return cls(
            specs=tuple(specs),
            manifest_id=manifest_id,
            description=description,
            created_at=created_at,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialise manifest to a JSON-compatible dictionary.

        The output is deterministic: specs are ordered as supplied;
        datetime fields are ISO 8601 with UTC offset.
        """
        return {
            "manifest_id": self.manifest_id,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "case_count": len(self.specs),
            "specs": [s.to_dict() for s in self.specs],
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialise manifest to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent, sort_keys=False)

    @classmethod
    def from_dict(
        cls,
        d: Dict[str, Any],
        validate: bool = True,
    ) -> "CaseManifest":
        """Deserialise a CaseManifest from a dictionary.

        Raises
        ------
        ManifestSerializationError
            If the dictionary is structurally invalid.
        ManifestValidationError
            If validate=True and specs fail validation.
        """
        if "specs" not in d:
            raise ManifestSerializationError(
                "Manifest dict must contain a 'specs' key"
            )
        if not isinstance(d["specs"], list):
            raise ManifestSerializationError(
                "'specs' must be a list"
            )

        specs = []
        for i, raw in enumerate(d["specs"]):
            try:
                specs.append(CaseSpec.from_dict(raw))
            except ManifestSerializationError as exc:
                raise ManifestSerializationError(
                    f"Error parsing spec at index {i}: {exc}"
                ) from exc

        created_at = None
        if d.get("created_at"):
            try:
                created_at = datetime.fromisoformat(d["created_at"])
            except ValueError:
                pass  # non-fatal; leave as None

        return cls.from_specs(
            specs=specs,
            manifest_id=d.get("manifest_id", ""),
            description=d.get("description", ""),
            created_at=created_at,
            validate=validate,
        )

    @classmethod
    def from_json(
        cls,
        json_str: str,
        validate: bool = True,
    ) -> "CaseManifest":
        """Deserialise a CaseManifest from a JSON string.

        Raises
        ------
        ManifestSerializationError
            If the JSON is malformed or structurally invalid.
        ManifestValidationError
            If validate=True and specs fail validation.
        """
        try:
            d = json.loads(json_str)
        except json.JSONDecodeError as exc:
            raise ManifestSerializationError(
                f"Invalid JSON: {exc}"
            ) from exc
        return cls.from_dict(d, validate=validate)

    @classmethod
    def from_json_file(
        cls,
        path: Path,
        validate: bool = True,
    ) -> "CaseManifest":
        """Load a CaseManifest from a JSON file on disk.

        Raises
        ------
        ManifestSerializationError
            If the file cannot be read or is structurally invalid.
        ManifestValidationError
            If validate=True and specs fail validation.
        """
        try:
            text = Path(path).read_text(encoding="utf-8")
        except OSError as exc:
            raise ManifestSerializationError(
                f"Cannot read manifest file '{path}': {exc}"
            ) from exc
        return cls.from_json(text, validate=validate)

    def to_json_file(self, path: Path, indent: int = 2) -> None:
        """Write this manifest to a JSON file.

        Creates parent directories if needed.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(indent=indent), encoding="utf-8")
