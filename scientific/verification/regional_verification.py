"""ForecastGuard Regional Forecast-versus-Observation Verification Engine.

Strictly complies with AGENTS.md:
- Rule 1: Never fabricate weather data or machine-learning predictions.
- Rule 4: Never use future observations as predictor features.
- Rule 5: Preserve chronological train/validation/test separation.
- Rule 6: Every prediction must use only information available at forecast lead.
- Rule 7: Never silently change scientific definitions, units, or coordinates.
- Rule 14: Never invent historical cases or historical verification results.

Evaluates forecast predictions against official IMD Tropical Cyclone Best Tracks
(RSMC New Delhi) across ForecastGuard Predefined Analytical Regions.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

import pandas as pd

from scientific.remapping.regions import PredefinedRegion, get_all_regions, get_region_by_id

BASE_DIR = Path(__file__).resolve().parent.parent.parent


@dataclass(frozen=True)
class RegionalVerificationRecord:
    """Rigorous forecast-versus-observation regional verification record."""

    case_id: str
    storm_name: str
    forecast_cycle: str
    lead_hours: int
    lead_label: str
    valid_time: str
    region_id: str
    region_name: str
    forecast_lat: float
    forecast_lon: float
    forecast_pressure_hpa: float
    observed_lat: float
    observed_lon: float
    observed_pressure_hpa: float
    track_error_km: float
    pressure_error_hpa: float
    threshold_km: float
    is_bust: bool
    severity: Literal["NORMAL", "MODERATE", "DEGRADED", "SEVERE"]
    ensemble_spread_km: float
    provenance: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to JSON-serializable dictionary."""
        return {
            "case_id": self.case_id,
            "storm_name": self.storm_name,
            "forecast_cycle": self.forecast_cycle,
            "lead_hours": self.lead_hours,
            "lead_label": self.lead_label,
            "valid_time": self.valid_time,
            "region_id": self.region_id,
            "region_name": self.region_name,
            "forecast_lat": round(self.forecast_lat, 2),
            "forecast_lon": round(self.forecast_lon, 2),
            "forecast_pressure_hpa": round(self.forecast_pressure_hpa, 1),
            "observed_lat": round(self.observed_lat, 2),
            "observed_lon": round(self.observed_lon, 2),
            "observed_pressure_hpa": round(self.observed_pressure_hpa, 1),
            "track_error_km": round(self.track_error_km, 1),
            "pressure_error_hpa": round(self.pressure_error_hpa, 1),
            "threshold_km": round(self.threshold_km, 1),
            "is_bust": self.is_bust,
            "severity": self.severity,
            "ensemble_spread_km": round(self.ensemble_spread_km, 1),
            "provenance": self.provenance,
        }


class RegionalVerificationEngine:
    """Engine that aligns forecasts with IMD Best Track observations across regions."""

    def __init__(self, dataset_path: Optional[Path] = None) -> None:
        self.dataset_path = dataset_path or (
            BASE_DIR / "data/validation/expanded_cyclone_verified_dataset.csv"
        )
        self._records: List[RegionalVerificationRecord] = []
        self._load_dataset()

    def _load_dataset(self) -> None:
        """Load and index verified observations against predefined regions."""
        if not self.dataset_path.exists():
            return

        df = pd.read_csv(self.dataset_path)
        all_regions = get_all_regions()

        for _, row in df.iterrows():
            obs_lat = float(row["observed_lat"])
            obs_lon = float(row["observed_lon"])

            # Map coordinates to predefined analytical region
            matched_region = None
            for reg in all_regions:
                if reg.contains_point(obs_lat, obs_lon):
                    matched_region = reg
                    break

            if matched_region is None:
                # If observed point is outside land/marine polygons, determine nearest basin
                if obs_lon >= 78.0:
                    matched_region = get_region_by_id("MAR_BOB")
                else:
                    matched_region = get_region_by_id("MAR_AS")

            lead_hours = int(row["forecast_lead_hours"])
            lead_label = f"D+{lead_hours // 24}" if lead_hours % 24 == 0 else f"+{lead_hours}h"
            storm = str(row["storm_name"]).upper()
            init_dt = pd.to_datetime(str(row["initialization_time"]).strip(), utc=True)
            init_iso = init_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

            valid_dt = pd.to_datetime(str(row["forecast_valid_time"]).strip(), utc=True)
            valid_iso = valid_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

            case_id = f"{storm}_00Z"

            track_err = float(row["track_error_km"])
            p_err = abs(float(row["forecast_pressure_hpa"]) - float(row["observed_pressure_hpa"]))
            threshold = float(row["threshold_km"])
            is_bust = bool(row["bust_label"] == 1)

            rec = RegionalVerificationRecord(
                case_id=case_id,
                storm_name=storm,
                forecast_cycle=init_iso,
                lead_hours=lead_hours,
                lead_label=lead_label,
                valid_time=valid_iso,
                region_id=matched_region.region_id if matched_region else "UNKNOWN",
                region_name=matched_region.name if matched_region else "Unknown Basin",
                forecast_lat=float(row["forecast_lat"]),
                forecast_lon=float(row["forecast_lon"]),
                forecast_pressure_hpa=float(row["forecast_pressure_hpa"]),
                observed_lat=obs_lat,
                observed_lon=obs_lon,
                observed_pressure_hpa=float(row["observed_pressure_hpa"]),
                track_error_km=track_err,
                pressure_error_hpa=p_err,
                threshold_km=threshold,
                is_bust=is_bust,
                severity=str(row.get("severity", "NORMAL")),  # type: ignore
                ensemble_spread_km=float(row["ensemble_spread_km"]),
                provenance=(
                    "NCMRWF NEPS 11-member ensemble forecast verified against official "
                    "India Meteorological Department (IMD) RSMC Best Track Archive"
                ),
            )
            self._records.append(rec)

    def get_all_records(self) -> List[RegionalVerificationRecord]:
        """Return all verified records."""
        return list(self._records)

    def get_records_for_case(
        self, case_id: str, lead_hours: Optional[int] = None
    ) -> List[RegionalVerificationRecord]:
        """Filter verified records by case and optional lead hours."""
        case_upper = case_id.upper()
        results = [r for r in self._records if r.case_id == case_upper]
        if lead_hours is not None:
            results = [r for r in results if r.lead_hours == lead_hours]
        return results

    def get_record_for_region(
        self, case_id: str, region_id: str, lead_hours: int
    ) -> Optional[RegionalVerificationRecord]:
        """Get verified observation for a specific region, case, and lead."""
        case_upper = case_id.upper()
        reg_upper = region_id.upper()
        for r in self._records:
            if r.case_id == case_upper and r.region_id == reg_upper and r.lead_hours == lead_hours:
                return r
        return None


# Global singleton verification engine
regional_verification_engine = RegionalVerificationEngine()
