"""Validation-only forecast and observation alignment contracts."""

from scientific.alignment.rainfall import (
	AlignmentStatus,
	GridCompatibility,
	RainfallAlignmentResult,
	compare_rainfall_grids,
	validate_rainfall_alignment,
)

__all__ = [
	"AlignmentStatus",
	"GridCompatibility",
	"RainfallAlignmentResult",
	"compare_rainfall_grids",
	"validate_rainfall_alignment",
]
"""Spatial and temporal alignment package."""
