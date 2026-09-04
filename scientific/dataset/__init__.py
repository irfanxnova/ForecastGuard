"""ML-ready dataset generation from verified historical forecast cases.

This module converts verified historical rainfall forecast cases into
structured dataset records suitable for training forecast-bust detection models.

Scientific rules enforced:
- Only ALIGNED cases produce training targets
- Blocked cases tracked explicitly with status/reason
- No fabricated targets or bust labels
- NaNs preserved (no silent imputation)
- Observation accumulation windows must be explicitly supplied
- No future observation information
- Deterministic, auditable output
"""

from scientific.dataset.builder import (
    DatasetRecord,
    DatasetRecordStatus,
    build_dataset_record,
)

__all__ = [
    "DatasetRecord",
    "DatasetRecordStatus",
    "build_dataset_record",
]
