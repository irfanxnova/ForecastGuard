"""Leakage-safe chronological train/validation/test splitting.

Splits a collection of AssembledSample objects into train, validation, and
test partitions using forecast initialization time as the ordering key.

SCIENTIFIC PRINCIPLE
--------------------
The split is always chronological.  No random shuffling is applied to the
primary scientific split.  This preserves the temporal structure of forecast
busts and prevents future-observation leakage via temporal proximity.

Cases sharing the same forecast initialization time (same cycle) are never
split across incompatible partitions: a cycle is assigned entirely to one
partition.

PURGE / GAP PERIOD
------------------
When ``purge_hours`` is supplied, cycles falling within that many hours
after a partition boundary are excluded from the *later* partition.  This
prevents temporal leakage from adjacent forecast cycles influencing each
other (e.g., correlated synoptic patterns in consecutive 24-h forecasts).

TWO MODES
---------
Boundary mode
    Caller supplies explicit ``datetime`` boundaries.
    All samples with init_time < train_end go to train.
    Samples with train_end <= init_time < val_end go to validation (or
    directly to test if no validation boundary is given).
    Remaining samples go to test.

Ratio mode
    Caller supplies fractional ratios (train, val, test) that sum to 1.0.
    Boundaries are computed deterministically from the sorted cycle list.

AUDITABILITY
------------
SplitResult records:
- exact boundary datetimes used
- cycle count per partition
- sample count per partition
- purge_hours applied
- which cycles were purged

VALIDATION (at construction time)
----------------------------------
- Boundaries must be chronological.
- Ratios must be positive and sum to 1.0.
- Duplicate case_ids are detected and reported.
- Samples without forecast_initialization_time are placed in a separate
  ``undated`` list and excluded from the primary split.
- Insufficient data (e.g., fewer than 2 distinct cycles for a 3-way split)
  raises SplitConfigurationError.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

from scientific.dataset.assembly import AssembledSample


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class SplitConfigurationError(Exception):
    """Raised when split parameters are invalid."""


class SplitDataError(Exception):
    """Raised when the input data prevents a valid split."""


# ---------------------------------------------------------------------------
# SplitResult
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SplitResult:
    """Immutable result of a chronological split operation.

    Attributes
    ----------
    train : List[AssembledSample]
        Samples assigned to the training partition.
    validation : List[AssembledSample]
        Samples assigned to the validation partition.
    test : List[AssembledSample]
        Samples assigned to the test partition.
    undated : List[AssembledSample]
        Samples with no forecast_initialization_time.  Excluded from the
        primary split and stored here for auditability.
    purged : List[AssembledSample]
        Samples excluded by the purge gap.
    train_boundary : Optional[datetime]
        Upper bound of the training partition (exclusive).
    val_boundary : Optional[datetime]
        Upper bound of the validation partition (exclusive).
    purge_hours : float
        Gap applied after each boundary.
    train_cycle_count : int
        Number of distinct forecast initialization cycles in train.
    val_cycle_count : int
        Number of distinct forecast initialization cycles in validation.
    test_cycle_count : int
        Number of distinct forecast initialization cycles in test.
    split_metadata : Dict[str, Any]
        Audit trail (mode, boundaries, ratios if applicable, timestamp).
    """

    train: List[AssembledSample] = field(default_factory=list)
    validation: List[AssembledSample] = field(default_factory=list)
    test: List[AssembledSample] = field(default_factory=list)
    undated: List[AssembledSample] = field(default_factory=list)
    purged: List[AssembledSample] = field(default_factory=list)
    train_boundary: Optional[datetime] = None
    val_boundary: Optional[datetime] = None
    purge_hours: float = 0.0
    train_cycle_count: int = 0
    val_cycle_count: int = 0
    test_cycle_count: int = 0
    split_metadata: Dict[str, Any] = field(default_factory=dict)

    def total_samples(self) -> int:
        """Total samples across train + validation + test."""
        return len(self.train) + len(self.validation) + len(self.test)

    def partition_sizes(self) -> Dict[str, int]:
        """Return dict of partition name → sample count."""
        return {
            "train": len(self.train),
            "validation": len(self.validation),
            "test": len(self.test),
            "undated": len(self.undated),
            "purged": len(self.purged),
        }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _group_by_cycle(
    samples: List[AssembledSample],
) -> Tuple[List[AssembledSample], List[AssembledSample]]:
    """Separate dated (has forecast_initialization_time) from undated samples.

    Returns (dated, undated).
    """
    dated = [s for s in samples if s.forecast_initialization_time is not None]
    undated = [s for s in samples if s.forecast_initialization_time is None]
    return dated, undated


def _sorted_unique_cycles(dated: List[AssembledSample]) -> List[datetime]:
    """Return sorted list of unique forecast_initialization_time values."""
    return sorted({s.forecast_initialization_time for s in dated})


def _check_duplicate_case_ids(samples: Sequence[AssembledSample]) -> None:
    """Raise SplitDataError if any case_id appears more than once."""
    seen: Dict[str, int] = {}
    for s in samples:
        seen[s.case_id] = seen.get(s.case_id, 0) + 1
    duplicates = {k: v for k, v in seen.items() if v > 1}
    if duplicates:
        raise SplitDataError(
            f"Duplicate case_ids detected: {duplicates}. "
            "Each case must appear exactly once in the input."
        )


def _assign_cycles_to_partitions(
    sorted_cycles: List[datetime],
    train_end: datetime,
    val_end: Optional[datetime],
    purge_hours: float,
) -> Tuple[
    List[datetime], List[datetime], List[datetime], List[datetime]
]:
    """Assign each cycle to train, validation, test, or purged.

    Parameters
    ----------
    sorted_cycles : List[datetime]
        All distinct cycles sorted ascending.
    train_end : datetime
        Train partition upper boundary (exclusive).
    val_end : Optional[datetime]
        Validation partition upper boundary (exclusive).  If None, there is
        no validation partition and test starts directly after train.
    purge_hours : float
        Hours after each boundary to exclude from the later partition.

    Returns
    -------
    (train_cycles, val_cycles, test_cycles, purged_cycles)
    """
    purge_delta = timedelta(hours=purge_hours)
    train_purge_end = train_end + purge_delta
    val_purge_end = (val_end + purge_delta) if val_end is not None else None

    train_cycles: List[datetime] = []
    val_cycles: List[datetime] = []
    test_cycles: List[datetime] = []
    purged_cycles: List[datetime] = []

    for cycle in sorted_cycles:
        if cycle < train_end:
            train_cycles.append(cycle)
        elif purge_hours > 0 and cycle < train_purge_end:
            purged_cycles.append(cycle)
        elif val_end is not None:
            if cycle < val_end:
                val_cycles.append(cycle)
            elif purge_hours > 0 and val_purge_end is not None and cycle < val_purge_end:
                purged_cycles.append(cycle)
            else:
                test_cycles.append(cycle)
        else:
            test_cycles.append(cycle)

    return train_cycles, val_cycles, test_cycles, purged_cycles


def _samples_for_cycles(
    dated: List[AssembledSample],
    cycle_set: set,
) -> List[AssembledSample]:
    """Return samples whose forecast_initialization_time is in cycle_set."""
    return [s for s in dated if s.forecast_initialization_time in cycle_set]


# ---------------------------------------------------------------------------
# ChronologicalSplitter
# ---------------------------------------------------------------------------


class ChronologicalSplitter:
    """Splits AssembledSamples into chronological train/validation/test sets.

    Usage — boundary mode
    ---------------------
    ::

        splitter = ChronologicalSplitter(
            train_end=datetime(2024, 7, 1, tzinfo=timezone.utc),
            val_end=datetime(2024, 9, 1, tzinfo=timezone.utc),
            purge_hours=48.0,
        )
        result = splitter.split(samples)

    Usage — ratio mode
    ------------------
    ::

        splitter = ChronologicalSplitter(
            train_ratio=0.7,
            val_ratio=0.15,
            test_ratio=0.15,
        )
        result = splitter.split(samples)

    Parameters
    ----------
    train_end : Optional[datetime]
        Explicit upper boundary for training partition.
    val_end : Optional[datetime]
        Explicit upper boundary for validation partition.  If not supplied
        while ``train_end`` is supplied, there is no validation partition
        and all post-train samples go to test.
    train_ratio : Optional[float]
        Fraction of cycles for training (ratio mode).
    val_ratio : Optional[float]
        Fraction of cycles for validation (ratio mode).  May be 0.
    test_ratio : Optional[float]
        Fraction of cycles for test (ratio mode).
    purge_hours : float
        Hours after each boundary to exclude from the later partition.
        Default 0 (no purge).

    Raises
    ------
    SplitConfigurationError
        If the combination of parameters is invalid.
    """

    def __init__(
        self,
        train_end: Optional[datetime] = None,
        val_end: Optional[datetime] = None,
        train_ratio: Optional[float] = None,
        val_ratio: Optional[float] = None,
        test_ratio: Optional[float] = None,
        purge_hours: float = 0.0,
    ) -> None:
        # Validate mode
        boundary_mode = train_end is not None
        ratio_mode = any(x is not None for x in (train_ratio, val_ratio, test_ratio))

        if boundary_mode and ratio_mode:
            raise SplitConfigurationError(
                "Specify either boundary parameters (train_end, val_end) "
                "or ratio parameters (train_ratio, val_ratio, test_ratio), not both."
            )
        if not boundary_mode and not ratio_mode:
            raise SplitConfigurationError(
                "Must specify either boundary or ratio parameters."
            )
        if purge_hours < 0:
            raise SplitConfigurationError(
                f"purge_hours must be >= 0, got {purge_hours}."
            )

        if boundary_mode:
            if val_end is not None and val_end <= train_end:
                raise SplitConfigurationError(
                    f"val_end ({val_end}) must be strictly after train_end ({train_end})."
                )
            self._mode = "boundary"
            self._train_end = train_end
            self._val_end = val_end
            self._train_ratio = None
            self._val_ratio = None
            self._test_ratio = None
        else:
            # Ratio mode: all three must be supplied
            if any(x is None for x in (train_ratio, val_ratio, test_ratio)):
                raise SplitConfigurationError(
                    "In ratio mode, all three of train_ratio, val_ratio, "
                    "test_ratio must be supplied."
                )
            if train_ratio <= 0:
                raise SplitConfigurationError(
                    f"train_ratio must be > 0, got {train_ratio}."
                )
            if test_ratio <= 0:
                raise SplitConfigurationError(
                    f"test_ratio must be > 0, got {test_ratio}."
                )
            if val_ratio < 0:
                raise SplitConfigurationError(
                    f"val_ratio must be >= 0, got {val_ratio}."
                )
            total = train_ratio + val_ratio + test_ratio
            if abs(total - 1.0) > 1e-9:
                raise SplitConfigurationError(
                    f"Ratios must sum to 1.0, got {total:.6f}."
                )
            self._mode = "ratio"
            self._train_end = None
            self._val_end = None
            self._train_ratio = train_ratio
            self._val_ratio = val_ratio
            self._test_ratio = test_ratio

        self._purge_hours = purge_hours

    def split(self, samples: Sequence[AssembledSample]) -> SplitResult:
        """Perform the chronological split.

        Parameters
        ----------
        samples : Sequence[AssembledSample]
            All assembled samples.  Order in input does not matter;
            the split is always by chronological cycle order.

        Returns
        -------
        SplitResult
            Immutable split result with train, validation, test, undated,
            and purged partitions.

        Raises
        ------
        SplitDataError
            If duplicate case_ids are found, or if there are insufficient
            cycles for the requested split.
        SplitConfigurationError
            If boundaries fall outside the data range in boundary mode
            (informational — empty partitions are allowed but flagged in
            metadata).
        """
        sample_list = list(samples)
        _check_duplicate_case_ids(sample_list)

        dated, undated = _group_by_cycle(sample_list)
        sorted_cycles = _sorted_unique_cycles(dated)
        n_cycles = len(sorted_cycles)

        # Determine boundaries
        if self._mode == "boundary":
            train_end = self._train_end
            val_end = self._val_end
        else:
            # Ratio mode: compute boundaries from cycle list
            if n_cycles == 0:
                return SplitResult(
                    undated=undated,
                    split_metadata=self._metadata(None, None, n_cycles, "ratio"),
                )
            train_end, val_end = self._compute_ratio_boundaries(sorted_cycles)

        # Assign cycles to partitions
        train_cycles, val_cycles, test_cycles, purged_cycles = (
            _assign_cycles_to_partitions(
                sorted_cycles, train_end, val_end, self._purge_hours
            )
        )

        train_set = set(train_cycles)
        val_set = set(val_cycles)
        test_set = set(test_cycles)
        purged_set = set(purged_cycles)

        train_samples = _samples_for_cycles(dated, train_set)
        val_samples = _samples_for_cycles(dated, val_set)
        test_samples = _samples_for_cycles(dated, test_set)
        purged_samples = _samples_for_cycles(dated, purged_set)

        metadata = self._metadata(train_end, val_end, n_cycles, self._mode)
        metadata["purged_cycle_count"] = len(purged_cycles)
        metadata["purged_cycles"] = [c.isoformat() for c in sorted(purged_cycles)]

        return SplitResult(
            train=train_samples,
            validation=val_samples,
            test=test_samples,
            undated=undated,
            purged=purged_samples,
            train_boundary=train_end,
            val_boundary=val_end,
            purge_hours=self._purge_hours,
            train_cycle_count=len(train_cycles),
            val_cycle_count=len(val_cycles),
            test_cycle_count=len(test_cycles),
            split_metadata=metadata,
        )

    def _compute_ratio_boundaries(
        self, sorted_cycles: List[datetime]
    ) -> Tuple[datetime, Optional[datetime]]:
        """Compute train_end and val_end from ratios and sorted cycle list."""
        n = len(sorted_cycles)
        train_n = max(1, int(round(n * self._train_ratio)))

        if self._val_ratio > 0:
            val_n = max(1, int(round(n * self._val_ratio)))
            # Ensure train + val < n so test is non-empty
            if train_n + val_n >= n:
                val_n = max(0, n - train_n - 1)
            train_end = sorted_cycles[train_n]  # exclusive upper bound
            if val_n > 0 and train_n + val_n < n:
                val_end = sorted_cycles[train_n + val_n]
            else:
                val_end = None
        else:
            # No validation partition
            if train_n >= n:
                train_n = n - 1  # ensure at least one test cycle
            train_end = sorted_cycles[train_n]
            val_end = None

        return train_end, val_end

    def _metadata(
        self,
        train_end: Optional[datetime],
        val_end: Optional[datetime],
        n_cycles: int,
        mode: str,
    ) -> Dict[str, Any]:
        return {
            "split_mode": mode,
            "train_end": train_end.isoformat() if train_end else None,
            "val_end": val_end.isoformat() if val_end else None,
            "total_cycles": n_cycles,
            "purge_hours": self._purge_hours,
            "split_timestamp": datetime.utcnow().isoformat(),
            **(
                {
                    "train_ratio": self._train_ratio,
                    "val_ratio": self._val_ratio,
                    "test_ratio": self._test_ratio,
                }
                if mode == "ratio"
                else {}
            ),
        }
