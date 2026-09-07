"""ForecastGuard Production Model Configuration & Metadata.

Deterministic weights, scaling parameters, and versioned configuration for
the primary machine baseline (M1_SpreadOnly) and operational reference (M0_Climatology).
"""

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ModelMetadata:
    """Versioned model metadata contract."""

    model_name: str
    model_version: str
    scientific_status: str
    training_dataset_id: str
    supported_forecast_domain: str
    supported_lead_range_hours: List[int]
    feature_schema: List[str]
    creation_timestamp_utc: str
    description: str


# Production Model Metadata Objects
M1_SPREAD_ONLY_METADATA = ModelMetadata(
    model_name="M1_SpreadOnly",
    model_version="1.0.0",
    scientific_status="PRIMARY_MACHINE_BASELINE",
    training_dataset_id="EXPANDED_CYCLONE_13CYCLES_101LEADS_TRAIN67",
    supported_forecast_domain="North Indian Ocean (Bay of Bengal & Arabian Sea: 5°N–30°N, 48°E–100°E)",
    supported_lead_range_hours=[6, 48],
    feature_schema=["forecast_lead_hours", "ensemble_spread_km"],
    creation_timestamp_utc="2026-09-07T10:15:05Z",
    description=(
        "Primary machine baseline predicting prospective forecast bust probability "
        "from forecast lead hours and scalar NCMRWF NEPS ensemble track spread. "
        "Trained on 67 prospective leads across 5 historical cyclones (MOCHA, BIPARJOY, "
        "TEJ, HAMOON, MIDHILI) and validated chronologically on unseen held-out storm MICHAUNG."
    ),
)

M0_CLIMATOLOGY_METADATA = ModelMetadata(
    model_name="M0_Climatology",
    model_version="1.0.0",
    scientific_status="OPERATIONAL_REFERENCE",
    training_dataset_id="EXPANDED_CYCLONE_13CYCLES_101LEADS_TRAIN67",
    supported_forecast_domain="North Indian Ocean (Bay of Bengal & Arabian Sea: 5°N–30°N, 48°E–100°E)",
    supported_lead_range_hours=[6, 48],
    feature_schema=["forecast_lead_hours"],
    creation_timestamp_utc="2026-09-07T10:15:05Z",
    description=(
        "Operational reference baseline modeling climatological bust vulnerability "
        "as a function of forecast lead time alone, without ensemble telemetry."
    ),
)

# Deterministic fitted parameters from audited dataset (zero retraining at startup)
M1_PARAMETERS = {
    "scaler_mean": [23.28358208955224, 94.17179104477611],
    "scaler_scale": [11.752174737010657, 26.38666804512275],
    "coefficients": [0.524702653769871, 0.003633292256724578],
    "intercept": 0.22472678563358695,
    "base_rate": 0.5522388059701493,
}

M0_PARAMETERS = {
    "scaler_mean": [23.28358208955224],
    "scaler_scale": [11.752174737010655],
    "coefficients": [0.5265386136996157],
    "intercept": 0.22489312938832492,
    "base_rate": 0.5522388059701493,
}

# Catalog of research candidates and diagnostic components
RESEARCH_MODELS_CATALOG = [
    {
        "model_id": "M0_Climatology",
        "scientific_status": "OPERATIONAL_REFERENCE",
        "description": "Climatological lead-risk curve baseline.",
        "held_out_brier": 0.3295,
        "loocv_brier": 0.3086,
    },
    {
        "model_id": "M1_SpreadOnly",
        "scientific_status": "PRIMARY_MACHINE_BASELINE",
        "description": "Established operational baseline: scalar ensemble spread.",
        "held_out_brier": 0.3302,
        "loocv_brier": 0.3213,
    },
    {
        "model_id": "M2_Spread_Trajectory",
        "scientific_status": "PROVISIONAL_CANDIDATE",
        "description": "Provisional candidate adding trajectory speed and curvature.",
        "held_out_brier": 0.2677,
        "loocv_brier": 0.2774,
    },
    {
        "model_id": "M3_Spread_Geometry",
        "scientific_status": "PROVISIONAL_CANDIDATE",
        "description": "Provisional candidate adding dispersion anisotropy and bimodality.",
        "held_out_brier": 0.1850,
        "loocv_brier": 0.2887,
    },
    {
        "model_id": "M4_Spread_CycleInstability",
        "scientific_status": "DIAGNOSTIC_TELEMETRY",
        "description": "Cycle-to-cycle revision shift telemetry (Pearson r = +0.4482 empirical association).",
        "held_out_brier": 0.5186,
        "loocv_brier": 0.3616,
    },
    {
        "model_id": "M5_Spread_FalseConfidence",
        "scientific_status": "DIAGNOSTIC_OVERLAY",
        "description": "Leakage-free diagnostic overlay detecting subtle ensemble divergence and contradiction.",
        "held_out_brier": 0.3619,
        "loocv_brier": 0.2956,
    },
    {
        "model_id": "M6_CombinedCandidate",
        "scientific_status": "PROVISIONAL_CANDIDATE",
        "description": "Provisional candidate combining spread, geometry, and trajectory features.",
        "held_out_brier": 0.1798,
        "loocv_brier": 0.2728,
    },
]
