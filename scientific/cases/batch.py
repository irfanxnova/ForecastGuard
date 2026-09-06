"""Deterministic batch processor for historical forecast cases.

Converts a CaseManifest into a collection of BatchCaseResult objects by
running each case through the existing ForecastGuard pipeline:

    CaseSpec
      → RainfallCase
      → run_rainfall_case()        (verification)
      → build_dataset_record()     (ML features)
      → build_rainfall_target()    (leakage-safe targets)
      → assemble_sample()          (tabular row)
      → BatchCaseResult

SCIENTIFIC GUARANTEES
---------------------
1.  Processing is case-by-case.  Each GRIB file is read, processed, and
    released before the next case starts.  No large arrays are held in
    memory across cases.

2.  A single case failure (read error, unexpected exception) does not
    prevent subsequent cases from being processed.

3.  Every case ends in an explicit BatchCaseStatus.  Nothing is silently
    skipped.

4.  Predictor features never contain observation-derived metrics.
    This is enforced by the existing leakage guard in assemble_sample().

5.  No raw-data files are modified.

6.  No model fitting is performed.

7.  Processing order is deterministic: cases are processed in the order
    they appear in the manifest.

BATCH CASE STATUSES
-------------------
VALID           Verification succeeded, features extracted, target valid,
                sample assembled and trainable.

BLOCKED         Verification was blocked by alignment/window rules.
                No target or features.  Provenance preserved.

INVALID         Verification metadata incomplete/inconsistent.
                No target or features.  Provenance preserved.

MISSING_INPUT   A required input file does not exist at processing time.
                No attempt to run the pipeline.

PROCESSING_ERROR
                An unexpected exception occurred.  Failure is captured
                with full traceback text.  Other cases continue.
"""

from __future__ import annotations

import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Iterator, List, Optional, Sequence

from pathlib import Path

from scientific.cases.manifest import CaseManifest, CaseSpec
from scientific.cases.rainfall_case import (
    RainfallCase,
    RainfallCaseResult,
    RainfallCaseStatus,
    run_rainfall_case,
)
from scientific.dataset.assembly import AssembledSample, assemble_sample
from scientific.dataset.builder import DatasetRecord, build_dataset_record
from scientific.targets.rainfall import (
    RainfallTarget,
    RainfallTargetStatus,
    SeverityThresholds,
    build_rainfall_target,
)


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class BatchCaseStatus(str, Enum):
    """Explicit outcome of processing one case in a batch.

    VALID
        Full pipeline succeeded.  sample is trainable.

    BLOCKED
        Verification was blocked by a known operational condition
        (temporal mismatch, unspecified window, read error, empty grid).
        sample has no predictors or target.

    INVALID
        Verification metadata was structurally invalid.
        sample has no predictors or target.

    MISSING_INPUT
        A required file (forecast or observation) did not exist at
        processing time.  The pipeline was not run.

    PROCESSING_ERROR
        An unexpected exception occurred during processing.
        error_traceback contains the full traceback.
    """

    VALID = "VALID"
    BLOCKED = "BLOCKED"
    INVALID = "INVALID"
    MISSING_INPUT = "MISSING_INPUT"
    PROCESSING_ERROR = "PROCESSING_ERROR"


# ---------------------------------------------------------------------------
# BatchCaseResult
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BatchCaseResult:
    """Result of processing one CaseSpec through the full ForecastGuard pipeline.

    Attributes
    ----------
    case_id : str
        Case identifier from the manifest.

    batch_status : BatchCaseStatus
        Explicit outcome.

    spec : CaseSpec
        Original case specification for auditability.

    case_result : Optional[RainfallCaseResult]
        Result from run_rainfall_case().  None if the pipeline was not run
        (MISSING_INPUT or PROCESSING_ERROR before case runner).

    dataset_record : Optional[DatasetRecord]
        Result from build_dataset_record().  None unless pipeline reached
        this stage.

    target : Optional[RainfallTarget]
        Result from build_rainfall_target().  None unless pipeline reached
        this stage.

    sample : Optional[AssembledSample]
        Final tabular row.  None unless pipeline reached assembly stage.

    reason : str
        Human-readable reason for non-VALID outcomes.

    error_traceback : str
        Full exception traceback for PROCESSING_ERROR cases.  Empty otherwise.

    processing_timestamp : datetime
        UTC timestamp of when this case was processed.

    provenance : Dict[str, Any]
        Audit trail: forecast_path, observation_path, init_time, lead_hours,
        source, variable, pipeline stages completed.
    """

    case_id: str
    batch_status: BatchCaseStatus
    spec: CaseSpec

    case_result: Optional[RainfallCaseResult] = None
    dataset_record: Optional[DatasetRecord] = None
    target: Optional[RainfallTarget] = None
    sample: Optional[AssembledSample] = None

    reason: str = ""
    error_traceback: str = ""

    processing_timestamp: datetime = field(
        default_factory=lambda: datetime.utcnow()
    )
    provenance: Dict[str, Any] = field(default_factory=dict)

    def is_trainable(self) -> bool:
        """Return True if this case produced a trainable sample."""
        return (
            self.batch_status == BatchCaseStatus.VALID
            and self.sample is not None
            and self.sample.is_trainable()
        )

    def to_summary_dict(self) -> Dict[str, Any]:
        """Return a compact audit-trail dictionary (no large arrays)."""
        return {
            "case_id": self.case_id,
            "batch_status": self.batch_status.value,
            "reason": self.reason,
            "processing_timestamp": self.processing_timestamp.isoformat(),
            "forecast_path": self.spec.forecast_path,
            "observation_path": self.spec.observation_path,
            "forecast_initialization_time": (
                self.spec.forecast_initialization_time.isoformat()
            ),
            "forecast_lead_hours": self.spec.forecast_lead_hours,
            "forecast_source": self.spec.forecast_source,
            "forecast_variable": self.spec.forecast_variable,
            "case_status": (
                self.case_result.status.value if self.case_result else None
            ),
            "target_status": (
                self.target.target_status.value if self.target else None
            ),
            "is_trainable": self.is_trainable(),
            "has_error_traceback": bool(self.error_traceback),
        }


# ---------------------------------------------------------------------------
# BatchResult
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BatchResult:
    """Immutable result of a complete batch processing run.

    Attributes
    ----------
    results : Tuple[BatchCaseResult, ...]
        One result per case in the manifest, in manifest order.
    manifest_id : str
        Identifier of the manifest that was processed.
    processing_start : datetime
        UTC timestamp when batch processing started.
    processing_end : datetime
        UTC timestamp when batch processing finished.
    total_cases : int
        Total number of cases in the manifest.
    valid_count : int
        Number of VALID (trainable) cases.
    blocked_count : int
        Number of BLOCKED cases.
    invalid_count : int
        Number of INVALID cases.
    missing_input_count : int
        Number of MISSING_INPUT cases.
    error_count : int
        Number of PROCESSING_ERROR cases.
    """

    results: tuple
    manifest_id: str = ""
    processing_start: datetime = field(default_factory=lambda: datetime.utcnow())
    processing_end: datetime = field(default_factory=lambda: datetime.utcnow())
    total_cases: int = 0
    valid_count: int = 0
    blocked_count: int = 0
    invalid_count: int = 0
    missing_input_count: int = 0
    error_count: int = 0

    def __iter__(self) -> Iterator[BatchCaseResult]:
        return iter(self.results)

    def __len__(self) -> int:
        return len(self.results)

    def trainable_samples(self) -> List[AssembledSample]:
        """Return assembled samples for all VALID trainable cases."""
        return [
            r.sample
            for r in self.results
            if r.is_trainable() and r.sample is not None
        ]

    def summary(self) -> Dict[str, Any]:
        """Return a compact processing summary."""
        duration = (self.processing_end - self.processing_start).total_seconds()
        return {
            "manifest_id": self.manifest_id,
            "total_cases": self.total_cases,
            "valid": self.valid_count,
            "blocked": self.blocked_count,
            "invalid": self.invalid_count,
            "missing_input": self.missing_input_count,
            "processing_errors": self.error_count,
            "processing_duration_seconds": duration,
            "processing_start": self.processing_start.isoformat(),
            "processing_end": self.processing_end.isoformat(),
        }


# ---------------------------------------------------------------------------
# Internal pipeline helpers
# ---------------------------------------------------------------------------


def _check_inputs_exist(spec: CaseSpec) -> Optional[str]:
    """Return a reason string if any required file is missing, else None."""
    missing = []
    if not Path(spec.forecast_path).exists():
        missing.append(f"forecast_path='{spec.forecast_path}'")
    if not Path(spec.observation_path).exists():
        missing.append(f"observation_path='{spec.observation_path}'")
    return f"Missing input files: {', '.join(missing)}" if missing else None


def _spec_to_rainfall_case(spec: CaseSpec) -> RainfallCase:
    """Convert a CaseSpec to a RainfallCase for the existing case runner."""
    return RainfallCase(
        case_id=spec.case_id,
        forecast_path=Path(spec.forecast_path),
        observation_path=Path(spec.observation_path),
        observation_date=spec.observation_date,
        observation_start=spec.observation_start,
        observation_end=spec.observation_end,
        observation_window_metadata=spec.observation_window_metadata,
    )


def _case_status_to_batch_status(
    case_status: RainfallCaseStatus,
    target_status: RainfallTargetStatus,
) -> BatchCaseStatus:
    """Map combined case + target status to a BatchCaseStatus."""
    if case_status == RainfallCaseStatus.ALIGNED and target_status == RainfallTargetStatus.VALID:
        return BatchCaseStatus.VALID
    if target_status == RainfallTargetStatus.INVALID:
        return BatchCaseStatus.INVALID
    _invalid_case_statuses = {
        RainfallCaseStatus.INVALID_METADATA,
        RainfallCaseStatus.NO_TP_MESSAGE,
    }
    if case_status in _invalid_case_statuses:
        return BatchCaseStatus.INVALID
    return BatchCaseStatus.BLOCKED


def _build_provenance(
    spec: CaseSpec,
    stages_completed: List[str],
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a provenance dict for a BatchCaseResult."""
    prov: Dict[str, Any] = {
        "case_id": spec.case_id,
        "forecast_path": spec.forecast_path,
        "observation_path": spec.observation_path,
        "forecast_initialization_time": spec.forecast_initialization_time.isoformat(),
        "forecast_lead_hours": spec.forecast_lead_hours,
        "forecast_source": spec.forecast_source,
        "forecast_variable": spec.forecast_variable,
        "observation_date": spec.observation_date,
        "observation_start": spec.observation_start.isoformat(),
        "observation_end": spec.observation_end.isoformat(),
        "observation_window_metadata": spec.observation_window_metadata,
        "stages_completed": stages_completed,
    }
    if extra:
        prov.update(extra)
    return prov


# ---------------------------------------------------------------------------
# Core: process one case
# ---------------------------------------------------------------------------


def process_case(
    spec: CaseSpec,
    thresholds: Optional[SeverityThresholds] = None,
) -> BatchCaseResult:
    """Process one CaseSpec through the full ForecastGuard pipeline.

    This function:
    1.  Checks that input files exist (MISSING_INPUT if not).
    2.  Converts the spec to a RainfallCase and runs it.
    3.  Builds a DatasetRecord from the case result.
    4.  Builds a RainfallTarget from the case result.
    5.  Assembles a tabular sample.
    6.  Returns a BatchCaseResult with explicit status.

    A single exception at any stage produces a PROCESSING_ERROR result
    rather than propagating the exception.  The full traceback is captured.

    No raw input files are modified.
    No model fitting is performed.
    No future observation information enters the predictor features.

    Parameters
    ----------
    spec : CaseSpec
        Case specification from the manifest.
    thresholds : Optional[SeverityThresholds]
        Optional severity thresholds for target construction.
        If None, severity is UNDEFINED.

    Returns
    -------
    BatchCaseResult
        Complete result with explicit status and audit trail.
    """
    ts = datetime.utcnow()

    # Stage 0: check inputs
    missing_reason = _check_inputs_exist(spec)
    if missing_reason:
        return BatchCaseResult(
            case_id=spec.case_id,
            batch_status=BatchCaseStatus.MISSING_INPUT,
            spec=spec,
            reason=missing_reason,
            processing_timestamp=ts,
            provenance=_build_provenance(spec, []),
        )

    try:
        # Stage 1: run rainfall case (ingestion + alignment + verification)
        rainfall_case = _spec_to_rainfall_case(spec)
        case_result = run_rainfall_case(rainfall_case)

        # Stage 2: build dataset record (feature extraction)
        dataset_record = build_dataset_record(rainfall_case, case_result)

        # Stage 3: build target (leakage-safe targets)
        target = build_rainfall_target(case_result, thresholds=thresholds)

        # Stage 4: assemble tabular sample
        sample = assemble_sample(dataset_record, target)

        # Determine batch status
        batch_status = _case_status_to_batch_status(
            case_result.status, target.target_status
        )

        reason = ""
        if batch_status != BatchCaseStatus.VALID:
            reason = target.reason or case_result.provenance.get("reason", "")

        return BatchCaseResult(
            case_id=spec.case_id,
            batch_status=batch_status,
            spec=spec,
            case_result=case_result,
            dataset_record=dataset_record,
            target=target,
            sample=sample,
            reason=reason,
            processing_timestamp=ts,
            provenance=_build_provenance(
                spec,
                stages_completed=["case_runner", "dataset_record", "target", "assembly"],
                extra={
                    "case_status": case_result.status.value,
                    "target_status": target.target_status.value,
                },
            ),
        )

    except Exception:  # noqa: BLE001
        tb = traceback.format_exc()
        return BatchCaseResult(
            case_id=spec.case_id,
            batch_status=BatchCaseStatus.PROCESSING_ERROR,
            spec=spec,
            reason="Unexpected exception during processing",
            error_traceback=tb,
            processing_timestamp=ts,
            provenance=_build_provenance(spec, [], extra={"exception": tb.splitlines()[-1]}),
        )


# ---------------------------------------------------------------------------
# BatchProcessor
# ---------------------------------------------------------------------------


class BatchProcessor:
    """Deterministic batch processor for a CaseManifest.

    Processes cases one at a time in manifest order.  Each GRIB file is
    read, processed, and released before the next case starts — no large
    arrays accumulate in memory across cases.

    A single case failure does not prevent later cases from processing.

    Usage
    -----
    ::

        processor = BatchProcessor(thresholds=my_thresholds)
        result = processor.run(manifest)
        samples = result.trainable_samples()

    Parameters
    ----------
    thresholds : Optional[SeverityThresholds]
        Severity thresholds for target construction.
        If None, severity is UNDEFINED for all cases.
    on_progress : Optional[Callable[[int, int, BatchCaseResult], None]]
        Optional callback called after each case with
        (case_index, total_cases, result).  Useful for progress reporting.
    """

    def __init__(
        self,
        thresholds: Optional[SeverityThresholds] = None,
        on_progress: Optional[Callable[[int, int, BatchCaseResult], None]] = None,
    ) -> None:
        self._thresholds = thresholds
        self._on_progress = on_progress

    def run(self, manifest: CaseManifest) -> BatchResult:
        """Process all cases in the manifest and return a BatchResult.

        Parameters
        ----------
        manifest : CaseManifest
            Validated manifest to process.

        Returns
        -------
        BatchResult
            Immutable result with one BatchCaseResult per case.
        """
        start = datetime.utcnow()
        results: List[BatchCaseResult] = []

        counts = {
            BatchCaseStatus.VALID: 0,
            BatchCaseStatus.BLOCKED: 0,
            BatchCaseStatus.INVALID: 0,
            BatchCaseStatus.MISSING_INPUT: 0,
            BatchCaseStatus.PROCESSING_ERROR: 0,
        }

        total = len(manifest)
        for i, spec in enumerate(manifest):
            result = process_case(spec, thresholds=self._thresholds)
            results.append(result)
            counts[result.batch_status] = counts.get(result.batch_status, 0) + 1

            if self._on_progress is not None:
                try:
                    self._on_progress(i, total, result)
                except Exception:  # noqa: BLE001
                    pass  # progress callback errors must not corrupt the batch

        end = datetime.utcnow()

        return BatchResult(
            results=tuple(results),
            manifest_id=manifest.manifest_id,
            processing_start=start,
            processing_end=end,
            total_cases=total,
            valid_count=counts[BatchCaseStatus.VALID],
            blocked_count=counts[BatchCaseStatus.BLOCKED],
            invalid_count=counts[BatchCaseStatus.INVALID],
            missing_input_count=counts[BatchCaseStatus.MISSING_INPUT],
            error_count=counts[BatchCaseStatus.PROCESSING_ERROR],
        )

    def iter_process(
        self,
        manifest: CaseManifest,
    ) -> Iterator[BatchCaseResult]:
        """Process cases one at a time, yielding each result as it is produced.

        Useful for streaming large manifests without accumulating all results
        in memory at once.

        Parameters
        ----------
        manifest : CaseManifest
            Manifest to process.

        Yields
        ------
        BatchCaseResult
            One result per case, in manifest order.
        """
        for spec in manifest:
            yield process_case(spec, thresholds=self._thresholds)
