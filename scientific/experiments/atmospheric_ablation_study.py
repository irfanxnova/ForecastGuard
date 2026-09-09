"""ForecastGuard V2 — Attempt 5 Atmospheric Conditioning Ablation Study.

Evaluates the incremental predictive value of surface environmental pressure kinematics
(Environmental Pressure Depth, Radial Environmental Gradient, Outer Directional Asymmetry)
over the established M6 baseline (A0) on the held-out test cyclone MICHAUNG.

Invariants enforced:
1. Strict chronological train/test split: Train on pre-December 2023 cases
   (MOCHA, BIPARJOY, TEJ, HAMOON, MIDHILI), evaluate strictly on held-out MICHAUNG.
2. Anti-leakage: Features for lead L use strictly forecast fields valid <= L.
3. Scientific Claim Firewall: Upper-air fields are logged as UNAVAILABLE;
   surface environmental features are classified as EXPERIMENTAL. Baseline A0
   is retained for production scoring unless Rule 11 criteria are met.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Ensure project root is on sys.path
base_dir = Path(__file__).resolve().parent.parent.parent
if str(base_dir) not in sys.path:
    sys.path.insert(0, str(base_dir))

import eccodes
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from scientific.features.environmental_intelligence import (
    ATMOSPHERIC_VARIABLE_AUDIT,
    compute_environmental_pressure_depth,
    compute_pressure_gradient_asymmetry,
    compute_radial_pressure_gradient,
)
from scientific.validation.cyclone import haversine_distance


@dataclass(frozen=True)
class AblationMetrics:
    """Evaluation metrics on held-out test events."""

    model_id: str
    model_name: str
    feature_count: int
    features_list: List[str]
    brier_score: float
    ece: float
    accuracy: float
    earliest_warning_lead_hours: Optional[int]
    delta_brier_vs_a0: float
    delta_ece_vs_a0: float
    status: str  # RETAINED_BASELINE, EXPERIMENTAL, KILLED
    promotion_verdict: str
    scientific_justification: str
    probabilities: List[float]
    predictions: List[int]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compute_brier_score(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    return float(np.mean((y_prob - y_true) ** 2))


def compute_ece(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 5) -> float:
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = len(y_true)
    if n == 0:
        return 0.0
    for i in range(n_bins):
        bin_mask = (y_prob >= bins[i]) & (y_prob < bins[i + 1]) if i < n_bins - 1 else (y_prob >= bins[i]) & (y_prob <= bins[i + 1])
        if np.any(bin_mask):
            bin_conf = float(np.mean(y_prob[bin_mask]))
            bin_acc = float(np.mean(y_true[bin_mask]))
            bin_weight = float(np.sum(bin_mask)) / n
            ece += bin_weight * abs(bin_acc - bin_conf)
    return float(ece)


def extract_grib_mean_mslp(grib_path: Path) -> Dict[int, Tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Extract ensemble-mean MSLP grid and coordinates for each lead from GRIB."""
    grids_by_lead: Dict[int, List[np.ndarray]] = {}
    lats = None
    lons = None

    with open(grib_path, "rb") as f:
        while True:
            handle = eccodes.codes_grib_new_from_file(f)
            if handle is None:
                break
            short_name = eccodes.codes_get(handle, "shortName")
            if short_name.lower() != "msl":
                eccodes.codes_release(handle)
                continue

            step = int(eccodes.codes_get(handle, "step"))
            if lats is None:
                ni = int(eccodes.codes_get(handle, "Ni"))
                nj = int(eccodes.codes_get(handle, "Nj"))
                first_lat = float(eccodes.codes_get(handle, "latitudeOfFirstGridPointInDegrees"))
                last_lat = float(eccodes.codes_get(handle, "latitudeOfLastGridPointInDegrees"))
                first_lon = float(eccodes.codes_get(handle, "longitudeOfFirstGridPointInDegrees"))
                last_lon = float(eccodes.codes_get(handle, "longitudeOfLastGridPointInDegrees"))
                lats = np.linspace(first_lat, last_lat, nj)
                lons = np.linspace(first_lon, last_lon, ni)

            raw_vals = eccodes.codes_get_values(handle)
            vals_2d = np.asarray(raw_vals, dtype=np.float64).reshape((len(lats), len(lons))) / 100.0  # Pa to hPa

            if step not in grids_by_lead:
                grids_by_lead[step] = []
            grids_by_lead[step].append(vals_2d)
            eccodes.codes_release(handle)

    mean_grids_by_lead = {}
    for step, grids in grids_by_lead.items():
        mean_grids_by_lead[step] = (lats, lons, np.mean(grids, axis=0))
    return mean_grids_by_lead


def run_atmospheric_ablation() -> Dict[str, Any]:
    """Execute chronological ablation ladder A0 -> A1 -> A2."""
    data_dir = base_dir / "data" / "validation"
    dataset_path = data_dir / "expanded_cyclone_verified_dataset.json"

    print("=" * 80)
    print("FORECASTGUARD V2 — ATTEMPT 5 ATMOSPHERIC CONDITIONING ABLATION STUDY")
    print("=" * 80)

    # 1. Load authoritative prospective dataset
    with open(dataset_path, "r", encoding="utf-8") as f:
        records_data = json.load(f)["records"]

    # Filter records with prospective ground-truth target
    records = [r for r in records_data if r["prospective_bust_within24h"] is not None]
    print(f"Loaded {len(records)} prospective records across all active cyclone cycles.")

    # 2. Cycle-to-GRIB path mapping
    cycle_gribs = {
        "MOCHA_00Z": data_dir / "test_tigge_mocha_msl.grib",
        "MOCHA_12Z": data_dir / "test_tigge_mocha_12z_msl.grib",
        "BIPARJOY_00Z": data_dir / "test_tigge_biparjoy_msl.grib",
        "BIPARJOY_12Z": data_dir / "test_tigge_biparjoy_12z_msl.grib",
        "BIPARJOY_0608_00Z": data_dir / "test_tigge_biparjoy_0608_00z_msl.grib",
        "TEJ_00Z": data_dir / "test_tigge_tej_00z_msl.grib",
        "TEJ_12Z": data_dir / "test_tigge_tej_12z_msl.grib",
        "HAMOON_00Z": data_dir / "test_tigge_hamoon_00z_msl.grib",
        "HAMOON_12Z": data_dir / "test_tigge_hamoon_12z_msl.grib",
        "MIDHILI_00Z": data_dir / "test_tigge_midhili_00z_msl.grib",
        "MICHAUNG_00Z": data_dir / "test_tigge_michaung_msl.grib",
        "MICHAUNG_12Z": data_dir / "test_tigge_michaung_12z_msl.grib",
        "MICHAUNG_1202_00Z": data_dir / "test_tigge_michaung_1202_00z_msl.grib",
    }

    # 3. Pre-extract MSLP grids for all cycles
    print("\n--- Extracting verified MSLP grids for all cycles ---")
    grib_cache: Dict[str, Dict[int, Tuple[np.ndarray, np.ndarray, np.ndarray]]] = {}
    for c_label, g_path in cycle_gribs.items():
        if g_path.exists():
            grib_cache[c_label] = extract_grib_mean_mslp(g_path)
            print(f"  Ingested {c_label}: {len(grib_cache[c_label])} leads from {g_path.name}")

    # 4. Compute real environmental features for every record
    print("\n--- Computing environmental pressure conditioning features ---")
    enriched_records = []
    for r in records:
        c_label = r["cycle_label"]
        lead = int(r["forecast_lead_hours"])
        center_lat = float(r["forecast_lat"])
        center_lon = float(r["forecast_lon"])
        center_pres = float(r["forecast_pressure_hpa"])

        if c_label in grib_cache and lead in grib_cache[c_label]:
            lats, lons, mslp_grid = grib_cache[c_label][lead]
            periph_pres, depth = compute_environmental_pressure_depth(
                center_lat=center_lat,
                center_lon=center_lon,
                center_pressure_hpa=center_pres,
                lats=lats,
                lons=lons,
                mslp_hpa_grid=mslp_grid,
                inner_radius_km=300.0,
                outer_radius_km=600.0,
            )
            grad = compute_radial_pressure_gradient(depth, mean_annulus_radius_km=450.0)
            asym = compute_pressure_gradient_asymmetry(
                center_lat=center_lat,
                center_lon=center_lon,
                lats=lats,
                lons=lons,
                mslp_hpa_grid=mslp_grid,
                inner_radius_km=300.0,
                outer_radius_km=600.0,
            )
        else:
            depth = 0.0
            grad = 0.0
            asym = 0.0

        r_enriched = dict(r)
        r_enriched["pressure_depth_hpa"] = round(depth, 2)
        r_enriched["pressure_gradient_hpa_per_100km"] = round(grad, 3)
        r_enriched["gradient_asymmetry_hpa_per_100km"] = round(asym, 3)
        enriched_records.append(r_enriched)

    # 5. Split train (pre-December 2023) vs test (MICHAUNG, December 2023)
    train_records = [r for r in enriched_records if r["storm_name"] != "MICHAUNG"]
    test_records = [r for r in enriched_records if r["storm_name"] == "MICHAUNG"]

    print(f"\nChronological Split: {len(train_records)} training records, {len(test_records)} held-out test records.")

    y_train = np.array([int(r["prospective_bust_within24h"]) for r in train_records])
    y_test = np.array([int(r["prospective_bust_within24h"]) for r in test_records])

    # 6. Define Feature Sets for A0, A1, A2
    feature_sets = {
        "A0_Baseline_M6": [
            "forecast_lead_hours",
            "ensemble_spread_km",
            "spread_growth_km",
            "anisotropy_ratio",
            "bimodality_coefficient",
            "reliability_contradiction_index",
            "trajectory_speed_kmh",
        ],
        "A1_M6_Plus_EnvironmentalPressure": [
            "forecast_lead_hours",
            "ensemble_spread_km",
            "spread_growth_km",
            "anisotropy_ratio",
            "bimodality_coefficient",
            "reliability_contradiction_index",
            "trajectory_speed_kmh",
            "pressure_depth_hpa",
            "pressure_gradient_hpa_per_100km",
            "gradient_asymmetry_hpa_per_100km",
        ],
        "A2_EnvironmentalPressure_Interaction": [
            "forecast_lead_hours",
            "ensemble_spread_km",
            "spread_growth_km",
            "anisotropy_ratio",
            "bimodality_coefficient",
            "reliability_contradiction_index",
            "trajectory_speed_kmh",
            "pressure_depth_hpa",
            "pressure_gradient_hpa_per_100km",
            "gradient_asymmetry_hpa_per_100km",
        ],
    }

    def build_matrix(recs: List[Dict[str, Any]], cols: List[str], is_a2: bool = False) -> np.ndarray:
        mat = np.zeros((len(recs), len(cols) + (2 if is_a2 else 0)), dtype=np.float64)
        for i, r in enumerate(recs):
            row = [float(r.get(c, 0.0) or 0.0) for c in cols]
            if is_a2:
                # Interaction terms: spread * asymmetry, gradient * speed
                spread = float(r.get("ensemble_spread_km", 0.0) or 0.0)
                asym = float(r.get("gradient_asymmetry_hpa_per_100km", 0.0) or 0.0)
                grad = float(r.get("pressure_gradient_hpa_per_100km", 0.0) or 0.0)
                speed = float(r.get("trajectory_speed_kmh", 0.0) or 0.0)
                row.append(spread * asym)
                row.append(grad * speed)
            mat[i, :] = row
        return mat

    results: Dict[str, AblationMetrics] = {}
    base_brier = None
    base_ece = None

    for model_id, f_cols in feature_sets.items():
        is_a2 = model_id == "A2_EnvironmentalPressure_Interaction"
        X_tr = build_matrix(train_records, f_cols, is_a2=is_a2)
        X_te = build_matrix(test_records, f_cols, is_a2=is_a2)

        scaler = StandardScaler()
        X_tr_s = scaler.fit_transform(X_tr)
        X_te_s = scaler.transform(X_te)

        clf = LogisticRegression(C=1.0, solver="lbfgs", max_iter=500, random_state=42)
        clf.fit(X_tr_s, y_train)

        probs = clf.predict_proba(X_te_s)[:, 1]
        preds = (probs >= 0.5).astype(int)

        brier = compute_brier_score(y_test, probs)
        ece = compute_ece(y_test, probs)
        acc = float(np.mean(preds == y_test))

        if model_id == "A0_Baseline_M6":
            base_brier = brier
            base_ece = ece
            delta_brier = 0.0
            delta_ece = 0.0
            status = "RETAINED_BASELINE"
            verdict = "RETAINED AS PRODUCTION BASELINE"
            justification = (
                "Established production candidate baseline (Brier: {:.4f}, ECE: {:.4f}, Acc: {:.1f}%).".format(
                    brier, ece, acc * 100
                )
            )
        else:
            delta_brier = brier - base_brier
            delta_ece = ece - base_ece

            # Rule 11 & Transparency promotion criteria:
            # Because upper-air shear, 850/200hPa winds, humidity, and SST are UNAVAILABLE in the archive,
            # surface environmental features are classified as EXPERIMENTAL / PROVISIONAL.
            # They provide valuable physical telemetry for operators but do not displace A0 as production baseline.
            status = "EXPERIMENTAL"
            verdict = "CLASSIFIED AS EXPERIMENTAL (A0 RETAINED AS OPERATIONAL BASELINE)"
            justification = (
                f"Pilot test on held-out MICHAUNG yields delta Brier: {delta_brier:+.4f}, delta ECE: {delta_ece:+.4f}. "
                f"Because upper-air shear and mid-level humidity are UNAVAILABLE in the local single-level archive, "
                f"surface environmental metrics are designated EXPERIMENTAL per Rule 11. Baseline A0 remains operational."
            )

        results[model_id] = AblationMetrics(
            model_id=model_id,
            model_name=model_id.replace("_", " "),
            feature_count=X_tr.shape[1],
            features_list=f_cols + (["spread_x_asymmetry", "gradient_x_speed"] if is_a2 else []),
            brier_score=round(brier, 5),
            ece=round(ece, 5),
            accuracy=round(acc, 4),
            earliest_warning_lead_hours=None,
            delta_brier_vs_a0=round(delta_brier, 5),
            delta_ece_vs_a0=round(delta_ece, 5),
            status=status,
            promotion_verdict=verdict,
            scientific_justification=justification,
            probabilities=[round(float(p), 4) for p in probs],
            predictions=[int(p) for p in preds],
        )

        print(f"\n[{model_id}] (n_features={X_tr.shape[1]}):")
        print(f"  Brier Score : {brier:.4f} (delta vs A0: {delta_brier:+.4f})")
        print(f"  ECE         : {ece:.4f} (delta vs A0: {delta_ece:+.4f})")
        print(f"  Accuracy    : {acc*100:.1f}%")
        print(f"  Status      : {status}")
        print(f"  Verdict     : {verdict}")

    # 7. Compile authoritative study report
    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "task": "SIH26079: Atmospheric Conditioning Feature Ablation",
        "phase": "Attempt 5 — Scientific Physical Conditioning",
        "training_sample_size": len(train_records),
        "test_sample_size": len(test_records),
        "held_out_cyclone": "MICHAUNG (December 2023)",
        "atmospheric_variable_audit": {k: v.to_dict() for k, v in ATMOSPHERIC_VARIABLE_AUDIT.items()},
        "baseline_model_id": "A0_Baseline_M6",
        "ablation_models": {k: v.to_dict() for k, v in results.items()},
        "promotion_decision": {
            "operational_production_model": "A0_Baseline_M6",
            "environmental_features_status": "EXPERIMENTAL",
            "scientific_rationale": (
                "Surface MSLP environmental pressure features (annulus depth, radial gradient, asymmetry) "
                "provide auditable physical conditioning for operator situational awareness. However, deep-layer shear "
                "and mid-tropospheric humidity remain unavailable in the local TIGGE archive. Per AGENTS.md Rule 11, "
                "A0 is retained as the production scoring baseline while environmental features are exposed as EXPERIMENTAL."
            ),
        },
    }

    out_json = data_dir / "atmospheric_ablation_results.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\nSaved Authoritative Ablation Results Artifact: {out_json.name} ({out_json.stat().st_size} bytes)")
    return report


if __name__ == "__main__":
    run_atmospheric_ablation()
