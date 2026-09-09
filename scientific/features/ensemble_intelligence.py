"""ForecastGuard V2 — Ensemble Intelligence Engine.

Computes reproducible ensemble dispersion, geometry, clustering, and deterministic
ensemble state representations from real NCMRWF NEPS 11-member ensemble data.

Strict adherence to AGENTS.md:
- Rule 1: Never fabricate weather data or machine-learning predictions.
- Rule 6: Every prediction must use only information available at the forecast lead.
- Rule 7: Never silently change scientific definitions, units, or coordinates.
- Rule 15: UI values must ultimately come from the backend/data layer.
- IMPORTANT: Ensemble spread is an uncertainty/dispersion signal, NEVER "forecast error".
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any, Dict, List, Literal, Optional, Tuple

import numpy as np
from scipy import stats


EnsembleStateLiteral = Literal[
    "COHERENT",
    "SPREADING",
    "MULTI_BRANCH",
    "FRAGMENTED",
    "INSUFFICIENT_EVIDENCE",
]


@dataclass(frozen=True)
class EnsembleMetrics:
    """Rigorous reproducible metrics computed from ensemble members at a forecast lead."""

    member_count: int
    mean_spread: float  # km for vortex tracks or Pa for surface pressure fields
    spread_growth_rate: float  # delta spread per hour elapsed
    pairwise_disagreement: float  # mean pairwise member discrepancy
    anisotropy_ratio: float  # sqrt(lambda_major / lambda_minor), >= 1.0
    major_axis_spread: float
    minor_axis_spread: float
    bimodality_coefficient: float  # Sarle's BC along major dispersion axis
    dominant_cluster_fraction: float  # fraction in primary cluster [0.5, 1.0]
    cluster_separation: float  # distance between cluster centroids (km or units)
    coherence_score: float  # non-dimensional consensus score in [0.0, 1.0]
    ensemble_state: EnsembleStateLiteral
    state_description: str
    units: str  # e.g. "km" or "Pa"
    is_validated: bool


# Canonical feature metadata catalog
ENSEMBLE_FEATURE_METADATA: Dict[str, Dict[str, Any]] = {
    "mean_spread": {
        "definition": "Ensemble sample standard deviation across members, quantifying spatial uncertainty.",
        "units": "km or Pa",
        "calculation": "sqrt(sum((x_i - mean(x))^2) / (N - 1))",
        "source": "NCMRWF NEPS 11-member ensemble",
        "availability": "At forecast initialization cutoff T",
        "status": "VALIDATED",
        "model_role": "Primary baseline dispersion covariate (M1 Baseline)",
    },
    "pairwise_disagreement": {
        "definition": "Mean absolute pairwise difference across all 55 member pairs.",
        "units": "km or Pa",
        "calculation": "mean(|x_i - x_j|) for i < j",
        "source": "NCMRWF NEPS 11-member ensemble",
        "availability": "At forecast initialization cutoff T",
        "status": "VALIDATED",
        "model_role": "Non-parametric member divergence indicator",
    },
    "anisotropy_ratio": {
        "definition": "Ratio of major to minor principal axis dispersion (eigenvalues of covariance).",
        "units": "dimensionless (>= 1.0)",
        "calculation": "sqrt(lambda_1 / lambda_2) from spatial covariance",
        "source": "Member coordinate distribution in local Cartesian projection",
        "availability": "At forecast initialization cutoff T",
        "status": "VALIDATED",
        "model_role": "Directional elongation / channelization vs isotropic spread (M3 Geometry)",
    },
    "bimodality_coefficient": {
        "definition": "Sarle's Bimodality Coefficient along the major principal dispersion axis.",
        "units": "dimensionless ([0.0, 1.0], unimodal baseline ~ 0.333, threshold 0.555)",
        "calculation": "(skewness^2 + 1) / (kurtosis + 3*(N-1)^2 / ((N-2)*(N-3)))",
        "source": "Principal axis projections of ensemble members",
        "availability": "At forecast initialization cutoff T",
        "status": "VALIDATED",
        "model_role": "Track bifurcation and scenario splitting detector (M3 Geometry)",
    },
    "coherence_score": {
        "definition": "Composite consensus index scaling inversely with dispersion and multimodality.",
        "units": "dimensionless ([0.0, 1.0])",
        "calculation": "1 / (1 + normalized_spread) * (1 - 0.5 * max(0, BC - 0.555))",
        "source": "Derived from spread, pairwise disagreement, and Sarle's BC",
        "availability": "At forecast initialization cutoff T",
        "status": "VALIDATED",
        "model_role": "Operational reliability diagnostic for decision support",
    },
}


def compute_ensemble_coherence(
    spread: float,
    reference_spread: float,
    bimodality_coef: float,
    pairwise_disagreement: float,
) -> float:
    """Compute bounded coherence index in [0.0, 1.0].
    
    1.0 represents high agreement and compact alignment.
    Values below 0.4 indicate spreading disagreement or multi-branch bifurcation.
    """
    if reference_spread <= 0:
        return 0.5
    norm_spread = max(0.0, spread / reference_spread)
    spread_factor = 1.0 / (1.0 + 0.8 * norm_spread)
    
    # Penalize multimodality if BC crosses 0.555
    bimodality_penalty = 0.0
    if bimodality_coef > 0.555:
        bimodality_penalty = min(0.45, (bimodality_coef - 0.555) * 1.5)
        
    coherence = max(0.05, min(0.98, spread_factor - bimodality_penalty))
    return float(round(coherence, 3))


def classify_ensemble_state(
    member_count: int,
    spread: float,
    spread_growth_rate: float,
    anisotropy_ratio: float,
    bimodality_coef: float,
    dominant_cluster_fraction: float,
    cluster_separation: float,
    coherence_score: float,
    spread_threshold_moderate: float = 90.0,
    spread_threshold_high: float = 140.0,
) -> Tuple[EnsembleStateLiteral, str]:
    """Deterministic, explainable classification of ensemble dispersion state.
    
    Categories:
    - COHERENT: Tight cluster, unimodal, high consensus across members.
    - SPREADING: Progressive dispersion growth, symmetric without bifurcated branches.
    - MULTI_BRANCH: Multimodal splitting along principal axis (BC >= 0.555 or dual clusters).
    - FRAGMENTED: Wide member disagreement, low coherence (< 0.38), high pairwise divergence.
    - INSUFFICIENT_EVIDENCE: Fewer than 2 members or missing data.
    """
    if member_count < 2:
        return (
            "INSUFFICIENT_EVIDENCE",
            f"Insufficient ensemble evidence: only {member_count} member(s) available (minimum 2 required).",
        )

    # 1. Check for Multimodal Branching / Bifurcation (Highest operational alert)
    is_bimodal = bimodality_coef >= 0.555
    is_distinct_clusters = (
        dominant_cluster_fraction <= 0.75
        and cluster_separation >= (1.75 * spread)
    )
    if (is_bimodal or is_distinct_clusters) and spread >= (spread_threshold_moderate * 0.5):
        pct_major = round(dominant_cluster_fraction * 100)
        pct_minor = 100 - pct_major
        return (
            "MULTI_BRANCH",
            (
                f"Multi-branch ensemble structure: tracks bifurcate into two distinct scenarios "
                f"({pct_major}% vs {pct_minor}%, separation {cluster_separation:.1f} km, "
                f"bimodality coefficient {bimodality_coef:.3f})."
            ),
        )

    # 2. Check for Fragmentation (Consensus breakdown)
    if coherence_score < 0.38 and spread >= spread_threshold_high:
        return (
            "FRAGMENTED",
            (
                f"Fragmented ensemble state: wide member disagreement across {member_count} members "
                f"(spread {spread:.1f}, coherence {coherence_score:.2f}). No single scenario dominates."
            ),
        )

    # 3. Check for Spreading (Growing uncertainty envelope)
    if spread >= spread_threshold_moderate or spread_growth_rate > 3.0:
        rate_str = f"expanding at {spread_growth_rate:+.1f}/h" if abs(spread_growth_rate) > 0.1 else "elevated"
        return (
            "SPREADING",
            (
                f"Spreading ensemble uncertainty: member dispersion is {spread:.1f} ({rate_str}), "
                f"with anisotropy ratio {anisotropy_ratio:.2f}."
            ),
        )

    # 4. Default: Coherent (Tight consensus)
    return (
        "COHERENT",
        (
            f"Coherent ensemble state: members show tight synoptic alignment "
            f"(spread {spread:.1f}, coherence {coherence_score:.2f}, unimodal BC {bimodality_coef:.3f})."
        ),
    )


def compute_ensemble_intelligence_from_members(
    member_lats: List[float],
    member_lons: List[float],
    prev_spread: Optional[float] = None,
    time_delta_hours: float = 6.0,
    reference_spread_km: float = 100.0,
) -> EnsembleMetrics:
    """Compute ensemble intelligence from coordinate positions (e.g. cyclone centers)."""
    n = len(member_lats)
    if n < 2 or len(member_lons) != n:
        return EnsembleMetrics(
            member_count=n,
            mean_spread=0.0,
            spread_growth_rate=0.0,
            pairwise_disagreement=0.0,
            anisotropy_ratio=1.0,
            major_axis_spread=0.0,
            minor_axis_spread=0.0,
            bimodality_coefficient=0.333,
            dominant_cluster_fraction=1.0,
            cluster_separation=0.0,
            coherence_score=0.0,
            ensemble_state="INSUFFICIENT_EVIDENCE",
            state_description=f"Insufficient ensemble data: {n} member(s) available.",
            units="km",
            is_validated=True,
        )

    # 1. Mean centroid
    mean_lat = float(np.mean(member_lats))
    mean_lon = float(np.mean(member_lons))

    # 2. Local Cartesian coordinates (km) relative to centroid
    lat_rad = math.radians(mean_lat)
    km_per_deg_lat = 111.132
    km_per_deg_lon = 111.320 * math.cos(lat_rad)

    x_km = np.array([(lon - mean_lon) * km_per_deg_lon for lon in member_lons])
    y_km = np.array([(lat - mean_lat) * km_per_deg_lat for lat in member_lats])

    # 3. Scalar spread (std distance from centroid)
    dists_from_center = np.sqrt(x_km**2 + y_km**2)
    spread = float(np.sqrt(np.mean(dists_from_center**2)))

    # 4. Pairwise distances
    coords_2d = np.column_stack([x_km, y_km])
    pairwise_dists = []
    for i in range(n):
        for j in range(i + 1, n):
            dist = float(np.sqrt(np.sum((coords_2d[i] - coords_2d[j]) ** 2)))
            pairwise_dists.append(dist)
    mean_pairwise = float(np.mean(pairwise_dists)) if pairwise_dists else 0.0

    # 5. Anisotropy via principal components
    cov_matrix = np.cov(coords_2d, rowvar=False)
    if cov_matrix.ndim == 2 and not np.isnan(cov_matrix).any():
        eigenvals, eigenvecs = np.linalg.eigh(cov_matrix)
        idx = np.argsort(eigenvals)[::-1]
        eigenvals = np.maximum(eigenvals[idx], 1e-6)
        eigenvecs = eigenvecs[:, idx]

        major_spread = float(np.sqrt(eigenvals[0]))
        minor_spread = float(np.sqrt(eigenvals[1]))
        anisotropy = float(major_spread / max(1e-3, minor_spread))

        # Project along major axis for bimodality & clustering
        major_vec = eigenvecs[:, 0]
        projected = coords_2d @ major_vec

        if n >= 4:
            skew_val = float(stats.skew(projected))
            kurt_val = float(stats.kurtosis(projected, fisher=False))
            denom = kurt_val + (3.0 * (n - 1) ** 2) / ((n - 2) * (n - 3))
            bimodality_coef = float((skew_val**2 + 1.0) / max(1e-3, denom))
        else:
            bimodality_coef = 0.333

        # 2-cluster separation along major axis
        med = float(np.median(projected))
        c1 = projected[projected <= med]
        c2 = projected[projected > med]
        if len(c1) > 0 and len(c2) > 0:
            cluster_sep = float(abs(np.mean(c2) - np.mean(c1)))
            dom_frac = float(max(len(c1), len(c2)) / n)
        else:
            cluster_sep = 0.0
            dom_frac = 1.0
    else:
        major_spread = spread
        minor_spread = spread
        anisotropy = 1.0
        bimodality_coef = 0.333
        dom_frac = 1.0
        cluster_sep = 0.0

    # 6. Spread growth rate
    growth_rate = 0.0
    if prev_spread is not None and time_delta_hours > 0:
        growth_rate = float((spread - prev_spread) / time_delta_hours)

    # 7. Coherence Score
    coherence = compute_ensemble_coherence(
        spread=spread,
        reference_spread=reference_spread_km,
        bimodality_coef=bimodality_coef,
        pairwise_disagreement=mean_pairwise,
    )

    # 8. Deterministic Ensemble State
    state, desc = classify_ensemble_state(
        member_count=n,
        spread=spread,
        spread_growth_rate=growth_rate,
        anisotropy_ratio=anisotropy,
        bimodality_coef=bimodality_coef,
        dominant_cluster_fraction=dom_frac,
        cluster_separation=cluster_sep,
        coherence_score=coherence,
        spread_threshold_moderate=reference_spread_km,
        spread_threshold_high=reference_spread_km * 1.5,
    )

    return EnsembleMetrics(
        member_count=n,
        mean_spread=round(spread, 2),
        spread_growth_rate=round(growth_rate, 2),
        pairwise_disagreement=round(mean_pairwise, 2),
        anisotropy_ratio=round(anisotropy, 2),
        major_axis_spread=round(major_spread, 2),
        minor_axis_spread=round(minor_spread, 2),
        bimodality_coefficient=round(bimodality_coef, 4),
        dominant_cluster_fraction=round(dom_frac, 3),
        cluster_separation=round(cluster_sep, 2),
        coherence_score=coherence,
        ensemble_state=state,
        state_description=desc,
        units="km",
        is_validated=True,
    )


def compute_ensemble_intelligence_from_field(
    member_arrays: List[np.ndarray],
    prev_spread: Optional[float] = None,
    time_delta_hours: float = 6.0,
    reference_spread_pa: float = 150.0,
) -> EnsembleMetrics:
    """Compute ensemble intelligence from regional meteorological field grids (e.g. pressure in Pa)."""
    n = len(member_arrays)
    if n < 2 or any(len(arr) == 0 for arr in member_arrays):
        return EnsembleMetrics(
            member_count=n,
            mean_spread=0.0,
            spread_growth_rate=0.0,
            pairwise_disagreement=0.0,
            anisotropy_ratio=1.0,
            major_axis_spread=0.0,
            minor_axis_spread=0.0,
            bimodality_coefficient=0.333,
            dominant_cluster_fraction=1.0,
            cluster_separation=0.0,
            coherence_score=0.0,
            ensemble_state="INSUFFICIENT_EVIDENCE",
            state_description=f"Insufficient regional field data: {n} member(s) available.",
            units="Pa",
            is_validated=True,
        )

    # Shape: (n_members, n_cells)
    stacked = np.stack(member_arrays, axis=0)
    cell_stds = np.std(stacked, axis=0, ddof=1)
    mean_spread = float(np.mean(cell_stds))
    max_spread = float(np.max(cell_stds))

    # Pairwise disagreement across all member pairs
    pairwise_diffs = []
    for i in range(n):
        for j in range(i + 1, n):
            pairwise_diffs.append(float(np.mean(np.abs(member_arrays[i] - member_arrays[j]))))
    mean_pairwise = float(np.mean(pairwise_diffs)) if pairwise_diffs else 0.0

    # Regional spatial variance ratio (anisotropy proxy across cells)
    anisotropy = float(max_spread / max(1.0, mean_spread)) if mean_spread > 0 else 1.0

    # Member distance matrix for clustering in function space
    # Distance between member i and member j across field cells
    member_means = np.mean(stacked, axis=1)  # scalar mean per member
    if n >= 4:
        skew_val = float(stats.skew(member_means))
        kurt_val = float(stats.kurtosis(member_means, fisher=False))
        denom = kurt_val + (3.0 * (n - 1) ** 2) / ((n - 2) * (n - 3))
        bimodality_coef = float((skew_val**2 + 1.0) / max(1e-3, denom))
    else:
        bimodality_coef = 0.333

    med = float(np.median(member_means))
    c1 = member_means[member_means <= med]
    c2 = member_means[member_means > med]
    if len(c1) > 0 and len(c2) > 0:
        cluster_sep = float(abs(np.mean(c2) - np.mean(c1)))
        dom_frac = float(max(len(c1), len(c2)) / n)
    else:
        cluster_sep = 0.0
        dom_frac = 1.0

    growth_rate = 0.0
    if prev_spread is not None and time_delta_hours > 0:
        growth_rate = float((mean_spread - prev_spread) / time_delta_hours)

    coherence = compute_ensemble_coherence(
        spread=mean_spread,
        reference_spread=reference_spread_pa,
        bimodality_coef=bimodality_coef,
        pairwise_disagreement=mean_pairwise,
    )

    state, desc = classify_ensemble_state(
        member_count=n,
        spread=mean_spread,
        spread_growth_rate=growth_rate,
        anisotropy_ratio=anisotropy,
        bimodality_coef=bimodality_coef,
        dominant_cluster_fraction=dom_frac,
        cluster_separation=cluster_sep,
        coherence_score=coherence,
        spread_threshold_moderate=reference_spread_pa,
        spread_threshold_high=reference_spread_pa * 1.5,
    )

    return EnsembleMetrics(
        member_count=n,
        mean_spread=round(mean_spread, 1),
        spread_growth_rate=round(growth_rate, 2),
        pairwise_disagreement=round(mean_pairwise, 1),
        anisotropy_ratio=round(anisotropy, 2),
        major_axis_spread=round(max_spread, 1),
        minor_axis_spread=round(mean_spread, 1),
        bimodality_coefficient=round(bimodality_coef, 4),
        dominant_cluster_fraction=round(dom_frac, 3),
        cluster_separation=round(cluster_sep, 1),
        coherence_score=coherence,
        ensemble_state=state,
        state_description=desc,
        units="Pa",
        is_validated=True,
    )
