"""Historical case runner for auditable forecast verification."""

from scientific.cases.rainfall_case import (
	RainfallCase,
	RainfallCaseResult,
	RainfallCaseStatus,
	persist_rainfall_case,
	run_rainfall_case,
)

__all__ = [
	"RainfallCase",
	"RainfallCaseResult",
	"RainfallCaseStatus",
	"run_rainfall_case",
	"persist_rainfall_case",
]

# CLI entry point support
__cli_main__ = "scientific.cases.cli:main"
