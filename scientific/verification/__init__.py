"""Forecast verification and error computation package."""

from scientific.verification.rainfall import (
	RainfallVerificationResult,
	RainfallVerificationStatus,
	verify_rainfall,
	verify_rainfall_field,
)

__all__ = [
	"RainfallVerificationResult",
	"RainfallVerificationStatus",
	"verify_rainfall",
	"verify_rainfall_field",
]
