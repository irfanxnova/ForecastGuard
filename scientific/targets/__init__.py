"""Target generation and bust definition package.

Converts verified rainfall forecast outcomes into ML target records.

Scientific rules enforced:
- Only ALIGNED cases produce training targets.
- Observation-derived values are legitimate TARGET fields (labels), not predictors.
- Blocked and invalid verifications produce BLOCKED/INVALID targets with no labels.
- Severity thresholds must be supplied explicitly; no thresholds are hardcoded.
- Spatial feature arrays are explicitly excluded from target records.
"""

from scientific.targets.rainfall import (
    LeakageError,
    RainfallTarget,
    RainfallTargetStatus,
    SeverityLevel,
    SeverityThresholds,
    build_rainfall_target,
)

__all__ = [
    "LeakageError",
    "RainfallTarget",
    "RainfallTargetStatus",
    "SeverityLevel",
    "SeverityThresholds",
    "build_rainfall_target",
]
