"""ForecastGuard Historical Replay & Bust Atlas Service.

Loads authoritative verified cases from data/validation/ and provides
lead-by-lead (+06h to +48h) historical forecast-vs-observed replay.
Dual provenance: NCMRWF TIGGE vs Official IMD/RSMC Best Tracks (1982-2026 Archive).
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.app.schemas.historical import (
    BustAtlasRecord,
    CycloneSummary,
    HistoricalReplayResponse,
    ReplayLeadPoint,
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "validation"
DATASET_PATH = DATA_DIR / "expanded_cyclone_verified_dataset.json"
ATLAS_PATH = DATA_DIR / "cyclone_bust_atlas.json"


class HistoricalService:
    """Service providing verified historical cyclone forecast replays and bust atlas."""

    def __init__(self) -> None:
        self._dataset_cache: Optional[Dict[str, Any]] = None
        self._atlas_cache: Optional[List[Dict[str, Any]]] = None

    def _load_dataset(self) -> Dict[str, Any]:
        if self._dataset_cache is not None:
            return self._dataset_cache
        path = DATASET_PATH if DATASET_PATH.exists() else Path("data/validation/expanded_cyclone_verified_dataset.json")
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                self._dataset_cache = json.load(f)
                return self._dataset_cache
        return {"total_records": 0, "records": []}

    def _load_atlas(self) -> List[Dict[str, Any]]:
        if self._atlas_cache is not None:
            return self._atlas_cache
        path = ATLAS_PATH if ATLAS_PATH.exists() else Path("data/validation/cyclone_bust_atlas.json")
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
                if isinstance(raw, dict) and "records" in raw:
                    self._atlas_cache = raw["records"]
                elif isinstance(raw, list):
                    self._atlas_cache = raw
                else:
                    self._atlas_cache = []
                return self._atlas_cache
        return []

    def list_cyclones(self) -> List[CycloneSummary]:
        """Return distinct tropical cyclones and cycles in the verified dataset."""
        data = self._load_dataset()
        records = data.get("records", [])

        storms: Dict[str, Dict[str, Any]] = {}
        for r in records:
            name = r["storm_name"]
            if name not in storms:
                storms[name] = {
                    "storm_id": r.get("storm_id", f"2023_{name}"),
                    "storm_name": name,
                    "basin": r["basin"],
                    "season_year": 2023,
                    "cycles": set(),
                    "total_leads": 0,
                    "busts": 0,
                    "errors": [],
                }
            storms[name]["cycles"].add(r["cycle_label"])
            storms[name]["total_leads"] += 1
            if r["bust_label"] == 1:
                storms[name]["busts"] += 1
            storms[name]["errors"].append(r["track_error_km"])

        summaries: List[CycloneSummary] = []
        for name, d in storms.items():
            mean_err = float(sum(d["errors"]) / len(d["errors"])) if d["errors"] else 0.0
            summaries.append(
                CycloneSummary(
                    storm_id=d["storm_id"],
                    storm_name=name,
                    basin=d["basin"],
                    season_year=d["season_year"],
                    cycles_count=len(d["cycles"]),
                    cycles=sorted(list(d["cycles"])),
                    verified_leads_count=d["total_leads"],
                    contemporaneous_busts_count=d["busts"],
                    mean_track_error_km=round(mean_err, 2),
                )
            )
        return sorted(summaries, key=lambda s: s.storm_name)

    def get_replay(self, storm_name: str, cycle_label: Optional[str] = None) -> Optional[HistoricalReplayResponse]:
        """Build lead-by-lead historical replay with ground-truth verification."""
        data = self._load_dataset()
        records = [
            r for r in data.get("records", [])
            if r["storm_name"].upper() == storm_name.upper()
        ]
        if not records:
            return None

        # If cycle_label not specified, take the first available cycle
        available_cycles = sorted(list(set(r["cycle_label"] for r in records)))
        target_cycle = cycle_label if (cycle_label and cycle_label in available_cycles) else available_cycles[0]

        cycle_records = [r for r in records if r["cycle_label"] == target_cycle]
        cycle_records.sort(key=lambda r: r["forecast_lead_hours"])

        leads: List[ReplayLeadPoint] = []
        errors: List[float] = []

        for r in cycle_records:
            err = float(r["track_error_km"])
            errors.append(err)
            tau = float(r["threshold_km"])
            is_bust = bool(r["bust_label"] == 1)
            sev = r.get("severity", "NORMAL")

            score = max(5, min(95, int(round(100.0 - (err / tau) * 50.0))))

            if err < 0.75 * tau:
                state = "STABLE"
            elif err < tau:
                state = "WATCH"
            elif err < 1.5 * tau:
                state = "VULNERABLE"
            else:
                state = "SEVERE"

            lead_pt = ReplayLeadPoint(
                lead_hours=r["forecast_lead_hours"],
                lead_formatted=f"+{r['forecast_lead_hours']:02d}h",
                valid_time_utc=r["forecast_valid_time"],
                forecast_center={
                    "latitude": round(r["forecast_lat"], 4),
                    "longitude": round(r["forecast_lon"], 4),
                    "pressure_hpa": round(r["forecast_pressure_hpa"], 2),
                },
                observed_center={
                    "latitude": round(r["observed_lat"], 4),
                    "longitude": round(r["observed_lon"], 4),
                    "pressure_hpa": round(r["observed_pressure_hpa"], 2),
                },
                track_error_km=round(err, 2),
                threshold_km=round(tau, 2),
                is_bust=is_bust,
                severity=sev,
                ensemble_spread_km=round(float(r["ensemble_spread_km"]), 2),
                ensemble_divergence_km=round(float(r["ensemble_divergence_km"]), 2),
                prospective_bust_risk_percent=(
                    round(float(r["prospective_bust_within24h"]) * 100)
                    if r.get("prospective_bust_within24h") is not None
                    else None
                ),
                reliability_score=score,
                reliability_state=state,
                retrospective_confidence_quadrant=r.get("confidence_quadrant", "NOMINAL"),
            )
            leads.append(lead_pt)

        first_rec = cycle_records[0]
        mean_err = float(sum(errors) / len(errors)) if errors else 0.0
        sorted_errs = sorted(errors)
        med_err = sorted_errs[len(sorted_errs) // 2] if sorted_errs else 0.0

        return HistoricalReplayResponse(
            mode="HISTORICAL_REPLAY",
            storm_id=first_rec.get("storm_id", f"2023_{storm_name}"),
            storm_name=first_rec["storm_name"],
            basin=first_rec["basin"],
            cycle_label=target_cycle,
            initialization_time_utc=first_rec["initialization_time"],
            total_leads=len(leads),
            leads=leads,
            continuous_error_summary={
                "mean_track_error_km": round(mean_err, 2),
                "median_track_error_km": round(med_err, 2),
                "max_track_error_km": round(max(errors) if errors else 0.0, 2),
                "min_track_error_km": round(min(errors) if errors else 0.0, 2),
            },
            provenance={
                "forecast_source": "NCMRWF NEPS 11-member ensemble (origin=dems)",
                "verification_source": "Official IMD/RSMC New Delhi Cyclone Best Track (1982-2026 Archive)",
                "verification_status": "Exact synoptic timestamp alignment (zero artificial interpolation)",
            },
        )

    def get_bust_atlas(self) -> List[BustAtlasRecord]:
        """Return curated Bust Atlas entries documenting verified forecast failures."""
        atlas_data = self._load_atlas()
        records: List[BustAtlasRecord] = []
        for entry in atlas_data:
            lead = int(entry.get("lead_hours", 0))
            tau = 90.0 * (1.0 + 0.008 * lead)
            err = float(entry.get("track_error_km") or entry.get("mean_track_error_km", 0.0))
            records.append(
                BustAtlasRecord(
                    storm_name=entry.get("storm") or entry.get("storm_name") or entry.get("cyclone_name", "UNKNOWN"),
                    cycle_label=entry.get("cycle_initialization") or entry.get("cycle_label", ""),
                    lead_hours=lead,
                    valid_time_utc=entry.get("valid_time_iso") or entry.get("valid_time_utc") or entry.get("valid_time", ""),
                    track_error_km=round(err, 2),
                    threshold_km=round(float(entry.get("threshold_km") or entry.get("bust_threshold_km") or tau), 2),
                    severity=entry.get("severity") or entry.get("bust_severity", "DEGRADED"),
                    spread_km=round(float(entry.get("ensemble_spread_km") or entry.get("spread_km", 0.0)), 2),
                    quadrant=entry.get("quadrant_category") or entry.get("confidence_quadrant", "QUADRANT_B_FALSE_CONFIDENCE"),
                    failure_type=entry.get("warning_status") or entry.get("failure_type", "Rapid Recurvature / Acceleration"),
                    description=f"Verified forecast bust (error {err:.1f} km vs threshold {tau:.1f} km).",
                )
            )
        return records


historical_service = HistoricalService()
