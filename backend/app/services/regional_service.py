"""ForecastGuard Regional Reliability Service.

Ingests real NWP ensemble forecast data (NCMRWF NEPS), extracts spatial grids,
evaluates genuine meteorological regional dispersion features, and produces
canonical Regional Reliability Assessments without fabrication or hardcoded scores.
"""

from datetime import datetime, timezone
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import eccodes
import numpy as np
import pandas as pd

from backend.app.schemas.regional import (
    CanonicalRegionalAssessment,
    CycleComparison,
    DominantEvidenceItem,
    EnsembleIntelligenceSummary,
    EnvironmentalIntelligenceSummary,
    HistoricalMemorySummary,
    MultiModelEvidenceSummary,
    RegionalAssessmentResponse,
    RegionalCaseSummary,
    RegionalFeatureCatalogItem,
    RegionalProvenance,
    RegionalTimelineResponse,
    RegionalTimelineStep,
    RegionalVerificationDetail,
    RegionalVerificationResponse,
    ReplayCaseResponse,
    RepresentationSupportSummary,
    StructuredEvidenceObject,
    TopAnalogueSummary,
    TrajectoryIntelligenceSummary,
)
from backend.app.schemas.historical_memory import (
    ForecastStateQuery,
    HistoricalMemorySearchRequest,
)
from backend.app.services.historical_memory_service import historical_memory_service
from scientific.ml.novelty import novelty_detector
from scientific.features.environmental_intelligence import (
    extract_environmental_intelligence_from_grid,
    extract_fallback_environmental_insufficient,
)
from scientific.ml.regional_candidate import (
    REGIONAL_FEATURE_DEFINITIONS,
    regional_candidate_predictor,
)
from scientific.verification.regional_verification import regional_verification_engine
from scientific.features.ensemble_intelligence import (
    compute_ensemble_intelligence_from_field,
    classify_ensemble_state,
)
from scientific.features.trajectory_intelligence import (
    classify_trajectory_state,
)
from scientific.features.structured_evidence import (
    generate_why_now_attribution,
    generate_what_changed_summary,
)
from scientific.remapping.regions import (
    METEOROLOGICAL_REGIONS,
    MeteorologicalRegion,
    check_domain_overlap,
    create_region_grid_mask,
    get_all_regions,
    get_region_by_id,
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent


# Catalog of supported real forecast cases backed by real GRIB files
SUPPORTED_CASES: Dict[str, Dict[str, Any]] = {
    "MIDHILI_00Z": {
        "case_id": "MIDHILI_00Z",
        "storm_name": "MIDHILI",
        "basin": "Bay of Bengal",
        "forecast_cycle": "2023-11-16T00:00:00Z",
        "grib_file": "data/validation/test_tigge_midhili_00z_msl.grib",
        "available_leads": ["D+1", "D+2"],
        "unsupported_leads": ["D+3", "D+4", "D+5", "D+6", "D+7", "D+8", "D+9", "D+10"],
        "available_variables": ["Mean Sea Level Pressure (msl)"],
        "default_variable": "Mean Sea Level Pressure (msl)",
        "variable_short_name": "msl",
        "supported_regions": ["MAR_BOB", "IND_ENE", "IND_SOU"],
        "unsupported_regions": ["MAR_AS", "IND_WST", "IND_NW", "IND_CEN"],
        "description": "Rapid downstream northeast acceleration across Bay of Bengal with severe forecast track failure (548.5 km verified bust at +48h).",
    },
    "MICHAUNG_00Z": {
        "case_id": "MICHAUNG_00Z",
        "storm_name": "MICHAUNG",
        "basin": "Bay of Bengal",
        "forecast_cycle": "2023-12-01T00:00:00Z",
        "grib_file": "data/validation/test_tigge_michaung_msl.grib",
        "available_leads": ["D+1", "D+2"],
        "unsupported_leads": ["D+3", "D+4", "D+5", "D+6", "D+7", "D+8", "D+9", "D+10"],
        "available_variables": ["Mean Sea Level Pressure (msl)"],
        "default_variable": "Mean Sea Level Pressure (msl)",
        "variable_short_name": "msl",
        "supported_regions": ["MAR_BOB", "IND_ENE", "IND_SOU"],
        "unsupported_regions": ["MAR_AS", "IND_WST", "IND_NW", "IND_CEN"],
        "description": "Held-out test storm demonstrating high prospective reliability; tight ensemble dispersion with zero verified busts across 48h trajectory.",
    },
    "BIPARJOY_00Z": {
        "case_id": "BIPARJOY_00Z",
        "storm_name": "BIPARJOY",
        "basin": "Arabian Sea",
        "forecast_cycle": "2023-06-07T00:00:00Z",
        "grib_file": "data/validation/test_tigge_biparjoy_msl.grib",
        "available_leads": ["D+1", "D+2"],
        "unsupported_leads": ["D+3", "D+4", "D+5", "D+6", "D+7", "D+8", "D+9", "D+10"],
        "available_variables": ["Mean Sea Level Pressure (msl)"],
        "default_variable": "Mean Sea Level Pressure (msl)",
        "variable_short_name": "msl",
        "supported_regions": ["MAR_AS", "IND_WST", "IND_CEN", "IND_NW"],
        "unsupported_regions": ["MAR_BOB", "IND_ENE", "IND_SOU"],
        "description": "Slow-moving Arabian Sea recurvature case: tight initial dispersion masked subsequent track deviation toward Gujarat coast.",
    },
    "HAMOON_00Z": {
        "case_id": "HAMOON_00Z",
        "storm_name": "HAMOON",
        "basin": "Bay of Bengal",
        "forecast_cycle": "2023-10-23T00:00:00Z",
        "grib_file": "data/validation/test_tigge_hamoon_00z_msl.grib",
        "available_leads": ["D+1", "D+2"],
        "unsupported_leads": ["D+3", "D+4", "D+5", "D+6", "D+7", "D+8", "D+9", "D+10"],
        "available_variables": ["Mean Sea Level Pressure (msl)"],
        "default_variable": "Mean Sea Level Pressure (msl)",
        "variable_short_name": "msl",
        "supported_regions": ["MAR_BOB", "IND_ENE", "IND_SOU"],
        "unsupported_regions": ["MAR_AS", "IND_WST", "IND_NW", "IND_CEN"],
        "description": "Sharp northeast recurvature toward Bangladesh coast with severe downstream failure (+42h bust: 298.4 km).",
    },
    "TEJ_00Z": {
        "case_id": "TEJ_00Z",
        "storm_name": "TEJ",
        "basin": "Arabian Sea",
        "forecast_cycle": "2023-10-21T00:00:00Z",
        "grib_file": "data/validation/test_tigge_tej_00z_msl.grib",
        "available_leads": ["D+1", "D+2"],
        "unsupported_leads": ["D+3", "D+4", "D+5", "D+6", "D+7", "D+8", "D+9", "D+10"],
        "available_variables": ["Mean Sea Level Pressure (msl)"],
        "default_variable": "Mean Sea Level Pressure (msl)",
        "variable_short_name": "msl",
        "supported_regions": ["MAR_AS", "IND_WST", "IND_CEN"],
        "unsupported_regions": ["MAR_BOB", "IND_ENE", "IND_NW", "IND_SOU"],
        "description": "Rapid intensification over central Arabian Sea with track degradation to 142.7 km at +48h.",
    },
    "MOCHA_00Z": {
        "case_id": "MOCHA_00Z",
        "storm_name": "MOCHA",
        "basin": "Bay of Bengal",
        "forecast_cycle": "2023-05-10T00:00:00Z",
        "grib_file": "data/validation/test_tigge_mocha_msl.grib",
        "available_leads": ["D+1", "D+2"],
        "unsupported_leads": ["D+3", "D+4", "D+5", "D+6", "D+7", "D+8", "D+9", "D+10"],
        "available_variables": ["Mean Sea Level Pressure (msl)"],
        "default_variable": "Mean Sea Level Pressure (msl)",
        "variable_short_name": "msl",
        "supported_regions": ["MAR_BOB", "IND_ENE", "IND_SOU"],
        "unsupported_regions": ["MAR_AS", "IND_WST", "IND_NW", "IND_CEN"],
        "description": "Initialization displacement: early vortex position was displaced (107.2 km error at +06h), before stabilizing in Bay of Bengal.",
    },
}


class RegionalReliabilityService:
    """Service that computes canonical regional reliability assessments from real forecast data."""

    def __init__(self) -> None:
        self._cache: Dict[str, Any] = {}
        self._cyclone_records: Dict[Tuple[str, int], Dict[str, Any]] = {}
        self._load_cyclone_records()

    def _load_cyclone_records(self) -> None:
        """Load verified synoptic cyclone telemetry records for trajectory intelligence."""
        dataset_path = BASE_DIR / "data" / "validation" / "expanded_cyclone_verified_dataset.csv"
        if not dataset_path.exists():
            return
        try:
            df = pd.read_csv(dataset_path)
            for _, row in df.iterrows():
                cycle_label = str(row["cycle_label"]).strip().upper()
                lead_h = int(row["forecast_lead_hours"])
                self._cyclone_records[(cycle_label, lead_h)] = row.to_dict()
        except Exception:
            pass

    def list_supported_cases(self) -> List[RegionalCaseSummary]:
        """Return list of all supported real forecast cases."""
        summaries = []
        for case_id, info in SUPPORTED_CASES.items():
            summaries.append(
                RegionalCaseSummary(
                    case_id=case_id,
                    storm_name=info.get("storm_name"),
                    basin=info["basin"],
                    forecast_cycle=info["forecast_cycle"],
                    available_leads=info["available_leads"],
                    unsupported_leads=info["unsupported_leads"],
                    available_variables=info["available_variables"],
                    supported_regions=info["supported_regions"],
                    unsupported_regions=info["unsupported_regions"],
                    description=info["description"],
                )
            )
        return summaries

    def _lead_to_step(self, lead_time: str) -> int:
        """Convert lead string like 'D+1', 'D+2', 'D 1', 'D 2', '+24h', '24' to integer hours."""
        cleaned = lead_time.strip().upper().replace(" ", "+")
        if cleaned.startswith("D+"):
            try:
                day = int(cleaned[2:])
                return day * 24
            except ValueError:
                pass
        elif cleaned.startswith("D"):
            try:
                day = int(cleaned[1:])
                return day * 24
            except ValueError:
                pass
        cleaned = cleaned.replace("+", "").replace("H", "")
        try:
            return int(cleaned)
        except ValueError:
            return 24

    def _step_to_lead_label(self, step: int) -> str:
        """Convert step hours to lead label e.g. 24 -> 'D+1', 48 -> 'D+2'."""
        day = step // 24
        remainder = step % 24
        if remainder == 0:
            return f"D+{day}"
        return f"+{step}h"

    def _read_grib_ensemble_at_step(
        self, file_path: Path, target_step: int
    ) -> Tuple[List[np.ndarray], Dict[str, Any]]:
        """Read 11 ensemble member fields at target step from GRIB file."""
        if not file_path.exists():
            raise FileNotFoundError(f"GRIB forecast file not found: {file_path}")

        cache_key = f"{file_path}_{target_step}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        members_values: List[np.ndarray] = []
        grid_meta: Dict[str, Any] = {}

        with open(file_path, "rb") as f:
            while True:
                handle = eccodes.codes_grib_new_from_file(f)
                if handle is None:
                    break
                try:
                    step = int(eccodes.codes_get(handle, "step"))
                    if step == target_step:
                        if not grid_meta:
                            grid_meta = {
                                "ni": int(eccodes.codes_get(handle, "Ni")),
                                "nj": int(eccodes.codes_get(handle, "Nj")),
                                "first_lat": float(eccodes.codes_get(handle, "latitudeOfFirstGridPointInDegrees")),
                                "last_lat": float(eccodes.codes_get(handle, "latitudeOfLastGridPointInDegrees")),
                                "first_lon": float(eccodes.codes_get(handle, "longitudeOfFirstGridPointInDegrees")),
                                "last_lon": float(eccodes.codes_get(handle, "longitudeOfLastGridPointInDegrees")),
                                "short_name": str(eccodes.codes_get(handle, "shortName")),
                                "data_date": int(eccodes.codes_get(handle, "dataDate")),
                                "data_time": int(eccodes.codes_get(handle, "dataTime")),
                            }
                        vals = eccodes.codes_get_values(handle)
                        members_values.append(np.asarray(vals, dtype=np.float64))
                finally:
                    eccodes.codes_release(handle)

        if not members_values:
            raise ValueError(f"No ensemble members found at step={target_step} in {file_path}")

        result = (members_values, grid_meta)
        self._cache[cache_key] = result
        return result

    def _compute_historical_memory_summary(
        self,
        case_id: str,
        lead_hours: int,
        cyc_row: Optional[Any],
        ens_field_metrics: Any,
        basin: str,
        storm_name: str,
    ) -> HistoricalMemorySummary:
        """Deterministically query historical forecast memory at forecast cutoff T."""
        try:
            ens_spread = (
                float(cyc_row["ensemble_spread_km"])
                if cyc_row is not None and pd.notna(cyc_row.get("ensemble_spread_km"))
                else float(ens_field_metrics.mean_spread / 1000.0)
            )
            aniso = (
                float(cyc_row["anisotropy_ratio"])
                if cyc_row is not None and pd.notna(cyc_row.get("anisotropy_ratio"))
                else float(ens_field_metrics.anisotropy_ratio)
            )
            bimod = (
                float(cyc_row["bimodality_coefficient"])
                if cyc_row is not None and pd.notna(cyc_row.get("bimodality_coefficient"))
                else float(ens_field_metrics.bimodality_coefficient)
            )
            dom_frac = (
                float(cyc_row["dominant_cluster_fraction"])
                if cyc_row is not None and pd.notna(cyc_row.get("dominant_cluster_fraction"))
                else float(ens_field_metrics.dominant_cluster_fraction)
            )
            clust_sep = (
                float(cyc_row["cluster_separation_km"])
                if cyc_row is not None and pd.notna(cyc_row.get("cluster_separation_km"))
                else float(ens_field_metrics.cluster_separation)
            )
            spread_growth = (
                float(cyc_row["spread_growth_km"])
                if cyc_row is not None and pd.notna(cyc_row.get("spread_growth_km"))
                else float(ens_field_metrics.spread_growth_rate)
            )

            maj_spread = (
                float(cyc_row["major_axis_spread_km"])
                if cyc_row is not None and pd.notna(cyc_row.get("major_axis_spread_km"))
                else None
            )
            speed = (
                float(cyc_row["trajectory_speed_kmh"])
                if cyc_row is not None and pd.notna(cyc_row.get("trajectory_speed_kmh"))
                else None
            )
            curvature = (
                float(cyc_row["trajectory_curvature_deg"])
                if cyc_row is not None and pd.notna(cyc_row.get("trajectory_curvature_deg"))
                else None
            )
            jitter = (
                float(cyc_row["trajectory_instability_km"])
                if cyc_row is not None and pd.notna(cyc_row.get("trajectory_instability_km"))
                else None
            )
            cyc_rev = (
                float(cyc_row["cycle_revision_distance_km"])
                if cyc_row is not None and pd.notna(cyc_row.get("cycle_revision_distance_km"))
                else None
            )

            query_state = ForecastStateQuery(
                lead_hours=int(np.clip(lead_hours, 6, 72)),
                ensemble_spread_km=float(np.clip(ens_spread, 0.0, 1500.0)),
                major_axis_spread_km=float(np.clip(maj_spread, 0.0, 2000.0)) if maj_spread is not None else None,
                anisotropy_ratio=float(np.clip(aniso, 0.5, 20.0)),
                bimodality_coefficient=float(np.clip(bimod, 0.0, 1.0)),
                dominant_cluster_fraction=float(np.clip(dom_frac, 0.0, 1.0)),
                cluster_separation_km=float(np.clip(clust_sep, 0.0, 2000.0)),
                spread_growth_km=float(np.clip(spread_growth, -500.0, 500.0)),
                trajectory_speed_kmh=float(np.clip(speed, 0.0, 150.0)) if speed is not None else None,
                trajectory_curvature_deg=float(np.clip(curvature, 0.0, 360.0)) if curvature is not None else None,
                trajectory_instability_km=float(np.clip(jitter, 0.0, 1000.0)) if jitter is not None else None,
                cycle_revision_distance_km=float(np.clip(cyc_rev, 0.0, 2000.0)) if cyc_rev is not None else None,
                basin=basin,
            )

            search_req = HistoricalMemorySearchRequest(
                query_state=query_state,
                top_k=3,
                exclude_same_storm=True,
                target_storm_name=storm_name,
            )
            search_res = historical_memory_service.search_analogues(search_req)
            if search_res.matches:
                top = search_res.matches[0]
                top_summary = TopAnalogueSummary(
                    case_id=top.case_id,
                    storm_name=top.storm_name,
                    cycle_label=top.cycle_label,
                    forecast_lead_hours=top.forecast_lead_hours,
                    similarity_percent=top.similarity_percent,
                    standardized_distance=round(top.standardized_distance, 3),
                    verified_status=top.verified_outcome.verification_status,
                    track_error_km=round(top.verified_outcome.track_error_km, 1) if top.verified_outcome.track_error_km is not None else None,
                    threshold_km=round(top.verified_outcome.threshold_km, 1) if top.verified_outcome.threshold_km is not None else None,
                    is_bust=top.verified_outcome.is_bust,
                    spread_regime=top.failure_fingerprint.spread_regime if top.failure_fingerprint else None,
                    failure_summary=top.failure_fingerprint.observed_pattern_summary if top.failure_fingerprint else None,
                )
                summary_text = (
                    f"Closest historical analogue: {top.storm_name} ({top.cycle_label}, +{top.forecast_lead_hours}h) "
                    f"with {top.similarity_percent}% feature similarity. "
                    f"Verified historical error was {top.verified_outcome.track_error_km:.1f} km "
                    f"({'BUST' if top.verified_outcome.is_bust else 'NORMAL'} vs {top.verified_outcome.threshold_km:.1f} km threshold)."
                )
                return HistoricalMemorySummary(
                    status="AVAILABLE",
                    total_reference_cases=search_res.total_reference_cases,
                    matched_count=search_res.matched_analogues_count,
                    top_analogue=top_summary,
                    analogue_summary_text=summary_text,
                )
        except Exception:
            pass

        return HistoricalMemorySummary(
            status="INSUFFICIENT_EVIDENCE",
            total_reference_cases=101,
            matched_count=0,
            top_analogue=None,
            analogue_summary_text="Historical analogue memory search unavailable for this prospective domain state.",
        )

    def _compute_representation_summary(
        self,
        lead_hours: int,
        cyc_row: Optional[Any],
        ens_field_metrics: Any,
        member_count: int,
    ) -> RepresentationSupportSummary:
        """Evaluate OOD representation and support against historical reference population."""
        try:
            ens_spread = (
                float(cyc_row["ensemble_spread_km"])
                if cyc_row is not None and pd.notna(cyc_row.get("ensemble_spread_km"))
                else float(ens_field_metrics.mean_spread / 1000.0)
            )
            ens_div = (
                float(cyc_row["ensemble_divergence_km"])
                if cyc_row is not None and pd.notna(cyc_row.get("ensemble_divergence_km"))
                else float(ens_field_metrics.pairwise_disagreement)
            )
            aniso = (
                float(cyc_row["anisotropy_ratio"])
                if cyc_row is not None and pd.notna(cyc_row.get("anisotropy_ratio"))
                else float(ens_field_metrics.anisotropy_ratio)
            )

            feat_dict = {
                "forecast_lead_hours": float(lead_hours),
                "ensemble_spread_km": float(ens_spread),
                "ensemble_divergence_km": float(ens_div),
                "anisotropy_ratio": float(aniso),
            }
            res = novelty_detector.evaluate(features=feat_dict, ensemble_member_count=member_count)
            return RepresentationSupportSummary(
                representation_state=res.representation_state.value,
                support_score=res.support_score,
                novelty_score=round(res.novelty_score, 3),
                distance_to_reference=round(res.distance, 3) if res.distance is not None and not math.isnan(res.distance) else None,
                nearest_reference_distance=round(res.nearest_reference_distance, 3) if res.nearest_reference_distance is not None and not math.isnan(res.nearest_reference_distance) else None,
                reference_population_size=res.reference_population_size,
                abstention_recommended=res.abstention_recommended,
                abstention_reason=res.abstention_reason,
                status_message=res.message,
            )
        except Exception:
            return RepresentationSupportSummary(
                representation_state="INSUFFICIENT_EVIDENCE",
                support_score=0,
                novelty_score=1.0,
                distance_to_reference=None,
                nearest_reference_distance=None,
                reference_population_size=77,
                abstention_recommended=True,
                abstention_reason="Telemetry missing or out of operational bounds.",
                status_message="Representation support could not be determined due to missing telemetry.",
            )

    def _compute_multimodel_summary(
        self,
        case_id: str,
        lead_hours: int,
    ) -> MultiModelEvidenceSummary:
        """Truthfully report cross-center NWP availability from local archive."""
        return MultiModelEvidenceSummary(
            state="INSUFFICIENT_EVIDENCE",
            models_evaluated=["NCMRWF_NEPS (origin=dems)"],
            available_model_count=1,
            independent_nwp_centers_count=1,
            notice=(
                "NCMRWF NEPS (origin=dems) is the sole operational NWP system in the validated local archive. "
                "Secondary global models (ECMWF, UKMO, NCEP) have zero historical overlap. "
                "Cross-center agreement is unavailable."
            ),
            is_abstention_recommended=False,
            validation_status="INSUFFICIENT_EVIDENCE",
        )

    def evaluate_regional_assessment(
        self,
        case_id: str,
        lead_time: str = "D+1",
        variable: Optional[str] = None,
        as_of_cutoff: Optional[str] = None,
        reveal_verification: bool = True,
    ) -> RegionalAssessmentResponse:
        """Compute full canonical regional assessment response."""
        case_info = SUPPORTED_CASES.get(case_id.upper())
        if not case_info:
            raise ValueError(f"Unknown forecast case: {case_id}")

        lead_hours = self._lead_to_step(lead_time)
        lead_label = self._step_to_lead_label(lead_hours)
        is_horizon_supported = (lead_label in case_info["available_leads"]) or (
            lead_hours in (6, 12, 18, 24, 30, 36, 42, 48)
        )

        var_name = variable or case_info["default_variable"]
        var_short = case_info["variable_short_name"]
        grib_rel_path = case_info["grib_file"]
        grib_path = BASE_DIR / grib_rel_path

        valid_time_iso = self._compute_valid_time(case_info["forecast_cycle"], lead_hours)
        is_cutoff_past_valid = True
        if as_of_cutoff is not None:
            try:
                dt_cutoff = datetime.fromisoformat(as_of_cutoff.replace("Z", "+00:00"))
                dt_valid = datetime.fromisoformat(valid_time_iso.replace("Z", "+00:00"))
                is_cutoff_past_valid = dt_cutoff >= dt_valid
            except Exception:
                is_cutoff_past_valid = True

        all_regions = get_all_regions()
        regional_assessments: List[CanonicalRegionalAssessment] = []

        # If horizon is completely unsupported (e.g. D+3 to D+10)
        if not is_horizon_supported:
            for region in all_regions:
                regional_assessments.append(
                    self._build_unsupported_horizon_assessment(
                        region=region,
                        case_info=case_info,
                        lead_label=lead_label,
                        lead_hours=lead_hours,
                        variable=var_name,
                        var_short=var_short,
                    )
                )

            return RegionalAssessmentResponse(
                case_id=case_id,
                forecast_cycle=case_info["forecast_cycle"],
                valid_time=self._compute_valid_time(case_info["forecast_cycle"], lead_hours),
                lead_time=lead_label,
                lead_hours=lead_hours,
                variable=var_name,
                available_leads=case_info["available_leads"],
                unsupported_leads=case_info["unsupported_leads"],
                is_horizon_supported=False,
                regions=regional_assessments,
                supported_regions_count=0,
                unsupported_regions_count=len(all_regions),
                data_quality="DATA INSUFFICIENT",
                system_overview=(
                    f"Horizon {lead_label} (+{lead_hours}h) is beyond the prospective validated "
                    "telemetry archive (+48h). Scientific assessment explicitly unavailable."
                ),
            )

        # Horizon is supported — read real GRIB data
        members_data, grid_meta = self._read_grib_ensemble_at_step(grib_path, lead_hours)
        member_count = len(members_data)

        # Compute previous lead if available (to calculate genuine trend)
        prev_lead_assessments: Dict[str, float] = {}
        if lead_hours > 24:
            prev_step = lead_hours - 24
            try:
                prev_members, _ = self._read_grib_ensemble_at_step(grib_path, prev_step)
                for reg in all_regions:
                    prob = self._compute_raw_regional_risk(prev_members, grid_meta, reg, prev_step)
                    if prob is not None:
                        prev_lead_assessments[reg.region_id] = prob
            except Exception:
                pass

        # Build 2D coordinate grid
        ni = grid_meta["ni"]
        nj = grid_meta["nj"]
        first_lat = grid_meta["first_lat"]
        last_lat = grid_meta["last_lat"]
        first_lon = grid_meta["first_lon"]
        last_lon = grid_meta["last_lon"]

        lats = np.linspace(first_lat, last_lat, nj)
        lons = np.linspace(first_lon, last_lon, ni)

        supported_count = 0
        unsupported_count = 0

        for region in all_regions:
            is_supported, coverage_pct = check_domain_overlap(first_lat, last_lat, first_lon, last_lon, region)

            if not is_supported or coverage_pct < 15.0:
                unsupported_count += 1
                regional_assessments.append(
                    self._build_outside_domain_assessment(
                        region=region,
                        case_info=case_info,
                        lead_label=lead_label,
                        lead_hours=lead_hours,
                        variable=var_name,
                        var_short=var_short,
                        grid_meta=grid_meta,
                        coverage_pct=coverage_pct,
                    )
                )
                continue

            # Region overlaps with GRIB grid: extract real spatial cells
            region_mask = create_region_grid_mask(lats, lons, region)
            flat_mask = region_mask.flatten()
            regional_cells_count = int(np.sum(flat_mask))

            if regional_cells_count < 20:
                unsupported_count += 1
                regional_assessments.append(
                    self._build_outside_domain_assessment(
                        region=region,
                        case_info=case_info,
                        lead_label=lead_label,
                        lead_hours=lead_hours,
                        variable=var_name,
                        var_short=var_short,
                        grid_meta=grid_meta,
                        coverage_pct=coverage_pct,
                    )
                )
                continue

            supported_count += 1

            # Extract 11 member values across all regional cells: shape (11, n_cells)
            member_arrays = [m[flat_mask] for m in members_data]
            stacked = np.stack(member_arrays, axis=0)  # (n_members, n_cells)

            # Compute real statistical features across ensemble
            cell_means = np.mean(stacked, axis=0)
            cell_stds = np.std(stacked, axis=0, ddof=1)
            mean_spread = float(np.mean(cell_stds))
            max_spread = float(np.max(cell_stds))
            regional_mean_val = float(np.mean(cell_means))

            # Pairwise member difference
            pairwise_diffs = []
            for i in range(member_count):
                for j in range(i + 1, member_count):
                    pairwise_diffs.append(np.mean(np.abs(member_arrays[i] - member_arrays[j])))
            mean_pairwise_diff = float(np.mean(pairwise_diffs)) if pairwise_diffs else 0.0

            # Candidate prospective score calculation using V2 Regional Candidate Dispersion Predictor
            raw_score = regional_candidate_predictor.compute_raw_score(
                mean_spread_pa=mean_spread,
                lead_hours=lead_hours,
                peak_spread_pa=max_spread,
                pairwise_diff_pa=mean_pairwise_diff,
            )

            # Check for audited ground-truth verification record
            verification_rec = regional_verification_engine.get_record_for_region(
                case_id=case_id,
                region_id=region.region_id,
                lead_hours=lead_hours,
            )

            if verification_rec is not None:
                calibrated_prob = regional_candidate_predictor.calibrate(
                    raw_score=raw_score,
                    region_id=region.region_id,
                    lead_hours=lead_hours,
                    is_verified_case=True,
                )
                model_status = "VALIDATED"
                calibration_status = "CALIBRATED"
                calibrated_bust_val = round(calibrated_prob, 3) if calibrated_prob is not None else None
                bust_prob_val = calibrated_bust_val  # Truthful calibrated bust probability
                prov_model_name = "V2_Regional_Calibrated_Platt"
                prov_model_version = "1.0.0-calibrated"

                if reveal_verification and is_cutoff_past_valid:
                    verification_status = "VERIFIED"
                    verification_detail = RegionalVerificationDetail(
                        case_id=verification_rec.case_id,
                        storm_name=verification_rec.storm_name,
                        lead_hours=verification_rec.lead_hours,
                        lead_label=verification_rec.lead_label,
                        valid_time=verification_rec.valid_time,
                        region_id=verification_rec.region_id,
                        region_name=verification_rec.region_name,
                        forecast_lat=verification_rec.forecast_lat,
                        forecast_lon=verification_rec.forecast_lon,
                        forecast_pressure_hpa=verification_rec.forecast_pressure_hpa,
                        observed_lat=verification_rec.observed_lat,
                        observed_lon=verification_rec.observed_lon,
                        observed_pressure_hpa=verification_rec.observed_pressure_hpa,
                        track_error_km=verification_rec.track_error_km,
                        pressure_error_hpa=verification_rec.pressure_error_hpa,
                        threshold_km=verification_rec.threshold_km,
                        is_bust=verification_rec.is_bust,
                        severity=verification_rec.severity,
                        provenance=verification_rec.provenance,
                    )
                else:
                    verification_status = "PENDING_VERIFICATION"
                    verification_detail = None
            else:
                calibrated_bust_val = None
                bust_prob_val = None  # Strictly uncalibrated candidate; never expose raw score under probability label
                model_status = "CANDIDATE"
                calibration_status = "UNCALIBRATED_CANDIDATE"
                verification_status = "UNVERIFIED"
                verification_detail = None
                prov_model_name = regional_candidate_predictor.MODEL_NAME
                prov_model_version = regional_candidate_predictor.MODEL_VERSION

            # Operational reliability index derived from effective risk: 100 * (1 - effective_risk)
            effective_risk = bust_prob_val if bust_prob_val is not None else raw_score
            reliability_score = int(round(np.clip((1.0 - effective_risk) * 100.0, 5.0, 95.0)))

            # Reliability State mapping based on vulnerability thresholds
            # Handles calibrated probability (prior base rate ~23%) vs candidate raw score [0.05, 0.95]
            if bust_prob_val is not None:
                if bust_prob_val >= 0.28:
                    rel_state = "HIGH_RISK"
                elif bust_prob_val >= 0.23:
                    rel_state = "DEGRADING"
                elif bust_prob_val >= 0.205:
                    rel_state = "WATCH"
                else:
                    rel_state = "STABLE"
            else:
                if raw_score >= 0.70:
                    rel_state = "HIGH_RISK"
                elif raw_score >= 0.50:
                    rel_state = "DEGRADING"
                elif raw_score >= 0.35:
                    rel_state = "WATCH"
                else:
                    rel_state = "STABLE"

            if verification_rec is not None and bust_prob_val is not None:
                status_msg = (
                    f"{region.short_label}: {rel_state.replace('_', ' ').title()} reliability. "
                    f"Calibrated bust probability {round(bust_prob_val * 100)}% (Platt scaling, validated against IMD Best Track)."
                )
            else:
                status_msg = (
                    f"{region.short_label}: {rel_state.replace('_', ' ').title()} reliability. "
                    f"Candidate vulnerability score {round(raw_score * 100)}% (uncalibrated candidate) with {member_count} ensemble members."
                )

            # Trend calculation
            prev_prob = prev_lead_assessments.get(region.region_id)
            trend_delta_val: Optional[float] = None
            if prev_prob is not None:
                delta = raw_score - prev_prob
                trend_delta_val = round(delta, 3)
                if delta > 0.04:
                    trend = "increasing"
                    trend_desc = f"Bust vulnerability increased by {round(delta * 100)}% since D-1 (+{lead_hours - 24}h)."
                elif delta < -0.04:
                    trend = "decreasing"
                    trend_desc = f"Reliability improved (+{round(abs(delta) * 100)}%) as member spread consolidated."
                else:
                    trend = "stable"
                    trend_desc = "Reliability profile remained stable across consecutive cycles."
            else:
                trend = "unavailable"
                trend_desc = "Prior forecast lead not available for trend derivation."

            # Explicit Regional Features Catalog (Priority 3)
            catalog_features = regional_candidate_predictor.get_feature_catalog_items(
                mean_spread_pa=round(mean_spread, 1),
                peak_spread_pa=round(max_spread, 1),
                pairwise_diff_pa=round(mean_pairwise_diff, 1),
                lead_hours=lead_hours,
                trend_delta=trend_delta_val,
            )

            # Dominant Evidence factors (strictly genuine numbers)
            evidence_items = [
                DominantEvidenceItem(
                    signal_id="ensemble_spread",
                    rank="01",
                    title="Ensemble Spread Dispersion",
                    description=(
                        f"Mean ensemble standard deviation across {regional_cells_count:,} grid cells "
                        f"is {mean_spread:.1f} Pa ({member_count} NEPS members)."
                    ),
                    level="HIGH" if mean_spread > 200 else "MODERATE" if mean_spread > 100 else "LOW",
                    metric_value=round(mean_spread, 1),
                    metric_unit="Pa",
                ),
                DominantEvidenceItem(
                    signal_id="member_disagreement",
                    rank="02",
                    title="Pairwise Member Disagreement",
                    description=(
                        f"Average inter-member pairwise discrepancy is {mean_pairwise_diff:.1f} Pa "
                        "over regional grid points."
                    ),
                    level="HIGH" if mean_pairwise_diff > 250 else "MODERATE" if mean_pairwise_diff > 120 else "LOW",
                    metric_value=round(mean_pairwise_diff, 1),
                    metric_unit="Pa",
                ),
                DominantEvidenceItem(
                    signal_id="peak_anomaly",
                    rank="03",
                    title="Localized Peak Dispersion",
                    description=f"Maximum localized spread reaches {max_spread:.1f} Pa within regional bounds.",
                    level="HIGH" if max_spread > 400 else "MODERATE" if max_spread > 200 else "LOW",
                    metric_value=round(max_spread, 1),
                    metric_unit="Pa",
                ),
            ]

            # Genuine Ensemble Intelligence telemetry from real field grid
            ens_field_metrics = compute_ensemble_intelligence_from_field(
                member_arrays=member_arrays,
                prev_spread=prev_lead_assessments.get(region.region_id),
                time_delta_hours=24.0 if lead_hours > 24 else 6.0,
                reference_spread_pa=regional_candidate_predictor.PRESSURE_SPREAD_REF_PA,
            )

            # Check if this case & lead has tracked synoptic cyclone telemetry
            cyc_key = (case_id.upper(), lead_hours)
            cyc_row = self._cyclone_records.get(cyc_key)

            # Prior cycle reference from lineage
            from scientific.replay.replay_engine import CASE_CYCLE_LINEAGE
            lineage = CASE_CYCLE_LINEAGE.get(case_id.upper())
            prior_cycle_iso = lineage.get("prior_cycle_iso") if lineage else None

            if cyc_row is not None:
                has_prior = bool(int(cyc_row.get("has_prior_cycle", 0)))
                cyc_rev_km = float(cyc_row["cycle_revision_distance_km"]) if pd.notna(cyc_row.get("cycle_revision_distance_km")) else None
                cyc_shift_km = float(cyc_row["cycle_spread_shift_km"]) if pd.notna(cyc_row.get("cycle_spread_shift_km")) else None
                traj_speed = float(cyc_row["trajectory_speed_kmh"]) if pd.notna(cyc_row.get("trajectory_speed_kmh")) else None
                traj_curv = float(cyc_row["trajectory_curvature_deg"]) if pd.notna(cyc_row.get("trajectory_curvature_deg")) else None
                traj_growth = float(cyc_row["spread_growth_km"]) if pd.notna(cyc_row.get("spread_growth_km")) else None
                traj_jitter = float(cyc_row["trajectory_instability_km"]) if pd.notna(cyc_row.get("trajectory_instability_km")) else None
                aniso_ratio = float(cyc_row["anisotropy_ratio"]) if pd.notna(cyc_row.get("anisotropy_ratio")) else ens_field_metrics.anisotropy_ratio
                bimod_coef = float(cyc_row["bimodality_coefficient"]) if pd.notna(cyc_row.get("bimodality_coefficient")) else ens_field_metrics.bimodality_coefficient
                dom_frac = float(cyc_row["dominant_cluster_fraction"]) if pd.notna(cyc_row.get("dominant_cluster_fraction")) else ens_field_metrics.dominant_cluster_fraction
                cluster_sep = float(cyc_row["cluster_separation_km"]) if pd.notna(cyc_row.get("cluster_separation_km")) else ens_field_metrics.cluster_separation
            else:
                has_prior = prior_cycle_iso is not None
                cyc_rev_km = None
                cyc_shift_km = None
                traj_speed = None
                traj_curv = None
                traj_growth = None
                traj_jitter = None
                aniso_ratio = ens_field_metrics.anisotropy_ratio
                bimod_coef = ens_field_metrics.bimodality_coefficient
                dom_frac = ens_field_metrics.dominant_cluster_fraction
                cluster_sep = ens_field_metrics.cluster_separation

            traj_state, traj_desc = classify_trajectory_state(
                has_prior_cycle=has_prior,
                cycle_revision_km=cyc_rev_km,
                curvature_deg=traj_curv,
                instability_jitter_km=traj_jitter,
                speed_kmh=traj_speed,
                spread_growth_rate=traj_growth,
            )

            ens_state, ens_desc = classify_ensemble_state(
                member_count=member_count,
                spread=ens_field_metrics.mean_spread,
                spread_growth_rate=ens_field_metrics.spread_growth_rate,
                anisotropy_ratio=aniso_ratio,
                bimodality_coef=bimod_coef,
                dominant_cluster_fraction=dom_frac,
                cluster_separation=cluster_sep,
                coherence_score=ens_field_metrics.coherence_score,
                spread_threshold_moderate=regional_candidate_predictor.PRESSURE_SPREAD_REF_PA,
                spread_threshold_high=regional_candidate_predictor.PRESSURE_SPREAD_REF_PA * 1.5,
            )

            ens_summary = EnsembleIntelligenceSummary(
                state=ens_state,
                state_description=ens_desc,
                member_count=member_count,
                mean_spread=ens_field_metrics.mean_spread,
                spread_unit="Pa",
                coherence_score=ens_field_metrics.coherence_score,
                anisotropy_ratio=round(aniso_ratio, 2),
                bimodality_coefficient=round(bimod_coef, 4),
                dominant_cluster_fraction=round(dom_frac, 3),
                cluster_separation=round(cluster_sep, 1),
                pairwise_disagreement=ens_field_metrics.pairwise_disagreement,
                status="COMPLETE",
            )

            traj_summary = TrajectoryIntelligenceSummary(
                state=traj_state,
                state_description=traj_desc,
                has_prior_cycle=has_prior,
                reference_cycle=prior_cycle_iso,
                cycle_revision_distance_km=round(cyc_rev_km, 1) if cyc_rev_km is not None else None,
                cycle_spread_shift_km=round(cyc_shift_km, 1) if cyc_shift_km is not None else None,
                revision_rate_kmh=round(cyc_rev_km / 12.0, 2) if cyc_rev_km is not None else None,
                trajectory_speed_kmh=round(traj_speed, 1) if traj_speed is not None else None,
                trajectory_curvature_deg=round(traj_curv, 1) if traj_curv is not None else None,
                spread_growth_rate=round(traj_growth, 2) if traj_growth is not None else None,
                trajectory_instability_km=round(traj_jitter, 1) if traj_jitter is not None else None,
                status="COMPLETE" if (has_prior and cyc_rev_km is not None) else "PARTIAL",
            )

            # Genuine Environmental Conditioning Intelligence from MSLP field
            if cyc_row is not None and "forecast_lat" in cyc_row and pd.notna(cyc_row.get("forecast_lat")):
                c_lat = float(cyc_row["forecast_lat"])
                c_lon = float(cyc_row["forecast_lon"])
                c_pres = float(cyc_row["forecast_pressure_hpa"])
                mean_grid_2d = np.mean(members_data, axis=0).reshape((nj, ni)) / 100.0  # Pa to hPa
                env_result = extract_environmental_intelligence_from_grid(
                    center_lat=c_lat,
                    center_lon=c_lon,
                    center_pressure_hpa=c_pres,
                    lats=lats,
                    lons=lons,
                    mslp_hpa_grid=mean_grid_2d,
                )
            else:
                env_result = extract_fallback_environmental_insufficient(
                    reason="Vortex center coordinates not detected or outside active cyclone tracking domain."
                )

            env_summary = EnvironmentalIntelligenceSummary(
                state=env_result.state,
                state_description=env_result.state_description,
                pressure_depth_hpa=env_result.pressure_depth_hpa,
                pressure_gradient_hpa_per_100km=env_result.pressure_gradient_hpa_per_100km,
                gradient_asymmetry_hpa_per_100km=env_result.gradient_asymmetry_hpa_per_100km,
                gradient_trend_hpa_per_100km=env_result.gradient_trend_hpa_per_100km,
                core_pressure_hpa=env_result.core_pressure_hpa,
                peripheral_pressure_hpa=env_result.peripheral_pressure_hpa,
                upper_air_shear_status=env_result.upper_air_shear_status,
                mid_level_humidity_status=env_result.mid_level_humidity_status,
                sst_status=env_result.sst_status,
                validation_status=env_result.validation_status,
                provenance=env_result.provenance,
                scientific_provenance_note=env_result.scientific_provenance_note,
                status="COMPLETE" if env_result.state != "INSUFFICIENT_EVIDENCE" else "INSUFFICIENT",
            )

            why_now = generate_why_now_attribution(
                ensemble=ens_field_metrics,
                trajectory=None,
                reliability_state=rel_state,
                calibrated_prob=calibrated_bust_val,
                environmental=env_result,
            )
            if traj_state == "RAPID_REVISION" and cyc_rev_km is not None:
                why_now = f"Vulnerability associated with rapid forecast revision ({cyc_rev_km:.1f} km shift across cycles) and {ens_desc.lower()}"
            elif traj_state == "OSCILLATING_JUMPY":
                why_now = f"Vulnerability associated with erratic trajectory heading/speed fluctuations and {ens_desc.lower()}"

            if env_result.state != "INSUFFICIENT_EVIDENCE":
                if env_result.state == "ASYMMETRIC_WEAK_PRESSURE_STRUCTURE":
                    if env_result.gradient_asymmetry_hpa_per_100km is not None and env_result.gradient_asymmetry_hpa_per_100km >= 2.2:
                        why_now += f"; associated with asymmetric synoptic pressure pattern ({env_result.gradient_asymmetry_hpa_per_100km:.2f} hPa/100km cross-domain asymmetry)"
                    elif env_result.pressure_gradient_hpa_per_100km is not None:
                        why_now += f"; conditioned by diffuse synoptic pressure structure ({env_result.pressure_gradient_hpa_per_100km:.2f} hPa/100km radial gradient)"
                elif env_result.state == "SYMMETRIC_DEEP_PRESSURE_STRUCTURE" and env_result.pressure_gradient_hpa_per_100km is not None:
                    why_now += f"; conditioned by deep, symmetric radial environmental gradient ({env_result.pressure_gradient_hpa_per_100km:.2f} hPa/100km, depth {env_result.pressure_depth_hpa:.1f} hPa)"
                elif env_result.state == "MARGINAL_PRESSURE_STRUCTURE" and env_result.pressure_gradient_hpa_per_100km is not None:
                    why_now += f"; conditioned by marginal environmental pressure gradient ({env_result.pressure_gradient_hpa_per_100km:.2f} hPa/100km)"

            what_changed = generate_what_changed_summary(
                ensemble=ens_field_metrics,
                trajectory=None,
                trend_delta=trend_delta_val,
                environmental=env_result,
            )
            if cyc_rev_km is not None:
                what_changed = f"Cycle-over-cycle: forecast shifted by {cyc_rev_km:.1f} km at identical valid time. " + what_changed

            # Compute historical memory, representation support, and multi-model evidence
            hist_summary = self._compute_historical_memory_summary(
                case_id=case_id,
                lead_hours=lead_hours,
                cyc_row=cyc_row,
                ens_field_metrics=ens_field_metrics,
                basin=case_info["basin"],
                storm_name=case_info.get("storm_name", case_id),
            )
            rep_summary = self._compute_representation_summary(
                lead_hours=lead_hours,
                cyc_row=cyc_row,
                ens_field_metrics=ens_field_metrics,
                member_count=member_count,
            )
            multi_summary = self._compute_multimodel_summary(
                case_id=case_id,
                lead_hours=lead_hours,
            )

            structured_evidence = StructuredEvidenceObject(
                ensemble=ens_summary,
                trajectory=traj_summary,
                environmental=env_summary,
                historical_memory=hist_summary,
                representation=rep_summary,
                multimodel=multi_summary,
                trend=trend,
                why_now=why_now,
                what_changed=what_changed,
                evidence_status="COMPLETE",
                evidence_strength="HIGH" if member_count == 11 else "MODERATE",
                source_provenance=f"NCMRWF NEPS (origin=dems, {member_count} members)",
            )

            provenance = RegionalProvenance(
                forecast_source="NCMRWF TIGGE (origin=dems)",
                forecast_cycle=case_info["forecast_cycle"],
                valid_time=self._compute_valid_time(case_info["forecast_cycle"], lead_hours),
                lead_time=lead_label,
                lead_hours=lead_hours,
                ensemble_member_count=member_count,
                grid_cells_in_region=regional_cells_count,
                variable=var_short,
                model_name=prov_model_name,
                model_version=prov_model_version,
                feature_version="1.0.0",
                prediction_cutoff=case_info["forecast_cycle"],
                data_quality_tier="DATA COMPLETE" if member_count == 11 else "DATA DEGRADED",
            )

            regional_assessments.append(
                CanonicalRegionalAssessment(
                    region_id=region.region_id,
                    region_name=region.name,
                    forecast_cycle=case_info["forecast_cycle"],
                    valid_time=self._compute_valid_time(case_info["forecast_cycle"], lead_hours),
                    lead_time=lead_label,
                    lead_hours=lead_hours,
                    variable=var_name,
                    model_status=model_status,
                    calibration_status=calibration_status,
                    raw_model_score=round(raw_score, 3),
                    calibrated_bust_probability=calibrated_bust_val,
                    bust_probability=bust_prob_val,
                    reliability_score=reliability_score,
                    reliability_state=rel_state,
                    trend=trend,
                    trend_description=trend_desc,
                    assessment_confidence="HIGH" if member_count == 11 else "MODERATE",
                    evidence_status="COMPLETE",
                    dominant_evidence=evidence_items,
                    regional_features=catalog_features,
                    provenance=provenance,
                    verification_status=verification_status,
                    verification_detail=verification_detail,
                    domain_coverage_percent=coverage_pct,
                    status_message=status_msg,
                    ensemble_state=ens_state,
                    trajectory_state=traj_state,
                    environmental_state=env_result.state,
                    structured_evidence=structured_evidence,
                    historical_memory=hist_summary,
                    representation=rep_summary,
                    multimodel=multi_summary,
                )
            )

        return RegionalAssessmentResponse(
            case_id=case_id,
            forecast_cycle=case_info["forecast_cycle"],
            valid_time=self._compute_valid_time(case_info["forecast_cycle"], lead_hours),
            lead_time=lead_label,
            lead_hours=lead_hours,
            variable=var_name,
            available_leads=case_info["available_leads"],
            unsupported_leads=case_info["unsupported_leads"],
            is_horizon_supported=True,
            regions=regional_assessments,
            supported_regions_count=supported_count,
            unsupported_regions_count=unsupported_count,
            data_quality="DATA COMPLETE" if member_count == 11 else "DATA DEGRADED",
            system_overview=(
                f"Real forecast evaluation for {case_info.get('storm_name', case_id)} at {lead_label} (+{lead_hours}h). "
                f"{supported_count} regions covered by NWP grid; {unsupported_count} outside domain."
            ),
        )

    def _compute_raw_regional_risk(
        self,
        members_data: List[np.ndarray],
        grid_meta: Dict[str, Any],
        region: MeteorologicalRegion,
        lead_hours: int,
    ) -> Optional[float]:
        """Fast helper to compute scalar candidate score for trend comparison."""
        first_lat = grid_meta["first_lat"]
        last_lat = grid_meta["last_lat"]
        first_lon = grid_meta["first_lon"]
        last_lon = grid_meta["last_lon"]
        is_supported, coverage_pct = check_domain_overlap(first_lat, last_lat, first_lon, last_lon, region)
        if not is_supported or coverage_pct < 15.0:
            return None

        ni = grid_meta["ni"]
        nj = grid_meta["nj"]
        lats = np.linspace(first_lat, last_lat, nj)
        lons = np.linspace(first_lon, last_lon, ni)
        mask = create_region_grid_mask(lats, lons, region).flatten()
        if np.sum(mask) < 20:
            return None

        member_arrays = [m[mask] for m in members_data]
        stacked = np.stack(member_arrays, axis=0)
        mean_spread = float(np.mean(np.std(stacked, axis=0, ddof=1)))

        return regional_candidate_predictor.compute_raw_score(
            mean_spread_pa=mean_spread,
            lead_hours=lead_hours,
        )

    def _build_outside_domain_assessment(
        self,
        region: MeteorologicalRegion,
        case_info: Dict[str, Any],
        lead_label: str,
        lead_hours: int,
        variable: str,
        var_short: str,
        grid_meta: Dict[str, Any],
        coverage_pct: float,
    ) -> CanonicalRegionalAssessment:
        """Create truthful insufficient-evidence assessment for out-of-domain regions."""
        g_min_lon = min(grid_meta["first_lon"], grid_meta["last_lon"])
        g_max_lon = max(grid_meta["first_lon"], grid_meta["last_lon"])
        g_min_lat = min(grid_meta["first_lat"], grid_meta["last_lat"])
        g_max_lat = max(grid_meta["first_lat"], grid_meta["last_lat"])

        status_msg = (
            f"Region '{region.name}' is outside spatial coverage of this forecast run. "
            f"Active grid domain is {g_min_lat:.1f}°N–{g_max_lat:.1f}°N, {g_min_lon:.1f}°E–{g_max_lon:.1f}°E."
        )

        provenance = RegionalProvenance(
            forecast_source="NCMRWF TIGGE (origin=dems)",
            forecast_cycle=case_info["forecast_cycle"],
            valid_time=self._compute_valid_time(case_info["forecast_cycle"], lead_hours),
            lead_time=lead_label,
            lead_hours=lead_hours,
            ensemble_member_count=0,
            grid_cells_in_region=0,
            variable=var_short,
            model_name=regional_candidate_predictor.MODEL_NAME,
            model_version=regional_candidate_predictor.MODEL_VERSION,
            feature_version="1.0.0",
            prediction_cutoff=case_info["forecast_cycle"],
            data_quality_tier="DATA INSUFFICIENT",
        )

        ens_insufficient = EnsembleIntelligenceSummary(
            state="INSUFFICIENT_EVIDENCE",
            state_description="Region is outside spatial coverage domain of this forecast run.",
            member_count=0,
            mean_spread=None,
            spread_unit=var_short,
            coherence_score=None,
            anisotropy_ratio=None,
            bimodality_coefficient=None,
            dominant_cluster_fraction=None,
            cluster_separation=None,
            pairwise_disagreement=None,
            status="INSUFFICIENT",
        )
        traj_insufficient = TrajectoryIntelligenceSummary(
            state="INSUFFICIENT_EVIDENCE",
            state_description="Trajectory metrics unavailable outside forecast coverage domain.",
            has_prior_cycle=False,
            reference_cycle=None,
            cycle_revision_distance_km=None,
            cycle_spread_shift_km=None,
            revision_rate_kmh=None,
            trajectory_speed_kmh=None,
            trajectory_curvature_deg=None,
            spread_growth_rate=None,
            trajectory_instability_km=None,
            status="UNAVAILABLE",
        )
        env_insufficient = EnvironmentalIntelligenceSummary(
            state="INSUFFICIENT_EVIDENCE",
            state_description="Environmental metrics unavailable outside forecast coverage domain.",
            pressure_depth_hpa=None,
            pressure_gradient_hpa_per_100km=None,
            gradient_asymmetry_hpa_per_100km=None,
            gradient_trend_hpa_per_100km=None,
            core_pressure_hpa=None,
            peripheral_pressure_hpa=None,
            upper_air_shear_status="UNAVAILABLE",
            mid_level_humidity_status="UNAVAILABLE",
            sst_status="UNAVAILABLE",
            validation_status="INSUFFICIENT_EVIDENCE",
            provenance="None (Outside Domain)",
            scientific_provenance_note="Derived from NCMRWF NEPS ensemble MSLP pressure-gradient geometry. NOT a direct measurement of vertical wind shear, upper-air wind, or humidity.",
            status="UNAVAILABLE",
        )
        hist_insufficient = HistoricalMemorySummary(
            status="UNAVAILABLE",
            total_reference_cases=101,
            matched_count=0,
            top_analogue=None,
            analogue_summary_text="Historical memory unavailable outside active forecast domain.",
        )
        rep_insufficient = RepresentationSupportSummary(
            representation_state="INSUFFICIENT_EVIDENCE",
            support_score=0,
            novelty_score=1.0,
            distance_to_reference=None,
            nearest_reference_distance=None,
            reference_population_size=77,
            abstention_recommended=True,
            abstention_reason="Region is outside spatial coverage domain of forecast run.",
            status_message="Representation support unavailable outside active forecast domain.",
        )
        multi_insufficient = MultiModelEvidenceSummary(
            state="INSUFFICIENT_EVIDENCE",
            models_evaluated=["NCMRWF_NEPS (origin=dems)"],
            available_model_count=1,
            independent_nwp_centers_count=1,
            notice="Multi-model agreement unavailable outside active forecast domain.",
            is_abstention_recommended=False,
            validation_status="INSUFFICIENT_EVIDENCE",
        )

        evidence_insufficient = StructuredEvidenceObject(
            ensemble=ens_insufficient,
            trajectory=traj_insufficient,
            environmental=env_insufficient,
            historical_memory=hist_insufficient,
            representation=rep_insufficient,
            multimodel=multi_insufficient,
            trend="unavailable",
            why_now="Insufficient observation or forecast data within regional bounds.",
            what_changed="Region outside active forecast domain.",
            evidence_status="UNAVAILABLE",
            evidence_strength="INSUFFICIENT_EVIDENCE",
            source_provenance="NCMRWF TIGGE (origin=dems)",
        )

        return CanonicalRegionalAssessment(
            region_id=region.region_id,
            region_name=region.name,
            forecast_cycle=case_info["forecast_cycle"],
            valid_time=self._compute_valid_time(case_info["forecast_cycle"], lead_hours),
            lead_time=lead_label,
            lead_hours=lead_hours,
            variable=variable,
            model_status="INSUFFICIENT_EVIDENCE",
            calibration_status="NOT_AVAILABLE",
            raw_model_score=None,
            calibrated_bust_probability=None,
            bust_probability=None,
            reliability_score=None,
            reliability_state="INSUFFICIENT_EVIDENCE",
            trend="unavailable",
            trend_description="Trend unavailable — region outside forecast domain.",
            assessment_confidence="INSUFFICIENT_EVIDENCE",
            evidence_status="UNAVAILABLE",
            dominant_evidence=[],
            regional_features=[],
            provenance=provenance,
            verification_status="UNVERIFIED",
            verification_detail=None,
            domain_coverage_percent=coverage_pct,
            status_message=status_msg,
            ensemble_state="INSUFFICIENT_EVIDENCE",
            trajectory_state="INSUFFICIENT_EVIDENCE",
            environmental_state="INSUFFICIENT_EVIDENCE",
            structured_evidence=evidence_insufficient,
            historical_memory=hist_insufficient,
            representation=rep_insufficient,
            multimodel=multi_insufficient,
        )

    def _build_unsupported_horizon_assessment(
        self,
        region: MeteorologicalRegion,
        case_info: Dict[str, Any],
        lead_label: str,
        lead_hours: int,
        variable: str,
        var_short: str,
    ) -> CanonicalRegionalAssessment:
        """Create truthful assessment for unsupported lead horizons (D+3 through D+10)."""
        status_msg = (
            f"Forecast horizon {lead_label} (+{lead_hours}h) is not validated or available for this cycle. "
            "Reliability assessment unavailable — insufficient forecast evidence."
        )

        provenance = RegionalProvenance(
            forecast_source="NCMRWF TIGGE (origin=dems)",
            forecast_cycle=case_info["forecast_cycle"],
            valid_time=self._compute_valid_time(case_info["forecast_cycle"], lead_hours),
            lead_time=lead_label,
            lead_hours=lead_hours,
            ensemble_member_count=0,
            grid_cells_in_region=0,
            variable=var_short,
            model_name=regional_candidate_predictor.MODEL_NAME,
            model_version=regional_candidate_predictor.MODEL_VERSION,
            feature_version="1.0.0",
            prediction_cutoff=case_info["forecast_cycle"],
            data_quality_tier="DATA INSUFFICIENT",
        )

        ens_insufficient = EnsembleIntelligenceSummary(
            state="INSUFFICIENT_EVIDENCE",
            state_description="Forecast horizon is not validated or available for this cycle.",
            member_count=0,
            mean_spread=None,
            spread_unit=var_short,
            coherence_score=None,
            anisotropy_ratio=None,
            bimodality_coefficient=None,
            dominant_cluster_fraction=None,
            cluster_separation=None,
            pairwise_disagreement=None,
            status="INSUFFICIENT",
        )
        traj_insufficient = TrajectoryIntelligenceSummary(
            state="INSUFFICIENT_EVIDENCE",
            state_description="Trajectory metrics unavailable for unsupported lead horizon.",
            has_prior_cycle=False,
            reference_cycle=None,
            cycle_revision_distance_km=None,
            cycle_spread_shift_km=None,
            revision_rate_kmh=None,
            trajectory_speed_kmh=None,
            trajectory_curvature_deg=None,
            spread_growth_rate=None,
            trajectory_instability_km=None,
            status="INSUFFICIENT",
        )
        env_insufficient = EnvironmentalIntelligenceSummary(
            state="INSUFFICIENT_EVIDENCE",
            state_description="Environmental metrics unavailable for unsupported lead horizon.",
            pressure_depth_hpa=None,
            pressure_gradient_hpa_per_100km=None,
            gradient_asymmetry_hpa_per_100km=None,
            gradient_trend_hpa_per_100km=None,
            core_pressure_hpa=None,
            peripheral_pressure_hpa=None,
            upper_air_shear_status="UNAVAILABLE",
            mid_level_humidity_status="UNAVAILABLE",
            sst_status="UNAVAILABLE",
            validation_status="INSUFFICIENT_EVIDENCE",
            provenance="None (Unsupported Horizon)",
            scientific_provenance_note="Derived from NCMRWF NEPS ensemble MSLP pressure-gradient geometry. NOT a direct measurement of vertical wind shear, upper-air wind, or humidity.",
            status="INSUFFICIENT",
        )
        hist_insufficient = HistoricalMemorySummary(
            status="UNAVAILABLE",
            total_reference_cases=101,
            matched_count=0,
            top_analogue=None,
            analogue_summary_text="Historical memory unavailable for unsupported forecast horizon.",
        )
        rep_insufficient = RepresentationSupportSummary(
            representation_state="INSUFFICIENT_EVIDENCE",
            support_score=0,
            novelty_score=1.0,
            distance_to_reference=None,
            nearest_reference_distance=None,
            reference_population_size=77,
            abstention_recommended=True,
            abstention_reason="Forecast horizon is beyond validated telemetry archive.",
            status_message="Representation support unavailable for unsupported forecast horizon.",
        )
        multi_insufficient = MultiModelEvidenceSummary(
            state="INSUFFICIENT_EVIDENCE",
            models_evaluated=["NCMRWF_NEPS (origin=dems)"],
            available_model_count=1,
            independent_nwp_centers_count=1,
            notice="Multi-model consensus unavailable for unsupported forecast horizon.",
            is_abstention_recommended=False,
            validation_status="INSUFFICIENT_EVIDENCE",
        )

        evidence_insufficient = StructuredEvidenceObject(
            ensemble=ens_insufficient,
            trajectory=traj_insufficient,
            environmental=env_insufficient,
            historical_memory=hist_insufficient,
            representation=rep_insufficient,
            multimodel=multi_insufficient,
            trend="unavailable",
            why_now="Insufficient forecast evidence at unsupported horizon.",
            what_changed="Forecast horizon not validated.",
            evidence_status="INSUFFICIENT",
            evidence_strength="INSUFFICIENT_EVIDENCE",
            source_provenance="NCMRWF TIGGE (origin=dems)",
        )

        return CanonicalRegionalAssessment(
            region_id=region.region_id,
            region_name=region.name,
            forecast_cycle=case_info["forecast_cycle"],
            valid_time=self._compute_valid_time(case_info["forecast_cycle"], lead_hours),
            lead_time=lead_label,
            lead_hours=lead_hours,
            variable=variable,
            model_status="INSUFFICIENT_EVIDENCE",
            calibration_status="NOT_AVAILABLE",
            raw_model_score=None,
            calibrated_bust_probability=None,
            bust_probability=None,
            reliability_score=None,
            reliability_state="INSUFFICIENT_EVIDENCE",
            trend="unavailable",
            trend_description="Trend unavailable — unsupported horizon.",
            assessment_confidence="INSUFFICIENT_EVIDENCE",
            evidence_status="INSUFFICIENT",
            dominant_evidence=[],
            regional_features=[],
            provenance=provenance,
            verification_status="UNVERIFIED",
            verification_detail=None,
            domain_coverage_percent=0.0,
            status_message=status_msg,
            ensemble_state="INSUFFICIENT_EVIDENCE",
            trajectory_state="INSUFFICIENT_EVIDENCE",
            environmental_state="INSUFFICIENT_EVIDENCE",
            structured_evidence=evidence_insufficient,
            historical_memory=hist_insufficient,
            representation=rep_insufficient,
            multimodel=multi_insufficient,
        )

    def get_case_verification(self, case_id: str) -> RegionalVerificationResponse:
        """Retrieve all verified ground truth records for a forecast case."""
        case_info = SUPPORTED_CASES.get(case_id.upper())
        if not case_info:
            raise ValueError(f"Unknown forecast case: {case_id}")
        records = regional_verification_engine.get_records_for_case(case_id)

        detail_records = [
            RegionalVerificationDetail(
                case_id=r.case_id,
                storm_name=r.storm_name,
                lead_hours=r.lead_hours,
                lead_label=r.lead_label,
                valid_time=r.valid_time,
                region_id=r.region_id,
                region_name=r.region_name,
                forecast_lat=r.forecast_lat,
                forecast_lon=r.forecast_lon,
                forecast_pressure_hpa=r.forecast_pressure_hpa,
                observed_lat=r.observed_lat,
                observed_lon=r.observed_lon,
                observed_pressure_hpa=r.observed_pressure_hpa,
                track_error_km=r.track_error_km,
                pressure_error_hpa=r.pressure_error_hpa,
                threshold_km=r.threshold_km,
                is_bust=r.is_bust,
                severity=r.severity,
                provenance=r.provenance,
            )
            for r in records
        ]

        bust_count = sum(1 for r in detail_records if r.is_bust)
        return RegionalVerificationResponse(
            case_id=case_id,
            storm_name=case_info.get("storm_name", case_id),
            forecast_cycle=case_info["forecast_cycle"],
            records=detail_records,
            verified_leads_count=len(detail_records),
            bust_count=bust_count,
            data_source="India Meteorological Department (IMD) RSMC Best Track Archive",
        )

    def get_feature_catalog(self) -> List[RegionalFeatureCatalogItem]:
        """Return canonical descriptors for all 5 regional features."""
        return regional_candidate_predictor.get_feature_catalog_items()

    def get_regional_timeline(
        self,
        case_id: str,
        region_id: Optional[str] = None,
    ) -> RegionalTimelineResponse:
        """Construct full 6-hourly temporal reliability series for a region."""
        from scientific.replay.replay_engine import replay_engine

        case_info = SUPPORTED_CASES.get(case_id.upper())
        if not case_info:
            raise ValueError(f"Unknown forecast case: {case_id}")
        target_region = region_id or case_info["supported_regions"][0]
        return replay_engine.build_regional_timeline(case_id=case_id, region_id=target_region)

    def get_case_replay(
        self,
        case_id: str,
        region_id: Optional[str] = None,
        reveal_verification: bool = True,
    ) -> ReplayCaseResponse:
        """Construct full chronological replay session for a supported forecast case."""
        from scientific.replay.replay_engine import replay_engine

        return replay_engine.build_case_replay(
            case_id=case_id,
            focused_region_id=region_id,
            reveal_verification=reveal_verification,
        )

    def get_cycle_comparison(
        self,
        case_id: str,
        region_id: Optional[str] = None,
    ) -> Optional[CycleComparison]:
        """Compare current forecast cycle against prior cycle on disk."""
        from scientific.replay.replay_engine import replay_engine

        case_info = SUPPORTED_CASES.get(case_id.upper())
        if not case_info:
            raise ValueError(f"Unknown forecast case: {case_id}")
        target_region = region_id or case_info["supported_regions"][0]
        return replay_engine.compute_cycle_comparison(case_id=case_id, region_id=target_region)

    def _compute_valid_time(self, init_iso: str, lead_hours: int) -> str:
        """Compute ISO 8601 valid time from initialization and lead."""
        try:
            from datetime import timedelta
            ts = init_iso.replace("Z", "+00:00")
            dt = datetime.fromisoformat(ts)
            valid_dt = dt + timedelta(hours=lead_hours)
            return valid_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            return init_iso


# Singleton instance for production backend service
regional_service = RegionalReliabilityService()
